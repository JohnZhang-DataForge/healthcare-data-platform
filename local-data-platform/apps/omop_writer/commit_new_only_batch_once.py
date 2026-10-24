#!/usr/bin/env python3
"""One authorized TASK004 NEW_ONLY v2 commit: REAL S3 -> Claim + OMOP + reconcile.

Scope intentionally freezes a single immutable historical READY Batch:
synthea-new-only-gh-38497355290, Person=1, Visit=812.
Never generate synthetic patients, run Spark, mutate S3, or trigger Airflow.

Pre-commit preparation runs as cdm_reader READ ONLY with real S3 checksum/
source-key preflight. The generated SQL runs as omop_admin with role boundaries
SET LOCAL ROLE landing_claim_worker -> cdm_writer -> landing_claim_worker.
All Claim, CDM, stage, mapping, checkpoints, reconciliation, completion are ONE
PostgreSQL transaction, ending in exactly ONE explicit business COMMIT.

This is a manually authorized single-batch Demo executor, NOT general-purpose
Airflow automation. No PHI or lease token in GitHub logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets

from joint_s3_rollback import compose_joint_rollback, for_psycopg, verified_plan, s3_rows, connect
from precommit_gate import inspect_new_only

BATCH="synthea-new-only-gh-38497355290"
SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
URI=f"s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id={BATCH}/manifest.json"


def quote(s: str) -> str:
    if not isinstance(s,str) or "\x00" in s or "\\" in s:
        raise ValueError("BLOCKED:UNSAFE_SQL_LITERAL")
    return "'"+s.replace("'","''")+"'"

def stage_digest(rows: list) -> str:
    canonical=json.dumps(sorted(rows,key=lambda r:r["source_key"]),
                         sort_keys=True,separators=(",",":"),allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()

def reconciliation_digest(ctx:dict,people:list,visits:list) -> str:
    data={"batch_id":ctx["batch_id"],"manifest_sha256":ctx["manifest_sha256"],
          "plan_sha256":ctx["plan_sha256"],
          "person_rows":len(people),"visit_rows":len(visits),
          "person_stage_digest":stage_digest(people),"visit_stage_digest":stage_digest(visits)}
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def generate_commit_sql(context:dict,people:list,visits:list,token:str) -> str:
    """Permanently frozen one-time real batch guard; still reject all other batches."""
    return _render_atomic_new_only_sql(
        context,people,visits,token,
        expected_identity=(BATCH,SHA,URI,1,812),
    )


def _render_atomic_new_only_sql(
    context:dict,people:list,visits:list,token:str,
    *,expected_identity:tuple[str,str,str,int,int],
) -> str:
    """Shared proven atomic SQL renderer. Private: caller MUST audit S3/PG first.

    No database access or execution. The one-shot public wrapper above stays
    frozen, while the new general batch adapter supplies a strict identity.
    Never expose this private renderer directly as an Airflow operator.
    """
    BATCH,SHA,URI,person_count,visit_count=expected_identity
    ctx=verified_plan(context)
    if (ctx["batch_id"],ctx["manifest_sha256"],ctx["manifest_uri"],len(people),len(visits)) != (BATCH,SHA,URI,person_count,visit_count):
        raise ValueError("BLOCKED:NOT_ONE_AUTHORIZED_REAL_READY_BATCH")
    if not isinstance(token,str) or len(token)!=48 or any(ch not in "0123456789abcdef" for ch in token):
        raise ValueError("BLOCKED:INVALID_COMMIT_OWNER")
    joint=for_psycopg(compose_joint_rollback(ctx,people,visits))
    if not joint.startswith("BEGIN;\n") or not joint.endswith("ROLLBACK;\n"):
        raise ValueError("BLOCKED:EXPECTED_ROLLBACK_ONLY_RENDERER")
    body=joint[len("BEGIN;\n"):-len("ROLLBACK;\n")]
    if any(line.strip().upper() in ("BEGIN;","ROLLBACK;","COMMIT;") for line in body.splitlines()):
        raise ValueError("BLOCKED:INNER_TRANSACTION_BOUNDARY")
    b=quote(BATCH); sha=quote(SHA); uri=quote(URI);owner=quote(token)
    proof=quote(reconciliation_digest(ctx,people,visits))
    pd=quote(stage_digest(people));vd=quote(stage_digest(visits))
    # Same DB transaction: role-separated claim, definer fence, full joint
    # Person/Visit Writer, DB row-by-row CDM reconciliation, COMPLETED, COMMIT.
    fence=f"SELECT task004_writer_fence.assert_active_claim('synthea',{b},{sha},{uri},{owner},1);"
    return f"""\\set ON_ERROR_STOP on
