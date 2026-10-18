import ast
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

COMMON = (
    PROJECT_ROOT
    / "spark/common/canonical_gate.py"
)

APP = (
    PROJECT_ROOT
    / "spark/apps/person/"
      "publish_canonical_patient.py"
)


class CanonicalGateStaticTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.common = COMMON.read_text(
            encoding="utf-8"
        )

        cls.app = APP.read_text(
            encoding="utf-8"
        )


    def test_python_parses(self):
        ast.parse(
            self.common
        )

        ast.parse(
            self.app
        )


    def test_shared_gate_exists(self):
        self.assertIn(
            "def validate_contract",
            self.common,
        )

        self.assertIn(
            "def validate_unique_key",
            self.common,
        )

        self.assertIn(
            "def validate_metadata",
            self.common,
        )


    def test_manifest_driven(self):
        self.assertIn(
            "read_json_document",
            self.app,
        )

        self.assertIn(
            "find_dataset_file",
            self.app,
        )

        self.assertNotIn(
            "EXPECTED_ROWS = 113",
            self.app,
        )


    def test_immutable_raw_write(self):
        self.assertIn(
            '"errorifexists"',
            self.app,
        )

        self.assertIn(
            "--raw-data-uri",
            self.app,
        )


    def test_no_database_write(self):
        self.assertNotIn(
            "jdbc:postgresql",
            self.app,
        )

        self.assertNotIn(
            "etl.person_stage",
            self.app,
        )


    def test_commit_boundary_not_published_here(self):
        self.assertIn(
            "RAW_MANIFEST_PUBLISHED=NO",
            self.app,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
