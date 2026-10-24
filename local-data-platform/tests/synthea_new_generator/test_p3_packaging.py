"""P3 packaging assertions; never touch real K8s or cloud resources."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "images/synthea-new-generator/Dockerfile"
PVC = ROOT / "kubernetes/manifests/synthea/new-generator/pvc.yaml"
JOB = ROOT / "kubernetes/manifests/synthea/new-generator/generate-job.yaml.tpl"


class P3PackagingTests(unittest.TestCase):
    def test_parent_pin_and_independent_entrypoint(self):
        body = DOCKERFILE.read_text()
        self.assertRegex(body, r"(?m)^ARG BASE_IMAGE$")
        self.assertIn("FROM ${BASE_IMAGE}", body)
        self.assertIn("synthea_new_generator", body)
        self.assertIn("PYTHONPATH=/opt/new-generator", body)
        self.assertIn("USER 10001:10001", body)
        self.assertIn('ENTRYPOINT ["python3", "-m", "apps.synthea.synthea_new_generator.entrypoint"]', body)
        self.assertNotIn("apps/synthea/new_only/", body)
        self.assertNotIn("apps/task004/", body)
        self.assertNotIn("pip install", body.lower())

    def test_isolated_durable_pvc(self):
        pvc = PVC.read_text()
        job = JOB.read_text()
        self.assertIn("name: synthea-new-generator-state", pvc)
        self.assertIn("storageClassName: synthea-local", pvc)
        self.assertIn("claimName: synthea-new-generator-state", job)
        self.assertNotIn("claimName: synthea-new-only-state", job)
        self.assertIn("namespace: dw-synthea", pvc)
        self.assertIn("namespace: dw-synthea", job)
        self.assertNotIn("kind: Secret", job)

    def test_job_runtime_hardening_and_placeholders(self):
        body = JOB.read_text()
        pvc = PVC.read_text()
        for expected in (
            "image: __IMAGE_DIGEST__", "__REQUEST_CONFIGMAP__", "name: __JOB_NAME__",
            "automountServiceAccountToken: false", "readOnlyRootFilesystem: true",
            "allowPrivilegeEscalation: false", "runAsNonRoot: true",
            "runAsUser: 10001", "runAsGroup: 10001", "fsGroup: 10001",
            "type: RuntimeDefault", "backoffLimit: 0",
            "activeDeadlineSeconds: 1800", "worker01", "cpu: 250m",
            "memory: 5Gi", "storage: 10Gi",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, body + pvc)
        self.assertIn("mountPath: /inputs/request.json", body)
        self.assertIn("subPath: request.json", body)
        self.assertIn("mountPath: /tmp", body)
        self.assertIn("mountPath: /synthea-new-generator-state", body)
        self.assertEqual(len(re.findall(r"^\s+name: __REQUEST_CONFIGMAP__$", body, re.M)), 1)

    def test_no_downstream_mutations(self):
        body = JOB.read_text().lower()
        for forbidden in ("az login", "kubectl apply", "postgresql", "secretkeyref",
                          "seaweedfs", "s3_endpoint", "airflow", "image: :latest"):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
