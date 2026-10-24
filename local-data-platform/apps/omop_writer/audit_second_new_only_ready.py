#!/usr/bin/env python3
"""Task004: real Airflow NEW_ONLY Spark -> S3 Parquet -> PostgreSQL read-only audit.

This tool never claims, writes, stages or commits. It consumes the immutable
Writer Handoff XCom created by a *successful* manual Airflow Spark DagRun,
re-reads both Parquet objects from S3 and verifies the exact writer-bound plan,
row fingerprints, Person/Visit linkage and target database source-key safety.

No mixed-batch, no simulated records, no reopening completed batch.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from joint_s3_rollback import verified_plan, s3_rows, connect
from new_only_omop_writer_handoff import assert_dynamic_handoff
from precommit_gate import inspect_new_only

EXPECTED_BATCH = "synthea-new-only-gh-38489944582"
EXPECTED_SHA = "be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256"
EXPECTED_PERSON = 70
EXPECTED_VISIT = 11487
COMPLETED_BATCH = "synthea-new-only-gh-38497355290"


def audit(handoff: dict) -> dict:
    if not isinstance(handoff, dict) or not isinstance(handoff.get("plan"), dict):
        raise ValueError("BLOCKED:HANDOFF_REQUIRED")
    context = verified_plan(handoff["plan"])
    assert_dynamic_handoff(context, handoff)
    if (context["batch_id"] != EXPECTED_BATCH
            or context["manifest_sha256"] != EXPECTED_SHA
            or context["person_rows"] != EXPECTED_PERSON
            or context["visit_rows"] != EXPECTED_VISIT
            or context["batch_id"] == COMPLETED_BATCH):
        raise ValueError("BLOCKED:NOT_VERIFIED_SECOND_READY")
    if os.environ.get("PGUSER") != "cdm_reader":
        raise ValueError("BLOCKED:READONLY_PRINCIPAL")
    people, visits = s3_rows(context)
    with connect("cdm_reader", readonly=True) as db:
        db.read_only = True
        check = inspect_new_only(db, context, people, visits, require_claim=False)
        if (check.status != "READY_TO_CLAIM"
                or check.claim_status != "ABSENT"
                or check.existing_person_keys != 0
                or check.existing_visit_keys != 0
                or check.historic_ledger_rows != 0
                or check.commit_authorized is not False):
            raise ValueError("BLOCKED:SECOND_READY_PG_SOURCE_COLLISION")
        with db.cursor() as cur:
            cur.execute("SELECT count(*) FROM etl.task004_batch_stage WHERE batch_id=%s",
                        (context["batch_id"],))
            stage_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM etl.task004_batch_commit WHERE batch_id=%s",
                        (context["batch_id"],))
            checkpoint_count = cur.fetchone()[0]
            if stage_count or checkpoint_count:
                raise ValueError("BLOCKED:SECOND_READY_WRITER_ALREADY_STARTED")
            cur.execute("SELECT count(*) FROM etl.landing_batch_ledger WHERE batch_id=%s",
                        (COMPLETED_BATCH,))
            if cur.fetchone() != (1,):
                raise ValueError("BLOCKED:OLD_COMPLETED_CLAIM_ABSENT")
        db.rollback()
    return {
        "status": "NEW_ONLY_SECOND_READY_READONLY_PREFLIGHT_PASS",
        "batch_id": context["batch_id"],
        "manifest_sha256": context["manifest_sha256"],
        "plan_sha256": context["plan_sha256"],
        "person_rows": len(people),
        "visit_rows": len(visits),
        "target_claim": "ABSENT",
        "new_writer_stage_count": 0,
        "new_writer_checkpoint_count": 0,
        "database_mutation": False,
        "spark_replayed": False,
        "writer_commit_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raw = Path(args.handoff)
    if not raw.is_file() or raw.stat().st_size > 131072:
        raise ValueError("BLOCKED:HANDOFF_TOO_LARGE")
    handoff = json.loads(raw.read_text(encoding="utf-8"))
    result = audit(handoff)
    target = Path(args.output)
    if not target.parent.is_dir() or target.exists():
        raise ValueError("BLOCKED:REPORT_NOT_EXCLUSIVE")
    target.write_text(json.dumps(result, sort_keys=True)+"\n", encoding="utf-8")
    os.chmod(target, 0o600)
    print("SECOND_REAL_S3_PERSON_ROWS="+str(result["person_rows"]), flush=True)
    print("SECOND_REAL_S3_VISIT_ROWS="+str(result["visit_rows"]), flush=True)
    print("SECOND_NEW_ONLY_PG_READER_SOURCE_COLLISIONS=0", flush=True)
    print("SECOND_NEW_ONLY_IMMUTABLE_HANDOFF=PASS", flush=True)
    print("SECOND_NEW_ONLY_REAL_S3_PG_READONLY_PREFLIGHT=PASS", flush=True)
    print("BUSINESS_COMMIT=NO",flush=True)
    print("SPARK_RERUN=NO",flush=True)


if __name__ == "__main__":
    main()
