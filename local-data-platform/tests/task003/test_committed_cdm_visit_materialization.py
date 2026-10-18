import importlib.util
import unittest
from pathlib import Path


APP_PATH = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "task003"
    / "verify_committed_cdm_visit_materialization.py"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_committed_cdm_visit_materialization",
    APP_PATH,
)

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)


class CommittedCDMVisitMaterializationTests(
    unittest.TestCase
):
    def test_parse_state_text(self):
        text = """
BEGIN
SET
CDM_STATE=5799|5799|2|5800
SEQUENCE_STATE=5800|true
ROLLBACK
"""

        values = MODULE.parse_state_text(
            text
        )

        self.assertEqual(
            values["CDM_STATE"],
            "5799|5799|2|5800",
        )

        self.assertEqual(
            values["SEQUENCE_STATE"],
            "5800|true",
        )

    def test_validate_state_accepts_exact_state(self):
        MODULE.validate_state(
            dict(
                MODULE.EXPECTED_STATE
            )
        )

    def test_validate_state_rejects_drift(self):
        values = dict(
            MODULE.EXPECTED_STATE
        )

        values["CDM_STATE"] = (
            "5798|5798|2|5799"
        )

        with self.assertRaises(
            RuntimeError
        ):
            MODULE.validate_state(
                values
            )


if __name__ == "__main__":
    unittest.main()
