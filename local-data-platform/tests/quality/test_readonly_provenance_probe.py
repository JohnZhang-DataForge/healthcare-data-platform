"""Offline contract tests: fake kubectl, never touches a Kubernetes API."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/quality/read-only-gitsync-spark-provenance.sh"


class ReadOnlyProvenanceProbeTests(unittest.TestCase):
    def invoke(self, *, pods=1, configmap="probe-cm", payload="print('ok')\n",
               expected="print('ok')\n", report=None):
        with tempfile.TemporaryDirectory(prefix="local-dp-probe-test-") as td:
            root = Path(td)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            code = root / "reconcile_person_visit.py"
            code.write_text(expected)
            fake = bin_dir / "kubectl"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "args = sys.argv[1:]\n"
                "if len(args) < 7 or args[0] != '--context' or args[2] != '-n' or args[4] != 'get':\n"
                "    raise SystemExit('UNEXPECTED_KUBECTL_COMMAND')\n"
                "if args[5] == 'pods':\n"
                "    print(json.dumps({'items': [{'metadata': {'name': 'airflow-0'}, 'spec': {'containers': [{'name': 'scheduler', 'env': [], 'volumeMounts': []}]}}] * int(os.environ['FAKE_PODS'])}))\n"
                "elif args[5] == 'configmap':\n"
                "    print(json.dumps({'metadata': {'name': os.environ['FAKE_CONFIGMAP']}, 'data': {'reconcile_person_visit.py': os.environ['FAKE_PAYLOAD']}}))\n"
                "else: raise SystemExit('UNEXPECTED_RESOURCE')\n"
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "PATH": str(bin_dir) + os.pathsep + env["PATH"],
                "KUBE_CONTEXT": "offline-fake",
                "AIRFLOW_NAMESPACE": "dw-airflow",
                "SPARK_NAMESPACE": "dw-spark",
                "SPARK_CONFIGMAP": "probe-cm",
                "EXPECTED_SPARK_FILE": str(code),
                "REPORT_DIR": str(report or root / "report"),
                "FAKE_PODS": str(pods),
                "FAKE_CONFIGMAP": configmap,
                "FAKE_PAYLOAD": payload,
            })
            result = subprocess.run(["bash", str(SCRIPT)], cwd=ROOT.parent, env=env, capture_output=True, text=True, timeout=20)
            return result

    def test_matching_source_is_partial_only(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SPARK_CONTENT_MATCH=PASS", result.stdout)
        self.assertIn("GITSYNC_ACTIVE_CHECKOUT=NOT_VERIFIED", result.stdout)
        self.assertIn("LIVE_POD_IMPORT_PATH=NOT_VERIFIED", result.stdout)

    def test_no_airflow_pods_holds(self):
        result = self.invoke(pods=0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AIRFLOW_PODS_EMPTY=HOLD", result.stderr)

    def test_mismatched_configmap_identity_holds(self):
        result = self.invoke(configmap="different")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPARK_CONFIGMAP_IDENTITY_MISMATCH=HOLD", result.stderr)

    def test_mismatched_source_fails(self):
        result = self.invoke(payload="wrong")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPARK_CONTENT_MATCH=FAIL", result.stdout)

    def test_relative_report_path_rejected(self):
        result = self.invoke(report=Path("relative-output"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REPORT_DIR_MUST_BE_ABSOLUTE", result.stdout)


if __name__ == "__main__":
    unittest.main()
