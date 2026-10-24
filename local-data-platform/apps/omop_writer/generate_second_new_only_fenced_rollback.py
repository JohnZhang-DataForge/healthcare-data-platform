#!/usr/bin/env python3
"""ONLY bounded TASK004 second NEW_ONLY 70/11487 Fenced Writer ROLLBACK.

Reads a completed Airflow Spark Writer Handoff, performs a fresh S3 Parquet
read and cdm_reader PostgreSQL preflight, then renders the real dynamic
atomic Claim -> fenced Person/Visit -> DB reconciliation statement body.
The exact final single COMMIT is replaced with ROLLBACK. NEVER persists a
Claim or OMOP business row. NOT a deployable Airflow Writer executor.
"""
from __future__ import annotations
import argparse
import json
import os
import secrets
from pathlib import Path

from audit_second_new_only_ready import EXPECTED_BATCH, EXPECTED_SHA
from dynamic_new_only_commit import generate_dynamic_commit_sql
from joint_s3_rollback import verified_plan, s3_rows, connect
from precommit_gate import inspect_new_only
from new_only_omop_writer_handoff import assert_dynamic_handoff


def generate_rollback(handoff: dict, people: list, visits: list, owner: str) -> str:
    if not isinstance(handoff,dict) or not isinstance(handoff.get("plan"),dict):
        raise ValueError("BLOCKED:SECOND_BATCH_HANDOFF_REQUIRED")
    plan=verified_plan(handoff["plan"])
    assert_dynamic_handoff(plan,handoff)
    if (plan["batch_id"],plan["manifest_sha256"],len(people),len(visits)) != (
            EXPECTED_BATCH,EXPECTED_SHA,70,11487):
        raise ValueError("BLOCKED:SECOND_BATCH_ONLY")
    sql=generate_dynamic_commit_sql(plan,people,visits,owner,handoff)
    boundary="\nCOMMIT;\n"
    if (sql.count(boundary)!=1 or
        sum(line.strip().upper()=="BEGIN;" for line in sql.splitlines())!=1 or
        sum(line.strip().upper()=="COMMIT;" for line in sql.splitlines())!=1 or
        sum(line.strip().upper()=="ROLLBACK;" for line in sql.splitlines())!=0 or
        sql.count("SELECT task004_writer_fence.assert_active_claim(")!=3):
        raise ValueError("BLOCKED:SECOND_BATCH_ATOMIC_SQL_BOUNDARIES")
    before,unused=sql.split(boundary,1)
    if "DO $reconcile$" not in before or "DO $complete$" not in before:
        raise ValueError("BLOCKED:SECOND_BATCH_MISSING_DB_RECONCILIATION")
    # The stage, claims and actual CDM inserts all ROLLBACK together.
    # The original post-COMMIT SELECT is deliberately DISCARDED.
    return (before+"\nROLLBACK;\n\\set QUIET 0\n"
            "SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM etl.landing_batch_ledger "
            "WHERE batch_id='"+EXPECTED_BATCH+"') "
            "THEN 'SECOND_NEW_ONLY_CLAIM_ROLLBACK=PASS' "
            "ELSE 'SECOND_NEW_ONLY_CLAIM_ROLLBACK=FAIL' END;\n"
            "\\echo SECOND_NEW_ONLY_REAL_FENCED_JOINT_ROLLBACK=PASS\n"
            "\\echo BUSINESS_COMMIT=NO\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    p=Path(a.handoff)
    if not p.is_file() or p.stat().st_size>131072 or p.stat().st_size<20:
        raise ValueError("BLOCKED:SECOND_BATCH_HANDOFF_FILE")
    handoff=json.loads(p.read_text(encoding="utf-8"))
    if os.environ.get("PGUSER")!="cdm_reader":
        raise ValueError("BLOCKED:READER_ROLE_REQUIRED")
    plan=verified_plan(handoff["plan"])
    assert_dynamic_handoff(plan,handoff)
    if (plan["batch_id"],plan["manifest_sha256"],plan["person_rows"],plan["visit_rows"]) != (
        EXPECTED_BATCH,EXPECTED_SHA,70,11487
    ):
        raise ValueError("BLOCKED:WRONG_SECOND_BATCH")
    people,visits=s3_rows(plan)
    with connect("cdm_reader",readonly=True) as conn:
        conn.read_only=True
        result=inspect_new_only(conn,plan,people,visits,require_claim=False)
        if result.status!="READY_TO_CLAIM" or result.claim_status!="ABSENT" or result.historic_ledger_rows or result.existing_person_keys or result.existing_visit_keys:
            raise ValueError("BLOCKED:SECOND_BATCH_SOURCE_ID_DRIFT")
        conn.rollback()
    sql=generate_rollback(handoff,people,visits,secrets.token_hex(24))
    dest=Path(a.output)
    if not dest.parent.is_dir() or dest.exists():
        raise ValueError("BLOCKED:SECOND_BATCH_OUTPUT_ALREADY_EXISTS")
    dest.write_text(sql,encoding="utf-8")
    os.chmod(dest,0o600)
    print("SECOND_NEW_ONLY_WRITER_SQL_REAL_PERSON=70",flush=True)
    print("SECOND_NEW_ONLY_WRITER_SQL_REAL_VISIT=11487",flush=True)
    print("SECOND_NEW_ONLY_WRITER_SQL_ROLLBACK_ONLY=PASS",flush=True)
    print("SECOND_NEW_ONLY_WRITER_NO_BUSINESS_COMMIT=PASS",flush=True)


if __name__=="__main__":
    main()
