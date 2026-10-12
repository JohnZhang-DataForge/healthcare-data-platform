import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DAG = (
    ROOT
    / "airflow/dags/task004_processing_pipeline.py"
)


class Task004AirflowStep03CSourceTests(
    unittest.TestCase
):

    def test_upstream_task_exists(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for token in (
            'task_id="generate_publish"',
            "GENERATE_PUBLISH_COMMAND",
            "GENERATE_PUBLISH_ENV",
            "do_xcom_push=True",
        ):
            self.assertIn(
                token,
                source,
            )


    def test_generate_publish_state_contract_is_xcom_safe(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for token in (
            'state["status"] == "INTAKE_VERIFIED"',
            'state["source_version"] == "v3.3.0"',
            'state["verified_file_count"] == 18',
            'state["report_source"] == "POD_LOG"',
            'state["landing_uri"]',
            'state["manifest_uri"]',
            'state["manifest_sha256"]',
            '"/airflow/xcom/return.json"',
        ):
            self.assertIn(
                token,
                source,
            )


    def test_processing_consumes_generate_publish_xcom(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for token in (
            "xcom_pull(task_ids='generate_publish')",
            "['batch_id']",
            "['manifest_uri']",
            "['manifest_sha256']",
            "PROCESSING_ENV",
        ):
            self.assertIn(
                token,
                source,
            )


    def test_dependency_graph_is_upstream_then_parallel_then_reconcile(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "generate_publish >> [person, visit]",
            source,
        )

        self.assertIn(
            "[person, visit] >> reconcile",
            source,
        )


    def test_dag_has_no_historical_manifest_params(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for token in (
            '"manifest_uri": (',
            '"manifest_sha256": (',
            '"batch_id":',
            "task004-p20-first-landing-20261011",
        ):
            self.assertNotIn(
                token,
                source,
            )


    def test_generate_publish_outer_pod_does_not_receive_s3_secret(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        start = source.index(
            "generate_publish = control_pod("
        )

        end = source.index(
            "    person = control_pod(",
            start,
        )

        block = source[
            start:end
        ]

        self.assertNotIn(
            "secrets=[",
            block,
        )


    def test_runtime_is_pinned_to_step03b_main_image(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "9438df07c495c5a408a856fbe8091f93"
            "b8ef1d1b2402645b37a71a42618f4ed0",
            source,
        )

        self.assertNotIn(
            ":latest",
            source,
        )


if __name__ == "__main__":
    unittest.main()
