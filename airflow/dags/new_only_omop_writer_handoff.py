"""Pure Airflow NEW_ONLY S3 -> Spark -> Writer handoff, NO Claim or CDM DML.

Sequence for a *future* fresh READY: S3 identity -> PG readonly ABSENT ->
Spark Person and Visit -> both XCom readbacks -> immutable CDM plan -> Writer
S3/PG preflight -> single *atomic* Claim+Fenced Writer+Reconcile+COMMIT.

Do not separately Claim the batch before Spark: this Demo deliberately keeps
the existing proven single transaction which creates and completes the Claim
together with CDM rows. It prevents orphan PROCESSING leases when Spark fails.
"""
from __future__ import annotations

from new_only_omop_routing import classify_new_only_claim
from task004_cdm_preflight_contract import validate_handoff
from task004_cdm_materialization_plan import plan as materialization_plan

VERSION = "synthea-new-only-v1"
STATUS = "NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED"


def prepare_new_only_writer_handoff(selected: dict, db_status: dict,
                                    person: dict, visit: dict) -> dict:
    """Called only AFTER both Spark tasks; doesn't authorize real COMMIT."""
    if classify_new_only_claim(selected, db_status) != "ABSENT":
        raise ValueError("BLOCKED:NOT_FRESH_NEW_ONLY")
    if not (isinstance(person,dict) and isinstance(visit,dict)):
        raise ValueError("BLOCKED:MISSING_REAL_SPARK_XCOM")
    for value in (person,visit):
        if value.get("processing_readback") != "PASS":
            raise ValueError("BLOCKED:SPARK_PARQUET_READBACK_NOT_PASS")
        if not isinstance(value.get("run_id"),str) or not value["run_id"]:
            raise ValueError("BLOCKED:MISSING_SPARK_RUN")
    metadata={
        "batch_id": selected["batch_id"],
        "manifest_uri": selected["manifest_uri"],
        "manifest_sha256": selected["manifest_sha256"],
        "source_version": "v3.3.0",
        "status": "INTAKE_VERIFIED",
        "new_only_processing_probe": True,
    }
    base=validate_handoff(metadata,person,visit)
    base["writer_identity_version"]=VERSION
    immutable=materialization_plan(base)
    if immutable.get("database_mutation_authorized") is not False:
        raise ValueError("BLOCKED:UNSAFE_WRITER_PLAN")
    if immutable["load_order"] != ["person","visit","db_reconcile"]:
        raise ValueError("BLOCKED:WRONG_WRITER_ORDER")
    return {
        "status": STATUS,
        "source_system": "synthea",
        "batch_id": selected["batch_id"],
        "manifest_uri": selected["manifest_uri"],
        "manifest_sha256": selected["manifest_sha256"],
        "plan_sha256": immutable["plan_sha256"],
        "plan": immutable,
        "claim_status_at_handoff": "ABSENT",
        "person_rows": immutable["person_rows"],
        "visit_rows": immutable["visit_rows"],
        "business_commit_authorized": False,
        "claim_mutation": False,
        "writer_mutation": False,
    }


def assert_dynamic_handoff(context: dict, handoff: dict) -> None:
    """Bind generated business SQL to immutable Airflow Spark provenance."""
    if not isinstance(handoff,dict) or handoff.get("status") != STATUS:
        raise ValueError("BLOCKED:DYNAMIC_WRITER_HANDOFF_STATUS")
    expected={
        "source_system": "synthea",
        "batch_id": context["batch_id"],
        "manifest_uri": context["manifest_uri"],
        "manifest_sha256": context["manifest_sha256"],
        "plan_sha256": context["plan_sha256"],
        "person_rows": context["person_rows"],
        "visit_rows": context["visit_rows"],
        "claim_status_at_handoff": "ABSENT",
        "business_commit_authorized": False,
        "claim_mutation": False,
        "writer_mutation": False,
    }
    for field,wanted in expected.items():
        if field not in handoff or type(handoff[field]) is not type(wanted) or handoff[field]!=wanted:
            raise ValueError("BLOCKED:DYNAMIC_WRITER_HANDOFF_"+field.upper())
    if handoff.get("plan") != context:
        raise ValueError("BLOCKED:DYNAMIC_WRITER_PLAN_DRIFT")
    if context.get("writer_identity_version")!=VERSION or context["database_mutation_authorized"] is not False:
        raise ValueError("BLOCKED:DYNAMIC_WRITER_PRECOMMIT_NOT_AUTHORIZED")
