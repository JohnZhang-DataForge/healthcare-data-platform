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
            "/airflow/xcom/return.json",
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
            "bf7f4611a9dcbd8bd79b420f80c5f97"
            "f4ec92e0dbd5ba8132cea4be59fdf57bf",
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
