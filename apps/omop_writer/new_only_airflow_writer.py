#!/usr/bin/env python3
"""Fail-closed single-batch Airflow NEW_ONLY OMOP atomic Writer.

Executes the same previously verified Claim + Person + Visit + reconciliation
SQL in one PG transaction. No retries, no second COMMIT on ambiguous outcomes.

Requires all of:
- exact manual Airflow commit selection (DAG gate, not trusted here),
- immutable Spark Handoff JSON,
- a separately provisioned K8s commit-enable secret,
- dedicated cdm_reader and omop_admin DB credentials.
This demo uses SET LOCAL ROLE under omop_admin exactly like the two previously
successful one-time business commits; it is not a production least-privilege
multi-login Writer.
"""
from __future__ import annotations
import json
import os
import re
import secrets

from dynamic_new_only_commit import generate_dynamic_commit_sql
from joint_s3_rollback import verified_plan, s3_rows, connect
from new_only_omop_writer_handoff import assert_dynamic_handoff
from precommit_gate import inspect_new_only

COMMITTED_HISTORIC={
    "synthea-new-only-gh-38497355290",
    "synthea-new-only-gh-38489944582",
}
MAX_HANDOFF_BYTES=131072


def load_handoff(raw: str) -> tuple[dict,dict]:
    if not isinstance(raw,str) or len(raw.encode("utf-8")) > MAX_HANDOFF_BYTES:
        raise ValueError("BLOCKED:WRITER_HANDOFF_SIZE")
    try: handoff=json.loads(raw)
    except (ValueError,TypeError) as exc:
        raise ValueError("BLOCKED:WRITER_HANDOFF_JSON") from exc
    if not isinstance(handoff,dict) or not isinstance(handoff.get("plan"),dict):
        raise ValueError("BLOCKED:WRITER_HANDOFF_SHAPE")
    plan=verified_plan(handoff["plan"])
    assert_dynamic_handoff(plan,handoff)
    if plan["batch_id"] in COMMITTED_HISTORIC:
        # An already-completed historical batch may be queried by the main
        # DAG's Claim reader but must never reach the business Writer pod.
        raise ValueError("BLOCKED:WRITER_HISTORIC_COMPLETED_BATCH")
    if plan["writer_identity_version"]!="synthea-new-only-v1":
        raise ValueError("BLOCKED:WRITER_IDENTITY_VERSION")
    if not (1 <= plan["person_rows"] <= 100 and 1 <= plan["visit_rows"] <= 100000):
        raise ValueError("BLOCKED:WRITER_ROW_BOUND")
    return handoff,plan


def transaction_sql(handoff: dict, plan: dict, people: list, visits: list,
                    lease_owner: str) -> str:
    assert_dynamic_handoff(plan,handoff)
    sql=generate_dynamic_commit_sql(plan,people,visits,lease_owner,handoff)
    lines=sql.splitlines()
    if lines[:2]!=[r"\set ON_ERROR_STOP on",r"\set QUIET 1"]:
        raise ValueError("BLOCKED:WRITER_PSQL_HEADER")
    cleaned=[]
    for line in lines:
        if line.startswith("\\"):
            if line not in (r"\set ON_ERROR_STOP on",r"\set QUIET 1",r"\set QUIET 0"):
                raise ValueError("BLOCKED:WRITER_UNSAFE_META_COMMAND")
            continue
        cleaned.append(line)
    body="\n".join(cleaned)+"\n"
    controls=[x.strip().upper() for x in body.splitlines()]
    if (controls.count("BEGIN;")!=1 or controls.count("COMMIT;")!=1
        or controls.count("ROLLBACK;")!=0
        or body.count("\nCOMMIT;\n")!=1
        or body.count("SELECT task004_writer_fence.assert_active_claim(")!=3
        or body.count("DO $reconcile$")!=1 or body.count("DO $complete$")!=1
        or "BLOCKED:COMMIT_PRECONDITION_NOT_CLEAN" not in body
        or "BLOCKED:EXISTING_TARGET_DRIFT" not in body):
        raise ValueError("BLOCKED:WRITER_SQL_BOUNDARIES")
    if not (body.index("DO $reconcile$") < body.index("DO $complete$")
            < body.index("\nCOMMIT;\n")):
        raise ValueError("BLOCKED:WRITER_SQL_ORDER")
    return body


