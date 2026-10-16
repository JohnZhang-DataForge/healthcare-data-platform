"""Unit tests for the offline relative Markdown link validation gate."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

FILE = Path(__file__).resolve().parents[2] / "scripts/quality/check_documentation_links.py"
SPEC = importlib.util.spec_from_file_location("documentation_links", FILE)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class DocumentationLinkTests(unittest.TestCase):
    def test_existing_relative_file_and_directory(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "code").mkdir()
            (root / "code" / "main.py").write_text("pass\n", encoding="utf-8")
            doc = root / "docs" / "README.md"
            text = "[source](../code/main.py) [directory](../code/) [anchor](#intro)\n"
            checked, errors = guard.missing_links(text, doc, root)
            self.assertEqual((checked, errors), (2, []))

    def test_missing_path_reports_source_location(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            doc = root / "README.md"
            checked, errors = guard.missing_links("First\n[broken](unknown.md)\n", doc, root)
            self.assertEqual(checked, 1)
            self.assertEqual(errors, ["README.md:2: MISSING unknown.md"])

    def test_external_and_fenced_examples_do_not_count(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            doc = root / "README.md"
            text = "[web](https://example.org) [mail](mailto:x@example.org)\n```md\n[fake](missing.md)\n```\n"
            self.assertEqual(guard.missing_links(text, doc, root), (0, []))


if __name__ == "__main__":
    unittest.main()
