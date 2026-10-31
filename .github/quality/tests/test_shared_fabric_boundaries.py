"""Positive and negative controls for Shared/Fabric source boundaries."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_shared_fabric_boundaries.py"
SPEC = importlib.util.spec_from_file_location("shared_guard", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

SHARED = "shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/bundle.py"
NOTEBOOK = ("azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/"
            "nb_fhir_ingest.Notebook/notebook-content.py")
ENV = ("azure-fabric/workspaces/healthcare-omop/environments/"
       "env_healthcare.Environment/libraries/PublicLibraries/environment.yml")


class SharedFabricGuardTest(unittest.TestCase):
    def test_valid_and_unmapped_source(self):
        owner = guard.OWNERS["shared"]
        link = "../../../../" + SHARED
        docs = {path: "" for path in guard.OWNERS.values()}
        docs[owner] = "| [bundle](" + link + ") | FHIR parser |"
        self.assertEqual(guard.check_ownership({SHARED}, docs, {owner}, {SHARED}), [])
        docs[owner] = ""
        self.assertIn("MISSING_OWNER:" + SHARED,
                      guard.check_ownership({SHARED}, docs, {owner}, {SHARED}))

    def test_wrong_owner_duplicate_and_stale(self):
        docs = {path: "" for path in guard.OWNERS.values()}
        docs[guard.OWNERS["shared"]] = "| [bundle](../../../../" + SHARED + ") | source |"
        docs[guard.OWNERS["notebooks"]] = docs[guard.OWNERS["shared"]]
        errors = guard.check_ownership(set(), docs, set(), set())
        self.assertIn("STALE_OWNER:" + SHARED, errors)
        self.assertIn("DUPLICATE_OWNER:" + SHARED, errors)
        self.assertIn("WRONG_OWNER:" + SHARED, errors)

    def test_same_pr_owner_sync(self):
        docs = {path: "" for path in guard.OWNERS.values()}
        docs[guard.OWNERS["shared"]] = "| [bundle](../../../../" + SHARED + ") | source |"
        errors = guard.check_ownership({SHARED}, docs, set(), {SHARED})
        self.assertIn("MISSING_SAME_PR_CODE_MAP_UPDATE:" + guard.OWNERS["shared"], errors)

    def test_native_environment_and_notebook_owner(self):
        self.assertEqual(guard.owner_for(NOTEBOOK), "notebooks")
        self.assertEqual(guard.owner_for(ENV), "environments")
        self.assertTrue(guard.is_owned_source(ENV))
        self.assertFalse(guard.is_owned_source("azure-fabric/workspaces/healthcare-omop/pipelines/.gitkeep"))

    def test_shared_good_imports(self):
        good = "from datetime import datetime\nfrom pyspark.sql import DataFrame\n"
        self.assertEqual(guard.check_imports(SHARED, good), [])

    def test_shared_provider_and_local_imports_blocked(self):
        for statement in ("import azure.storage.blob", "from boto3 import client",
                          "from airflow.models import DAG", "import local_data_platform.spark",
                          "import delta.tables", "import notebookutils",
                          "import healthcare_fabric"):
            with self.subTest(statement=statement):
                self.assertTrue(any("FORBIDDEN_SHARED_IMPORT" in msg for msg in
                                    guard.check_imports(SHARED, statement)))

    def test_shared_import_side_effect_blocked(self):
        for code in ("open('local.json')", "os.getenv('SECRET')",
                     "SparkSession.builder.getOrCreate()", "subprocess.run(['ls'])"):
            with self.subTest(code=code):
                self.assertTrue(guard.check_imports(SHARED, code), code)

    def test_native_notebook_must_not_duplicate_business_mapper(self):
        self.assertIn("DUPLICATE_BUSINESS_MAPPER:" + NOTEBOOK + ":normalize_fhir_patient",
                      guard.check_layout(NOTEBOOK, "def normalize_fhir_patient(x): return x"))
        self.assertEqual(guard.check_layout(NOTEBOOK, "def run_notebook(x): return x"), [])

    def test_contract_clone_and_retired_path(self):
        copy = '{"fields":[],"primary_key":[],"canonical_version":"v1"}'
        self.assertTrue(any("COPIED_LOCAL_CANONICAL_CONTRACT:" in x for x in
                            guard.check_layout("shared-data-engine/contracts/patient-v1.json", copy)))
        self.assertTrue(guard.check_layout("azure-fabric/runtime/framework.py", ""))
        self.assertTrue(guard.check_layout("azure-fabric/workspaces/johnzhang-test/a.py", ""))
        self.assertTrue(guard.check_layout("shared-data-engine/src/other_engine/x.py", ""))

    def test_environment_rejects_python_source(self):
        bad = ENV.replace("environment.yml", "src/helper.py")
        self.assertTrue(guard.check_layout(bad, "print('not an Environment wheel')"))

    def test_contract_digests_are_explicit_sha256(self):
        self.assertEqual(len(guard.CONTRACT_HASHES), 2)
        for value in guard.CONTRACT_HASHES.values():
            self.assertEqual(len(value), 64)
            int(value, 16)


if __name__ == "__main__":
    unittest.main()
