#!/usr/bin/env python3
"""Strict single-transaction NEW_ONLY Person->Visit ROLLBACK from real S3.

This is a diagnostic transaction, never a COMMIT/Claim executor. The only
persistent writes permitted are PostgreSQL sequence nextval() side effects:
ordinary transactional rows are rolled back, but PG sequence values are not.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

from build_s3_rollback_plan import build
from precommit_gate import validate_input, inspect_new_only
from task004_cdm_dynamic_pg_writer import render
from task004_cdm_dynamic_source import read

IDENTITY_VERSION = "synthea-new-only-v1"
PSQL_PREFIX = "\\set ON_ERROR_STOP on\nBEGIN;\n"
ENDING = "ROLLBACK;\n"


def verified_plan(input_data: dict) -> dict:
    if input_data.get("writer_identity_version") != IDENTITY_VERSION:
        raise ValueError("BLOCKED=explicit_new_only_identity_required")
    if input_data.get("database_mutation_authorized") is not False:
        raise ValueError("BLOCKED=unsafe_plan_mutation")
    required = (
        "batch_id", "manifest_uri", "manifest_sha256",
        "person_processing_uri", "visit_processing_uri",
        "person_rows", "visit_rows", "source_version", "writer_identity_version",
    )
    plan = build(**{name: input_data[name] for name in required})
    if plan["plan_sha256"] != input_data.get("plan_sha256"):
        raise ValueError("BLOCKED=immutable_writer_plan_drift")
    return plan


def strip_transaction(sql: str) -> str:
    if not isinstance(sql,str) or not sql.startswith(PSQL_PREFIX) or not sql.endswith(ENDING):
        raise ValueError("BLOCKED=unrecognized_or_commit_sql")
    # Count COMPLETE SQL control lines, not overlapping substrings. A
    # consecutive second BEGIN used to escape a str.count("\\nBEGIN;\\n") gate.
    boundary=[line.strip().upper() for line in sql.splitlines()]
    if (boundary.count("BEGIN;")!=1
        or boundary.count("ROLLBACK;")!=1
        or "COMMIT;" in sql.upper()):
        raise ValueError("BLOCKED=unrecognized_or_commit_sql")
    return sql[len(PSQL_PREFIX):-len(ENDING)]


def compose_joint_rollback(context: dict, people: list, visits: list) -> str:
    """Full Person/Visit renderer checks, one TX, two verified checkpoints."""
    verified = verified_plan(context)
    validate_input(verified, people, visits)
    person_sql = strip_transaction(render(verified, people, "person", allow_commit=False))
    visit_sql = strip_transaction(render(verified, visits, "visit", allow_commit=False))
    if "CREATE TEMP TABLE task004_expected ON COMMIT DROP" not in person_sql:
        raise ValueError("BLOCKED=missing_person_temp_table_contract")
    if "CREATE TEMP TABLE task004_rows ON COMMIT DROP" not in person_sql:
        raise ValueError("BLOCKED=missing_person_row_temp_table_contract")
    # Temp tables cannot be created again in one transaction without explicit
    # DROP, but their CHECKPOINTS and actual mapped Person rows MUST survive
    # until Visit SQL runs. Dropping temps does not remove either checkpoint.
    checkpoint = """
DO $joint_verify$
BEGIN
 IF (SELECT count(*) FROM etl.task004_batch_commit
     WHERE batch_id=%s AND commit_state='VERIFIED'
     AND entity IN ('person','visit'))<>2
 THEN RAISE EXCEPTION 'BLOCKED:JOINT_CHECKPOINTS'; END IF;
 IF (SELECT count(*) FROM etl.task004_batch_stage
     WHERE batch_id=%s)<>%s
 THEN RAISE EXCEPTION 'BLOCKED:JOINT_STAGE_COUNT'; END IF;
 IF NOT EXISTS (SELECT 1 FROM etl.task004_batch_ledger
     WHERE batch_id=%s AND manifest_sha256=%s)
 THEN RAISE EXCEPTION 'BLOCKED:JOINT_LEDGER_DRIFT'; END IF;
