import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RUNNER = (
    ROOT
    / "scripts/task004/"
      "04c-run-synthea-generate-publish.sh"
)

GENERATOR = (
    ROOT
    / "scripts/task004/"
      "04a-prepare-synthea-landing-publisher.sh"
)


class Task004AirflowStep03ERuntimeReportTests(
    unittest.TestCase
):

    def test_incluster_report_path_is_project_owned(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        block_start = source.index(
            'if [[ "${TASK004_RUNTIME_CONTEXT:-}" '
            '== "in-cluster" ]]; then'
        )

        block_end = source.index(
            'mkdir -p "$REPORT_DIR"',
            block_start,
        )

        block = source[
            block_start:block_end
        ]

        self.assertIn(
            'REPORT_DIR="${ROOT}/runtime/reports/task004/landing"',
            block,
        )

        self.assertIn(
            "command -v git",
            block,
        )


    def test_generator_contains_same_incluster_rule(self):
        source = GENERATOR.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'REPORT_DIR="${ROOT}/runtime/reports/task004/landing"',
            source,
        )

        self.assertIn(
            "command -v git >/dev/null 2>&1",
            source,
        )


if __name__ == "__main__":
    unittest.main()
