"""Offline guard for scoped ACHILLES analyses 200/201.

OpenSpec-Change: deploy-local-ohdsi-atlas
OpenSpec-Task: 4.0.4, 4.0.5
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[5]
RFILE=ROOT/"local-data-platform/atlas/config/achilles_visit200201_once.R"
JOB=ROOT/"local-data-platform/kubernetes/manifests/atlas/achilles-visit200201-once-job.yaml.tpl"
ORIGINAL=ROOT/"local-data-platform/kubernetes/manifests/atlas/achilles-local-omop-once-job.yaml"

class TestAchilles200201(unittest.TestCase):
    def test_scoped_official_r_invocation(self):
        code=RFILE.read_text(encoding="utf-8")
        self.assertIn("Achilles::achilles(",code)
        self.assertRegex(code,r"analysisIds\s*=\s*c\(200L,\s*201L\)")
        for term in ("createTable = FALSE","updateGivenAnalysesOnly = TRUE",
                     "createIndices = FALSE","numThreads = 1",
                     "defaultAnalysesOnly = FALSE","verboseMode = FALSE",
                     "Achilles::achilles","cdmDatabaseSchema = \"cdm\"",
                     "resultsDatabaseSchema = \"atlas_results\""):
            self.assertIn(term,code)
        for forbidden in ("exportToJson(","runMissingAnalyses(","runAllAnalyses(",
                          "createTable = TRUE","updateGivenAnalysesOnly = FALSE"):
            self.assertNotIn(forbidden,code)
        self.assertIn("1.7.2",code)

    def test_immutable_original_image_and_scope(self):
        job=JOB.read_text(encoding="utf-8")
        old=ORIGINAL.read_text(encoding="utf-8")
        original_image=re.search(r"image:\s*(docker\.io/ohdsi/broadsea-achilles@sha256:[0-9a-f]{64})",old)
        self.assertIsNotNone(original_image)
        self.assertIn(original_image.group(1),job)
        self.assertIn("namespace: dw-atlas",job)
        self.assertIn("kubernetes.io/hostname: worker03",job)
        self.assertIn("backoffLimit: 0",job)
        self.assertIn('command: ["Rscript", "/opt/achilles/visit200201.R"]',job)
        self.assertIn("atlas-webapi-db",job)
        self.assertIn("automountServiceAccountToken: false",job)
        self.assertIn("readOnly: true",job)
        self.assertIn("__RUN_ID__",job)
        self.assertNotIn("kind: Deployment",job)
        self.assertNotIn("kind: StatefulSet",job)
        self.assertNotIn("hostNetwork: true",job)

if __name__=="__main__":
    unittest.main()