def durable_snapshot(plan: dict) -> dict:
    """Fresh cdm_reader PG transaction; no reliance on same-session COMMIT."""
    batch=plan["batch_id"]
    with connect("cdm_reader",readonly=True) as conn:
        conn.read_only=True
        with conn.cursor() as cur:
            cur.execute("SELECT current_user,current_setting('transaction_read_only')")
            if cur.fetchone()!=("cdm_reader","on"):
                raise ValueError("BLOCKED:WRITER_SNAPSHOT_NOT_READONLY")
            cur.execute("""SELECT manifest_sha256,manifest_uri,status,attempt_count,
                         lease_owner,lease_expires_at,reconciliation_sha256
                         FROM etl.landing_batch_ledger
                         WHERE source_system='synthea' AND batch_id=%s""",(batch,))
            claim=cur.fetchone()
            cur.execute("SELECT count(*) FROM etl.task004_batch_ledger WHERE batch_id=%s",(batch,))
            ledger=cur.fetchone()[0]
            cur.execute("""SELECT entity,count(*) FROM etl.task004_batch_stage
                           WHERE batch_id=%s GROUP BY entity""",(batch,))
            stage=dict(cur.fetchall())
            cur.execute("""SELECT entity,stage_rows,mapped_rows,commit_state
                           FROM etl.task004_batch_commit WHERE batch_id=%s""",(batch,))
            checkpoints=cur.fetchall()
            cur.execute("""SELECT count(*) FROM etl.task004_batch_stage s
                       JOIN etl.person_id_map m ON m.source_system='synthea'
                        AND m.source_person_id=s.source_key
                       JOIN cdm.person p ON p.person_id=m.person_id
                       WHERE s.batch_id=%s AND s.entity='person'""",(batch,))
            mapped_person=cur.fetchone()[0]
            cur.execute("""SELECT count(*) FROM etl.task004_batch_stage s
                       JOIN etl.visit_occurrence_id_map m ON m.source_system='synthea'
                        AND m.source_encounter_id=s.source_key
                       JOIN etl.person_id_map pm ON pm.source_system='synthea'
                        AND pm.source_person_id=s.source_person_key
                       JOIN cdm.visit_occurrence v ON v.visit_occurrence_id=m.visit_occurrence_id
                        AND v.person_id=pm.person_id
                       WHERE s.batch_id=%s AND s.entity='visit'""",(batch,))
            mapped_visit=cur.fetchone()[0]
        conn.rollback()
    return {"claim":claim,"ledger":ledger,"stage":stage,"checkpoints":checkpoints,
            "mapped_person":mapped_person,"mapped_visit":mapped_visit}


def classify_snapshot(plan: dict, snapshot: dict) -> str:
    claim=snapshot["claim"]
    if claim is None:
        if (snapshot["ledger"] or snapshot["stage"] or snapshot["checkpoints"]
            or snapshot["mapped_person"] or snapshot["mapped_visit"]):
            raise ValueError("BLOCKED:WRITER_ORPHANED_DB_STATE")
        return "ABSENT"
    sha,uri,status,attempt,owner,expiry,proof=claim
    if sha!=plan["manifest_sha256"] or uri!=plan["manifest_uri"]:
        raise ValueError("BLOCKED:WRITER_CLAIM_MANIFEST_DRIFT")
    if status!="COMPLETED":
        raise ValueError("BLOCKED:WRITER_EXISTING_INCOMPLETE_CLAIM")
    if (attempt!=1 or owner is not None or expiry is not None
        or not isinstance(proof,str) or not re.fullmatch(r"[a-f0-9]{64}",proof)
        or snapshot["ledger"]!=1
        or snapshot["stage"]!={"person":plan["person_rows"],"visit":plan["visit_rows"]}
        or snapshot["mapped_person"]!=plan["person_rows"]
        or snapshot["mapped_visit"]!=plan["visit_rows"]):
        raise ValueError("BLOCKED:WRITER_COMPLETED_RECONCILIATION_DRIFT")
    checkpoints=snapshot["checkpoints"]
    if (len(checkpoints)!=2 or
        set((e,n,m,s) for e,n,m,s in checkpoints)!={
            ("person",plan["person_rows"],plan["person_rows"],"VERIFIED"),
            ("visit",plan["visit_rows"],plan["visit_rows"],"VERIFIED")}):
        raise ValueError("BLOCKED:WRITER_COMPLETED_CHECKPOINT_DRIFT")
    return "COMPLETED"


