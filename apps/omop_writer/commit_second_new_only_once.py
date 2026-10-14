#!/usr/bin/env python3
"""User-authorized ONE-TIME second NEW_ONLY 70/11487 real business COMMIT.

Only renders a complete SQL file, never opens a write connection. The caller
has to run that SQL once, guarded by the same-session PostgreSQL preconditions.
We revalidate actual immutable Airflow XCom, S3 Parquet and cdm_reader audit;
the SQL itself atomically makes Claim PROCESSING, inserts Person and Visit with
Fencing/Checkpoint/full-row reconciliation, final Claim COMPLETED and COMMIT.

DO NOT invoke twice. If the SQL run errors or the connection drops, ALWAYS
inspect the durable DB state before contemplating any other action.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from audit_second_new_only_ready import (
    audit, EXPECTED_BATCH, EXPECTED_SHA, EXPECTED_PERSON, EXPECTED_VISIT,
)
from dynamic_new_only_commit import generate_dynamic_commit_sql
from joint_s3_rollback import verified_plan, s3_rows
from new_only_omop_writer_handoff import assert_dynamic_handoff


def render_authorized_one_time_commit(handoff: dict, people: list, visits: list,
                                      owner: str) -> str:
    if not isinstance(handoff,dict) or not isinstance(handoff.get("plan"),dict):
        raise ValueError("BLOCKED:SECOND_BATCH_HANDOFF_REQUIRED")
    ctx=verified_plan(handoff["plan"])
    assert_dynamic_handoff(ctx,handoff)
    if (ctx["batch_id"],ctx["manifest_sha256"],len(people),len(visits))!=(
        EXPECTED_BATCH,EXPECTED_SHA,EXPECTED_PERSON,EXPECTED_VISIT
    ):
        raise ValueError("BLOCKED:SECOND_BATCH_EXACT_IDENTITY_REQUIRED")
    sql=generate_dynamic_commit_sql(ctx,people,visits,owner,handoff)
    lines=[line.strip().upper() for line in sql.splitlines()]
    if (lines.count("BEGIN;")!=1 or lines.count("COMMIT;")!=1
        or lines.count("ROLLBACK;")!=0
        or sql.count("\nCOMMIT;\n")!=1
        or sql.count("SELECT task004_writer_fence.assert_active_claim(")!=3
        or sql.count("DO $reconcile$")!=1
        or sql.count("DO $complete$")!=1
        or "BLOCKED:COMMIT_PRECONDITION_NOT_CLEAN" not in sql
        or "BLOCKED:EXISTING_TARGET_DRIFT" not in sql
        or "REAL_NEW_ONLY_BUSINESS_COMMIT_AND_COMPLETED=PASS" not in sql):
        raise ValueError("BLOCKED:SECOND_BATCH_UNSAFE_SQL_TRANSACTION")
    if sql.index("DO $reconcile$")>sql.index("DO $complete$") or (
        sql.index("DO $complete$")>sql.index("\nCOMMIT;\n")
    ):
        raise ValueError("BLOCKED:SECOND_BATCH_WRONG_TX_ORDER")
    # SQL remains exactly the already-rollback-proven shared renderer.
    # Crucially, do not replace the one COMMIT here.
    return sql


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--handoff",required=True)
    ap.add_argument("--output",required=True)
    opts=ap.parse_args()
    if os.environ.get("PGUSER")!="cdm_reader":
        raise ValueError("BLOCKED:SECOND_BATCH_REQUIRES_CDM_READER")
    file=Path(opts.handoff)
    if not file.is_file() or not (20<=file.stat().st_size<=131072):
        raise ValueError("BLOCKED:SECOND_BATCH_HANDOFF_FILE")
    handoff=json.loads(file.read_text(encoding="utf-8"))
    if handoff.get("business_commit_authorized") is not False:
        # A handoff is proof of processing, never a delegated commit grant.
        raise ValueError("BLOCKED:HANDOFF_MUST_NOT_AUTHORIZE_COMMIT")
    # Real source bytes + identity + PG stage/claim/map/fingerprint audit.
    # Only this explicitly user-authorized deployment may execute SQL later.
    proof=audit(handoff)
    if proof["status"]!="NEW_ONLY_SECOND_READY_READONLY_PREFLIGHT_PASS":
        raise ValueError("BLOCKED:SECOND_BATCH_NOT_READY")
    ctx=verified_plan(handoff["plan"])
    people,visits=s3_rows(ctx)
    sql=render_authorized_one_time_commit(
        handoff,people,visits,secrets.token_hex(24),
    )
    path=Path(opts.output)
    if not path.parent.is_dir() or path.exists():
        raise ValueError("BLOCKED:SECOND_BATCH_OUTPUT_NOT_EXCLUSIVE")
    path.write_text(sql,encoding="utf-8")
    os.chmod(path,0o600)
    print("SECOND_COMMIT_REAL_S3_CDM_READER_PREFLIGHT=PASS",flush=True)
    print("SECOND_COMMIT_REAL_PERSON_ROWS=70",flush=True)
    print("SECOND_COMMIT_REAL_VISIT_ROWS=11487",flush=True)
    print("SECOND_COMMIT_SQL_ONE_TRANSACTION=PASS",flush=True)
    print("SECOND_COMMIT_SQL_READY_NOT_YET_EXECUTED=PASS",flush=True)


if __name__=="__main__":
    main()
