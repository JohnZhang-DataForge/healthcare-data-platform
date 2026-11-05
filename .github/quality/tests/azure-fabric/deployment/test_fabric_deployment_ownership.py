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

    def test_trusted_policy_mutation_forbidden_after_bootstrap(self):
        base = {checker.TRUSTED_WORKFLOW, checker.OWNER_FILE}
        for protected in checker.PROTECTED_POLICY:
            errors = checker.evaluate({protected: "M"}, REGISTRY, base_paths=base)
            self.assertTrue(any("trusted-owner-policy-mutation" in e for e in errors), protected)

    def test_first_workflow_introduction_is_allowed(self):
        self.assertEqual(checker.evaluate(
            {checker.TRUSTED_WORKFLOW: "A"}, REGISTRY, base_paths=set()), [])

    def test_added_deploy_source_needs_exact_code_map_link(self):
        path = "azure-fabric/deployment/warehouse/schema_apply.py"
        changes = {path: "A", checker.CODE_MAP: "M"}
        self.assertEqual(checker.evaluate(changes, REGISTRY, code_map_text=path), [])
        self.assertTrue(any("missing-exact-code-map-source-link" in e for e in
            checker.evaluate(changes, REGISTRY, code_map_text="not linked")))

    def test_unregistered_existing_head_is_rejected(self):
        paths = {checker.OWNER_FILE, checker.CODE_MAP,
                 "azure-fabric/deployment/unknown/not_allowed.py"}
        errors = checker.evaluate({}, REGISTRY, head_paths=paths)
        self.assertTrue(any("unregistered-deployment-component" in e for e in errors))
    def test_retired_paths_are_not_reintroduced(self):
        self.assertEqual(checker.evaluate({}, REGISTRY), [])

if __name__ == "__main__":
    unittest.main()
