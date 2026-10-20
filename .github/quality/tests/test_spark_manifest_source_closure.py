"""Offline tests for Spark manifest/entrypoint closure (no Spark/K8s/network)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_spark_manifest_source_closure.py"
spec = importlib.util.spec_from_file_location("spark_source_closure", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


SAMPLE = """apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: __APP_NAME__
spec:
  type: Python
  mode: cluster
  mainApplicationFile: local:///opt/spark/app/example_job.py
  driver:
    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true
  executor:
    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true
  volumes:
    - name: spark-app
      configMap:
        name: __CONFIGMAP_NAME__
"""
POD = """apiVersion: v1
kind: Pod
metadata:
  name: __POD_NAME__
spec:
  containers:
    - name: helper
      image: example:only
"""


class ManifestSourceClosureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / gate.MANIFESTS / "visit" / "template.yaml.tpl"
        self.pod = self.root / gate.MANIFESTS / "visit" / "helper.yaml.tpl"
        self.source = self.root / gate.APPS / "visit" / "example_job.py"
        for path, content in ((self.manifest, SAMPLE), (self.pod, POD),
                              (self.source, "print('not executed')\n")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def audit(self):
        return gate.audit(self.root)

    def test_one_main_source_and_auxiliary_pod(self):
        apps, pods = self.audit()
        self.assertEqual(len(apps), 1)
        self.assertEqual(len(pods), 1)
        self.assertEqual(apps[0]["source"], "local-data-platform/spark/apps/visit/example_job.py")

    def test_rejects_missing_source(self):
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.audit()

    def test_rejects_duplicate_source_basename(self):
        duplicate = self.root / gate.APPS / "person" / self.source.name
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text("pass\n")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.audit()

    def test_rejects_legacy_root_or_remote_entry(self):
        for path in ("local:///old/spark/example_job.py",
                     "s3a://bucket/example_job.py",
                     "local:///opt/spark/app/old/example_job.py"):
            with self.subTest(path=path):
                self.manifest.write_text(SAMPLE.replace(
                    "local:///opt/spark/app/example_job.py", path))
                with self.assertRaises(ValueError):
                    self.audit()

    def test_requires_readonly_mount_both_roles(self):
        self.manifest.write_text(SAMPLE.replace("readOnly: true", "readOnly: false", 1))
        with self.assertRaisesRegex(ValueError, "driver"):
            self.audit()
        self.manifest.write_text(SAMPLE.replace("readOnly: true", "readOnly: false", 2))
        with self.assertRaisesRegex(ValueError, "driver"):
            self.audit()

    def test_executor_mount_must_match(self):
        # Split after executor rather than replacing driver.
        front, tail = SAMPLE.split("  executor:", 1)
        self.manifest.write_text(front + "  executor:" +
                                 tail.replace("mountPath: /opt/spark/app",
                                              "mountPath: /old/root"))
        with self.assertRaisesRegex(ValueError, "executor"):
            self.audit()

    def test_rejects_unbound_configmap_or_duplicate_mount(self):
        self.manifest.write_text(SAMPLE.replace("__CONFIGMAP_NAME__", "old-configmap"))
        with self.assertRaisesRegex(ValueError, "ConfigMap"):
            self.audit()
        self.manifest.write_text(SAMPLE.replace(
            "  executor:", "  driver:\n    volumeMounts:\n      - name: spark-app\n        mountPath: /opt/spark/app\n        readOnly: true\n  executor:"))
        with self.assertRaises(ValueError):
            self.audit()

    def test_auxiliary_pod_cannot_masquerade_as_spark(self):
        self.pod.write_text(POD + "  mainApplicationFile: local:///opt/spark/app/example_job.py\n")
        with self.assertRaisesRegex(ValueError, "auxiliary Pod"):
            self.audit()

    def test_unsupported_kind_fails_closed(self):
        self.manifest.write_text(SAMPLE.replace("kind: SparkApplication", "kind: Deployment"))
        with self.assertRaisesRegex(ValueError, "unsupported resource"):
            self.audit()

    def test_bad_python_syntax_fails_without_importing_or_running(self):
        self.source.write_text("def broken(\n", encoding="utf-8")
        with self.assertRaises(SyntaxError):
            self.audit()

    def test_manifest_main_must_be_single(self):
        self.manifest.write_text(SAMPLE.replace(
            "  mainApplicationFile:",
            "  mainApplicationFile: local:///opt/spark/app/example_job.py\n  mainApplicationFile:"))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
