"""Read-only, synthetic fixtures for OpenSpec-first task index."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

FILE = Path(__file__).resolve().parents[1] / "scripts/active_openspec_index.py"
SPEC = importlib.util.spec_from_file_location("active_openspec_index", FILE)
assert SPEC and SPEC.loader
index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(index)


class ActiveOpenSpecIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "openspec/changes/archive/2026-11-01-retired").mkdir(parents=True)
        (self.root / "openspec/changes/archive/2026-11-01-retired/tasks.md").write_text(
            "- [ ] 9.9 Old archived task\n", encoding="utf-8"
        )

    def active(self, name, content=None):
        folder = self.root / "openspec/changes" / name
        folder.mkdir(parents=True)
        if content is not None:
            (folder / "tasks.md").write_text(content, encoding="utf-8")

    def test_active_only_sorted_and_live_checkbox_counts(self):
        self.active("z-writer", "# F2\n- [x] 2.1a Preview\n- [ ] 2.1d.2 Mapping profile\n")
        self.active("a-fhir", "- [x] 1.1 Done\n- [x] 1.2 Done\n")
        got = index.load_active_changes(self.root)
        self.assertEqual([x["change"] for x in got], ["a-fhir", "z-writer"])
        self.assertEqual((got[0]["open"], got[0]["done"], got[0]["status"]), (0, 2, "NO_OPEN_TASKS"))
        self.assertEqual((got[1]["open"], got[1]["done"], got[1]["status"]), (1, 1, "OPEN"))
        self.assertIn("2.1d.2", got[1]["next"])
        self.assertNotIn("retired", index.render_markdown(got))

    def test_missing_or_unrecognized_tasks_is_unknown_not_done(self):
        self.active("no-tasks")
        self.active("unrecognized", "There are no numbered tasks yet.\n")
        got = index.load_active_changes(self.root)
        self.assertEqual([x["status"] for x in got], ["UNKNOWN", "UNKNOWN"])
        self.assertTrue(all(x["open"] is None for x in got))

    def test_next_run_reflects_additions_and_archive(self):
        self.active("new-change", "- [x] 1.1 Existing\n")
        self.assertEqual(index.load_active_changes(self.root)[0]["open"], 0)
        task_file = self.root / "openspec/changes/new-change/tasks.md"
        task_file.write_text("- [x] 1.1 Existing\n- [ ] 1.2 Added\n", encoding="utf-8")
        self.assertEqual(index.load_active_changes(self.root)[0]["open"], 1)
        target = self.root / "openspec/changes/archive/2026-11-05-new-change"
        (self.root / "openspec/changes/new-change").rename(target)
        self.assertEqual(index.load_active_changes(self.root), [])

    def test_cli_json_readonly(self):
        self.active("example", "- [ ] 1.1 Needed\n")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        run = subprocess.run(
            [sys.executable, str(FILE), "--repo-root", str(self.root), "--format", "json"],
            capture_output=True, text=True, check=True
        )
        got = json.loads(run.stdout)
        self.assertEqual(got["active_changes"][0]["open"], 1)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))

    def test_empty_active_collection_is_valid(self):
        self.assertEqual(index.load_active_changes(self.root), [])
        self.assertIn("No active changes", index.render_markdown([]))


if __name__ == "__main__":
    unittest.main()
