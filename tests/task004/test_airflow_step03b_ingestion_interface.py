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


class Task004AirflowStep03BTests(
    unittest.TestCase
):

    def test_sources_exist(self):
        self.assertTrue(
            RUNNER.is_file()
        )

        self.assertTrue(
            RBAC.is_file()
        )


    def test_runner_exposes_state_contract(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        for token in (
            '"source_version":',
            'echo "STATE_FILE=${REPORT_FILE}"',
            '"status":',
            '"manifest_uri":',
            '"manifest_sha256":',
            '"ingest_date":',
        ):
            self.assertIn(
                token,
                source,
            )


    def test_runner_keeps_cluster_scope_preflight_out_of_incluster_path(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        start = source.index(
            'if [[ "${TASK004_RUNTIME_CONTEXT:-}" '
            '== "in-cluster" ]]; then'
        )

        secret = source.index(
            "kubectl get secret",
            start,
        )

        block = source[
            start:secret
        ]

        self.assertIn(
            "CLUSTER_SCOPE_PREFLIGHT="
            "SKIPPED_IN_CLUSTER",
            block,
        )

        self.assertIn(
            "else",
            block,
        )

        self.assertIn(
            "kubectl get namespace",
            block,
        )

        self.assertIn(
            'kubectl get node "$NODE"',
            block,
        )


    def test_rbac_is_namespace_scoped(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "namespace: dw-synthea",
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


    def test_rbac_binds_dw_spark_control_runtime(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "name: task004-control-runtime",
            source,
        )

        self.assertIn(
            "namespace: dw-spark",
            source,
        )


    def test_rbac_allows_generate_publish_resources(self):
        source = RBAC.read_text(
            encoding="utf-8"
        )

        for token in (
            "- jobs",
            "- configmaps",
            "- pods",
            "- pods/log",
            "- secrets",
            "- dw-synthea-s3-secret",
        ):
            self.assertIn(
                token,
                source,
            )


if __name__ == "__main__":
    unittest.main()
