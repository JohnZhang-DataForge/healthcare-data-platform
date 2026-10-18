import ast
import json
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

COMMON = (
    PROJECT_ROOT
    / "spark/common/omop.py"
)

CONTRACT = (
    PROJECT_ROOT
    / "spark/contracts/omop/"
      "person-v5.4.json"
)


class OmopPersonFoundationTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.source = COMMON.read_text(
            encoding="utf-8"
        )

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )


    def test_helper_parses(self):
        ast.parse(
            self.source
        )


    def test_contract_has_18_columns(self):
        fields = self.contract[
            "fields"
        ]

        names = [
            field["name"]
            for field in fields
        ]

        self.assertEqual(
            len(names),
            18,
        )

        self.assertEqual(
            len(names),
            len(set(names)),
        )


    def test_contract_identity(self):
        self.assertEqual(
            self.contract[
                "contract_name"
            ],
            "omop.person",
        )

        self.assertEqual(
            self.contract[
                "omop_version"
            ],
            "v5.4",
        )


    def test_stable_key_contract(self):
        self.assertEqual(
            self.contract[
                "primary_key"
            ],
            ["person_id"],
        )

        self.assertEqual(
            self.contract[
                "source_key"
            ],
            ["person_source_value"],
        )


    def test_verified_demographic_concepts(self):
        expected = {
            8507,
            8532,
            8515,
            8516,
            8557,
            8527,
            38003563,
            38003564,
        }

        namespace = {}

        exec(
            compile(
                self.source,
                str(COMMON),
                "exec",
            ),
            namespace,
        )

        actual = set(
            namespace[
                "DEMOGRAPHIC_CONCEPT_IDS"
            ]
        )

        self.assertEqual(
            actual,
            expected,
        )


    def test_no_batch_row_hardcoding(self):
        self.assertNotIn(
            "113",
            self.source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
