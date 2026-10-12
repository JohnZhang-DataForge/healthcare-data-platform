import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RUNNER = (
    ROOT
    / "scripts/task004/"
    "04c-run-synthea-generate-publish.sh"
)

RBAC = (
    ROOT
    / "kubernetes/manifests/task004/"
    "control-runtime-synthea-rbac.yaml"
)

FULL_DAG = (
    ROOT
    / "airflow/dags/task004_full_pipeline.py"
)

PROCESSING_DAG = (
    ROOT
    / "airflow/dags/task004_processing_pipeline.py"
)


class Task004AirflowUpstreamSourceTests(
    unittest.TestCase
):

    def test_generate_publish_has_incluster_mode(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'TASK004_RUNTIME_CONTEXT="${TASK004_RUNTIME_CONTEXT:-manual}"',
            source,
        )

        self.assertIn(
            'in-cluster)',
            source,
        )

        self.assertIn(
            "TASK004_GENERATE_PUBLISH_CLUSTER_PREFLIGHT=SKIPPED_IN_CLUSTER",
            source,
        )


    def test_incluster_branch_has_no_cluster_scope_preflight(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        start = source.index(
            "  in-cluster)"
        )

        end = source.index(
            "  manual)",
            start,
        )

        incluster = source[
            start:end
        ]

        self.assertNotIn(
            "kubectl get namespace",
            incluster,
        )

        self.assertNotIn(
            "kubectl get node",
            incluster,
        )


    def test_manual_branch_retains_cluster_preflight(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        start = source.index(
            "  manual)"
        )

        end = source.index(
            "  *)",
            start,
        )

        manual = source[
            start:end
        ]

        self.assertIn(
            "kubectl get namespace",
            manual,
        )

        self.assertIn(
            "kubectl get node",
            manual,
        )


    def test_synthea_rbac_is_namespaced(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        for value in (
            "name: task004-control-runtime-synthea",
            "namespace: dw-synthea",
            "kind: Role",
            "kind: RoleBinding",
            "- jobs",
            "- configmaps",
            "- pods",
            "- pods/log",
            "- dw-synthea-s3-secret",
            "name: task004-control-runtime",
            "namespace: dw-spark",
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

        self.assertNotIn(
            'resources:\n      - "*"',
            source,
        )

        self.assertNotIn(
            'verbs:\n      - "*"',
            source,
        )


    def test_synthea_rbac_does_not_grant_cluster_resources(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "- nodes",
            source,
        )

        self.assertNotIn(
            "- namespaces",
            source,
        )


    def test_full_dag_is_separate_from_processing_baseline(self):
        self.assertTrue(
            FULL_DAG.is_file()
        )

        self.assertTrue(
            PROCESSING_DAG.is_file()
        )

        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'dag_id="task004_full_pipeline"',
            source,
        )

        self.assertNotIn(
            'dag_id="task004_processing_pipeline"',
            source,
        )


    def test_full_dag_pins_step03_runtime_digest(self):
        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "cc5ce5238a31f78974e8204ff2081c79"
            "bb5639e9caa83e76cdd00ad3ab8e071f",
            source,
        )

        self.assertNotIn(
            ":latest",
            source,
        )


    def test_generate_publish_is_kpo_with_xcom(self):
        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "KubernetesPodOperator",
            'task_id="generate_publish"',
            "task004-runtime generate-publish",
            "/airflow/xcom/return.json",
            "MANIFEST_URI",
            "MANIFEST_SHA256",
            "LANDING_URI",
            'do_xcom_push=True',
        ):
            self.assertIn(
                value,
                source,
            )


    def test_manifest_lineage_flows_dynamically_to_processing(self):
        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            "xcom_pull(task_ids='generate_publish')",
            "['manifest_uri']",
            "['manifest_sha256']",
            '"MANIFEST_URI"',
            '"MANIFEST_SHA256"',
        ):
            self.assertIn(
                value,
                source,
            )


    def test_full_dag_preserves_processing_dependency_shape(self):
        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        for value in (
            'task_id="person"',
            'task_id="visit"',
            'task_id="reconcile"',
            "generate_publish >> [",
            "] >> reconcile",
            "xcom_pull(task_ids='person')",
            "xcom_pull(task_ids='visit')",
        ):
            self.assertIn(
                value,
                source,
            )


    def test_full_dag_defaults_unpaused(self):
        source = FULL_DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "is_paused_upon_creation=False",
            source,
        )


if __name__ == "__main__":
    unittest.main()
