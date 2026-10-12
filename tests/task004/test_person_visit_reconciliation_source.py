import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

APP = (
    ROOT
    / "spark/apps/task004/reconcile_person_visit.py"
)

RUNNER = (
    ROOT
    / "scripts/task004/05f-reconcile-person-visit.sh"
)

TEMPLATE = (
    ROOT
    / "spark/manifests/task004/"
    "person-visit-reconciliation.yaml.tpl"
)


def read(path):
    return path.read_text(
        encoding="utf-8"
    )


class PersonVisitReconciliationSourceTests(
    unittest.TestCase
):

    def test_python_parses(self):
        ast.parse(
            read(APP)
        )


    def test_test_root_is_repo_relative(self):
        source = read(
            Path(__file__)
        )

        self.assertIn(
            "Path(__file__).resolve().parents[2]",
            source,
        )


    def test_python_has_nonblank_lineage_gate(self):
        source = read(APP)

        self.assertIn(
            "def one_nonblank_value",
            source,
        )

        for value in (
            '"source_system"',
            '"source_version"',
            '"source_batch_id"',
            '"source_ingest_date"',
        ):
            self.assertIn(
                value,
                source,
            )

        self.assertIn(
            "must not be null",
            source,
        )

        self.assertIn(
            "must not be blank",
            source,
        )


    def test_python_checks_both_batch_ids(self):
        source = read(APP)

        self.assertIn(
            "Patient batch_id mismatch",
            source,
        )

        self.assertIn(
            "Encounter batch_id mismatch",
            source,
        )


    def test_orphan_metric_counts_encounter_rows(self):
        source = read(APP)

        self.assertIn(
            '"source_encounter_id"',
            source,
        )

        self.assertIn(
            '"left_anti"',
            source,
        )

        self.assertIn(
            "orphan_encounters",
            source,
        )

        self.assertNotIn(
            'encounter.select("source_person_id").distinct().join',
            source,
        )


    def test_wrapper_is_read_only_reconciliation(self):
        shell = read(RUNNER)
        app = read(APP)

        self.assertIn(
            "PROCESSING_MUTATION=NO",
            shell,
        )

        self.assertIn(
            "POSTGRESQL_MUTATION=NO",
            shell,
        )

        self.assertNotIn(
            "psql ",
            shell,
        )

        self.assertNotIn(
            ".write.",
            app,
        )


    def test_wrapper_has_source_guard(self):
        source = read(RUNNER)

        self.assertIn(
            'BASH_SOURCE[0]',
            source,
        )

        self.assertIn(
            "execute with bash; do not source",
            source,
        )


    def test_wrapper_validates_processing_uri_lineage(self):
        source = read(RUNNER)

        for value in (
            "INPUT_URI_PREFLIGHT=PASS",
            'parsed.scheme == "s3a"',
            'parsed.netloc == "health-processing"',
            '"batch_id"',
            '"entity"',
            '"run_id"',
            'f"Processing URI {key} mismatch"',
        ):
            self.assertIn(
                value,
                source,
            )


    def test_wrapper_supports_render_only(self):
        source = read(RUNNER)

        self.assertIn(
            "--render-only",
            source,
        )

        self.assertIn(
            "TASK004_RECONCILIATION_INTERFACE_RENDER=PASS",
            source,
        )

        self.assertIn(
            "SPARKAPPLICATION_APPLY=NO",
            source,
        )


    def test_wrapper_retains_failed_resources(self):
        source = read(RUNNER)

        for value in (
            "FAILED_SPARKAPPLICATION_RETAINED=YES",
            "FAILED_CONFIGMAP_RETAINED=YES",
            "FAILED_DRIVER_POD_RETAINED=YES",
            "report_failure_resources",
            "trap on_exit EXIT",
        ):
            self.assertIn(
                value,
                source,
            )


    def test_wrapper_writes_structured_state(self):
        source = read(RUNNER)

        self.assertIn(
            'STATE_FILE="${RUN_DIR}/run-state.json"',
            source,
        )

        for value in (
            '"stage": "batch-reconciliation"',
            '"orphan_encounters": 0',
            '"processing_mutation": False',
            '"postgresql_mutation": False',
        ):
            self.assertIn(
                value,
                source,
            )


    def test_wrapper_verifies_success_cleanup(self):
        source = read(RUNNER)

        self.assertGreaterEqual(
            source.count(
                'kubectl get sparkapplication "$APP_NAME"'
            ),
            2,
        )

        self.assertGreaterEqual(
            source.count(
                'kubectl get configmap "$CM_NAME"'
            ),
            2,
        )

        self.assertIn(
            'kubectl get pod "$DRIVER_POD"',
            source,
        )

        self.assertIn(
            "SUCCESSFUL_DRIVER_POD_RESIDUAL=NO",
            source,
        )


    def test_wrapper_requires_strong_runtime_markers(self):
        source = read(RUNNER)

        for value in (
            "PATIENT_UNIQUE_IDS=$EXPECTED_PATIENT_ROWS",
            "ENCOUNTER_UNIQUE_IDS=$EXPECTED_ENCOUNTER_ROWS",
            "ORPHAN_ENCOUNTERS=0",
            "SOURCE_BATCH_ID=$BATCH_ID",
            "BATCH_RECONCILIATION=PASS",
        ):
            self.assertIn(
                value,
                source,
            )


    def test_template_is_task004_and_read_only(self):
        source = read(TEMPLATE)

        self.assertIn(
            "healthcare-task: task004",
            source,
        )

        self.assertIn(
            "person-visit-reconciliation",
            source,
        )

        self.assertIn(
            "reconcile_person_visit.py",
            source,
        )

        self.assertIn(
            "dw-spark-s3-secret",
            source,
        )


if __name__ == "__main__":
    unittest.main()
