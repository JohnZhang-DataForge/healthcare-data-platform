"""Unit checks that do not require PySpark on runner01."""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spark/apps/visit"))

from validate_visit_candidate_preflight import verify_projection


class F2PreflightTests(unittest.TestCase):

    def test_projection_exact(self):
        fields = [
            {"name": "x", "type": "integer"},
            {"name": "y", "type": "date"},
        ]
        verify_projection([("x", "int"), ("y", "date")], fields)

    def test_projection_wrong_order(self):
        fields = [
            {"name": "x", "type": "integer"},
            {"name": "y", "type": "date"},
        ]
        with self.assertRaises(ValueError):
            verify_projection(
                [("y", "date"), ("x", "int")], fields
            )

    def test_projection_no_premature_id(self):
        fields = [
            {"name": "visit_occurrence_id", "type": "integer"}
        ]
        with self.assertRaises(ValueError):
            verify_projection(
                [("visit_occurrence_id", "int")], fields
            )

    def test_no_write_invocations(self):
        path = (
            ROOT
            / "spark/apps/visit/validate_visit_candidate_preflight.py"
        )
        tree = ast.parse(path.read_text())

        calls = [
            n.func.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
        ]

        for forbidden in (
            "save", "saveAsTable", "insertInto",
            "jdbc", "write", "collectToPython",
        ):
            self.assertNotIn(forbidden, calls)


if __name__ == "__main__":
    unittest.main()
