import unittest
from pathlib import Path


ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

BRIDGE = (
    ROOT
    / "scripts/task004/"
    "05c-resolve-runtime-lineage.sh"
)

PERSON = (
    ROOT
    / "scripts/task004/"
    "05d-run-person-canonical.sh"
)

VISIT = (
    ROOT
    / "scripts/task004/"
    "05e-run-visit-canonical.sh"
)


def read(path):
    return path.read_text(
        encoding="utf-8"
    )


class PersonVisitRuntimeInterfaceTests(
    unittest.TestCase
):

    def test_bridge_requires_dataset(self):
        source = read(
            BRIDGE
        )

        self.assertIn(
            'DATASET="${1:-}"',
            source,
        )


    def test_bridge_uses_generic_resolver(self):
        source = read(
            BRIDGE
        )

        self.assertIn(
            "resolve_verified_landing_file.py",
            source,
        )

        self.assertIn(
            "--manifest-sha256",
            source,
        )


    def test_bridge_uses_dw_spark_secret(self):
        self.assertIn(
            "dw-spark-s3-secret",
            read(
                BRIDGE
            ),
        )


    def test_bridge_has_no_task001_dependency(self):
        source = read(
            BRIDGE
        ).lower()

        self.assertNotIn(
            "task001",
            source,
        )

        self.assertNotIn(
            "task-001",
            source,
        )


    def test_bridge_direct_mode_exists(self):
        source = read(
            BRIDGE
        )

        self.assertIn(
            'TASK004_RUNTIME_CONTEXT="${TASK004_RUNTIME_CONTEXT:-manual}"',
            source,
        )

        self.assertIn(
            "in-cluster)",
            source,
        )

        self.assertIn(
            'exec python3 \\\n      "$RESOLVER"',
            source,
        )


    def test_bridge_manual_mode_preserved(self):
        source = read(
            BRIDGE
        )

        self.assertIn(
            "manual)",
            source,
        )

        self.assertIn(
            "kubectl exec",
            source,
        )

        self.assertIn(
            "dw-airflow-scheduler-",
            source,
        )


    def test_person_requires_lineage(self):
        source = read(
            PERSON
        )

        for value in (
            "BATCH_ID",
            "MANIFEST_URI",
            "MANIFEST_SHA256",
        ):
            self.assertIn(
                value + " is required",
                source,
            )


    def test_visit_requires_lineage(self):
        source = read(
            VISIT
        )

        for value in (
            "BATCH_ID",
            "MANIFEST_URI",
            "MANIFEST_SHA256",
        ):
            self.assertIn(
                value + " is required",
                source,
            )


    def test_person_resolves_patients(self):
        self.assertIn(
            '"$BRIDGE" patients',
            read(
                PERSON
            ),
        )


    def test_visit_resolves_encounters(self):
        self.assertIn(
            '"$BRIDGE" encounters',
            read(
                VISIT
            ),
        )


    def test_person_reuses_frozen_adapter_template(self):
        source = read(
            PERSON
        )

        self.assertIn(
            "spark/apps/person/"
            "synthea_patient_adapter.py",
            source,
        )

        self.assertIn(
            "spark/manifests/task002/"
            "person-canonical-adapter.yaml.tpl",
            source,
        )


    def test_visit_reuses_frozen_adapter_template(self):
        source = read(
            VISIT
        )

        self.assertIn(
            "spark/apps/visit/"
            "synthea_encounter_adapter.py",
            source,
        )

        self.assertIn(
            "spark/manifests/task003/"
            "encounter-canonical-adapter.yaml.tpl",
            source,
        )


    def test_person_has_no_legacy_113_gate(self):
        source = read(
            PERSON
        )

        self.assertNotIn(
            'Expected canonical rows=113',
            source,
        )

        self.assertNotIn(
            '!= "113"',
            source,
        )


    def test_person_dynamic_row_acceptance(self):
        source = read(
            PERSON
        )

        self.assertIn(
            '"CANONICAL_ROWS=${EXPECTED_ROWS}"',
            source,
        )

        self.assertIn(
            '"PROCESSING_READBACK_ROWS=${EXPECTED_ROWS}"',
            source,
        )


    def test_visit_dynamic_row_acceptance(self):
        source = read(
            VISIT
        )

        self.assertIn(
            '"SOURCE_ROWS=${EXPECTED_ROWS}"',
            source,
        )

        self.assertIn(
            '"CANONICAL_ROWS=${EXPECTED_ROWS}"',
            source,
        )


    def test_person_supports_render_only(self):
        source = read(
            PERSON
        )

        self.assertIn(
            "--render-only",
            source,
        )

        self.assertIn(
            "TASK004_PERSON_INTERFACE_RENDER=PASS",
            source,
        )


    def test_visit_supports_render_only(self):
        source = read(
            VISIT
        )

        self.assertIn(
            "--render-only",
            source,
        )

        self.assertIn(
            "TASK004_VISIT_INTERFACE_RENDER=PASS",
            source,
        )


    def test_success_cleanup_policy(self):
        for path in (
            PERSON,
            VISIT,
        ):
            source = read(
                path
            )

            self.assertIn(
                "kubectl delete sparkapplication",
                source,
            )

            self.assertIn(
                "kubectl delete configmap",
                source,
            )

            self.assertIn(
                "FAILED_SPARKAPPLICATION_RETAINED=YES",
                source,
            )


if __name__ == "__main__":
    unittest.main()
