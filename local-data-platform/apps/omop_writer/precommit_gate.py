"""Read-only OMOP NEW_ONLY pre-COMMIT safety gate.

This module is intentionally not a COMMIT executor. It validates an immutable
processing plan, full prepared Person/Visit rows, referential integrity and
PostgreSQL source-key collisions before any new-batch mutation can be enabled.
Runs under cdm_reader with an enforced read-only PG transaction.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re

from task004_cdm_materialization_plan import plan as validate_plan
from task004_cdm_dynamic_adapters import digest, source_keys_match

_SHA=re.compile(r"^[a-f0-9]{64}$")

class PrecommitBlocked(ValueError):
    pass

def refuse(reason: str) -> None:
    raise PrecommitBlocked("BLOCKED:" + reason)

@dataclass(frozen=True)
class GateResult:
    status: str
    batch_id: str
    person_rows: int
    visit_rows: int
    existing_person_keys: int
    existing_visit_keys: int
    historic_ledger_rows: int
    claim_status: str
    commit_authorized: bool = False

def validate_input(context: dict, people: list, visits: list) -> None:
    """Replay-stable source integrity before touching PostgreSQL."""
    if not isinstance(context, dict) or context.get("database_mutation_authorized") is not False:
        refuse("UNTRUSTED_SOURCE_PLAN")
    try:
        core={k:context[k] for k in (
            "batch_id","manifest_sha256","manifest_uri",
            "person_processing_uri","visit_processing_uri","person_rows",
            "visit_rows","source_version")}
        if "writer_identity_version" in context:
            core["writer_identity_version"]=context["writer_identity_version"]
        core.update(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False)
        expected=validate_plan(core)
    except (KeyError, ValueError, TypeError) as exc:
        raise PrecommitBlocked("BLOCKED:INVALID_SOURCE_PLAN") from exc
    if expected["plan_sha256"]!=context.get("plan_sha256"):
        refuse("SOURCE_PLAN_DRIFT")
    if len(people)!=context["person_rows"] or len(visits)!=context["visit_rows"]:
        refuse("SOURCE_ROW_COUNT_DRIFT")
    if not (1<=len(people)<=100 and 1<=len(visits)<=100_000):
        refuse("NEW_ONLY_ROW_BOUNDS")
    # This is explicitly a NEW_ONLY gate; legacy contract tests remain valid,
    # but a foreign versioned producer must never pass through this path.
    if context.get("writer_identity_version") not in (None,"synthea-new-only-v1"):
        refuse("UNSUPPORTED_WRITER_IDENTITY")
    for entity,rows in (("person",people),("visit",visits)):
        seen=set()
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get("canonical_payload"),dict):
                refuse("ROW_SHAPE")
            key=row.get("source_key")
            if not isinstance(key,str) or not key or len(key)>255 or key in seen:
                refuse("DUPLICATE_OR_INVALID_SOURCE_KEY")
            seen.add(key)
            parent=row.get("source_person_key")
            if (entity=="person" and parent is not None) or (entity=="visit" and (not isinstance(parent,str) or not parent)):
                refuse("PARENT_IDENTITY")
            fingerprint=row.get("row_fingerprint")
            if not isinstance(fingerprint,str) or not _SHA.fullmatch(fingerprint):
                refuse("ROW_FINGERPRINT_SHAPE")
            if digest({"source_person_key":parent,"payload":row["canonical_payload"]})!=fingerprint:
                refuse("ROW_FINGERPRINT_DRIFT")
    try:
        source_keys_match(people,visits)
    except (KeyError,ValueError) as exc:
        raise PrecommitBlocked("BLOCKED:VISIT_PARENT_NOT_IN_BATCH") from exc

def inspect_new_only(conn,context:dict,people:list,visits:list,*,require_claim:bool=False) -> GateResult:
    """Read-only PG checks. Never allocates IDs, UPDATEs, INSERTs or claims.

    Default mode is candidate audit: returns READY_TO_CLAIM only for zero
    collision inputs. Strict mode requires an existing PROCESSING ledger
    entry for this exact immutable manifest and returns READY_TO_LOAD_CHECK;
    neither result is itself a COMMIT authorization.
    """
    validate_input(context,people,visits)
    person_ids=[x["source_key"] for x in people]
    visit_ids=[x["source_key"] for x in visits]
    with conn.cursor() as cur:
        cur.execute("SELECT current_user,current_setting('transaction_read_only')")
        role,mode=cur.fetchone()
        if (role,mode)!=("cdm_reader","on"):
            refuse("NOT_READONLY_READER")
        cur.execute("SELECT has_table_privilege(current_user,'cdm.person','INSERT')")
        if cur.fetchone()[0] is not False:
            refuse("READER_HAS_PERSON_WRITE")
        cur.execute("SELECT count(*) FROM etl.task004_batch_ledger WHERE batch_id=%s",
                    (context["batch_id"],))
        historical=cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM etl.person_id_map
            WHERE source_system='synthea' AND source_person_id=ANY(%s)""",
                    (person_ids,))
        overlapping_people=cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM etl.visit_occurrence_id_map
            WHERE source_system='synthea' AND source_encounter_id=ANY(%s)""",
                    (visit_ids,))
        overlapping_visits=cur.fetchone()[0]
        cur.execute("""SELECT manifest_sha256,manifest_uri,status,lease_expires_at>clock_timestamp()
            FROM etl.landing_batch_ledger WHERE source_system='synthea' AND batch_id=%s""",
                    (context["batch_id"],))
        record=cur.fetchone()
    claim_status="ABSENT"
    if record is not None:
        sha,uri,status,lease_alive=record
        if sha!=context["manifest_sha256"] or uri!=context["manifest_uri"]:
            refuse("CLAIM_MANIFEST_IDENTITY_DRIFT")
        claim_status=status if status!="PROCESSING" else ("PROCESSING_LIVE" if lease_alive else "PROCESSING_EXPIRED")
    if historical:
        refuse("HISTORIC_BATCH_ALREADY_REGISTERED")
    if overlapping_people or overlapping_visits:
        refuse("NEW_ONLY_SOURCE_KEY_COLLISION")
    if record is not None and claim_status!="PROCESSING_LIVE":
        refuse("INCOMPATIBLE_CLAIM_STATUS")
    if require_claim and claim_status!="PROCESSING_LIVE":
        refuse("LIVE_EXCLUSIVE_CLAIM_REQUIRED")
    return GateResult(
        status="READY_TO_LOAD_CHECK" if require_claim else "READY_TO_CLAIM",
        batch_id=context["batch_id"],person_rows=len(people),visit_rows=len(visits),
        existing_person_keys=overlapping_people,existing_visit_keys=overlapping_visits,
        historic_ledger_rows=historical,claim_status=claim_status,commit_authorized=False
    )
