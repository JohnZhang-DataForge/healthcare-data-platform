"""Static gates for scheduled read-only Landing discovery."""
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

    def test_read_only_scheduled_dag(self):
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
        ]:
            self.assertIn(token, s)
        self.assertNotIn("generate_publish", s)
        self.assertNotIn("task004_processing_pipeline", s)
        self.assertNotIn("SparkApplication", s)
        self.assertNotIn("cdm.person", s)
        self.assertNotIn("PostgresOperator", s)

    def test_pinned_immutable_discovery_image(self):
        self.assertRegex(self.source, r'@sha256:[a-f0-9]{64}')
        self.assertIn("healthcare-landing-discovery", self.source)
        self.assertNotIn("latest", self.source)


if __name__ == "__main__":
    unittest.main()
