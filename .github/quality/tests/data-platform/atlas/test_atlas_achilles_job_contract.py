"""Offline contract for the official digest-pinned ACHILLES Data Sources Job.

OpenSpec-Change: deploy-local-ohdsi-atlas
OpenSpec-Task: 4.0.4
No cluster access or SQL execution.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[5]
JOB = ROOT / "local-data-platform/kubernetes/manifests/atlas/achilles-local-omop-once-job.yaml"

class AchillesJobStaticContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = JOB.read_text(encoding="utf-8")

    def test_unique_ownership_and_manual_one_shot(self):
        s = self.s
        self.assertIn("namespace: dw-atlas", s)
        self.assertIn("kind: Job", s)
        self.assertIn("name: atlas3-achilles-local-omop-once-20261110", s)
        self.assertIn("CONTROLLED ONE-SHOT ONLY", s)
        self.assertIn("backoffLimit: 0", s)
        self.assertIn("completions: 1", s)
        self.assertIn("parallelism: 1", s)
        self.assertIn("activeDeadlineSeconds: 2400", s)

    def test_pinned_official_linux_amd64_verified_image(self):
        s = self.s
        self.assertIn("docker.io/ohdsi/broadsea-achilles@sha256:"
                      "9bae4871c3e1465f1a721fe3215f8a5fec5f2c2928408d9330a64ab32bfd6866",s)
        self.assertNotIn("broadsea-achilles:master",s)
        self.assertNotIn("broadsea-achilles:latest",s)
        self.assertIn("runAsNonRoot: true",s)
        self.assertIn("automountServiceAccountToken: false",s)
        self.assertIn("allowPrivilegeEscalation: false",s)
        self.assertIn('drop: ["ALL"]',s)

    def test_synthetic_local_cdm_read_achilles_results_write(self):
        s = self.s
        for k in ("ACHILLES_SOURCE","ACHILLES_DB_URI","ACHILLES_DB_USERNAME",
                  "ACHILLES_DB_PASSWORD","ACHILLES_CDM_SCHEMA",
                  "ACHILLES_VOCAB_SCHEMA","ACHILLES_RES_SCHEMA",
                  "ACHILLES_CDM_VERSION","ACHILLES_NUM_THREADS"):
            self.assertIn("name: "+k,s)
        self.assertIn("value: LOCAL_OMOP",s)
        self.assertIn("value: cdm",s)
        self.assertIn("value: atlas_results",s)
        self.assertIn('value: "5.4"',s)
        self.assertIn('value: "1"',s)
        self.assertIn("name: atlas-webapi-db",s)
        self.assertIn("key: app-username",s)
        self.assertIn("key: app-password",s)
        self.assertNotIn("password:",s)
        self.assertNotIn("INSERT INTO cdm.",s)
        self.assertNotIn("UPDATE cdm.",s)
        self.assertNotIn("ALTER ROLE",s)

    def test_memory_bounds_and_no_persistent_export_volume(self):
        s=self.s
        self.assertIn("cpu: 200m",s)
        self.assertIn("memory: 1Gi",s)
        self.assertIn("memory: 4Gi",s)
        self.assertIn("emptyDir:",s)
        self.assertIn("sizeLimit: 1Gi",s)
        self.assertNotIn("persistentVolumeClaim:",s)
        self.assertIn("kubernetes.io/hostname: worker03",s)


if __name__ == "__main__":
    unittest.main()
