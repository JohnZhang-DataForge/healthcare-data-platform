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
            "ready_count": 101,
            "quarantined_count": 1,
            "ready_batches": [{"batch_id": str(i)} for i in range(101)],
        }
        actual = run_airflow_scan.xcom_preview(inventory)
        self.assertEqual(len(actual["ready_batches_preview"]), 100)
        self.assertTrue(actual["preview_truncated"])
        self.assertEqual(actual["ready_count"], 101)
        self.assertFalse(actual["processing_authorized"])

    def test_exact_selection_works_outside_preview_and_is_read_only(self):
        target={"batch_id":"synthea-new-only-gh-new","manifest_uri":"s3://health-landing/example/manifest.json",
                "manifest_sha256":"a"*64,"source":"synthea","source_version":"v3.3.0",
                "status":"INTAKE_VERIFIED","file_count":18}
        inv={"database_mutation":False,"processing_authorized":False,
             "ready_count":101,"quarantined_count":0,
             "ready_batches":[{"batch_id":"synthea-new-only-gh-old-%03d"%i}
                              for i in range(100)]+[target]}
        kw=dict(batch_id=target["batch_id"],manifest_uri=target["manifest_uri"],
                manifest_sha256=target["manifest_sha256"])
        result=run_airflow_scan.xcom_preview(inv,**kw)
        self.assertEqual(len(result["ready_batches_preview"]),100)
        self.assertTrue(result["preview_truncated"])
        self.assertEqual(result["verified_selected_batch"],target)
        self.assertNotIn(target,result["ready_batches_preview"])
        self.assertFalse(result["processing_authorized"])
        self.assertFalse(result["database_mutation"])
        for changes in ({"batch_id":"synthea-new-only-gh-missing"},
                        {"manifest_uri":"s3://health-landing/other/manifest.json"},
                        {"manifest_sha256":"f"*64},
                        {"manifest_sha256":None}):
            with self.subTest(changes=changes),self.assertRaises(run_airflow_scan.DiscoveryError):
                run_airflow_scan.xcom_preview(inv,**(kw|changes))
        # Existing preview-only users remain unaffected.
        self.assertNotIn("verified_selected_batch",run_airflow_scan.xcom_preview(inv))

    def test_26_ready_batches_are_fully_visible_below_100_cap(self):
        inv={"database_mutation":False,"processing_authorized":False,
             "ready_count":26,"quarantined_count":0,
             "ready_batches":[{"batch_id":"synthea-new-only-gh-%02d"%i}
                              for i in range(26)]}
        x=run_airflow_scan.xcom_preview(inv)
        self.assertEqual(len(x["ready_batches_preview"]),26)
        self.assertFalse(x["preview_truncated"])
        self.assertEqual(x["ready_count"],26)

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
