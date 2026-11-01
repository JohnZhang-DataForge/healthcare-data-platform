"""P2 OFFLINE ONLY: synthetic Manifest, exact SHA, PySpark canonical and readback DQ."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from pyspark.sql import SparkSession, functions as F
from healthcare_data_engine import BatchContext, SourceObject

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
SRC = HERE / "fhir_ingest_notebook.py"
NATIVE = HERE / "native_item_readiness.py"
sys.path.insert(0, str(HERE))
import fhir_ingest_notebook as ingest
import native_item_readiness as readiness

PATIENT = ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json"
ENCOUNTER = ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json"
FIXTURE = ROOT / "shared-data-engine/tests/fixtures/fhir_r4/patient_encounters_bundle.json"


def make_batch(resource=None, *, hospital="hospital-a", request_id="offline-request"):
    source_bytes = json.dumps(resource or json.loads(FIXTURE.read_text()), sort_keys=True).encode()
    source = SourceObject.from_bytes(
        "fhir/synthetic-patient-encounters.json", source_bytes,
        hospital_id=hospital, feed_id="fhir-r4", source_system="synthetic")
    manifest = json.dumps({
        "hospital_id": hospital, "feed_id": "fhir-r4", "source_system": "synthetic",
        "request_id": request_id,
        "objects": [{
            "path": source.source_file, "sha256": source.sha256,
            "size_bytes": source.size_bytes,
        }],
    }, sort_keys=True, separators=(",", ":")).encode()
    context = BatchContext(
        hospital_id=hospital, feed_id="fhir-r4", source_system="synthetic",
        request_id=request_id, manifest_sha256=hashlib.sha256(manifest).hexdigest(),
        processing_version="shared-0.1.0:canonical-v1:code-sha",
        processing_run_id="offline-p2-run-a", source_version="FHIR_R4",
        source_ingest_date=date(2026, 10, 31),
        processed_at=datetime(2026, 10, 31, 12, tzinfo=timezone.utc),
    )
    return context, manifest, source


class ManifestGuards(unittest.TestCase):
    def test_good_manifest_receipt_and_replay_stability(self):
        ctx, manifest, source = make_batch()
        receipts = ingest.verify_source_objects(manifest, (source,), ctx)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["sha256"], source.sha256)
        self.assertEqual(ctx.source_batch_id, replace(
            ctx, processed_at=ctx.processed_at + timedelta(hours=1)).source_batch_id)

    def test_wrong_manifest_sha_hold(self):
        ctx, manifest, obj = make_batch()
        with self.assertRaisesRegex(ValueError, "MANIFEST_SHA256_CONFLICT_HOLD"):
            ingest.verify_source_objects(manifest + b" ", (obj,), ctx)

    def test_source_bytes_wrong_size_sha_and_unlisted_path(self):
        ctx, manifest, obj = make_batch()
        corrupt = SourceObject(obj.source_file, obj.payload + b"x", obj.sha256,
                               obj.size_bytes, obj.hospital_id, obj.feed_id, obj.source_system)
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH|SOURCE_SIZE_MISMATCH"):
            ingest.verify_source_objects(manifest, (corrupt,), ctx)
        wrong_path = replace(obj, source_file="fhir/other.json")
        with self.assertRaisesRegex(ValueError, "MANIFEST_SOURCE_PATH_SET_MISMATCH"):
            ingest.verify_source_objects(manifest, (wrong_path,), ctx)

    def test_cross_hospital_and_feed_rejected(self):
        ctx, manifest, obj = make_batch()
        with self.assertRaisesRegex(ValueError, "CROSS_HOSPITAL_SOURCE_CONFLICT"):
            ingest.verify_source_objects(manifest, (replace(obj, hospital_id="another-hospital"),), ctx)
        with self.assertRaisesRegex(ValueError, "CROSS_FEED_SOURCE_CONFLICT"):
            ingest.verify_source_objects(manifest, (replace(obj, feed_id="legacy-feed"),), ctx)

    def test_duplicate_manifest_name_and_path_traversal_hold(self):
        ctx, manifest, obj = make_batch()
        payload = json.loads(manifest)
        payload["objects"].append(payload["objects"][0])
        amended = json.dumps(payload).encode()
        with self.assertRaisesRegex(ValueError, "DUPLICATE_MANIFEST_OBJECT_PATH"):
            ingest._manifest_objects(amended, replace(ctx, manifest_sha256=hashlib.sha256(amended).hexdigest()))
        payload["objects"] = [dict(payload["objects"][0], path="../secrets.env")]
        amended = json.dumps(payload).encode()
        with self.assertRaisesRegex(ValueError, "MANIFEST_OBJECT_PATH_INVALID"):
            ingest._manifest_objects(amended, replace(ctx, manifest_sha256=hashlib.sha256(amended).hexdigest()))

    def test_no_cloud_execution_even_with_input(self):
        ctx, manifest, obj = make_batch()
        result = ingest.execute_native_notebook(
            object(), context=ctx, manifest_bytes=manifest,
            source_root="Files/bronze", silver_root="Tables/silver",
            patient_contract_bytes=b"forbidden", encounter_contract_bytes=b"forbidden")
        self.assertEqual(result.status, "HOLD_NO_CLOUD_WRITE_AUTHORIZATION")

    def test_native_items_exported_runtime_still_hold(self):
        root = ROOT / "azure-fabric/workspaces/healthcare-omop"
        result = readiness.check_native_export(root)
        self.assertEqual(result.state, "HOLD_NATIVE_RUNTIME_DEPLOYMENT")
        self.assertEqual(len(result.reasons), 1)


class OfflineSparkCanonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]").appName("fabric-p2-offline-synthetic")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.session.timeZone", "UTC")
                     .getOrCreate())

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def prepared(self, ctx=None, manifest=None, source=None):
        if ctx is None:
            ctx, manifest, source = make_batch()
        return ingest.prepare_batch(self.spark, context=ctx, manifest_bytes=manifest,
                                    source_objects=(source,),
                                    patient_contract_bytes=PATIENT.read_bytes(),
                                    encounter_contract_bytes=ENCOUNTER.read_bytes())

    def test_shared_engine_effective_package_version_is_pinned_to_011(self):
        from unittest.mock import patch
        from healthcare_data_engine import __version__ as installed_version
        self.assertEqual(installed_version, "0.1.1")
        self.assertEqual(ingest.engine_version, installed_version)
        # A stale 0.1.0 Spark session must fail *before* constructing any
        # dataframes. adapter_version remains a distinct canonical wire format.
        context, manifest, obj = make_batch()
        with patch.object(ingest, "engine_version", "0.1.0"):
            with self.assertRaisesRegex(ValueError,
                                        "SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH"):
                self.prepared(context, manifest, obj)

    def test_engine_011_published_version_required_and_legacy_010_rejected(self):
        # The business Adapter contract remains independently versioned at
        # 0.1.0; the PACKAGE version must match Fabric Environment 0.1.1.
        self.assertEqual(ingest.engine_version, "0.1.1")
        ctx, manifest, obj = make_batch()
        with patch.dict(ingest.prepare_batch.__globals__, {"engine_version": "0.1.0"}):
            with self.assertRaisesRegex(ValueError, "SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH"):
                self.prepared(ctx, manifest, obj)
        # Return to actual Wheel 0.1.1, and verify synthetic canonical output
        # maintains its separate data-record adapter_version contract 0.1.0.
        batch = self.prepared(ctx, manifest, obj)
        self.assertEqual(batch.patient_df.select("adapter_version").first()[0], "0.1.0")
        self.assertEqual(batch.encounter_df.select("adapter_version").first()[0], "0.1.0")

    def test_synthetic_patient_encounter_spark_schema_pk_fk_and_readback(self):
        ctx, manifest, source = make_batch()
        prepared = self.prepared(ctx, manifest, source)
        self.assertTrue(prepared.acceptable)
        self.assertEqual((prepared.patient_count, prepared.encounter_count), (1, 2))
        self.assertEqual(prepared.patient_df.count(), 1)
        self.assertEqual(prepared.encounter_df.count(), 2)
        ingest.validate_silver_readback(prepared.patient_df, prepared.encounter_df, prepared, ctx)

    def test_publication_deterministic_across_run_time_and_run_id(self):
        ctx, manifest, source = make_batch()
        base = self.prepared(ctx, manifest, source)
        replay_ctx = replace(ctx, processing_run_id="different-run-id",
                             processed_at=ctx.processed_at + timedelta(days=1))
        replay = self.prepared(replay_ctx, manifest, source)
        self.assertEqual(base.publication_id, replay.publication_id)
        self.assertEqual(base.source_batch_id, replay.source_batch_id)
        self.assertNotEqual(base.source_batch_id, base.publication_id)

    def test_missing_dob_yields_quarantine_and_orphan_fk_not_approved(self):
        data = json.loads(FIXTURE.read_text())
        data["entry"][0]["resource"].pop("birthDate")
        ctx, manifest, obj = make_batch(data)
        batch = self.prepared(ctx, manifest, obj)
        self.assertEqual(batch.patient_count, 0)
        self.assertEqual(batch.encounter_count, 0)
        self.assertFalse(batch.acceptable)
        self.assertIn("PATIENT_CANONICAL_V1_INCOMPATIBLE", {x.reason for x in batch.findings})
        self.assertIn("ENCOUNTER_PATIENT_NOT_ACCEPTED", {x.reason for x in batch.findings})

    def test_duplicate_resource_fails_closed(self):
        data = json.loads(FIXTURE.read_text())
        data["entry"].append(data["entry"][0])
        ctx, manifest, obj = make_batch(data)
        batch = self.prepared(ctx, manifest, obj)
        self.assertFalse(batch.acceptable)
        self.assertIn("DUPLICATE_RESOURCE_ID", {x.reason for x in batch.findings})

    def test_pyspark_readback_rejects_corrupt_fk(self):
        ctx, manifest, obj = make_batch()
        batch = self.prepared(ctx, manifest, obj)
        wrong = batch.encounter_df.withColumn("source_person_id", F.lit("does-not-exist"))
        with self.assertRaisesRegex(ValueError, "SILVER_READBACK_PATIENT_ENCOUNTER_FK"):
            ingest.validate_silver_readback(batch.patient_df, wrong, batch, ctx)

    def test_pyspark_readback_rejects_count_and_version(self):
        ctx, manifest, obj = make_batch()
        batch = self.prepared(ctx, manifest, obj)
        with self.assertRaisesRegex(ValueError, "SILVER_READBACK_ROW_COUNT_MISMATCH"):
            ingest.validate_silver_readback(batch.patient_df.limit(0), batch.encounter_df, batch, ctx)
        wrong = batch.patient_df.withColumn("canonical_version", F.lit("v2"))
        with self.assertRaisesRegex(ValueError, "SILVER_READBACK_VERSION_OR_NAMESPACE"):
            ingest.validate_silver_readback(wrong, batch.encounter_df, batch, ctx)

    def test_spark_schema_uses_no_fabric_extensions_or_second_wheel(self):
        ctx, manifest, obj = make_batch()
        batch = self.prepared(ctx, manifest, obj)
        self.assertEqual(batch.patient_df.schema.fieldNames()[:2],
                         ["source_record_id", "birth_date"])
        self.assertEqual(batch.encounter_df.schema.fieldNames()[:3],
                         ["source_encounter_id", "source_person_id", "start_datetime"])


if __name__ == "__main__":
    unittest.main()
