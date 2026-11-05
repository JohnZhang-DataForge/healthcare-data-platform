"""G5 Native Fabric Pipeline contract checks: offline only, no cloud run."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
PIPELINE = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "pl_fhir_ingest.DataPipeline/pipeline-content.json")
NOTEBOOK = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "nb_fhir_ingest.Notebook/notebook-content.py")


class PipelineReadOnlyContract(unittest.TestCase):
    def setUp(self):
        self.definition = json.loads(PIPELINE.read_text(encoding="utf-8"))
        self.props = self.definition["properties"]
        self.activity = self.props["activities"][0]
        self.params = self.activity["typeProperties"]["parameters"]

    def test_default_halt_and_explicit_silver_readback_arguments(self):
        expected = {"run_mode", "request_id", "manifest_sha256",
                    "source_preservation_strategy", "patient_contract_json",
                    "encounter_contract_json"}
        self.assertEqual(set(self.props["parameters"]), expected)
        self.assertEqual(self.props["parameters"]["run_mode"]["defaultValue"], "HALT")
        self.assertEqual(self.props["parameters"]["source_preservation_strategy"]["defaultValue"],
                         "HALT")
        for key in expected - {"run_mode", "source_preservation_strategy"}:
            self.assertEqual(self.props["parameters"][key]["defaultValue"], "")
        for key in expected:
            self.assertEqual(
                self.params[key],
                {"value": {"value": f"@pipeline().parameters.{key}",
                           "type": "Expression"}, "type": "string"})
        self.assertEqual(set(self.params), expected |
                         {"write_authorized", "retention_preflight_verified"})
        self.assertEqual(self.params["write_authorized"], {"value": False, "type": "bool"})
        self.assertEqual(self.params["retention_preflight_verified"],
                         {"value": False, "type": "bool"})

    def test_no_schedule_retry_or_other_side_effect(self):
        self.assertEqual(len(self.props["activities"]), 1)
        self.assertEqual(self.activity["type"], "TridentNotebook")
        self.assertEqual(self.activity["dependsOn"], [])
        self.assertEqual(self.activity["policy"]["retry"], 0)
        self.assertTrue(self.activity["policy"]["secureInput"])
        self.assertTrue(self.activity["policy"]["secureOutput"])
        self.assertNotIn("triggers", self.definition)
        self.assertNotIn("triggers", self.props)
        annotations = self.props["annotations"]
        self.assertIn("DEFAULT_HALT", annotations)
        self.assertIn("NO_AUTO_RETRY", annotations)
        self.assertIn("NO_SCHEDULE", annotations)
        self.assertIn("NO_CANDIDATE_OR_GOLD_WRITE", annotations)

    def test_preserved_git_native_notebook_logical_reference(self):
        # Verified existing native Git logicalId, not physical Notebook item UUID.
        self.assertEqual(self.activity["typeProperties"]["notebookId"],
                         "eb751633-bade-8370-4e96-34848311ab6b")
        self.assertEqual(self.activity["typeProperties"]["workspaceId"],
                         "00000000-0000-0000-0000-000000000000")

    def test_nonapproved_or_accidentally_writable_mode_fails_in_notebook(self):
        text = NOTEBOOK.read_text(encoding="utf-8")
        self.assertIn('run_mode = "HALT"', text)
        self.assertIn("elif run_mode in (\"SILVER_WRITE\", \"SILVER_READBACK_ONLY\"):", text)
        self.assertIn('elif run_mode in ("SILVER_WRITE", "SILVER_READBACK_ONLY"):', text)
        self.assertIn("HOLD_G4_BOOLEAN_WRITE_GATES", text)
        self.assertIn("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED", text)
        self.assertIn("raise RuntimeError(\"HOLD_FHIR_G4_\" + g4.status)", text)


if __name__ == "__main__":
    unittest.main()
