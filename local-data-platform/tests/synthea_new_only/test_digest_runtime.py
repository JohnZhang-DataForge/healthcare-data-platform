"""NEW_ONLY image packaging and phase routing regression, no S3/PG writes."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"apps/synthea/new_only"
IMAGE=ROOT/"images/synthea-new-only/Dockerfile"
GENERATE=ROOT/"kubernetes/manifests/synthea/new-only/runtime-generate-job.yaml.tpl"
LANDING=ROOT/"kubernetes/manifests/synthea/new-only/runtime-landing-job.yaml.tpl"
spec=importlib.util.spec_from_file_location("new_only_entry", APP/"entrypoint.py")
entry=importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)

class StandaloneDigestRuntimeTests(unittest.TestCase):
    def test_runtime_contains_exact_proven_components(self):
        text=IMAGE.read_text()
        parent="ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea:latest"
        self.assertIn("ARG BASE_IMAGE="+parent,text)
        self.assertIn("FROM ${BASE_IMAGE}",text)
        self.assertNotIn("@sha256:",text)
        # The 8-image release injects this run's freshly built parent via BASE_IMAGE.
        # Static sources must not depend on a previously published fixed digest.
        for script in ["entrypoint","generate_new_only","prepublish_gate","publish_v1_verified","verify_v1_ready"]:
            self.assertIn(f"apps/synthea/new_only/{script}.py",text)
        for script in ["publish_synthea_landing","validate_generated_synthea_batch","resolve_verified_landing_file"]:
            self.assertIn("apps/task004/"+script+".py",text)
        self.assertIn("apps/landing_discovery/scan_ready_batches.py",text)
        self.assertIn("contracts/synthea/new-only/csv-contract-v2.json",text)
        self.assertIn('USER 10001:10001',text)
        self.assertIn('ENTRYPOINT ["python3", "/opt/synthea-new-only/entrypoint.py"]',text)
        self.assertNotIn("ENTRYPOINT [\"/usr/local/bin/healthcare-synthea-generator",text)

    def test_all_six_phases_and_frozen_request_guard(self):
        self.assertEqual(len(entry.PHASES),6)
        for phase in entry.PHASES:
            argv=entry.command(phase,"gh-38484300008")
            self.assertIn("python",Path(argv[0]).name)
            self.assertTrue(any(x.endswith(".py") for x in argv))
        self.assertIn("/opt/synthea-new-only/csv-contract-v1.json",
                      entry.command("publish","gh-38484300008"))
        self.assertIn("--scan-s3",entry.command("prepublish","gh-38484300008"))
        self.assertEqual(entry.command("generate","gh-38484300008")[-1],
                         "/opt/synthea-new-only/generate_new_only.py")
        for bad in ("../traversal","", "tiny","a/b","a"*80):
            with self.assertRaises(entry.RuntimeBlocked):
                entry.command("generate",bad)
        with self.assertRaises(entry.RuntimeBlocked):
            entry.command("update-only","gh-38484300008")

    def test_worker01_pvc_and_image_digest_guards(self):
        g=GENERATE.read_text();landing=LANDING.read_text()
        self.assertIn("kubernetes.io/hostname: worker01",g)
        self.assertIn("kubernetes.io/hostname: worker01",landing)
        self.assertIn("synthea-new-only-state",g)
        self.assertIn("synthea-new-only-state",landing)
        self.assertIn("__IMAGE_DIGEST__",g)
        self.assertIn("__IMAGE_DIGEST__",landing)
        self.assertNotIn("secretKeyRef",g)
        self.assertNotIn("generator-code",g)
        self.assertNotIn("configMap:",g)
        self.assertIn("readOnly: true",landing)
        self.assertIn("__AUDIT_S3__",landing)
        self.assertIn("__AUDIT_PG__",landing)
        self.assertNotIn('value: "PASS"',landing)
        self.assertIn("runAsNonRoot: true",g)
        self.assertIn("runAsNonRoot: true",landing)

    def test_other_two_generator_modes_not_built(self):
        policy=json.loads((ROOT/"contracts/synthea/producer-batch-identity-v1.json").read_text())
        self.assertEqual([x["mode"] for x in policy["producer_modes"]],
                         ["NEW_ONLY","UPDATE_ONLY","MIX_DATA"])
        self.assertFalse((ROOT/"images/synthea-update-only").exists())
        self.assertFalse((ROOT/"images/synthea-mix-data").exists())


if __name__=="__main__":
    unittest.main()
