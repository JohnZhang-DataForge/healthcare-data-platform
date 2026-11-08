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
        # Exercise the ONE native Canonical Silver physical writer on transient
        # GitHub-hosted LOCAL Delta only. No Fabric/OneLake, cloud credentials,
        # official Silver publication, or preserved Processing data.
        from dataclasses import replace
        from datetime import datetime
        from unittest.mock import patch
        from healthcare_data_engine.canonical.validation import (
            accepted_dataframe, load_pinned_contract, validate_row)
        from healthcare_data_engine.quality.result import TransformResult
        from healthcare_data_engine.reconciliation.patient_encounter import (
            reconcile_patient_encounter)
        sys.path.insert(0, str(ROOT/"azure-fabric/notebook-development"))
        import fhir_ingest_notebook as native

        patient_contract = load_pinned_contract(p_contract, "patient")
        encounter_contract = load_pinned_contract(e_contract, "encounter")
        accepted_p = tuple(result.patient.accepted)
        accepted_e = tuple(result.encounter.accepted)
        prepared = native.PreparedBatch(
            patient_df=accepted_dataframe(spark, accepted_p, patient_contract),
            encounter_df=accepted_dataframe(spark, accepted_e, encounter_contract),
            patient_count=len(accepted_p), encounter_count=len(accepted_e),
            findings=(),
            source_batch_id=context.source_batch_id,
            processing_version=context.processing_version,
            publication_id=native._content_publication_id(context, accepted_p, accepted_e),
            manifest_sha256=context.manifest_sha256, source_receipts=())
        prefix = (
            os.environ["HL7_LOCAL_WAREHOUSE_URI"].rstrip("/")
            + "/ephemeral-silver-publication-test/"
            + context.source_batch_id + "/processing="
            + hashlib.sha256(context.processing_version.encode()).hexdigest())
        targets = {
            "patient": prefix + "/canonical_patient",
            "encounter": prefix + "/canonical_encounter",
            "approval": prefix + "/silver_approval",
        }

        def verify_reopened(patient_delta, encounter_delta, expected, scope):
            # Spark returns naive Python TIMESTAMPs in UTC; normalize for the
            # pinned Shared Contract before re-running Shared PK/FK DQ.
            def rows(frame, contract):
                output = []
                for record in frame.collect():
                    row = record.asDict(recursive=True)
                    for key, value in row.items():
                        if isinstance(value, datetime) and value.tzinfo is None:
                            row[key] = value.replace(tzinfo=timezone.utc)
                    if validate_row(row, contract):
                        raise RuntimeError("HL7_PHYSICAL_SILVER_CONTRACT_HOLD")
                    output.append(row)
                return tuple(output)
            persisted_p = rows(patient_delta, patient_contract)
            persisted_e = rows(encounter_delta, encounter_contract)
            reconciliation = reconcile_patient_encounter(
                TransformResult(persisted_p, (), ()),
                TransformResult(persisted_e, (), ()), scope)
            counts = reconciliation.metrics
            if (counts["patient_accepted"] != expected.patient_count
                    or counts["encounter_accepted"] != expected.encounter_count
                    or any(counts[k] for k in (
                        "patient_quarantined", "encounter_quarantined",
                        "patient_rejected", "encounter_rejected"))):
                raise RuntimeError("HL7_PHYSICAL_SILVER_RECONCILIATION_HOLD")

        original_write = native._write_delta
        write_order = []
        def observed_write(frame, path):
            write_order.append(path.rsplit("/", 1)[-1])
            return original_write(frame, path)
        with patch.dict(native._write_verified_canonical_silver.__globals__, {
                "_write_delta": observed_write}):
            approval = native._write_verified_canonical_silver(
                spark, context=context, batch=prepared, paths=targets,
                patient_contract_bytes=p_contract,
                encounter_contract_bytes=e_contract,
                source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
                validate_persisted_canonical=verify_reopened)
        if write_order != [
                "canonical_patient", "canonical_encounter", "silver_approval"]:
            raise RuntimeError("HL7_LOCAL_APPROVAL_LAST_ORDER_HOLD")
        if (approval["patient_count"] != 1
                or approval["encounter_count"] != 1
                or approval["status"] != "SILVER_APPROVED"
                or spark.read.format("delta").load(targets["approval"]).count() != 1):
            raise RuntimeError("HL7_LOCAL_APPROVAL_INDEPENDENT_READBACK_HOLD")
        # A second direct writer call is NOT a replay approval. A caller must
        # use independently verified existing-data SKIP / unknown-ACK gates.
        try:
            native._write_verified_canonical_silver(
                spark, context=context, batch=prepared, paths=targets,
                patient_contract_bytes=p_contract,
                encounter_contract_bytes=e_contract,
                source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
                validate_persisted_canonical=verify_reopened)
        except ValueError as exc:
            if "HOLD_SILVER_EXISTING_OR_PARTIAL_DELTA" not in str(exc):
                raise
        else:
            raise RuntimeError("HL7_LOCAL_REPLAY_OVERWRITE_NOT_BLOCKED")
        bad_paths = {k: v.replace(
            "/ephemeral-silver-publication-test/",
            "/ephemeral-silver-negative-test/") for k, v in targets.items()}
        try:
            native._write_verified_canonical_silver(
                spark, context=context,
                batch=replace(prepared, findings=(object(),)),
                paths=bad_paths, patient_contract_bytes=p_contract,
                encounter_contract_bytes=e_contract,
                source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
                validate_persisted_canonical=verify_reopened)
        except ValueError as exc:
            if "HOLD_SILVER_UNVERIFIED_BATCH_OR_DQ" not in str(exc):
                raise
        else:
            raise RuntimeError("HL7_LOCAL_BAD_DQ_WROTE_SILVER")
        if any(native._g3_delta_exists(spark, value)
               for value in bad_paths.values()):
            raise RuntimeError("HL7_LOCAL_BAD_DQ_LEFT_ANY_DELTA")
        print("HL7_LOCAL_EPHEMERAL_SHARED_SILVER_APPROVAL_LAST_PHYSICAL=PASS")
        print("HL7_LOCAL_EPHEMERAL_REPLAY_AND_DQ_HOLD=PASS")
        print("HL7_CANONICAL_REMOTE_SILVER_APPROVED=NO")
        print("HL7_CANONICAL_SHARED_DQ_HANDOFF_PHYSICAL_LOCAL_CANDIDATE=PASS")
        print("HL7_CANONICAL_SILVER_APPROVED=NO")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
