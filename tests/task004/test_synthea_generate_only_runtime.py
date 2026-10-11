"""Static tests for TASK004 canonical Synthea generate-only runtime."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

TEMPLATE = (
    ROOT
    / "kubernetes/manifests/task004/"
      "synthea-generate-only-job.yaml.tpl"
)

RUNNER = (
    ROOT
    / "scripts/task004/"
      "03b-run-synthea-generate-only.sh"
)

GENERATOR = (
    ROOT
    / "scripts/task004/"
      "03a-prepare-synthea-generate-only-runtime.sh"
)

EXPECTED_DIGEST = (
    "sha256:"
    "2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d"
)


class SyntheaGenerateOnlyRuntimeTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text(
            encoding="utf-8"
        )

        cls.runner = RUNNER.read_text(
            encoding="utf-8"
        )

        cls.generator = GENERATOR.read_text(
            encoding="utf-8"
        )

    def test_source_files_exist(self):
        self.assertTrue(
            TEMPLATE.is_file()
        )

        self.assertTrue(
            RUNNER.is_file()
        )

        self.assertTrue(
            GENERATOR.is_file()
        )

    def test_namespace_is_dw_synthea(self):
        self.assertIn(
            "namespace: dw-synthea",
            self.template,
        )

    def test_worker01_is_mandatory(self):
        self.assertIn(
            "kubernetes.io/hostname: worker01",
            self.template,
        )

        self.assertIn(
            'NODE="worker01"',
            self.runner,
        )

    def test_job_is_non_retrying(self):
        self.assertIn(
            "backoffLimit: 0",
            self.template,
        )

        self.assertIn(
            "restartPolicy: Never",
            self.template,
        )

    def test_service_account_token_not_mounted(self):
        self.assertIn(
            "automountServiceAccountToken: false",
            self.template,
        )

    def test_runtime_is_non_root(self):
        for token in (
            "runAsNonRoot: true",
            "runAsUser: 10001",
            "runAsGroup: 10001",
            "allowPrivilegeEscalation: false",
        ):
            self.assertIn(
                token,
                self.template,
            )

    def test_image_is_digest_pinned(self):
        self.assertIn(
            EXPECTED_DIGEST,
            self.runner,
        )

        self.assertIn(
            r'@sha256:[0-9a-f]{64}',
            self.runner,
        )

    def test_supported_profiles_are_20_and_50(self):
        self.assertIn(
            '"20" || "$POPULATION_SIZE" == "50"',
            self.runner,
        )

    def test_clinician_seed_defaults_to_seed(self):
        self.assertIn(
            'CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"',
            self.runner,
        )

    def test_generate_only_invokes_canonical_entrypoint(self):
        self.assertIn(
            "/usr/local/bin/healthcare-synthea-generator",
            self.template,
        )

    def test_exact_18_file_evidence_is_required(self):
        self.assertIn(
            '[[ "$FILE_COUNT" == "18" ]]',
            self.runner,
        )

        self.assertIn(
            '"validated_file_count"',
            self.template,
        )

        self.assertIn(
            '"ERROR: validated_file_count "',
            self.template,
        )

        self.assertIn(
            '"is not 18"',
            self.template,
        )

        self.assertIn(
            '"VALIDATED_FILE_COUNT="',
            self.template,
        )

    def test_patients_match_requested_population(self):
        self.assertIn(
            '[[ "$PATIENT_ROWS" == "$POPULATION_SIZE" ]]',
            self.runner,
        )

    def test_generate_only_does_not_publish_landing(self):
        combined = (
            self.template
            + "\n"
            + self.runner
        )

        self.assertIn(
            "LANDING_PUBLICATION=NOT_STARTED",
            combined,
        )

        forbidden = (
            "aws s3",
            "s3api",
            "mc cp",
            "boto3",
            "psql ",
            "jdbc:postgresql",
        )

        lowered = combined.lower()

        for token in forbidden:
            self.assertNotIn(
                token.lower(),
                lowered,
            )

    def test_runner_supports_render_only(self):
        self.assertIn(
            "--render-only",
            self.runner,
        )

        self.assertIn(
            'if [[ "$RENDER_ONLY" -eq 1 ]]',
            self.runner,
        )

    def test_success_cleanup_is_required(self):
        self.assertIn(
            'kubectl delete job',
            self.runner,
        )

        self.assertIn(
            "KUBERNETES_RESIDUAL_RESOURCE=NO",
            self.runner,
        )

    def test_template_placeholders_are_explicit(self):
        placeholders = set(
            re.findall(
                r"__[A-Z0-9_]+__",
                self.template,
            )
        )

        self.assertEqual(
            placeholders,
            {
                "__JOB_NAME__",
                "__IMAGE_REF_JSON__",
                "__BATCH_ID_JSON__",
                "__POPULATION_SIZE_JSON__",
                "__SEED_JSON__",
                "__CLINICIAN_SEED_JSON__",
                "__REFERENCE_DATE_JSON__",
                "__STATE_JSON__",
                "__CITY_JSON__",
            },
        )


if __name__ == "__main__":
    unittest.main()
