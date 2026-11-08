"""Independent physical local Delta readback to pure shared Canonical DQ plan.

Synthetic hosted-CI-only. No Silver write/approval, no raw HL7 upload.
"""
from __future__ import annotations

from datetime import timezone
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/"shared-data-engine/src"))
sys.path.insert(0, str(ROOT/"local-data-platform/spark/apps/hl7"))

from healthcare_data_engine.models.batch_context import BatchContext
from silver_handoff import prepare_hl7_canonical_handoff
from write_staging_delta import _spark, _warehouse


def main() -> None:
    path = Path(os.environ["HL7_LOCAL_MANIFEST_PATH"])
    manifest_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    uri = _warehouse(os.environ["HL7_LOCAL_WAREHOUSE_URI"])
    spark = _spark(uri)
    try:
        if spark.conf.get("spark.sql.session.timeZone") != "UTC":
            raise RuntimeError("HL7_HANDOFF_SPARK_TIMEZONE_NOT_VERIFIED")
        patients = [r.asDict(recursive=True) for r in
                    spark.table("hl7_candidate.canonical_patient").collect()]
        encounters = [r.asDict(recursive=True) for r in
                      spark.table("hl7_candidate.canonical_encounter").collect()]
        # This test fixture is the already-reviewed one Patient/A01 and one
        # Encounter/A03. Never infer these expected counts in production.
        if len(patients) != 1 or len(encounters) != 1:
            raise RuntimeError("HL7_HANDOFF_SYNTHETIC_CANDIDATE_COUNT_HOLD")
        seed = patients[0]
        processed_at = seed["processed_at"]
        if processed_at.tzinfo is None:
            processed_at = processed_at.replace(tzinfo=timezone.utc)
        else:
            processed_at = processed_at.astimezone(timezone.utc)
        context = BatchContext(
            hospital_id="johns-creek-hospital-b",
            feed_id="johns-creek-hospital-b-hl7-v2",
            source_system="johns-creek-hl7",
            request_id=seed["source_batch_id"],
            manifest_sha256=manifest_sha,
            processing_version="hl7-canonical-v1-hosted-synthetic-candidate",
            processing_run_id=seed["processing_run_id"],
            source_version=seed["source_version"],
            source_ingest_date=seed["source_ingest_date"],
            processed_at=processed_at,
            adapter_version=seed["adapter_version"],
        )
        p_contract = (ROOT/"local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes()
        e_contract = (ROOT/"local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes()
        result = prepare_hl7_canonical_handoff(
            patients, encounters,
            context=context,
            patient_contract_bytes=p_contract,
            encounter_contract_bytes=e_contract,
            spark_timestamp_timezone="UTC",
        )
        if result.status != "CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED":
            raise RuntimeError("HL7_HANDOFF_DQ_HOLD")
        if result.metrics["patient_accepted"] != 1 or result.metrics["encounter_accepted"] != 1:
            raise RuntimeError("HL7_HANDOFF_COUNT_HOLD")
        if (result.patient.accepted[0]["source_system"] != context.namespaced_source_system
                or result.patient.accepted[0]["source_batch_id"] != context.source_batch_id
                or result.encounter.accepted[0]["source_batch_id"] != context.source_batch_id):
            raise RuntimeError("HL7_HANDOFF_SHARED_IDENTITY_HOLD")
        if seed["source_system"] != "johns-creek-hl7":
            raise RuntimeError("HL7_HANDOFF_MUTATED_INPUT_HOLD")
        print("HL7_CANONICAL_SHARED_DQ_HANDOFF_PHYSICAL_LOCAL_CANDIDATE=PASS")
        print("HL7_CANONICAL_SILVER_APPROVED=NO")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
