"""Positive/negative tests for trusted repository layout; no runtime effects."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_repository_layout.py"
spec = importlib.util.spec_from_file_location("check_repository_layout", SCRIPT)
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class LayoutGateTests(unittest.TestCase):
    def setUp(self):
        self.old = {
            "shared-data-engine/tests/test_fhir_r4_contract.py",
            "azure-fabric/warehouse/omop-foundation/writer/README.md",
            "azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/.platform",
            "documents/systems/azure-fabric/notebooks/CODE.md",
            "README.md",
        }
        self.baseline = frozenset(p for p in self.old if layout.legacy_violation(p))

    def check(self, additions=(), removals=(), changed=()):
        after = self.old.union(additions).difference(removals)
        diff = set(additions) | set(removals) | set(changed)
        return layout.check_layout(self.old, after, diff, self.baseline)

    def assert_rule(self, result, rule, path, owner):
        self.assertTrue(any(f"PATH={path} RULE={rule} EXPECTED_OWNER={owner}" in s for s in result), result)

    def test_historical_readme_and_test_edits_pass(self):
        self.assertEqual([], self.check(changed=["shared-data-engine/tests/test_fhir_r4_contract.py", "azure-fabric/warehouse/omop-foundation/writer/README.md"]))

    def test_new_central_test_and_quality_script_pass(self):
        self.assertEqual([], self.check(additions=[".github/quality/tests/azure-fabric/notebook/test_replay.py", ".github/quality/scripts/check_new_dq.py"]))

    def test_existing_native_metadata_edit_pass(self):
        self.assertEqual([], self.check(changed=["azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/.platform"]))

    def test_new_native_metadata_needs_code_map(self):
        p = "azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/definition.json"
        self.assert_rule(self.check(additions=[p]), "fabric-code-map-sync", p, "documents/systems/azure-fabric/notebooks/CODE.md")
        self.assertEqual([], self.check(additions=[p], changed=["documents/systems/azure-fabric/notebooks/CODE.md"]))

    def test_readme_rejected(self):
        p = "azure-fabric/warehouse/new-writer/README.md"
        self.assert_rule(self.check(additions=[p]), "new-source-document", p, "documents/")

    def test_old_readme_cannot_reappear_after_retirement(self):
        p = "azure-fabric/warehouse/omop-foundation/writer/README.md"
        result = layout.check_layout(self.old - {p}, self.old, {p}, self.baseline)
        self.assert_rule(result, "new-source-document", p, "documents/")

    def test_test_under_old_source_tests_rejected(self):
        p = "local-data-platform/tests/spark/test_new_pipeline.py"
        self.assert_rule(self.check(additions=[p]), "new-test-outside-quality", p, ".github/quality/tests/")

    def test_integration_tests_folder_cannot_bypass_owner(self):
        p = "azure-fabric/warehouse/integration_tests/helper.py"
        self.assert_rule(self.check(additions=[p]), "new-test-outside-quality", p, ".github/quality/tests/")

    def test_code_map_checker_mutation_rejected(self):
        p = ".github/quality/scripts/check_component_code_map.py"
        self.old.add(p)
        self.assert_rule(self.check(changed=[p]), "trusted-policy-mutation", p, "separate approved governance/bootstrap procedure")

    def test_top_level_module_rejected(self):
        p = "brand-new-system/api.py"
        self.assert_rule(self.check(additions=[p]), "unapproved-top-level-module", p, "approved root module and OpenSpec architecture approval")

    def test_fake_native_warehouse_rejected(self):
        p = "azure-fabric/workspaces/healthcare-omop/dw-omop-5.4.Warehouse/.platform"
        self.assert_rule(self.check(additions=[p]), "fabric-native-unapproved-item", p, "existing root-level Fabric Git Item; Warehouse SQL/Writer: azure-fabric/warehouse/")

    def test_fake_native_folder_rejected(self):
        p = "azure-fabric/workspaces/healthcare-omop/notebooks/nb_shadow.Notebook/.platform"
        self.assert_rule(self.check(additions=[p]), "fabric-native-unapproved-item", p, "existing root-level Fabric Git Item; Warehouse SQL/Writer: azure-fabric/warehouse/")

    def test_quality_scripts_not_test_folder(self):
        p = ".github/quality/scripts/test_replay.py"
        self.assert_rule(self.check(additions=[p]), "misplaced-quality-test", p, ".github/quality/tests/")

    def test_path_traversal_rejected(self):
        p = "local-data-platform/../bad/README.md"
        self.assert_rule(self.check(additions=[p]), "unsafe-git-path", p, "normalized repository relative path")

    def test_remove_and_readd_not_allowed(self):
        p = "azure-fabric/notebook-development/tests/test_shadow.py"
        self.assert_rule(self.check(additions=[p]), "new-test-outside-quality", p, ".github/quality/tests/")

    def test_policy_mutation_rejected(self):
        p = ".github/workflows/openspec-trusted-change-gate.yml"
        self.old.add(p)
        self.assert_rule(self.check(changed=[p]), "trusted-policy-mutation", p, "separate approved governance/bootstrap procedure")

    def test_legacy_inventory_is_sorted_and_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "inventory"
            target.write_text("# frozen\nazure-fabric/notebook-development/README.md\nshared-data-engine/tests/test_fhir_r4_contract.py\n", encoding="utf-8")
            self.assertEqual(2, len(layout.load_legacy_baseline(target)))
            target.write_text("shared-data-engine/tests/test_fhir_r4_contract.py\nshared-data-engine/tests/test_fhir_r4_contract.py\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                layout.load_legacy_baseline(target)


if __name__ == "__main__":
    unittest.main()
