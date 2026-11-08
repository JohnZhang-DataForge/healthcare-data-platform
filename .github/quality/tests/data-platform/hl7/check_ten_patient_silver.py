"""Ten fresh synthetic FHIR patients -> V2 HL7 -> local dbt -> one Silver.

The fixture is deliberately offline and *not* a Synthea generation job or an
OIE GET/POST. Physically verifies Delta+Approval-last with one real shared
Silver Writer in GitHub-hosted local Spark. Never publishes cloud Silver.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "local-data-platform/spark/apps/hl7"))
sys.path.insert(0, str(ROOT / "shared-data-engine/src"))
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))

from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.canonical.validation import load_pinned_contract
from landing_intake import verified_seed_rows
from silver_handoff import prepare_hl7_canonical_handoff
from candidate_transport import prepare_hl7_candidate_transport
from write_staging_delta import _spark, _warehouse
import fhir_ingest_notebook as native


def main() -> None:
    manifest_path = Path(os.environ["HL7_LOCAL_MANIFEST_PATH"])
    original = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(original).hexdigest()
    source_dir = manifest_path.parent / "staged-local-blob-keys"
    request = "johnscreek-hl7-gh-12345678901"
    rows = verified_seed_rows(
        original, source_dir, manifest_sha256=manifest_sha,
        source_sha256="a" * 64, request_id=request,
        ingest_date="2026-11-07", processing_run_id="synthetic-v2-001",
        processed_at="2026-11-07 13:00:00")
    if (len(rows) != 17
            or Counter(item["event_type"] for item in rows) !=
               {"A01": 10, "A03": 7}
            or len({item["source_encounter_id"] for item in rows}) != 10):
        raise RuntimeError("HL7_V2_TEN_SYNTHETIC_RAW_EVENT_COUNT_HOLD")
    manifest = json.loads(original)
    receipts = {
        o["blob_key"]: (o["sha256"], o["size_bytes"])
        for o in manifest["objects"]
    }
    if len(receipts) != 17:
        raise RuntimeError("HL7_V2_TEN_RAW_PROVENANCE_COLLISION")
    print("HL7_V2_TEN_PATIENTS_A01_10_A03_7_RAW_PROVENANCE=PASS")

    spark = _spark(_warehouse(os.environ["HL7_LOCAL_WAREHOUSE_URI"]))
    try:
        if spark.conf.get("spark.sql.session.timeZone") != "UTC":
            raise RuntimeError("HL7_V2_TEN_SPARK_TIMEZONE_CHANGED")
        data = {}
        for table, count in (
            ("hl7_staging.hl7_events", 17),
            ("hl7_candidate.canonical_patient", 10),
            ("hl7_candidate.canonical_encounter", 10),
        ):
            detail = spark.sql(f"DESCRIBE DETAIL {table}").first().asDict()
            uri = urlparse(detail["location"])
            if (detail["format"] != "delta" or uri.scheme not in ("", "file")
                    or not (Path(uri.path) / "_delta_log").is_dir()):
                raise RuntimeError("HL7_V2_TEN_NOT_PHYSICAL_DELTA:" + table)
            df = spark.table(table)
            if df.count() != count:
                raise RuntimeError("HL7_V2_TEN_PHYSICAL_COUNT_HOLD:" + table)
            data[table] = df

        pframe = data["hl7_candidate.canonical_patient"]
        eframe = data["hl7_candidate.canonical_encounter"]
        pc = (ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes()
        ec = (ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes()
        for entity, df, raw in (
            ("patient", pframe, pc), ("encounter", eframe, ec)):
            schema = load_pinned_contract(raw, entity)
            want = [(f["name"], f["type"]) for f in schema["fields"]]
            got = [(f.name, f.dataType.simpleString()) for f in df.schema.fields]
            if want != got:
                raise RuntimeError("HL7_V2_TEN_CANONICAL_CONTRACT_FIELD_HOLD:" + entity)
            for f in schema["fields"]:
                if not f["nullable"] and df.filter(df[f["name"]].isNull()).limit(1).count():
                    raise RuntimeError("HL7_V2_TEN_REQUIRED_FIELD_NULL:" + f["name"])

        raw_patients = [r.asDict(recursive=True) for r in pframe.collect()]
        raw_encounters = [r.asDict(recursive=True) for r in eframe.collect()]
        expect_person = {"patient-" + str(i).zfill(2) for i in range(1, 11)}
        expect_enc = {"visit-" + str(i).zfill(2) for i in range(1, 11)}
        if ({r["source_record_id"] for r in raw_patients} != expect_person
                or {r["source_encounter_id"] for r in raw_encounters} != expect_enc
                or {r["source_person_id"] for r in raw_encounters} != expect_person):
            raise RuntimeError("HL7_V2_TEN_MULTI_PERSON_IDENTITY_HOLD")
        if any(r["source_code"] != "IMP" for r in raw_encounters):
            raise RuntimeError("HL7_V2_TEN_CLINICAL_CLASS_CHANGED")
        if sum(r["end_datetime"] is None for r in raw_encounters) != 3:
            raise RuntimeError("HL7_V2_TEN_A03_NOT_ELIGIBLE_COUNT_HOLD")
        if any(r["start_datetime"] >= r["end_datetime"]
               for r in raw_encounters if r["end_datetime"] is not None):
            raise RuntimeError("HL7_V2_TEN_REVERSED_VISIT_TIME")

        first = raw_patients[0]
        observed_at = first["processed_at"]
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        else:
            observed_at = observed_at.astimezone(timezone.utc)
        context = BatchContext(
            hospital_id="johns-creek-hospital-b",
            feed_id="johns-creek-hospital-b-hl7-v2",
            source_system="johns-creek-hl7",
            request_id=request,
            manifest_sha256=manifest_sha,
            processing_version="hl7-canonical-v1-hosted-ten-patient",
            processing_run_id=first["processing_run_id"],
            source_version=first["source_version"],
            source_ingest_date=first["source_ingest_date"],
            processed_at=observed_at,
            adapter_version=first["adapter_version"],
        )
        result = prepare_hl7_canonical_handoff(
            raw_patients, raw_encounters, context=context,
            patient_contract_bytes=pc, encounter_contract_bytes=ec,
            spark_timestamp_timezone="UTC")
        if (result.status != "CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED"
                or result.metrics["patient_accepted"] != 10
                or result.metrics["encounter_accepted"] != 10
                or any(result.metrics[k] for k in (
                    "patient_rejected", "patient_quarantined",
                    "encounter_rejected", "encounter_quarantined"))):
            raise RuntimeError("HL7_V2_TEN_SHARED_DQ_NOT_PASS")

        bundle = prepare_hl7_candidate_transport(
            result, context=context,
            patient_contract_bytes=pc, encounter_contract_bytes=ec)
        pinned = hashlib.sha256(bundle["candidate_manifest.json"]).hexdigest()
        kwargs = dict(
            spark=spark, bundle=bundle, bundle_manifest_sha256=pinned,
            context=context, patient_contract_bytes=pc,
            encounter_contract_bytes=ec, source_evidence_verified=True)
        prepared = native.prepare_hl7_candidate_bundle_for_silver(**kwargs)
        if (prepared.patient_count != 10 or prepared.encounter_count != 10
                or prepared.publication_id is None):
            raise RuntimeError("HL7_V2_TEN_TRANSFER_ADMISSION_HOLD")
        corrupted = dict(bundle)
        corrupted["canonical_encounter.json"] += b" "
        try:
            native.prepare_hl7_candidate_bundle_for_silver(
                **{**kwargs, "bundle": corrupted})
        except ValueError as exc:
            if not str(exc).startswith("HOLD_HL7_BUNDLE_"):
                raise
        else:
            raise RuntimeError("HL7_V2_TEN_TRANSFER_MUTATION_ACCEPTED")

        local_prefix = (
            os.environ["HL7_LOCAL_WAREHOUSE_URI"].rstrip("/") +
            "/ephemeral-ten-silver/" + context.source_batch_id)
        paths = {
            "patient": local_prefix + "/canonical_patient",
            "encounter": local_prefix + "/canonical_encounter",
            "approval": local_prefix + "/silver_approval",
            "quarantine": local_prefix + "/quarantine",
        }
        def readback(p, e, batch, scope):
            native._hl7_reopened_dq(p, e, batch, scope, pc, ec)
        approval = native._write_verified_canonical_silver(
            spark, context=context, batch=prepared, paths=paths,
            patient_contract_bytes=pc, encounter_contract_bytes=ec,
            source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
            validate_persisted_canonical=readback)
        if (approval.get("status") != "SILVER_APPROVED"
                or approval["patient_count"] != 10
                or approval["encounter_count"] != 10):
            raise RuntimeError("HL7_V2_TEN_APPROVAL_LAST_HOLD")
        if (spark.read.format("delta").load(paths["approval"]).count() != 1
                or spark.read.format("delta").load(paths["patient"]).count() != 10
                or spark.read.format("delta").load(paths["encounter"]).count() != 10):
            raise RuntimeError("HL7_V2_TEN_PERSISTED_DELTA_COUNT_DRIFT")
        # Explicitly drop ephemeral Candidate to verify replay cold from
        # physical Delta, pinned original source receipts and Approval only.
        del bundle
        del kwargs
        cold = native._hl7_recompute_persisted_approval(
            spark, paths, context, pc, ec, receipts, pinned)
        if (cold.publication_id != prepared.publication_id
                or cold.patient_count != 10 or cold.encounter_count != 10):
            raise RuntimeError("HL7_V2_TEN_COLD_SILVER_REPLAY_HOLD")
        try:
            native._write_verified_canonical_silver(
                spark, context=context, batch=prepared, paths=paths,
                patient_contract_bytes=pc, encounter_contract_bytes=ec,
                source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
                validate_persisted_canonical=readback)
        except ValueError as exc:
            if "HOLD_SILVER_EXISTING_OR_PARTIAL_DELTA" not in str(exc):
                raise
        else:
            raise RuntimeError("HL7_V2_TEN_REPLAY_OVERWRITE_NOT_BLOCKED")
        print("HL7_V2_TEN_PATIENT_SHARED_DQ_AND_SHA_TRANSFER=PASS")
        print("HL7_V2_TEN_LOCAL_PHYSICAL_SILVER_APPROVAL_LAST_COLD_REPLAY=PASS")
        print("HL7_V2_TEN_REMOTE_FABRIC_SILVER_APPROVED=NO")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