def one_transaction_commit(sql: str) -> None:
    """Exactly one submission; unknown outcomes are checked by caller, NEVER retried."""
    import psycopg
    password=os.environ.get("TASK004_WRITER_ADMIN_PASSWORD")
    if not password:
        raise ValueError("BLOCKED:WRITER_ADMIN_SECRET_MISSING")
    with psycopg.connect(
        host=os.environ["PGHOST"],port=os.environ.get("PGPORT","5432"),
        dbname="omop",user="omop_admin",password=password,
        connect_timeout=8,autocommit=True,
        options="-c statement_timeout=180000 -c lock_timeout=4000",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user,session_user")
            if cur.fetchone()!=("omop_admin","omop_admin"):
                raise ValueError("BLOCKED:WRITER_ADMIN_IDENTITY")
            # Simple query protocol accepts the proven multi-statement BEGIN
            # ... COMMIT script. No client implicit transaction or auto retry.
            cur.execute(sql,prepare=False)


def execute(handoff: dict, plan: dict, *, can_commit: bool) -> str:
    """Read-only skip first. For ABSENT, audited S3 -> atomic Writer once."""
    if os.environ.get("PGUSER")!="cdm_reader":
        raise ValueError("BLOCKED:WRITER_READER_IDENTITY")
    previous=classify_snapshot(plan,durable_snapshot(plan))
    if previous=="COMPLETED":
        return "SKIP_COMPLETED"
    if not can_commit or os.environ.get("TASK004_WRITER_DEPLOY_ENABLE")!="YES":
        raise ValueError("BLOCKED:WRITER_NOT_EXPLICITLY_ENABLED")
    people,visits=s3_rows(plan)
    with connect("cdm_reader",readonly=True) as conn:
        conn.read_only=True
        audit=inspect_new_only(conn,plan,people,visits,require_claim=False)
        if (audit.status!="READY_TO_CLAIM" or audit.claim_status!="ABSENT"
            or audit.historic_ledger_rows or audit.existing_person_keys
            or audit.existing_visit_keys or audit.commit_authorized):
            raise ValueError("BLOCKED:WRITER_PG_PREFLIGHT")
        conn.rollback()
    sql=transaction_sql(handoff,plan,people,visits,secrets.token_hex(24))
    try:
        one_transaction_commit(sql)
    except Exception:
        # The COMMIT may have succeeded before network error. Durable state
        # is authoritative, but NEVER issue a second mutation in this run.
        try:
            state=classify_snapshot(plan,durable_snapshot(plan))
        except Exception:
            raise RuntimeError("WRITER_UNKNOWN_OUTCOME_NO_RETRY") from None
        if state=="COMPLETED":
            return "COMPLETED_VERIFIED_AFTER_AMBIGUOUS_RESPONSE"
        raise RuntimeError("WRITER_COMMIT_FAILED_NO_RETRY") from None
    if classify_snapshot(plan,durable_snapshot(plan))!="COMPLETED":
        raise RuntimeError("WRITER_POST_COMMIT_RECONCILIATION_FAILED")
    return "COMPLETED"


def main() -> None:
    if (os.environ.get("TASK004_WRITER_MODE")!="COMMIT"
        or os.environ.get("TASK004_WRITER_AIRFLOW_COMMIT_SELECTION")!="YES"):
        raise ValueError("BLOCKED:WRITER_MODE_OR_AIRFLOW_GATE_NOT_EXPLICIT")
    handoff,plan=load_handoff(os.environ.get("TASK004_WRITER_HANDOFF_JSON",""))
    # The manifest digest and batch are already bound into the XCom and
    # source plan. An extra env binding is checked to prevent wrong Pod args.
    if (os.environ.get("TASK004_WRITER_BATCH_ID")!=plan["batch_id"]
        or os.environ.get("TASK004_WRITER_MANIFEST_SHA256")!=plan["manifest_sha256"]):
        raise ValueError("BLOCKED:WRITER_POD_IDENTITY_DRIFT")
    state=execute(handoff,plan,can_commit=True)
    print("TASK004_NEW_ONLY_WRITER_RESULT="+state,flush=True)
    print("TASK004_NEW_ONLY_WRITER_PG_RECONCILIATION=PASS",flush=True)
    print("TASK004_NEW_ONLY_WRITER_NO_SECOND_COMMIT=PASS",flush=True)


if __name__=="__main__":
    main()
