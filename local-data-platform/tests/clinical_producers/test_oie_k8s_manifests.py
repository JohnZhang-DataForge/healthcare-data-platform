"""Static-only OIE Kubernetes manifest safety regression; no Kubernetes API."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "kubernetes/manifests/oie"


class OieIsolationTemplates(unittest.TestCase):
    def setUp(self):
        self.files = {p.name: p.read_text(encoding="utf-8") for p in BASE.glob("*.yaml*")}
        self.assertEqual(
            set(self.files),
            {"namespace.yaml", "pvc.yaml.tpl", "statefulset.yaml.tpl", "service.yaml"},
        )

    def test_namespace_and_distinct_pvc(self):
        self.assertRegex(self.files["namespace.yaml"], r"(?m)^  name: dw-oie$")
        s = self.files["pvc.yaml.tpl"]
        self.assertIn("name: oie-state", s)
        self.assertIn("namespace: dw-oie", s)
        self.assertIn("storageClassName: __OIE_WORKER01_STORAGE_CLASS__", s)
        self.assertNotIn("synthea-new-only-state", s)
        self.assertNotIn("synthea-new-generator-state", s)

    def test_every_oie_pod_is_worker01_only_single_replica(self):
        s = self.files["statefulset.yaml.tpl"]
        self.assertIn("kind: StatefulSet", s)
        self.assertRegex(s, r"(?m)^  replicas: 1$")
        self.assertRegex(s, r"nodeSelector:\s+\n\s+kubernetes.io/hostname: worker01")
        self.assertIn("automountServiceAccountToken: false", s)
        self.assertIn("runAsNonRoot: true", s)
        self.assertIn("allowPrivilegeEscalation: false", s)
        self.assertIn("claimName: oie-state", s)
        self.assertNotIn("hostPath:", s)
        self.assertNotIn("tolerations:", s)

    def test_require_immutable_image_and_external_secret(self):
        s = self.files["statefulset.yaml.tpl"]
        self.assertIn("image: __OIE_PINNED_IMAGE_DIGEST__", s)
        self.assertIn("secretName: oie-bootstrap-properties", s)
        self.assertIn("subPath: mirth_properties", s)
        self.assertIn("mountPath: /run/secrets/mirth_properties", s)
        self.assertNotIn("server.initialadminpassword =", s)
        self.assertNotIn("readOnlyRootFilesystem: true", s)
        self.assertNotIn("envFrom:", s)

    def test_no_public_service(self):
        s = self.files["service.yaml"]
        self.assertIn("type: ClusterIP", s)
        for banned in ("NodePort", "LoadBalancer", "externalIPs", "Ingress"):
            self.assertNotIn(banned + ":", s)
        self.assertIn("port: 8443", s)

    def test_templates_parse_after_safe_nonproduction_placeholder_rendering(self):
        # PyYAML is installed only for static CI, not a production dependency.
        import yaml
        rendered = dict(self.files)
        rendered["pvc.yaml.tpl"] = rendered["pvc.yaml.tpl"].replace(
            "__OIE_WORKER01_STORAGE_CLASS__", "verified-worker01-sc"
        )
        rendered["statefulset.yaml.tpl"] = rendered["statefulset.yaml.tpl"].replace(
            "__OIE_PINNED_IMAGE_DIGEST__",
            "ghcr.io/example/never-deploy@sha256:" + "a" * 64,
        )
        for name, content in rendered.items():
            item = yaml.safe_load(content)
            self.assertIsInstance(item, dict)
            self.assertIn("metadata", item)
            if name != "namespace.yaml":
                self.assertEqual(item["metadata"]["namespace"], "dw-oie")


if __name__ == "__main__":
    unittest.main()
