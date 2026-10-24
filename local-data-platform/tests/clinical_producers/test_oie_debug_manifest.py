"""Static-only assurance: disposable OIE never creates a PVC."""
from pathlib import Path
import unittest
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "kubernetes" / "manifests" / "oie" / "debug"


class DebugOieManifestTests(unittest.TestCase):
    def test_template_boundary_and_worker(self):
        names = {p.name for p in DIR.iterdir() if p.is_file() and p.suffix in (".tpl", ".yaml")}
        self.assertEqual(names, {"deployment.yaml.tpl", "service.yaml"})
        d = (DIR / "deployment.yaml.tpl").read_text()
        s = (DIR / "service.yaml").read_text()
        self.assertIn("kind: Deployment", d)
        self.assertIn("name: oie-debug", d)
        self.assertIn("namespace: dw-oie", d)
        self.assertIn("replicas: 1", d)
        self.assertIn("type: Recreate", d)
        self.assertRegex(d, r"nodeSelector:\n\s+kubernetes.io/hostname: worker01")
        self.assertIn("automountServiceAccountToken: false", d)
        self.assertIn("emptyDir:", d)
        self.assertIn("sizeLimit: 4Gi", d)
        self.assertIn("mountPath: /opt/engine/appdata", d)
        self.assertNotIn("persistentVolumeClaim", d)
        self.assertNotIn("hostPath:", d)
        self.assertNotIn("StorageClass", d)
        self.assertNotIn("statefulset", d.lower())
        self.assertNotIn("synthea-new-only-state", d)
        self.assertIn("type: ClusterIP", s)
        for forbidden in ("NodePort", "LoadBalancer", "externalIPs", "Ingress"):
            self.assertNotIn(forbidden + ":", s)

    def test_identity_secret_and_image_gate(self):
        d = (DIR / "deployment.yaml.tpl").read_text()
        for needed in ("runAsNonRoot: true", "runAsUser: __OIE_ENGINE_UID__",
                       "runAsGroup: __OIE_ENGINE_GID__", "fsGroup: __OIE_ENGINE_GID__",
                       "image: __OIE_PINNED_IMAGE_DIGEST__", "name: debug-bootstrap",
                       "secretName: oie-debug-bootstrap", "defaultMode: 0440",
                       "allowPrivilegeEscalation: false", "drop:"):
            self.assertIn(needed, d)
        self.assertNotIn("server.initialadminpassword =", d)
        self.assertNotIn("readOnlyRootFilesystem: true", d)

    def test_yaml_valid_after_placeholders(self):
        d = (DIR / "deployment.yaml.tpl").read_text()
        rendered = (d.replace("__OIE_ENGINE_UID__", "10001")
                     .replace("__OIE_ENGINE_GID__", "10001")
                     .replace("__OIE_PINNED_IMAGE_DIGEST__",
                              "ghcr.io/example/oie@sha256:" + "a"*64))
        value = yaml.safe_load(rendered)
        self.assertEqual(value["kind"], "Deployment")
        volumes = value["spec"]["template"]["spec"]["volumes"]
        self.assertTrue(any("emptyDir" in v for v in volumes))
        self.assertFalse(any("persistentVolumeClaim" in v for v in volumes))
        service = yaml.safe_load((DIR / "service.yaml").read_text())
        self.assertEqual(service["spec"]["type"], "ClusterIP")


if __name__ == "__main__":
    unittest.main()
