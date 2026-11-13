"""G3 read-only physical Delta negative/ACK recovery path tests (offline)."""
from __future__ import annotations
from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from healthcare_data_engine import BatchContext

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))
import fhir_ingest_notebook as nb
from test_g3_bronze_receipt import SparkStub, fixture


REQUEST = "atlanta-fhir-gh-41539769718"


class G3PhysicalProbe(unittest.TestCase):
    def setUp(self):
        raw, sha, sources = fixture(request=REQUEST)
        self.spark = SparkStub(raw)
        context = BatchContext(
            hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4",
            source_system="synthea-fhir", request_id=REQUEST,
            manifest_sha256=sha,
            processing_version="fhir-bronze-raw-snapshot-v1:engine-0.1.1",
            processing_run_id="g3:" + REQUEST,
            source_version="FHIR_R4", source_ingest_date=date(2026, 11, 2),
            processed_at=datetime(2026, 11, 2, tzinfo=timezone.utc))
        specs = nb._manifest_objects(raw, context)
        receipts = nb._expected_bronze_source_receipts(context, specs)
        payloads = {x.source_file: x.payload for x in sources}
        path = nb._bronze_source_receipt_path(REQUEST)
        self.spark.delta[path] = [
            {**x, "source_payload": payloads[x["source_path"]]} for x in receipts]
        self.args = dict(
            request=REQUEST, manifest_sha=sha,
            scenario="BRONZE_DRIFT_PROBE",
            allow_write=False, retention_ok=False,
            strategy="DELTA_RAW_SNAPSHOT_V1",
            manifest_override="", source_override="", target_override="")

    def execute(self, **diff):
        g = nb.verify_fhir_g3_negative_readonly.__globals__
        with patch.dict(g, {
            "_G3_NEGATIVE_MANIFEST_SHA": self.args["manifest_sha"],
            "_delta_snapshot_exists": lambda spark, path: path in spark.delta,
            "_write_delta": lambda df, path: self.fail("read-only probe attempted a write"),
        }):
            return nb.verify_fhir_g3_negative_readonly(
                self.spark, **{**self.args, **diff})

    def test_actual_saved_delta_rejects_counterfactual_same_request_drift(self):
        self.assertEqual(self.execute(),
                         "FHIR_G3_COUNTERFACTUAL_REQUEST_DRIFT_HOLD_5_DELTA_PASS_20261102")

    def test_readonly_unknown_ack_recovery_path_reopens_stored_bytes(self):
        self.assertEqual(
            self.execute(scenario="BRONZE_ACK_RECOVERY_PROBE"),
            "FHIR_G3_READONLY_ACK_RECOVERY_PATH_VERIFIED_5_DELTA_PASS_20261102")

    def test_corrupt_raw_snapshot_never_passes_recovery_or_drift(self):
        path = nb._bronze_source_receipt_path(REQUEST)
        self.spark.delta[path][0]["source_payload"] = b"corrupted"
        for scenario in ("BRONZE_ACK_RECOVERY_PROBE", "BRONZE_DRIFT_PROBE"):
            with self.subTest(scenario=scenario), self.assertRaisesRegex(
                    RuntimeError, "NEGATIVE_BASELINE_DELTA_NOT_VERIFIED"):
                self.execute(scenario=scenario)

    def test_bad_flags_request_manifest_or_roots_rejected_before_delta(self):
        for key, value in (
            ("allow_write", True), ("retention_ok", True),
            ("strategy", "HALT"), ("source_override", "Files/evil"),
            ("target_override", "Tables/evil"),
            ("manifest_override", "{}"), ("request", "atlanta-fhir-gh-12345678"),
            ("manifest_sha", "f" * 64),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                    RuntimeError, "NEGATIVE_READONLY_GATES"):
                self.execute(**{key: value})


if __name__ == "__main__":
    unittest.main()
