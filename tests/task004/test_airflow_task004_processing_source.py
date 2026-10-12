import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DAG = (
    ROOT
    / "airflow/dags/task004_processing_pipeline.py"
)

RBAC = (
    ROOT
    / "kubernetes/manifests/task004/"
    "airflow-task004-control-runtime-rbac.yaml"
)


class Task004AirflowProcessingSourceTests(
    unittest.TestCase
):

    def test_dag_uses_kubernetes_pod_operator(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "KubernetesPodOperator",
            'dag_id="task004_processing_pipeline"',
            'namespace=CONTROL_NAMESPACE',
            'service_account_name=CONTROL_SERVICE_ACCOUNT',
            'in_cluster=True',
            'do_xcom_push=True',
            'on_finish_action="delete_succeeded_pod"',
            'on_kill_action="keep_pod"',
            "is_paused_upon_creation=False",
            "/airflow/xcom/return.json",
            'task_id="generate_publish"',
            "generate_publish >> [person, visit]",
            "[person, visit] >> reconcile",
        ):
            self.assertIn(
                value,
                source,
            )


    def test_dag_pins_mainline_runtime_digest(self):
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


    def test_dag_uses_dynamic_processing_outputs(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "processing_data_uri",
            "canonical_rows",
            "xcom_pull(task_ids='person')",
            "xcom_pull(task_ids='visit')",
            '"PATIENT_PROCESSING_URI"',
            '"ENCOUNTER_PROCESSING_URI"',
        ):
            self.assertIn(
                value,
                source,
            )


    def test_generate_publish_feeds_processing_lineage(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "GENERATE_PUBLISH_COMMAND",
            "GENERATE_PUBLISH_ENV",
            'task004-runtime generate-publish',
            '"source_version":',
            '"manifest_uri":',
            '"manifest_sha256":',
            '"verified_file_count":',
            "xcom_pull(task_ids='generate_publish')",
            "generate_publish >> [person, visit]",
        ):
            self.assertIn(
                value,
                source,
            )


    def test_historical_landing_manifest_is_not_hardcoded(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "task004-p20-first-landing-20261011",
            "d7a1ce5fb3cc1e25737b2ed5c35b7d463bbc8e7523b6531dcd1ce819360ff445",
            "ingest_date=2026-10-11",
        ):
            self.assertNotIn(
                value,
                source,
            )


    def test_generate_publish_batch_identity_is_airflow_run_scoped(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"BATCH_ID": (',
            source,
        )

        self.assertIn(
            "{{ run_id ",
            source,
        )

        self.assertIn(
            '"REFERENCE_DATE": "{{ ds_nodash }}"',
            source,
        )

        self.assertIn(
            '"LANDING_INGEST_DATE": "{{ ds }}"',
            source,
        )


    def test_airflow_scheduler_has_pod_launcher_rbac(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        for value in (
            "name: task004-airflow-pod-launcher",
            "namespace: dw-spark",
            "- pods",
            "- pods/log",
            "- pods/exec",
            "- events",
            "name: dw-airflow-scheduler",
            "namespace: dw-airflow",
        ):
            self.assertIn(
                value,
                source,
            )

        self.assertNotIn(
            "kind: ClusterRole",
            source,
        )

        self.assertNotIn(
            "kind: ClusterRoleBinding",
            source,
        )


if __name__ == "__main__":
    unittest.main()
