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
        self.assertIn('"tags": [', content)
        self.assertIn('def execute_native_notebook(', content)
        self.assertIn('HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED', content)
        self.assertNotIn("def execute_native_notebook(", candidate)
        self.assertNotIn("write_authorized = True", content)

    def test_native_notebook_fabric_cell_source_round_trip_structure(self):
        # Git-aware Notebook parser requires a metadata JSON block per cell.
        # Python syntax alone would not catch a malformed FabricGitSource.
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        self.assertTrue(content.startswith("# Fabric notebook source\n# METADATA ********************\n# META {"))
        self.assertEqual(content.count("# CELL ********************"), 2)
        self.assertEqual(content.count("# PARAMETERS CELL ********************"), 1)
        chunks = content.split("# METADATA ********************")
        self.assertEqual(len(chunks), 5)
        for i, chunk in enumerate(chunks[1:], start=1):
            end = chunk.find("# CELL ********************")
            metadata_lines = chunk if end < 0 else chunk[:end]
            stripped = [line[len("# META "):] for line in metadata_lines.splitlines()
                        if line.startswith("# META ")]
            self.assertTrue(stripped, f"missing Fabric metadata block {i}")
            self.assertEqual(stripped[0], "{")
            self.assertEqual(stripped[-1], "}")
            metadata = json.loads("\n".join(stripped))
            if i == 1:
                self.assertEqual(metadata["kernel_info"]["name"], "synapse_pyspark")
                self.assertIn("lakehouse", metadata["dependencies"])
            else:
                self.assertEqual(metadata["language"], "python")
                self.assertEqual(metadata["language_group"], "synapse_pyspark")
                if i == 3:
                    self.assertEqual(metadata.get("tags"), ["parameters"])
        self.assertIn("def execute_native_notebook(", chunks[1])
        self.assertIn('# PARAMETERS CELL ********************', chunks[2])
        self.assertIn('run_mode = "HALT"', chunks[2])
        self.assertIn('raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")', chunks[3])

    def test_fabric_source_section_separators_match_official_samples(self):
        # This is a serialization preflight, NOT a proof of Fabric round-trip.
        content = (GIT_ROOT / 'nb_fhir_ingest.Notebook/notebook-content.py').read_text()
        self.assertTrue(content.startswith('# Fabric notebook source\n\n# METADATA ********************\n\n# META {'))
        self.assertEqual(content.count('\n\n# METADATA ********************\n\n# META {'), 3)
        self.assertEqual(content.count('# CELL ********************\n\n'), 2)
        self.assertEqual(content.count('# PARAMETERS CELL ********************\n\n'), 1)
        self.assertIn('# META }\n\n# PARAMETERS CELL ********************', content)
        self.assertIn('# META }\n\n# CELL ********************', content)
        self.assertIn('def execute_native_notebook(', content)
        self.assertIn('HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED', content)

    def test_pipeline_is_wired_to_existing_notebook_without_retry(self):
        data = json.loads((GIT_ROOT / "pl_fhir_ingest.DataPipeline/pipeline-content.json").read_text())
        activities = data["properties"]["activities"]
        self.assertEqual(len(activities), 1)
        a = activities[0]
        self.assertEqual(a["type"], "TridentNotebook")
        notebook_platform = json.loads((GIT_ROOT / "nb_fhir_ingest.Notebook/.platform").read_text())
        logical_id = notebook_platform["config"]["logicalId"]
        props = a["typeProperties"]
        # Native Git references MUST use logicalId and the same-workspace sentinel.
        self.assertEqual(props["notebookId"], logical_id)
        self.assertEqual(props["workspaceId"], "00000000-0000-0000-0000-000000000000")
        self.assertEqual(set(props), {"notebookId", "workspaceId", "parameters"})
        # Official TridentNotebook REST Schema is typeProperties.parameters.
        # The unsupported "notebookParameters" field was dropped on Fabric round-trip.
        self.assertNotIn("notebookParameters", props)
        self.assertEqual(a["policy"]["retry"], 0)
        self.assertTrue(a["policy"]["secureInput"])
        self.assertTrue(a["policy"]["secureOutput"])
        p = props["parameters"]
        self.assertEqual(set(p), {"run_mode", "write_authorized", "retention_preflight_verified", "request_id"})
        self.assertEqual(p["run_mode"], {"value": "HALT", "type": "string"})
        self.assertEqual(p["write_authorized"], {"value": False, "type": "bool"})
        self.assertEqual(p["retention_preflight_verified"], {"value": False, "type": "bool"})
        self.assertEqual(p["request_id"], {"value": "", "type": "string"})
        self.assertFalse(data["properties"].get("triggers"))
        self.assertEqual(len(activities), 1)

    def test_native_environment_has_exact_hashed_custom_wheel(self):
        import hashlib
        import zipfile
        lib = GIT_ROOT / "env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.0-py3-none-any.whl"
        self.assertTrue(lib.is_file())
        self.assertEqual(hashlib.sha256(lib.read_bytes()).hexdigest(),
                         "603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7")
        self.assertEqual([p.name for p in lib.parent.glob("*.whl")], [lib.name])
        with zipfile.ZipFile(lib) as wheel:
            names = wheel.namelist()
            self.assertTrue(any(n.endswith(".dist-info/METADATA") for n in names))
            self.assertTrue(any(n.startswith("healthcare_data_engine/") for n in names))

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
