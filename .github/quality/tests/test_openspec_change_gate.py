"""Offline positive and negative tests for mandatory OpenSpec PR association."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SOURCE = Path(__file__).resolve().parents[3] / ".github/quality/scripts/check_openspec_change_gate.py"
SPEC = importlib.util.spec_from_file_location("openspec_change_gate", SOURCE)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class OpenSpecChangeGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.slug = "implement-patient-snapshot"
        self.create_change()
        self.body = "OpenSpec-Change: implement-patient-snapshot\nOpenSpec-Task: 2.1"
        self.paths = ["local-data-platform/apps/person/loader.py",
                      "openspec/changes/implement-patient-snapshot/tasks.md"]

    def create_change(self, tasks="- [x] 1.1 Plan\n- [ ] 2.1 Build\n"):
        folder = self.root / "openspec/changes" / self.slug
        folder.mkdir(parents=True, exist_ok=True)
        for name, content in {
            ".openspec.yaml": "schema: spec-driven\n",
            "proposal.md": "# Proposal\n",
            "design.md": "# Design\n",
            "tasks.md": tasks,
        }.items():
            (folder / name).write_text(content, encoding="utf-8")

    def check(self, paths=None, body=None, base_has_active=None):
        return gate.evaluate(
            self.paths if paths is None else paths,
            self.body if body is None else body,
            self.root,
            base_has_active,
        )

    def assert_denied(self, *args, **kwargs):
        passed, msg = self.check(*args, **kwargs)
        self.assertFalse(passed, msg)
        self.assertTrue(msg)

    def test_valid_material_pr_with_change_task_and_sync(self):
        self.assertTrue(self.check()[0])

    def test_change_created_in_same_pr_is_valid(self):
        paths = ["openspec/changes/implement-patient-snapshot/proposal.md",
                 "openspec/changes/implement-patient-snapshot/tasks.md"]
        self.assertTrue(self.check(paths=paths)[0])

    def test_zero_changed_paths_rejected(self):
        self.assert_denied(paths=[])

    def test_duplicate_diff_paths_rejected(self):
        self.assert_denied(paths=self.paths + [self.paths[0]])

    def test_missing_body_association(self):
        self.assert_denied(body="No Change recorded")

    def test_change_only_without_task(self):
        self.assert_denied(body="OpenSpec-Change: implement-patient-snapshot")

    def test_task_only_without_change(self):
        self.assert_denied(body="OpenSpec-Task: 2.1")

    def test_nonexistent_change(self):
        self.assert_denied(body="OpenSpec-Change: invented-change\nOpenSpec-Task: 2.1")

    def test_duplicate_change_declaration(self):
        self.assert_denied(body=self.body + "\nOpenSpec-Change: another")

    def test_duplicate_task_declaration(self):
        self.assert_denied(body=self.body + "\nOpenSpec-Task: 2.2")

    def test_invalid_slug_rejected(self):
        self.assert_denied(body="OpenSpec-Change: ../bad\nOpenSpec-Task: 2.1")

    def test_invalid_task_reference_rejected(self):
        self.assert_denied(body="OpenSpec-Change: implement-patient-snapshot\nOpenSpec-Task: 6.6")

    def test_task_file_not_changed_rejected(self):
        self.assert_denied(paths=["local-data-platform/apps/person/loader.py"])

    def test_missing_proposal_rejected(self):
        (self.root / "openspec/changes" / self.slug / "proposal.md").unlink()
        self.assert_denied()

    def test_empty_tasks_rejected(self):
        self.create_change("# no recorded tasks\n")
        self.assert_denied()

    def test_duplicate_task_ids_rejected(self):
        self.create_change("- [ ] 2.1 One\n- [x] 2.1 Duplicate\n")
        with self.assertRaises(ValueError):
            self.check()

    def test_safe_docs_only_requires_explicit_exemption(self):
        self.assertTrue(self.check(
            paths=["README.md", "documents/systems/data-platform/airflow/README.md"],
            body="OpenSpec-Exemption: docs-only",
        )[0])
        self.assert_denied(paths=["README.md"], body="Minor typo")

    def test_docs_only_fails_for_code(self):
        self.assert_denied(paths=["README.md", "local-data-platform/apps/example.py"],
                           body="OpenSpec-Exemption: docs-only")

    def test_docs_only_fails_for_workflow_or_checker(self):
        for path in (".github/workflows/publish.yml", ".github/quality/scripts/check.py"):
            with self.subTest(path=path):
                self.assert_denied(paths=[path], body="OpenSpec-Exemption: docs-only")

    def test_docs_only_fails_for_architecture_governance_and_code_map(self):
        for path in ("AGENTS.md", "documents/README.md",
                     "documents/architecture/SYSTEM-OVERVIEW.md",
                     "documents/engineering/status/PROJECT-STATUS.md",
                     "documents/systems/data-platform/spark/CODE.md",
                     "openspec/config.yaml", "azure-fabric/infra-terraform/main.tf"):
            with self.subTest(path=path):
                self.assert_denied(paths=[path], body="OpenSpec-Exemption: docs-only")

    def test_docs_only_cannot_be_mixed_with_change(self):
        self.assert_denied(paths=["README.md"],
                           body=self.body + "\nOpenSpec-Exemption: docs-only")

    def test_invalid_exemption_rejected(self):
        self.assert_denied(paths=["README.md"], body="OpenSpec-Exemption: anything")

    def test_archived_change_requires_base_and_closed_tasks(self):
        source = self.root / "openspec/changes" / self.slug
        archive = self.root / ("openspec/changes/archive/2026-10-18-" + self.slug)
        archive.parent.mkdir(parents=True)
        source.rename(archive)
        (archive / "tasks.md").write_text("- [x] 1.1 Plan\n- [x] 2.1 Build\n", encoding="utf-8")
        archive_paths = [f"openspec/changes/{self.slug}/tasks.md",
                         f"openspec/changes/archive/{archive.name}/tasks.md"]
        self.assertTrue(self.check(paths=archive_paths, base_has_active=lambda s: s == self.slug)[0])
        self.assert_denied(paths=archive_paths, base_has_active=lambda _: False)
        self.assert_denied(paths=archive_paths + [".github/workflows/build.yml"],
                           base_has_active=lambda _: True)
        (archive / "tasks.md").write_text("- [x] 1.1 Plan\n- [ ] 2.1 Build\n", encoding="utf-8")
        self.assert_denied(paths=archive_paths, base_has_active=lambda _: True)

    def test_archive_move_absent_rejected(self):
        active = self.root / "openspec/changes" / self.slug
        target = self.root / ("openspec/changes/archive/2026-10-18-" + self.slug)
        target.parent.mkdir(parents=True)
        active.rename(target)
        (target / "tasks.md").write_text("- [x] 2.1 Build\n", encoding="utf-8")
        self.assert_denied(paths=[f"openspec/changes/archive/{target.name}/tasks.md"],
                           base_has_active=lambda _: True)

    def test_safe_path_policy(self):
        self.assertTrue(gate.safe_docs_only("README.md"))
        self.assertTrue(gate.safe_docs_only("documents/systems/azure-fabric/README.md"))
        self.assertFalse(gate.safe_docs_only("documents/architecture/README.md"))
        self.assertFalse(gate.safe_docs_only("documents/systems/data-platform/CODE.md"))
        self.assertFalse(gate.safe_docs_only("documents/engineering/README.md"))


if __name__ == "__main__":
    unittest.main()
