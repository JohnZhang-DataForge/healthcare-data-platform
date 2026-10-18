"""Standalone read-only Airflow runner tests: no Airflow installation required."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "landing_discovery"))
import run_airflow_scan


class XcomBoundaryTests(unittest.TestCase):
    def test_xcom_is_bounded_and_only_preview(self):
        inventory = {
            "database_mutation": False,
            "processing_authorized": False,
            "ready_count": 26,
            "quarantined_count": 1,
            "ready_batches": [{"batch_id": str(i)} for i in range(26)],
        }
        actual = run_airflow_scan.xcom_preview(inventory)
        self.assertEqual(len(actual["ready_batches_preview"]), 25)
        self.assertTrue(actual["preview_truncated"])
        self.assertEqual(actual["ready_count"], 26)
        self.assertFalse(actual["processing_authorized"])

    def test_mutation_claim_is_not_accepted(self):
        with self.assertRaisesRegex(run_airflow_scan.DiscoveryError, "invariant"):
            run_airflow_scan.xcom_preview({
                "database_mutation": False, "processing_authorized": True,
            })

    def test_xcom_file_stable_and_generated_without_airflow(self):
        original = run_airflow_scan.discover_ready_batches
        def fake(*args, **kwargs):
            return {
                "ready_count": 1, "quarantined_count": 0,
                "database_mutation": False, "processing_authorized": False,
                "ready_batches": [{"batch_id": "existing", "manifest_uri": "s3://health-landing/d"}],
            }
        run_airflow_scan.discover_ready_batches = fake
        try:
            with tempfile.TemporaryDirectory() as tmp:
                file = Path(tmp) / "xcom" / "return.json"
                report = run_airflow_scan.run(s3=object(), bucket="health-landing",
                                              prefix="source=synthea/", xcom_path=file)
                self.assertEqual(json.loads(file.read_text()), report)
                self.assertEqual(report["status"], "READ_ONLY_DISCOVERED")
        finally:
            run_airflow_scan.discover_ready_batches = original


if __name__ == "__main__":
    unittest.main()
