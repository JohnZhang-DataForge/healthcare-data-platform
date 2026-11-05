"""Offline ownership checker tests; no Fabric/SQL/Blob runtime."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = ROOT / ".github/quality/scripts/check_fabric_deployment_ownership.py"
spec = importlib.util.spec_from_file_location("fabric_deployment_owner_check", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
REGISTRY = (ROOT / "azure-fabric/deployment/owners.json").read_text()

class DeploymentOwnerTests(unittest.TestCase):
    def test_exact_owner_inventory(self):
        self.assertEqual(len(checker.load_registry(REGISTRY)["components"]), 7)
    def test_valid_deploy_script_requires_code_map(self):
        changes = {"azure-fabric/deployment/warehouse/apply_schema.py": "A",
                   checker.CODE_MAP: "M"}
        self.assertEqual(checker.evaluate(changes, REGISTRY), [])
        self.assertIn("missing-code-map", "|".join(checker.evaluate(
            {"azure-fabric/deployment/warehouse/apply_schema.py": "A"}, REGISTRY)))
    def test_reject_unknown_component(self):
        errors = checker.evaluate({"azure-fabric/deployment/other/run.py": "A",
                                   checker.CODE_MAP: "M"}, REGISTRY)
        self.assertTrue(any("unregistered-deployment-component" in e for e in errors))
    def test_reject_docs_tests_and_duplicate_src(self):
        bad = {"azure-fabric/deployment/notebook/README.md": "A",
               "azure-fabric/deployment/openlineage/tests/test_bad.py": "A",
               "azure-fabric/deployment/common/src/new_engine.py": "A",
               checker.CODE_MAP: "M"}
        errors = checker.evaluate(bad, REGISTRY)
        self.assertTrue(any("source-document" in e for e in errors))
        self.assertTrue(any("test-belongs-in-quality" in e for e in errors))
        self.assertTrue(any("wrong-deployment-owner" in e for e in errors))
    def test_retired_paths_are_not_reintroduced(self):
        self.assertEqual(checker.evaluate({}, REGISTRY), [])

if __name__ == "__main__":
    unittest.main()
