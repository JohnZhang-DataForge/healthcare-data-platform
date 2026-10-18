import ast
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SOURCE_PATH = (
    PROJECT_ROOT
    / "spark/apps/person/"
      "synthea_patient_adapter.py"
)


class PatientAdapterStaticTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.source = (
            SOURCE_PATH.read_text(
                encoding="utf-8"
            )
        )

        cls.tree = ast.parse(
            cls.source
        )


    def test_source_parses(self):
        self.assertIsNotNone(
            self.tree
        )


    def test_no_legacy_phase3c_path(self):
        self.assertNotIn(
            "/data/spark/phase3c",
            self.source,
        )

        self.assertNotIn(
            "seed=20261005",
            self.source,
        )

        self.assertNotIn(
            "population=100",
            self.source,
        )


    def test_no_hardcoded_113(self):
        self.assertNotIn(
            "EXPECTED_ROWS = 113",
            self.source,
        )


    def test_manifest_driven_input(self):
        self.assertIn(
            "--manifest-uri",
            self.source,
        )

        self.assertIn(
            'patient_file["row_count"]',
            self.source,
        )

        self.assertIn(
            'manifest["landing_uri"]',
            self.source,
        )


    def test_isolated_processing_write(self):
        self.assertIn(
            '"errorifexists"',
            self.source,
        )

        self.assertIn(
            "--processing-data-uri",
            self.source,
        )


    def test_no_raw_or_database_publish(self):
        self.assertNotIn(
            "health-raw",
            self.source,
        )

        self.assertNotIn(
            "jdbc:postgresql",
            self.source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
