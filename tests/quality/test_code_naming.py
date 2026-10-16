"""Unit tests for the component-first new-code-path naming policy."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / "scripts/quality/check_new_code_names.py"
SPEC = importlib.util.spec_from_file_location("code_naming", PATH)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class NewCodeNamingTests(unittest.TestCase):
    def test_reject_new_task_step_code(self):
        for path in (
            "apps/task005/condition.py", "airflow/dags/task005_pipeline.py",
            "spark/apps/task004/new_adapter.py", "sql/omop/step04a_add.sql",
            "scripts/task005/step02.sh", "tests/task005/test_step04.py",
            "images/task005-runtime/Dockerfile",
            ".github/workflows/task005-validation.yml",
            "kubernetes/manifests/task_005/consumer.yaml",
        ):
            with self.subTest(path=path):
                self.assertTrue(policy.invalid_path(path))

    def test_allow_component_capability_names(self):
        for path in (
            "apps/omop_writer/condition_writer.py",
            "airflow/dags/condition_omop_consumer.py",
            "spark/apps/condition/transform_condition.py",
            "sql/omop/condition_occurrence_indexes.sql",
            "scripts/omop/verify_condition_fk.sh",
            "tests/omop_writer/test_condition_idempotency.py",
            "images/omop-condition-writer/Dockerfile",
            ".github/workflows/condition-validation.yml",
            "kubernetes/manifests/condition/consumer-job.yaml.tpl",
        ):
            with self.subTest(path=path):
                self.assertFalse(policy.invalid_path(path))

    def test_historical_documentation_not_checked(self):
        for path in ("docs/tasks/TASK-004-FINAL-CLOSEOUT.md", "documents/migration/task005-notes.md"):
            self.assertFalse(policy.invalid_path(path))


if __name__ == "__main__":
    unittest.main()
