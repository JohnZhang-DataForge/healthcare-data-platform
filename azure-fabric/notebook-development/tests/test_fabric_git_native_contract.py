"""Native Git source, policy and Pipeline link validation: no Fabric network calls."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
GIT_ROOT = ROOT / "azure-fabric/workspaces/healthcare-omop"
sys.path.insert(0, str(HERE))
import native_item_readiness as native

class FabricGitNativeContract(unittest.TestCase):
    def test_real_ids_and_file_structure(self):
        result = native.check_native_export(GIT_ROOT)
        self.assertEqual(result.state, "HOLD_NATIVE_RUNTIME_DEPLOYMENT")
        self.assertEqual(len(result.reasons), 1)

    def test_native_notebook_contains_one_business_implementation(self):
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        candidate = (HERE / "fhir_ingest_notebook.py").read_text()
        self.assertIn("# Fabric notebook source", content)
        self.assertIn("# CELL ********************", content)
        self.assertIn('"tags": ["parameters"]', content)
        self.assertIn('def execute_native_notebook(', content)
        self.assertIn('HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED', content)
        self.assertNotIn("def execute_native_notebook(", candidate)
        self.assertNotIn("write_authorized = True", content)

    def test_pipeline_is_wired_to_existing_notebook_without_retry(self):
        data = json.loads((GIT_ROOT / "pl_fhir_ingest.DataPipeline/pipeline-content.json").read_text())
        activities = data["properties"]["activities"]
        self.assertEqual(len(activities), 1)
        a = activities[0]
        self.assertEqual(a["type"], "TridentNotebook")
        self.assertEqual(a["typeProperties"]["notebookId"], "8311ab6b-3484-4e96-8370-badeeb751633")
        self.assertEqual(a["typeProperties"]["workspaceId"], "745ce03b-15b6-4870-b0e5-8c5750aa18dc")
        self.assertEqual(a["policy"]["retry"], 0)
        p = a["typeProperties"]["notebookParameters"]
        self.assertEqual(p["run_mode"]["value"], "HALT")
        self.assertFalse(p["write_authorized"]["value"])
        self.assertFalse(p["retention_preflight_verified"]["value"])

    def test_wrong_native_platform_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            dst = Path(folder)
            for _kind, (name, _, required) in native.ITEMS.items():
                source = GIT_ROOT / name
                (dst / name).mkdir()
                shutil.copyfile(source / ".platform", dst / name / ".platform")
                dest = dst / name / required
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((source / required).read_bytes())
            platform = dst / "nb_fhir_ingest.Notebook/.platform"
            d = json.loads(platform.read_text())
            d["config"]["logicalId"] = "00000000-0000-0000-0000-000000000000"
            platform.write_text(json.dumps(d))
            result = native.check_native_export(dst)
            self.assertEqual(result.state, "BLOCKED_NATIVE_EXPORT")
            self.assertTrue(any("INVALID_NATIVE_LOGICAL_ID" in x for x in result.reasons))

if __name__ == "__main__":
    unittest.main()
