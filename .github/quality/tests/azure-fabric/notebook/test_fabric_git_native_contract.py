"""Native Git source, policy and Pipeline link validation: no Fabric network calls."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[5] / "azure-fabric/notebook-development"
ROOT = HERE.parents[1]
GIT_ROOT = ROOT / "azure-fabric/workspaces/healthcare-omop"
sys.path.insert(0, str(HERE))
import native_item_readiness as native

class FabricGitNativeContract(unittest.TestCase):
    def test_real_ids_and_file_structure(self):
        result = native.check_native_export(GIT_ROOT)
        self.assertEqual(result.state, "HOLD_NATIVE_RUNTIME_DEPLOYMENT")
        self.assertEqual(len(result.reasons), 1)

    def test_git_native_notebook_references_published_same_workspace_environment(self):
        nb = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        top = nb.split("# CELL ********************", 1)[0]
        metadata_lines = [line[len("# META "):] for line in top.splitlines()
                          if line.startswith("# META ")]
        metadata = json.loads("\n".join(metadata_lines))
        binding = metadata["dependencies"]["environment"]
        env_platform = json.loads(
            (GIT_ROOT / "env_healthcare.Environment/.platform").read_text())
        # Fabric Git Integration uses same-workspace logical IDs, not the
        # physical Environment GUID returned by the REST API.
        self.assertEqual(binding, {
            "environmentId": env_platform["config"]["logicalId"],
            "workspaceId": "00000000-0000-0000-0000-000000000000"
        })
        self.assertEqual(env_platform["metadata"]["displayName"], "env_healthcare")
        self.assertIn('if engine_version != "0.1.6":', nb)
        self.assertIn('run_mode = "HALT"', nb)
        self.assertIn("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED", nb)
        self.assertNotIn("write_authorized = True", nb)

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

    def test_g5_engine_package_016_is_distinct_from_adapter_record_010(self):
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        self.assertEqual(content.count('if engine_version != "0.1.6":'), 3)  # ETL, runtime smoke and source-only intake
        self.assertNotIn('if engine_version != "0.1.0":', content)
        self.assertIn('(F.col("adapter_version") != "0.1.0")', content)
        # Engine is a published dependency version; adapter_version is the
        # serialized FHIR canonical record version, not package metadata.
        self.assertIn('run_mode = "HALT"', content)
        self.assertIn('write_authorized = False', content)
        self.assertIn('retention_preflight_verified = False', content)
        self.assertIn('HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED', content)

    def test_native_notebook_fabric_cell_source_round_trip_structure(self):
        # Git-aware Notebook parser requires a metadata JSON block per cell.
        # Python syntax alone would not catch a malformed FabricGitSource.
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        self.assertTrue(content.startswith("# Fabric notebook source\n\n# METADATA ********************\n\n# META {"))
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
        self.assertEqual(content.count('\n\n# METADATA ********************\n\n# META {'), 4)
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
        forwarded = {"run_mode", "request_id", "manifest_sha256",
                     "source_preservation_strategy", "patient_contract_json",
                     "encounter_contract_json"}
        self.assertEqual(set(p), forwarded |
                         {"write_authorized", "retention_preflight_verified"})
        for key in forwarded:
            self.assertEqual(p[key], {
                "value": {"value": f"@pipeline().parameters.{key}",
                          "type": "Expression"}, "type": "string"})
        self.assertEqual(data["properties"]["parameters"]["run_mode"]["defaultValue"], "HALT")
        self.assertEqual(p["write_authorized"], {"value": False, "type": "bool"})
        self.assertEqual(p["retention_preflight_verified"], {"value": False, "type": "bool"})
        self.assertFalse(data["properties"].get("triggers"))
        self.assertEqual(len(activities), 1)

    def test_business_runtime_smoke_is_parameterized_and_strictly_read_only(self):
        # Mocks the Spark version, NOT a claim of an actual Fabric Spark run.
        from unittest.mock import patch
        import fhir_ingest_notebook as notebook
        base = dict(
            mode="RUNTIME_SMOKE", allow_write=False, retention_ok=False,
            request="", manifest="", source="", target="",
        )
        with patch("pyspark.__version__", "4.1.1"):
            self.assertEqual(
                notebook.validate_read_only_runtime_smoke(**base),
                "FHIR_BUSINESS_RUNTIME_SMOKE_ENGINE_016_SPARK41_PASS_20261106",
            )
            for key, value in (
                ("mode", "HALT"), ("mode", "ETL"),
                ("allow_write", True), ("allow_write", "false"),
                ("retention_ok", True), ("request", "anything"),
                ("manifest", "{}"), ("source", "Files/source"),
                ("target", "Tables/silver"),
            ):
                case = dict(base)
                case[key] = value
                with self.subTest(key=key, value=value):
                    with self.assertRaisesRegex(RuntimeError, "HOLD_"):
                        notebook.validate_read_only_runtime_smoke(**case)
        with patch("pyspark.__version__", "3.5.7"):
            with self.assertRaisesRegex(RuntimeError, "HOLD_RUNTIME_SMOKE_WRONG_SPARK_VERSION"):
                notebook.validate_read_only_runtime_smoke(**base)
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        self.assertIn('run_mode = "HALT"', content)
        self.assertIn('write_authorized = False', content)
        self.assertIn('raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")', content)
        self.assertIn("notebookutils.notebook.exit(smoke_exit)", content)

    def test_fhir_intake_readonly_requires_frozen_request_no_mutations(self):
        import inspect
        import fhir_ingest_notebook as notebook
        from unittest.mock import Mock
        good = dict(
            request="atlanta-fhir-gh-40238053772",
            allow_write=False, retention_ok=False,
            manifest="", source="", target="",
        )
        guarded = notebook.verify_fhir_intake_readonly
        for key, value in (
            ("request", "unknown-request"),
            ("allow_write", True),
            ("retention_ok", True),
            ("manifest", "{}"),
            ("source", "SomePath"),
            ("target", "DeltaTables"),
        ):
            c = dict(good, **{key: value})
            dummy = Mock()
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, "HOLD_FHIR"):
                guarded(dummy, **c)
            dummy.assert_not_called()
        source = inspect.getsource(guarded)
        frozen_source = inspect.getsource(notebook._frozen_fhir_source_context)
        # Physical native GET moved to shared frozen-source helper, used by
        # both existing Intake and new no-write Canonical runtime probes.
        self.assertIn('_frozen_fhir_source_context(', source)
        self.assertIn('spark.read.format("binaryFile")', frozen_source)
        self.assertIn("read_source_objects_native(", frozen_source)
        self.assertIn("parse_fhir_resources(", source)
        self.assertNotIn(".write(", source + frozen_source)
        content = (GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        self.assertIn('elif run_mode == "INTAKE_READONLY":', content)
        self.assertIn('run_mode = "HALT"', content)
        self.assertIn("notebookutils.notebook.exit(intake_exit)", content)
        self.assertIn('raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")', content)

    def test_native_environment_has_exact_hashed_custom_wheel(self):
        import hashlib
        import zipfile
        # Git-native is a declarative staging asset and NOT the Fabric GA
        # published library. Source-only branches retain 0.1.6 while the
        # reviewed Wheel staging branch contains 0.1.7. Both must be exact
        # SHA pinned, solitary and structurally valid.
        folder = GIT_ROOT / "env_healthcare.Environment/Libraries/CustomLibraries"
        wheels = list(folder.glob("*.whl"))
        self.assertEqual(len(wheels), 1, "HOLD_GIT_NATIVE_MULTIPLE_WHEELS")
        pinned = {
            "healthcare_data_engine-0.1.6-py3-none-any.whl":
                "473df0171de89a1260ce8bd4b58de301802a23f28cd7c6007c8f9563772748ff",
            "healthcare_data_engine-0.1.7-py3-none-any.whl":
                "0ae651aab21ce52592ac7462e365554dfc4a8cb0e65d44dd5ba9a39cb448c301",
        }
        lib = wheels[0]
        self.assertIn(lib.name, pinned, "HOLD_UNREVIEWED_GIT_NATIVE_WHEEL")
        self.assertEqual(hashlib.sha256(lib.read_bytes()).hexdigest(),
                         pinned[lib.name], "HOLD_GIT_NATIVE_WHEEL_SHA_DRIFT")
        with zipfile.ZipFile(lib) as wheel:
            names = wheel.namelist()
            self.assertTrue(any(n.endswith(".dist-info/METADATA") for n in names))
            self.assertTrue(any(n.startswith("healthcare_data_engine/") for n in names))
            p3 = "healthcare_data_engine/mapping/omop/candidate_publication.py"
            self.assertEqual(p3 in names, "0.1.7" in lib.name)
        # Existing HALT Native business Notebook STILL pins 0.1.6. A
        # review-only Git 0.1.7 Wheel is not a GA Publish or activation.
        notebook = (
            GIT_ROOT / "nb_fhir_ingest.Notebook/notebook-content.py"
        ).read_text()
        self.assertIn('if engine_version != "0.1.6":', notebook)
        self.assertIn('run_mode = "HALT"', notebook)
        self.assertIn('write_authorized = False', notebook)

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
