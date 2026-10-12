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


if __name__ == "__main__":
    unittest.main()