END $joint_verify$;
""" % (repr(verified["batch_id"]), repr(verified["batch_id"]),
       len(people)+len(visits), repr(verified["batch_id"]),
       repr(verified["manifest_sha256"]))
    result = (
        PSQL_PREFIX
        + person_sql
        + "\nDROP TABLE task004_expected;\nDROP TABLE task004_rows;\n"
        + visit_sql
        + checkpoint
        + ENDING
    )
    if result.count("\nBEGIN;\n") != 1 or result.count(ENDING) != 1 or "COMMIT;" in result:
        raise ValueError("BLOCKED=joint_rollback_sql_safety")
    return result


def s3_rows(context: dict):
    import boto3
    import pyarrow.parquet as parquet

    endpoint=os.environ.get("TASK004_S3_ENDPOINT_URL","")
    if not endpoint.startswith(("http://","https://")):
        raise ValueError("BLOCKED=missing_s3_endpoint")
    s3=boto3.client("s3",endpoint_url=endpoint)
    def decode(data):
        return parquet.read_table(io.BytesIO(data)).to_pylist()
    people=read(s3,context,"person",decode)
    visits=read(s3,context,"visit",decode)
    validate_input(context,people,visits)
    return people,visits


def connect(principal: str, *, readonly: bool):
    import psycopg
    if os.environ.get("PGUSER") != principal:
        raise ValueError("BLOCKED=postgres_role_boundary")
    for k in ("PGHOST","PGPORT","PGPASSWORD"):
        if not os.environ.get(k):
            raise ValueError("BLOCKED=missing_postgres_"+k)
    opts="-c default_transaction_read_only=on -c statement_timeout=20000" if readonly else "-c statement_timeout=120000"
    return psycopg.connect(
        host=os.environ["PGHOST"],port=os.environ["PGPORT"],
        dbname="omop",user=principal,password=os.environ["PGPASSWORD"],
        connect_timeout=8,autocommit=not readonly,options=opts)


def run(plan_data: dict, mode: str) -> dict:
    context=verified_plan(plan_data)
    people,visits=s3_rows(context)
    if mode=="audit":
        with connect("cdm_reader",readonly=True) as conn:
            conn.read_only=True
            result=inspect_new_only(conn,context,people,visits,require_claim=False)
            if (result.status!="READY_TO_CLAIM" or result.commit_authorized
                or result.claim_status!="ABSENT"
                or result.existing_person_keys or result.existing_visit_keys):
                raise ValueError("BLOCKED=writer_precommit_audit_not_clean")
            conn.rollback()
        print("NEW_ONLY_REAL_S3_PERSON_ROWS="+str(len(people)),flush=True)
        print("NEW_ONLY_REAL_S3_VISIT_ROWS="+str(len(visits)),flush=True)
        print("NEW_ONLY_PRECOMMIT_READER_REAL_PG=PASS",flush=True)
        print("CLAIM_ENABLE=NO",flush=True)
        print("POSTGRESQL_MUTATION=NO",flush=True)
        return {"mode":"audit","rows":len(people)+len(visits)}
    if mode!="rollback":
        raise ValueError("BLOCKED=unsupported_joint_mode")
    sql=compose_joint_rollback(context,people,visits)
    # This deliberately runs TWO entity writers in ONE transaction. The SQL
    # ends in unconditional ROLLBACK. Never accept a COMMIT-enabled flag.
    with connect("cdm_writer",readonly=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            if cur.fetchone()[0]!="cdm_writer":
                raise ValueError("BLOCKED=incorrect_writer_user")
            cur.execute(sql,prepare=False)
        # psycopg closes/commits its outer context, but SQL explicitly
        # ROLLBACKs the multi-statement transaction before it returns.
    print("NEW_ONLY_JOINT_PERSON_ROWS="+str(len(people)),flush=True)
    print("NEW_ONLY_JOINT_VISIT_ROWS="+str(len(visits)),flush=True)
    print("NEW_ONLY_JOINT_PERSON_VISIT_SQL_ROLLBACK=PASS",flush=True)
    print("POSTGRESQL_COMMIT=NO",flush=True)
    print("POSTGRESQL_SEQUENCE_COUNTERS_MAY_ADVANCE=YES",flush=True)
    return {"mode":"rollback","rows":len(people)+len(visits)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan-file",required=True)
    ap.add_argument("--mode",choices=["audit","rollback"],required=True)
    opts=ap.parse_args()
    data=json.loads(Path(opts.plan_file).read_text())
    run(data,opts.mode)


if __name__=="__main__":
    main()
