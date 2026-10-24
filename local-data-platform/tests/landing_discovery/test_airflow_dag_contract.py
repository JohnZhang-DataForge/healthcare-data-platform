"""Static gates for discovery -> guarded Claim scheduled Airflow DAG."""
import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
DAG_FILE = ROOT / "airflow" / "dags" / "landing_batch_discovery.py"


class ScheduledDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DAG_FILE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_scheduled_discovery_then_guarded_claim(self):
        s = self.source
        for token in [
            'dag_id="landing_batch_discovery"',
            'schedule="*/15 * * * *"',
            "is_paused_upon_creation=True",
            'task_id="scan_ready_manifests"',
            "KubernetesPodOperator(",
            "do_xcom_push=True",
            '"dw-spark-s3-secret"',
            '"worker02"',
            'task_id="evaluate_batch_claims"',
            'scan_ready_manifests >> evaluate_batch_claims',
            '"CLAIM_ENABLE": "NO"',
            '"CLAIM_ALLOWLIST": ""',
            '"landing-claim-db"',
        ]:
            self.assertIn(token, s)
        self.assertNotIn("generate_publish", s)
        self.assertNotIn("task004_processing_pipeline", s)
        self.assertNotIn("SparkApplication", s)
        self.assertNotIn("cdm.person", s)
        self.assertNotIn("PostgresOperator", s)

    def test_both_images_use_current_development_release(self):
        self.assertIn("healthcare-landing-discovery", self.source)
        self.assertIn("healthcare-landing-claim", self.source)
        self.assertEqual(self.source.count('":latest"'), 2)
        self.assertEqual(self.source.count('image_pull_policy="Always"'), 2)
        self.assertNotIn("@sha256:", self.source)


if __name__ == "__main__":
    unittest.main()
