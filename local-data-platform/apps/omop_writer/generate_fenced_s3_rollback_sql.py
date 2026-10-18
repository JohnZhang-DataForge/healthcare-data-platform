#!/usr/bin/env python3
"""Generate real S3 Person+Visit, same-PG-transaction fenced ROLLBACK SQL.

This bounded one-shot demo uses real immutable Parquet and the actual effective
cdm_writer role. Because the real NEW_ONLY READY batch is deliberately unclaimed,
a TEMPORARY Claim ledger fixture for that actual batch is inserted by admin in
the SAME transaction, then SET LOCAL ROLE cdm_writer. The Claim fixture and all
business DML are rolled back together. No auto Claim and no business COMMIT.
NOT a production Claim/COMMIT executor; never wire it to Airflow.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets

from joint_s3_rollback import compose_joint_rollback, for_psycopg, s3_rows, verified_plan


def _q(value: str) -> str:
    if not isinstance(value, str) or "\\" in value or "\x00" in value:
        raise ValueError("BLOCKED:FENCE_SQL_LITERAL")
    return "'" + value.replace("'", "''") + "'"


def generate_rollback_sql(context: dict, people: list, visits: list,
                          owner: str) -> str:
    plan=verified_plan(context)
    if not isinstance(owner,str) or len(owner)!=48 or any(c not in "0123456789abcdef" for c in owner):
        raise ValueError("BLOCKED:FENCE_OWNER_SHAPE")
    if plan["batch_id"]!="synthea-new-only-gh-38497355290" or plan["person_rows"]!=1 or plan["visit_rows"]!=812:
        raise ValueError("BLOCKED:FENCE_DEMO_BATCH_BOUNDS")
    if len(people)!=1 or len(visits)!=812:
        raise ValueError("BLOCKED:FENCE_REAL_S3_COUNTS")
    joint=for_psycopg(compose_joint_rollback(plan,people,visits))
    if not joint.startswith("BEGIN;\n") or not joint.endswith("ROLLBACK;\n"):
        raise ValueError("BLOCKED:FENCE_JOINT_SHELL")
    body=joint[len("BEGIN;\n"):-len("ROLLBACK;\n")]
    if "COMMIT;" in body:
        raise ValueError("BLOCKED:FENCE_COMMIT_SQL")
    b,uri,sha=(_q(plan[x]) for x in ("batch_id","manifest_uri","manifest_sha256"))
    tok=_q(owner)
    fence=f"SELECT task004_writer_fence.assert_active_claim('synthea',{b},{sha},{uri},{tok},1);"
    return f"""\\set ON_ERROR_STOP on
-- DEMO PROBE: one transaction, never persist a real Claim or OMOP rows.
BEGIN;
SET LOCAL lock_timeout='2500ms';
SET LOCAL statement_timeout='120s';
DO $before$
BEGIN
 IF current_user <> 'omop_admin'
 OR EXISTS (SELECT 1 FROM etl.landing_batch_ledger
            WHERE source_system='synthea' AND batch_id={b})
 OR EXISTS (SELECT 1 FROM etl.task004_batch_ledger WHERE batch_id={b})
 THEN RAISE EXCEPTION 'BLOCKED:REAL_READY_NOT_UNCLAIMED_OR_ADMIN'; END IF;
END $before$;
-- This is the only synthetic Claim fixture. It remains uncommitted throughout.
INSERT INTO etl.landing_batch_ledger
 (source_system,batch_id,manifest_sha256,manifest_uri,
  status,attempt_count,lease_owner,lease_expires_at)
VALUES ('synthea',{b},{sha},{uri},
        'PROCESSING',1,{tok},clock_timestamp()+interval '30 minutes');
SET LOCAL ROLE cdm_writer;
DO $role$
BEGIN
 IF current_user <> 'cdm_writer'
 OR has_table_privilege(current_user,'etl.landing_batch_ledger','SELECT')
 OR has_table_privilege(current_user,'etl.landing_batch_ledger','UPDATE')
 THEN RAISE EXCEPTION 'BLOCKED:FENCED_WRITER_ROLE_PRIVILEGE'; END IF;
END $role$;
{fence}
\\echo REAL_S3_FENCE_BEFORE_PERSON_VISIT=PASS
{body}
{fence}
\\echo REAL_S3_FENCE_AFTER_PERSON_VISIT=PASS
-- Explicit unconditional rollback; a psql error also aborts its connection.
ROLLBACK;
SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM etl.landing_batch_ledger
                           WHERE source_system='synthea' AND batch_id={b})
 THEN 'REAL_S3_FENCED_ROLLBACK_CLAIM_ABSENT=PASS'
 ELSE 'REAL_S3_FENCED_ROLLBACK_CLAIM_ABSENT=FAIL' END;
\\echo REAL_S3_FENCED_PERSON_VISIT_PG_ROLLBACK=PASS
\\echo REAL_S3_READY_CLAIM_PERSISTED=NO
\\echo OMOP_BUSINESS_COMMIT=NO
"""


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan-file",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    import json
    context=json.loads(Path(args.plan_file).read_text())
    plan=verified_plan(context)
    people,visits=s3_rows(plan)
    owner=secrets.token_hex(24)
    sql=generate_rollback_sql(context,people,visits,owner)
    out=Path(args.output)
    if not out.parent.is_dir() or out.exists():
        raise ValueError("BLOCKED:FENCE_OUTPUT_ALREADY_EXISTS")
    out.write_text(sql,encoding="utf-8")
    os.chmod(out,0o600)
    print("FENCED_REAL_S3_PERSON=1",flush=True)
    print("FENCED_REAL_S3_VISIT=812",flush=True)
    print("FENCED_REAL_SQL_NO_COMMIT=PASS",flush=True)


if __name__=="__main__":
    main()
