#!/usr/bin/env python3
"""Build an immutable, no-COMMIT plan from one explicitly pinned S3 batch.

Input must originate from separately verified S3 READY + Spark Processing.
This utility does not call S3, PostgreSQL, Airflow or Synthea. Runtime source
verification MUST re-read S3 Manifest and exact Parquet and enforce row counts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from task004_cdm_materialization_plan import plan

def build(
    *, batch_id: str, manifest_uri: str, manifest_sha256: str,
    person_processing_uri: str, visit_processing_uri: str,
    person_rows: int, visit_rows: int, source_version: str = "v3.3.0",
) -> dict:
    if any(isinstance(n, bool) or not isinstance(n, int) for n in (person_rows, visit_rows)):
        raise ValueError("BLOCKED=invalid_processing_row_counts")
    payload = dict(
        batch_id=batch_id, manifest_uri=manifest_uri, manifest_sha256=manifest_sha256,
        person_processing_uri=person_processing_uri, visit_processing_uri=visit_processing_uri,
        person_rows=person_rows, visit_rows=visit_rows, source_version=source_version,
        state="HANDOFF_VERIFIED_NOT_LOADED", cdm_write_permitted=False,
    )
    ctx=plan(payload)
    if ctx["database_mutation_authorized"] is not False:
        raise ValueError("BLOCKED=commit_authorization")
    if ctx["load_order"] != ["person","visit","db_reconcile"]:
        raise ValueError("BLOCKED=load_order")
    return ctx

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batch-id",required=True)
    p.add_argument("--manifest-uri",required=True)
    p.add_argument("--manifest-sha256",required=True)
    p.add_argument("--person-processing-uri",required=True)
    p.add_argument("--visit-processing-uri",required=True)
    p.add_argument("--person-rows",type=int,required=True)
    p.add_argument("--visit-rows",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    ctx=build(**{
        "batch_id":a.batch_id,"manifest_uri":a.manifest_uri,
        "manifest_sha256":a.manifest_sha256,
        "person_processing_uri":a.person_processing_uri,
        "visit_processing_uri":a.visit_processing_uri,
        "person_rows":a.person_rows,"visit_rows":a.visit_rows,
    })
    output=Path(a.output)
    output.write_text(json.dumps(ctx,sort_keys=True)+"\n",encoding="utf8")
    print("OMOP_IMMUTABLE_S3_ROLLBACK_PLAN=PASS",flush=True)
    print("OMOP_PLAN_COMMIT_AUTHORIZED=NO",flush=True)

if __name__=="__main__":
    main()
