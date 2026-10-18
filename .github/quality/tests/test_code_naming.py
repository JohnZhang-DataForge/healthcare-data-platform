"""Unit tests for the component-first new-code-path naming policy."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[3] / ".github/quality/scripts/check_new_code_names.py"
SPEC = importlib.util.spec_from_file_location("code_naming", PATH)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class NewCodeNamingTests(unittest.TestCase):
    def test_reject_new_task_step_code(self):
        for path in (
            "data-platform/scripts/task999/step03.sh",
            "local-data-platform/scripts/task999/step03.sh",
            ".github/quality/scripts/task999.py",
            "data-platform/airflow/dags/task004_pipeline.py",
            "apps/task005/condition.py", "airflow/dags/task005_pipeline.py",
            "spark/apps/task004/new_adapter.py", "sql/omop/step04a_add.sql",
            "scripts/task005/step02.sh", "tests/task005/test_step04.py",
            "images/task005-runtime/Dockerfile",
            ".github/workflows/task005-validation.yml",
            "kubernetes/manifests/task_005/consumer.yaml",
            "azure-fabric/exporter/task005_snapshot.py",
            "azure-fabric/workspace/healthcare-omop/notebooks/ingestion/step01.Notebook/notebook-content.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(policy.invalid_path(path))

    def test_allow_component_capability_names(self):
        for path in (
            "data-platform/apps/omop_writer/condition_writer.py",
            "local-data-platform/apps/omop_writer/condition_writer.py",
            ".github/quality/scripts/check_example.py",
            "data-platform/scripts/omop/verify_fk.sh",
            "apps/omop_writer/condition_writer.py",
            "airflow/dags/condition_omop_consumer.py",
            "spark/apps/condition/transform_condition.py",
            "sql/omop/condition_occurrence_indexes.sql",
            "scripts/omop/verify_condition_fk.sh",
            "tests/omop_writer/test_condition_idempotency.py",
            "images/omop-condition-writer/Dockerfile",
            ".github/workflows/condition-validation.yml",
            "kubernetes/manifests/condition/consumer-job.yaml.tpl",
            "azure-fabric/exporter/omop_snapshot_export.py",
            "azure-fabric/workspace/healthcare-omop/notebooks/ingestion/omop_snapshot_load.Notebook/notebook-content.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(policy.invalid_path(path))

    def test_historical_documentation_not_checked(self):
        for path in ("docs/tasks/TASK-004-FINAL-CLOSEOUT.md", "documents/migration/task005-notes.md"):
            self.assertFalse(policy.invalid_path(path))



class LegacyRelocationTests(unittest.TestCase):
    """Exercise actual Git tree and blob comparisons in temporary repositories."""

    def setUp(self):
        import os
        import subprocess
        import tempfile
        self._os, self._subprocess = os, subprocess
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self._original = os.getcwd()
        os.chdir(self._temp.name)
        self.addCleanup(lambda: os.chdir(self._original))
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "CI Fixture")
        self.write(".github/legacy-relocations.json", '{"schema_version":1,"entries":[]}\n')
        self.write("scripts/task004/step03.sh", "# old script\n")
        self.git("add", ".")
        self.git("commit", "-qm", "original source")
        self.source_commit = self.git("rev-parse", "HEAD")
        self.source_blob = self.git("rev-parse", "HEAD:scripts/task004/step03.sh")

    def git(self, *args):
        proc = self._subprocess.run(["git", *args], capture_output=True,
                                    text=True, check=True)
        return proc.stdout.strip()

    def write(self, path, value):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")

    def authorize(self):
        import json
        entry = {
            "old_path": "scripts/task004/step03.sh",
            "new_path": "data-platform/scripts/task004/step03.sh",
            "source_commit": self.source_commit,
            "blob_sha": self.source_blob,
        }
        self.write(".github/legacy-relocations.json",
                   json.dumps({"schema_version": 1, "entries": [entry]}) + "\n")
        self.git("add", ".")
        self.git("commit", "-qm", "separate reviewed approval")
        return self.git("rev-parse", "HEAD")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "proposed move")
        return self.git("rev-parse", "HEAD")

    def move(self, content="# old script\n"):
        self.write("data-platform/scripts/task004/step03.sh", content)
        Path("scripts/task004/step03.sh").unlink()

    def test_identical_preapproved_move(self):
        base = self.authorize()
        self.move()
        head = self.commit()
        _, approved, blocked = policy.scan(base, head)
        self.assertEqual(approved, ["data-platform/scripts/task004/step03.sh"])
        self.assertEqual(blocked, [])

    def test_bad_new_file_cannot_hide_beside_approved_move(self):
        base = self.authorize()
        self.move()
        self.write("data-platform/scripts/task999/step03.sh", "# newly written\n")
        head = self.commit()
        _, approved, blocked = policy.scan(base, head)
        self.assertEqual(len(approved), 1)
        self.assertEqual(blocked, ["data-platform/scripts/task999/step03.sh"])

    def test_changed_legacy_content_cannot_claim_identical_move(self):
        base = self.authorize()
        self.move("# changed logic\n")
        head = self.commit()
        self.assertEqual(policy.scan(base, head)[2],
                         ["data-platform/scripts/task004/step03.sh"])

    def test_unapproved_move_is_rejected(self):
        base = self.git("rev-parse", "HEAD")
        self.move()
        head = self.commit()
        self.assertEqual(policy.scan(base, head)[2],
                         ["data-platform/scripts/task004/step03.sh"])

    def test_same_pr_allowlist_injection_is_not_trusted(self):
        import json
        base = self.git("rev-parse", "HEAD")
        self.write(".github/legacy-relocations.json", json.dumps({
            "schema_version": 1,
            "entries": [{
                "old_path": "scripts/task004/step03.sh",
                "new_path": "data-platform/scripts/task004/step03.sh",
                "source_commit": self.source_commit,
                "blob_sha": self.source_blob,
            }],
        }))
        self.move()
        head = self.commit()
        self.assertEqual(policy.scan(base, head)[2],
                         ["data-platform/scripts/task004/step03.sh"])

    def test_new_functional_path_is_allowed(self):
        base = self.git("rev-parse", "HEAD")
        self.write("data-platform/scripts/omop/verify_fk.sh", "# new component\n")
        head = self.commit()
        self.assertEqual(policy.scan(base, head)[2], [])

if __name__ == "__main__":
    unittest.main()
