"""Positive/negative default-branch component path policy regression."""
import importlib.util
from pathlib import Path
import unittest

POLICY = Path(__file__).resolve().parents[1] / "scripts" / "check_new_source_structure_trusted.py"
spec = importlib.util.spec_from_file_location("trusted_structure", POLICY)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ComponentPathGateTests(unittest.TestCase):
    def test_old_task_files_are_left_unchanged(self):
        legacy = {"local-data-platform/apps/task003/visit_candidate_rules.py"}
        self.assertEqual(gate.evaluate({"local-data-platform/apps/task003/visit_candidate_rules.py": "M"},
                                       base_paths=legacy, head_paths=legacy), [])

    def test_reject_addition_under_all_source_roots(self):
        examples = (
            "local-data-platform/apps/task005/condition.py",
            "local-data-platform/scripts/task003/new_writer.sh",
            "azure-fabric/openlineage/task006_publisher.py",
            "shared-data-engine/src/healthcare_data_engine/step02.py",
            "platform-portal/portal/web/task005_frontend.ts",
            ".github/workflows/task005-condition.yml",
            ".github/quality/tests/local-dp/task005/test_condition.py",
        )
        for path in examples:
            with self.subTest(path=path):
                errors = gate.evaluate({path: "A"})
                self.assertTrue(any("new-task-or-step-source-path" in e for e in errors), errors)

    def test_allow_function_first_names_and_historical_docs(self):
        for path in (
            "local-data-platform/spark/apps/condition/canonical.py",
            "local-data-platform/apps/omop_writer/condition_commit.py",
            "azure-fabric/deployment/warehouse/condition.sql",
            "shared-data-engine/src/healthcare_data_engine/mapping/condition.py",
            "platform-portal/portal/web/lineage.ts",
            ".github/quality/tests/data-platform/condition/test_candidate.py",
            "documents/systems/data-platform/README-task004-history.md",
            "openspec/changes/archive/2026-10-18-task004-study/tasks.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(gate.introduced_bad_name(path))

    def test_reject_added_direct_legacy_module_import(self):
        path = "local-data-platform/spark/apps/condition/loader.py"
        errors = gate.evaluate({path: "A"}, head_text={path:
            "from apps.task004 import cdm_runtime_cli\n"})
        self.assertTrue(any("new-direct-legacy-task-import" in e for e in errors), errors)

    def test_reject_added_direct_legacy_source_path(self):
        path = "local-data-platform/apps/omop_writer/condition.py"
        errors = gate.evaluate({path: "A"}, head_text={path:
            'ENTRY = "local-data-platform/apps/task003/visit_candidate_rules.py"\n'})
        self.assertTrue(any("new-direct-legacy-task-filepath" in e for e in errors), errors)

    def test_existing_postgres_task004_ledger_is_not_renamed(self):
        path = "local-data-platform/apps/omop_writer/condition.py"
        self.assertEqual(gate.evaluate({path: "A"}, head_text={path:
            'QUERY = "SELECT * FROM etl.task004_batch_ledger"\n'}), [])

    def test_brand_new_source_without_legacy_dependency_passes(self):
        path = "local-data-platform/spark/apps/condition/canonical.py"
        self.assertEqual(gate.evaluate({path: "A"}, head_text={path:
            "def canonical_condition(x):\n    return x\n"}), [])

    def test_existing_old_code_may_keep_legacy_import(self):
        path = "local-data-platform/apps/omop_writer/existing.py"
        self.assertEqual(gate.evaluate({path: "M"}, head_text={path:
            "from apps.task004 import old_writer\n"}), [])

    def test_new_quality_test_may_validate_existing_legacy(self):
        path = ".github/quality/tests/data-platform/omop/test_legacy_bridge.py"
        self.assertEqual(gate.evaluate({path: "A"}, head_text={path:
            'HISTORICAL = "local-data-platform/apps/task004/cdm_runtime_cli.py"\n'}), [])

    def test_user_cannot_edit_trusted_policy_after_bootstrap(self):
        before = {gate.TRUSTED_WORKFLOW, gate.POLICY_SCRIPT, gate.POLICY_TEST}
        for item in gate.PROTECTED:
            errors = gate.evaluate({item: "M"}, base_paths=before, head_paths=before)
            self.assertTrue(any("trusted-directory-policy-mutation" in e for e in errors), item)

    def test_bootstrap_first_pr_allowed_and_future_deletion_denied(self):
        self.assertEqual(gate.evaluate({gate.TRUSTED_WORKFLOW: "A"}, base_paths=set()), [])
        errors = gate.evaluate({gate.TRUSTED_WORKFLOW: "D"},
                               base_paths={gate.TRUSTED_WORKFLOW}, head_paths=set())
        self.assertTrue(any("trusted-workflow-deleted" in e for e in errors))

    def test_invalid_new_python_fails_closed(self):
        path = "local-data-platform/apps/condition/invalid.py"
        errors = gate.evaluate({path: "A"}, head_text={path: "def invalid(\n"})
        self.assertTrue(any("invalid-new-python-syntax" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