\\set QUIET 1
BEGIN;
SET LOCAL lock_timeout='4s';
SET LOCAL statement_timeout='120s';
DO $pre$
BEGIN
 IF session_user <> 'omop_admin' OR current_user <> 'omop_admin'
 OR EXISTS(SELECT 1 FROM etl.landing_batch_ledger WHERE batch_id={b})
 OR EXISTS(SELECT 1 FROM etl.task004_batch_ledger WHERE batch_id={b})
 OR EXISTS(SELECT 1 FROM etl.task004_batch_stage WHERE batch_id={b})
 OR EXISTS(SELECT 1 FROM etl.task004_batch_commit WHERE batch_id={b})
 OR to_regprocedure('task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)') IS NULL
 THEN RAISE EXCEPTION 'BLOCKED:COMMIT_PRECONDITION_NOT_CLEAN';END IF;
END $pre$;
-- Claim is REAL and will become durable in SAME COMMIT as OMOP data.
SET LOCAL ROLE landing_claim_worker;
DO $claim$
BEGIN
 IF current_user <> 'landing_claim_worker'
 OR has_schema_privilege(current_user,'cdm','USAGE')
 THEN RAISE EXCEPTION 'BLOCKED:CLAIM_ROLE_ESCALATED';END IF;
END $claim$;
INSERT INTO etl.landing_batch_ledger
 (source_system,batch_id,manifest_sha256,manifest_uri,
  status,attempt_count,lease_owner,lease_expires_at)
VALUES ('synthea',{b},{sha},{uri},
        'PROCESSING',1,{owner},clock_timestamp()+interval '30 minutes');
SET LOCAL ROLE cdm_writer;
DO $writer_role$
BEGIN
 IF current_user <> 'cdm_writer'
 OR has_table_privilege(current_user,'etl.landing_batch_ledger','SELECT')
 OR has_table_privilege(current_user,'etl.landing_batch_ledger','UPDATE')
 THEN RAISE EXCEPTION 'BLOCKED:WRITER_DIRECT_CLAIM_PRIVILEGE';END IF;
END $writer_role$;
{fence}
{body}
{fence}
-- Actual in-transaction reconciliation of both entities, not merely a
-- caller-supplied digest. The renderer's verified checkpoints remain intact.
DO $reconcile$
BEGIN
 IF (SELECT count(*) FROM etl.task004_batch_stage
     WHERE batch_id={b} AND entity='person')<>{person_count}
 OR (SELECT count(*) FROM etl.task004_batch_stage
     WHERE batch_id={b} AND entity='visit')<>{visit_count}
 OR (SELECT count(*) FROM etl.task004_batch_commit
     WHERE batch_id={b} AND commit_state='VERIFIED'
       AND ((entity='person' AND stage_rows={person_count} AND mapped_rows={person_count} AND stage_digest={pd})
         OR (entity='visit' AND stage_rows={visit_count} AND mapped_rows={visit_count} AND stage_digest={vd})))<>2
 OR NOT EXISTS (SELECT 1 FROM etl.task004_batch_ledger
     WHERE batch_id={b} AND manifest_sha256={sha}
       AND person_processing_uri={quote(ctx["person_processing_uri"])}
       AND visit_processing_uri={quote(ctx["visit_processing_uri"])})
 THEN RAISE EXCEPTION 'BLOCKED:COMMIT_LEDGER_OR_CHECKPOINT_DRIFT'; END IF;
 -- Row-by-row comparison, including Person and Visit OMOP schema fields,
 -- matching the existing Writer's JSONB round-trip validation.
 IF (SELECT count(*) FROM etl.task004_batch_stage s
     JOIN etl.person_id_map m ON m.source_system='synthea'
      AND m.source_person_id=s.source_key
     JOIN cdm.person p ON p.person_id=m.person_id
     WHERE s.batch_id={b} AND s.entity='person'
       AND to_jsonb(p) IS NOT DISTINCT FROM to_jsonb(jsonb_populate_record(
          NULL::cdm.person,s.canonical_payload || jsonb_build_object('person_id',m.person_id))))<>{person_count}
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_DB_RECONCILIATION'; END IF;
 IF (SELECT count(*) FROM etl.task004_batch_stage s
     JOIN etl.visit_occurrence_id_map m ON m.source_system='synthea'
      AND m.source_encounter_id=s.source_key
     JOIN etl.person_id_map pm ON pm.source_system='synthea'
      AND pm.source_person_id=s.source_person_key
     JOIN cdm.visit_occurrence v ON v.visit_occurrence_id=m.visit_occurrence_id
     WHERE s.batch_id={b} AND s.entity='visit'
       AND to_jsonb(v) IS NOT DISTINCT FROM to_jsonb(jsonb_populate_record(
          NULL::cdm.visit_occurrence,s.canonical_payload ||
          jsonb_build_object('visit_occurrence_id',m.visit_occurrence_id,'person_id',pm.person_id))))<>{visit_count}
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_DB_RECONCILIATION'; END IF;
END $reconcile$;
-- Final fencing runs with the original row lock STILL HELD.
{fence}
-- Claim worker closes batch with proof derived from source+stage digests.
SET LOCAL ROLE landing_claim_worker;
DO $complete$
BEGIN
 UPDATE etl.landing_batch_ledger
 SET status='COMPLETED',lease_owner=NULL,lease_expires_at=NULL,
     reconciliation_sha256={proof},
     completed_at=clock_timestamp(),updated_at=clock_timestamp()
 WHERE source_system='synthea' AND batch_id={b}
   AND manifest_sha256={sha} AND manifest_uri={uri}
   AND status='PROCESSING' AND attempt_count=1 AND lease_owner={owner}
   AND lease_expires_at>clock_timestamp();
 IF NOT FOUND THEN RAISE EXCEPTION 'BLOCKED:STALE_CLAIM_FINAL_COMPLETION';END IF;
