#!/usr/bin/env python3
"""Real PostgreSQL cdm_reader proof for NEW_ONLY pre-COMMIT safety gate.

Synthetic payloads are for permission/collision checks only; their invented S3
URIs are NOT verified source publications and may NEVER authorize COMMIT.
No S3 writes, no OMOP writes, no batch claims.
"""
from __future__ import annotations
import os
import psycopg

from task004_cdm_materialization_plan import plan
from task004_cdm_dynamic_adapters import digest
from precommit_gate import inspect_new_only,PrecommitBlocked


def make_plan(batch:str):
    p="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+batch+"/"
    return plan({"state":"HANDOFF_VERIFIED_NOT_LOADED","cdm_write_permitted":False,
        "batch_id":batch,"manifest_sha256":"a"*64,"source_version":"v3.3.0",
        "manifest_uri":"s3://health-landing/"+p+"manifest.json",
        "person_processing_uri":"s3a://health-processing/"+p+"entity=patient/run_id=read-only-preflight/data/",
        "visit_processing_uri":"s3a://health-processing/"+p+"entity=encounter/run_id=read-only-preflight/data/",
        "person_rows":1,"visit_rows":1})


def row(source_key,kind,parent=None):
    payload={"gender_concept_id":8507} if kind=="person" else {"visit_concept_id":9202}
    v={"source_key":source_key,"canonical_payload":payload}
    if kind=="visit":
        v["source_person_key"]=parent
    v["row_fingerprint"]=digest({"source_person_key":parent,"payload":payload})
    return v


def main():
    with psycopg.connect(
        host=os.environ["PGHOST"],port=os.environ.get("PGPORT","5432"),
        dbname="omop", user=os.environ["PGUSER"],password=os.environ["PGPASSWORD"],
        connect_timeout=8,
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    ) as db:
        db.read_only=True
        with db.cursor() as cur:
            cur.execute("SELECT source_person_id FROM etl.person_id_map WHERE source_system='synthea' ORDER BY person_id LIMIT 1")
            record=cur.fetchone()
            if record is None:
                raise RuntimeError("BLOCKED:NEED_EXISTING_PERSON_MAPPING_FOR_NEGATIVE_TEST")
            actual_historic_key=record[0]
            cur.execute("SELECT count(*) FROM cdm.person")
            baseline_person=cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM cdm.visit_occurrence")
            baseline_visit=cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM etl.landing_batch_ledger")
            baseline_claim=cur.fetchone()[0]

        batch="task004-airflow-precommit-probe-"+os.environ["GITHUB_PROBE_RUN_ID"]
        # No real generation with this probe batch ID. It must never be COMMITted.
        proposed=make_plan(batch)
        people=[row("read-only-fresh-test-"+os.environ["GITHUB_PROBE_RUN_ID"],"person")]
        visits=[row("read-only-visit-test-"+os.environ["GITHUB_PROBE_RUN_ID"],
                    "visit",people[0]["source_key"])]

        allow=inspect_new_only(db,proposed,people,visits)
        if allow.status!="READY_TO_CLAIM" or allow.commit_authorized:
            raise RuntimeError("BLOCKED:PRECOMMIT_NOT_SAFE")
        print("REAL_PG_FRESH_SOURCE_PREFLIGHT=PASS",flush=True)

        try:
            inspect_new_only(db,proposed,[row(actual_historic_key,"person")],
                            visits)
        except PrecommitBlocked as exc:
            if str(exc)!="BLOCKED:VISIT_PARENT_NOT_IN_BATCH":
                raise
            # Parent gate must reject malformed batches before querying PG.
        else:
            raise RuntimeError("BLOCKED:INVALID_PARENT_ACCEPTED")
        colliding_visits=[row("read-only-collision-visit","visit",actual_historic_key)]
        try:
            inspect_new_only(db,proposed,[row(actual_historic_key,"person")],
                            colliding_visits)
        except PrecommitBlocked as exc:
            if str(exc)!="BLOCKED:NEW_ONLY_SOURCE_KEY_COLLISION":
                raise
        else:
            raise RuntimeError("BLOCKED:HISTORICAL_PERSON_COLLISION_ACCEPTED")
        print("REAL_PG_EXISTING_PERSON_SOURCE_BLOCKED=PASS",flush=True)

        try:
            inspect_new_only(db,proposed,people,visits,require_claim=True)
        except PrecommitBlocked as exc:
            if str(exc)!="BLOCKED:LIVE_EXCLUSIVE_CLAIM_REQUIRED":
                raise
        else:
            raise RuntimeError("BLOCKED:UNCLAIMED_BATCH_ACCEPTED")
        print("REAL_PG_UNCLAIMED_COMMIT_BLOCKED=PASS",flush=True)

        old=make_plan("task004-airflow-task004-step03e-38324111846")
        try:
            inspect_new_only(db,old,people,visits)
        except PrecommitBlocked as exc:
            if str(exc)!="BLOCKED:HISTORIC_BATCH_ALREADY_REGISTERED":
                raise
        else:
            raise RuntimeError("BLOCKED:LEGACY_BATCH_ACCEPTED")
        print("REAL_PG_HISTORICAL_BATCH_BLOCKED=PASS",flush=True)

        with db.cursor() as cur:
            cur.execute("SELECT count(*) FROM cdm.person")
            assert cur.fetchone()[0]==baseline_person
            cur.execute("SELECT count(*) FROM cdm.visit_occurrence")
            assert cur.fetchone()[0]==baseline_visit
            cur.execute("SELECT count(*) FROM etl.landing_batch_ledger")
            assert cur.fetchone()[0]==baseline_claim
        db.rollback()
    print("REAL_PG_READONLY_PRECOMMIT=PASS",flush=True)
    print("DATABASE_MUTATION=NO",flush=True)


if __name__=="__main__":
    main()
