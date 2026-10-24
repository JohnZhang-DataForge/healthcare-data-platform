"""Static-only Kubernetes namespace boundary assertions. Does NOT use kubectl."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "kubernetes" / "manifests" / "azure-blob"


class AzureBlobNamespaceStaticTests(unittest.TestCase):
    def test_namespace_is_dedicated_and_restricted(self):
        yaml = (MANIFESTS / "namespace.yaml").read_text(encoding="utf-8")
        self.assertIn("kind: Namespace\n", yaml)
        self.assertIn("  name: dw-az-blob\n", yaml)
        self.assertIn("pod-security.kubernetes.io/enforce: restricted", yaml)
        self.assertNotIn("dw-synthea\n", yaml)
        self.assertNotIn("kind: Secret", yaml)

    def test_network_policy_is_default_deny_only(self):
        yaml = (MANIFESTS / "networkpolicy-default-deny.yaml").read_text(
            encoding="utf-8")
        self.assertIn("kind: NetworkPolicy\n", yaml)
        self.assertIn("  namespace: dw-az-blob\n", yaml)
        self.assertIn("  podSelector: {}\n", yaml)
        self.assertIn("    - Ingress\n    - Egress\n", yaml)
        self.assertNotIn("  ingress:", yaml)
        self.assertNotIn("  egress:", yaml)

    def test_handoff_never_cross_mounts_existing_pvc(self):
        # Static namespace templates may NEVER declare a namespaced PVC that
        # is owned by dw-synthea. Explicit readback transport is separate.
        for path in MANIFESTS.glob("*.yaml"):
            yaml = path.read_text(encoding="utf-8")
            self.assertNotIn("persistentVolumeClaim:", yaml, str(path))
            self.assertNotIn("hostPath:", yaml, str(path))
            self.assertNotIn("kind: Pod", yaml, str(path))
            self.assertNotIn("kind: Job", yaml, str(path))
            self.assertNotIn("valueFrom:\n    secretKeyRef:", yaml, str(path))


if __name__ == "__main__":
    unittest.main()