END $complete$;
RESET ROLE;
-- **ONLY COMMIT STATEMENT**; all 813 OMOP rows + Claim COMPLETED are atomic.
COMMIT;
\\set QUIET 0
SELECT CASE WHEN (SELECT count(*) FROM etl.landing_batch_ledger
 WHERE batch_id={b} AND status='COMPLETED' AND manifest_sha256={sha}
 AND reconciliation_sha256={proof})=1
 THEN 'REAL_NEW_ONLY_BUSINESS_COMMIT_AND_COMPLETED=PASS'
 ELSE 'REAL_NEW_ONLY_BUSINESS_COMMIT_AND_COMPLETED=FAIL' END;
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file",required=True)
    parser.add_argument("--output",required=True)
    opts=parser.parse_args()
    if os.environ.get("PGUSER")!="cdm_reader":
        raise ValueError("BLOCKED:READER_AUDIT_REQUIRED")
    context=json.loads(Path(opts.plan_file).read_text())
    ctx=verified_plan(context)
    if (ctx["batch_id"],ctx["manifest_uri"],ctx["manifest_sha256"]) != (BATCH,URI,SHA):
        raise ValueError("BLOCKED:IMMUTABLE_MANIFEST_DISAGREEMENT")
    people,visits=s3_rows(ctx)
    with connect("cdm_reader",readonly=True) as connection:
        connection.read_only=True
        audit=inspect_new_only(connection,ctx,people,visits,require_claim=False)
        if (audit.status!="READY_TO_CLAIM" or audit.claim_status!="ABSENT"
            or audit.historic_ledger_rows or audit.existing_person_keys or audit.existing_visit_keys):
            raise ValueError("BLOCKED:READONLY_REAL_SOURCE_COLLISION_OR_CLAIM")
        connection.rollback()
    sql=generate_commit_sql(ctx,people,visits,secrets.token_hex(24))
    out=Path(opts.output)
    if not out.parent.is_dir() or out.exists():
        raise ValueError("BLOCKED:OUTPUT_NOT_EXCLUSIVE")
    out.write_text(sql,encoding="utf-8")
    os.chmod(out,0o600)
    print("REAL_NEW_ONLY_SOURCE_READONLY_AUDIT=PASS",flush=True)
    print("REAL_NEW_ONLY_PERSON_ROWS=1",flush=True)
    print("REAL_NEW_ONLY_VISIT_ROWS=812",flush=True)
    print("ONE_TRANSACTION_ATOMIC_CLAIM_WRITER_COMPLETION=PASS",flush=True)
    print("REAL_COMMIT_SQL_STAGED_NOT_EXECUTED=PASS",flush=True)

if __name__=="__main__":
    main()
