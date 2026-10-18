"""Fail-closed routing of existing NEW_ONLY S3 batches into an Airflow consumer.

This phase deliberately does not claim or write: its only terminal states are
SKIP_COMPLETED and NEW_BATCH_ON_HOLD.  The latter will receive an explicitly
gated Claim -> Spark -> Writer sequence in a separate tested release.
No dependency on Airflow so source/identity contracts remain unit testable.
"""
from __future__ import annotations
import json
import re

BATCH = re.compile(r"^synthea-new-only-[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
SHA = re.compile(r"^[a-f0-9]{64}$")


def _obj(value, label: str) -> dict:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("BLOCKED:" + label + "_JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("BLOCKED:" + label + "_OBJECT")
    return value


def select_verified_new_only(inventory, dag_conf, run_type: str) -> dict:
    """Require manual exact manifest selection from complete REAL S3 discovery."""
    if str(run_type).lower() != "manual":
        raise ValueError("BLOCKED:NEW_ONLY_MANUAL_ONLY")
    conf = _obj(dag_conf, "CONF")
    expected={"batch_id","manifest_uri","manifest_sha256","consumer_readonly"}
    keys=set(conf)
    supported=(expected, expected|{"spark_processing"},
               expected|{"spark_processing","writer_commit"})
    if (keys not in supported
        or conf["consumer_readonly"] is not True
        or ("spark_processing" in conf and conf["spark_processing"] is not True)
        or ("writer_commit" in conf and (
            conf["writer_commit"] is not True or conf.get("spark_processing") is not True))):
        raise ValueError("BLOCKED:NEW_ONLY_MANUAL_COMMIT_CONF")
    batch, uri, sha = (conf.get(x) for x in ("batch_id","manifest_uri","manifest_sha256"))
    if (not isinstance(batch,str) or not BATCH.fullmatch(batch)
        or not isinstance(sha,str) or not SHA.fullmatch(sha)
        or not isinstance(uri,str)
        or not uri.startswith("s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=")
        or not uri.endswith("/batch_id="+batch+"/manifest.json")):
        raise ValueError("BLOCKED:NEW_ONLY_IDENTITY")
    discovery = _obj(inventory, "DISCOVERY")
    rows = discovery.get("ready_batches_preview")
    if (discovery.get("status")!="READ_ONLY_DISCOVERED"
        or discovery.get("processing_authorized") is not False
        or discovery.get("database_mutation") is not False
        or discovery.get("preview_truncated") is not False
        or not isinstance(rows,list) or len(rows)>25
        or discovery.get("ready_count") != len(rows)):
        raise ValueError("BLOCKED:NEW_ONLY_DISCOVERY_INCOMPLETE")
    matched=[row for row in rows if isinstance(row,dict) and row.get("batch_id")==batch]
    if len(matched)!=1:
        raise ValueError("BLOCKED:NEW_ONLY_NOT_IN_DISCOVERY")
    row=matched[0]
    if (row.get("manifest_uri")!=uri or row.get("manifest_sha256")!=sha
        or row.get("source")!="synthea" or row.get("source_version")!="v3.3.0"
        or row.get("status")!="INTAKE_VERIFIED" or row.get("file_count")!=18):
        raise ValueError("BLOCKED:NEW_ONLY_DISCOVERY_DRIFT")
    return {"source_system":"synthea","batch_id":batch,"manifest_uri":uri,
            "manifest_sha256":sha,"consumer_readonly":True,
            "spark_processing":conf.get("spark_processing") is True,
            "writer_commit":conf.get("writer_commit") is True}


def classify_new_only_claim(selected, database_result) -> str:
    """Fail-closed actual claim readback; no side effects.

    Decouple classification from manual Spark branching so a downstream
    Writer handoff can revalidate ABSENT without depending on task IDs.
    """
    selected = _obj(selected,"SELECTION")
    row=_obj(database_result,"CLAIM_STATUS")
    if selected.get("consumer_readonly") is not True or not BATCH.fullmatch(selected.get("batch_id","")):
        raise ValueError("BLOCKED:NEW_ONLY_SELECTION")
    if (row.get("source_system")!="synthea" or row.get("batch_id")!=selected["batch_id"]
        or row.get("manifest_sha256")!=selected["manifest_sha256"]
        or row.get("manifest_uri")!=selected["manifest_uri"]
        or row.get("role")!="landing_claim_worker"
        or row.get("pg_transaction_readonly") is not True
        or row.get("business_mutation") is not False):
        raise ValueError("BLOCKED:NEW_ONLY_CLAIM_READBACK_DRIFT")
    status=row.get("claim_status")
    if status=="COMPLETED":
        if row.get("writer_ledger_rows")!=1 or row.get("attempt_count",0)<1:
            raise ValueError("BLOCKED:NEW_ONLY_COMPLETED_WITHOUT_WRITER_LEDGER")
        return "COMPLETED"
    if status=="ABSENT":
        if row.get("writer_ledger_rows")!=0 or row.get("attempt_count")!=0:
            raise ValueError("BLOCKED:NEW_ONLY_ABSENT_WITH_WRITER_HISTORY")
        return "ABSENT"
    if status in ("PROCESSING","FAILED"):
        raise ValueError("BLOCKED:NEW_ONLY_EXISTING_INCOMPLETE_CLAIM")
    raise ValueError("BLOCKED:NEW_ONLY_UNKNOWN_CLAIM_STATE")


def route_claim_status(selected, database_result):
    """Manual-only opt-in fresh batch --> BOTH Spark tasks; never Claim/Writer.

    Safe legacy behavior remains: completed goes to Skip; ABSENT without
    the explicit single-run spark flag remains on HOLD.
    """
    selected=_obj(selected,"SELECTION")
    status=classify_new_only_claim(selected,database_result)
    if status=="COMPLETED":
        return "already_completed_no_replay"
    if status=="ABSENT":
        if selected.get("spark_processing") is True:
            return ["spark_patient","spark_encounter"]
        return "unclaimed_batch_hold"
    raise ValueError("BLOCKED:NEW_ONLY_ROUTING_STATE")


def route_new_only_writer_commit(selected, handoff, run_type: str) -> str:
    """Manual opt-in only; physical Kubernetes secret remains second hard gate.

    Completed batches cannot produce Spark handoff in this DAG; even manual
    clearing of the branch must not silently authorize a Writer mutation.
    """
    selected=_obj(selected,"WRITER_SELECTION")
    handoff=_obj(handoff,"WRITER_HANDOFF")
    if str(run_type).lower()!="manual":
        raise ValueError("BLOCKED:WRITER_ONLY_MANUAL")
    from new_only_omop_writer_handoff import assert_dynamic_handoff
    plan=handoff.get("plan")
    if not isinstance(plan,dict):
        raise ValueError("BLOCKED:WRITER_MISSING_PLAN")
    assert_dynamic_handoff(plan,handoff)
    for field in ("batch_id","manifest_sha256","manifest_uri"):
        if selected.get(field)!=plan.get(field):
            raise ValueError("BLOCKED:WRITER_SPARK_SELECTION_DRIFT")
    if selected.get("consumer_readonly") is not True or selected.get("spark_processing") is not True:
        raise ValueError("BLOCKED:WRITER_MUST_FOLLOW_VERIFIED_SPARK")
    if selected.get("writer_commit") is True:
        if plan["batch_id"] in (
            "synthea-new-only-gh-38497355290",
            "synthea-new-only-gh-38489944582",
        ):
            raise ValueError("BLOCKED:ALREADY_COMMITTED_BATCH")
        return "execute_new_only_writer"
    if selected.get("writer_commit") is False:
        return "writer_awaits_live_preflight"
    raise ValueError("BLOCKED:WRITER_FLAG_NOT_BOOLEAN")
