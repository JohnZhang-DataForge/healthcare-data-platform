import ast
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

APP = (
    PROJECT_ROOT
    / "spark/apps/person/"
      "map_canonical_patient_to_omop.py"
)


class PersonOmopMapperStaticTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(
            encoding="utf-8"
        )

        cls.tree = ast.parse(
            cls.source
        )


    def test_python_parses(self):
        self.assertIsNotNone(
            self.tree
        )


    def test_approved_raw_required(self):
        self.assertIn(
            '"APPROVED"',
            self.source,
        )

        self.assertIn(
            '"dq_status"',
            self.source,
        )


    def test_v2_canonical_fields(self):
        for name in [
            "source_record_id",
            "birth_date",
            "gender_code",
            "race_code",
            "ethnicity_code",
        ]:
            self.assertIn(
                name,
                self.source,
            )

        self.assertNotIn(
            "patient_source_id",
            self.source,
        )


    def test_stable_id_map_is_read(self):
        self.assertIn(
            "etl.person_id_map",
            self.source,
        )

        self.assertIn(
            "source_person_id",
            self.source,
        )

        self.assertIn(
            "STABLE_PERSON_ID_MAP=PASS",
            self.source,
        )


    def test_concepts_are_runtime_validated(self):
        self.assertIn(
            "cdm.concept",
            self.source,
        )

        self.assertIn(
            "standard_concept",
            self.source,
        )

        self.assertIn(
            "invalid_reason",
            self.source,
        )


    def test_no_fixed_mapping_table_size(self):
        self.assertNotIn(
            "map_count != EXPECTED_ROWS",
            self.source,
        )

        self.assertNotIn(
            "EXPECTED_ROWS = 113",
            self.source,
        )


    def test_no_postgresql_write(self):
        self.assertNotIn(
            'format("jdbc")\n        .mode',
            self.source,
        )

        self.assertNotIn(
            "etl.person_stage",
            self.source,
        )

        self.assertNotIn(
            "INSERT INTO",
            self.source,
        )

        self.assertNotIn(
            "UPDATE cdm.person",
            self.source,
        )


    def test_processed_write_is_immutable(self):
        self.assertIn(
            '"errorifexists"',
            self.source,
        )

        self.assertIn(
            "--output-data-uri",
            self.source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
