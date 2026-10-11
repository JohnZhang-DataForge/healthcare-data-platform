from __future__ import annotations

import copy
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

APP = (
    ROOT
    / "apps/task004/publish_synthea_landing.py"
)

TEMPLATE = (
    ROOT
    / "kubernetes/manifests/task004/"
      "synthea-generate-publish-job.yaml.tpl"
)

SECRET_SYNC = (
    ROOT
    / "scripts/task004/"
      "04b-sync-s3-secret-to-synthea.sh"
)

RUNNER = (
    ROOT
    / "scripts/task004/"
      "04c-run-synthea-generate-publish.sh"
)


spec = importlib.util.spec_from_file_location(
    "task004_landing_publisher",
    APP,
)

module = importlib.util.module_from_spec(
    spec
)

assert spec.loader is not None

sys.modules[
    spec.name
] = module

spec.loader.exec_module(
    module
)


def sample_draft():
    files = []

    for index in range(18):

        filename = (
            "patients.csv"
            if index == 0
            else f"file{index:02d}.csv"
        )

        dataset = (
            "patients"
            if index == 0
            else f"dataset{index:02d}"
        )

        files.append(
            {
                "dataset":
                    dataset,
                "header":
                    ["A"],
                "path":
                    "payload/csv/"
                    + filename,
                "row_count":
                    20
                    if index == 0
                    else 1,
                "sha256":
                    f"{index + 1:064x}",
                "size_bytes":
                    index + 10,
            }
        )

    return {
        "batch_id":
            "batch-001",
        "contract": {
            "path":
                "contracts/synthea/v3.3.0/"
                "csv-contract.json",
            "sha256":
                "a" * 64,
        },
        "expected_file_count":
            18,
        "files":
            files,
        "manifest_version":
            "1.0",
        "payload_format":
            "csv",
        "source":
            "synthea",
        "source_parameters": {
            "city":
                None,
            "clinician_seed":
                1,
            "population_size":
                20,
            "reference_date":
                "20261010",
            "seed":
                1,
            "state":
                "Georgia",
        },
        "source_provenance": {
            "synthea_commit":
                "x",
            "synthea_version":
                "v3.3.0",
        },
        "source_version":
            "v3.3.0",
        "status":
            "LOCAL_VALIDATED_NOT_UPLOADED",
    }


class LandingPublisherTests(
    unittest.TestCase
):

    def test_resolve_new_prefix(self):
        prefix, date, mode = (
            module.resolve_batch_prefix(
                [],
                "source=synthea/"
                "source_version=v3.3.0/",
                "batch-001",
                "2026-10-10",
            )
        )

        self.assertEqual(
            date,
            "2026-10-10",
        )

        self.assertEqual(
            mode,
            "CREATE_NEW_PREFIX",
        )

        self.assertTrue(
            prefix.endswith(
                "ingest_date=2026-10-10/"
                "batch_id=batch-001/"
            )
        )

    def test_resolve_existing_prefix(self):
        root = (
            "source=synthea/"
            "source_version=v3.3.0/"
        )

        key = (
            root
            + "ingest_date=2026-10-08/"
            + "batch_id=batch-001/"
            + "manifest.json"
        )

        prefix, date, mode = (
            module.resolve_batch_prefix(
                [key],
                root,
                "batch-001",
                "2026-10-10",
            )
        )

        self.assertEqual(
            date,
            "2026-10-08",
        )

        self.assertEqual(
            mode,
            "REUSE_EXISTING_PREFIX",
        )

        self.assertIn(
            "batch_id=batch-001/",
            prefix,
        )

    def test_multiple_prefixes_rejected(self):
        root = (
            "source=synthea/"
            "source_version=v3.3.0/"
        )

        keys = [
            root
            + "ingest_date=2026-10-08/"
            + "batch_id=batch-001/"
            + "manifest.json",

            root
            + "ingest_date=2026-10-09/"
            + "batch_id=batch-001/"
            + "manifest.json",
        ]

        with self.assertRaises(
            module.PublishError
        ):
            module.resolve_batch_prefix(
                keys,
                root,
                "batch-001",
                "2026-10-10",
            )

    def test_unknown_remote_object_rejected(self):
        draft = sample_draft()

        prefix = (
            "source=synthea/"
            "source_version=v3.3.0/"
            "ingest_date=2026-10-10/"
            "batch_id=batch-001/"
        )

        with self.assertRaises(
            module.PublishError
        ):
            module.inspect_batch_keys(
                draft,
                prefix,
                [
                    prefix
                    + "unexpected.bin"
                ],
            )

    def test_final_manifest_preserves_provenance(self):
        draft = sample_draft()

        final = (
            module.build_final_manifest(
                draft,
                "2026-10-10",
                "s3://health-landing/x/",
                "2026-10-10T12:00:00Z",
                "f" * 64,
            )
        )

        self.assertEqual(
            final["source_provenance"],
            draft["source_provenance"],
        )

        self.assertEqual(
            final["contract"],
            draft["contract"],
        )

        self.assertEqual(
            final["status"],
            "INTAKE_VERIFIED",
        )

    def test_final_manifest_file_conflict_rejected(self):
        draft = sample_draft()

        final = (
            module.build_final_manifest(
                draft,
                "2026-10-10",
                "s3://health-landing/x/",
                "2026-10-10T12:00:00Z",
                "f" * 64,
            )
        )

        final = copy.deepcopy(
            final
        )

        final["files"][0][
            "sha256"
        ] = "0" * 64

        with self.assertRaises(
            module.PublishError
        ):
            module.validate_final_manifest(
                draft,
                final,
                "2026-10-10",
                "s3://health-landing/x/",
                "f" * 64,
            )

    def test_manifest_last_source_semantics(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        readback = source.index(
            "# Mandatory independent readback "
            "of all 18 payload objects."
        )

        manifest_last = source.index(
            "# Manifest is deliberately "
            "the LAST object created."
        )

        self.assertLess(
            readback,
            manifest_last,
        )

    def test_no_boto3_or_database_dependency(self):
        source = APP.read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn(
            "boto3",
            source,
        )

        self.assertNotIn(
            "psycopg",
            source,
        )

        self.assertNotIn(
            "jdbc:postgresql",
            source,
        )

    def test_template_targets_dw_synthea(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "namespace: dw-synthea",
            source,
        )

        self.assertIn(
            "kubernetes.io/hostname: worker01",
            source,
        )

    def test_template_uses_namespace_local_secret(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "name: dw-synthea-s3-secret",
            source,
        )

    def test_same_container_generates_then_publishes(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        generate = source.index(
            "/usr/local/bin/"
            "healthcare-synthea-generator"
        )

        publish = source.index(
            "publish_synthea_landing.py"
        )

        self.assertLess(
            generate,
            publish,
        )

    def test_template_has_no_postgresql(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn(
            "postgres",
            source,
        )

    def test_secret_sync_is_cross_namespace_copy(self):
        source = SECRET_SYNC.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'SOURCE_NAMESPACE="dw-spark"',
            source,
        )

        self.assertIn(
            'TARGET_NAMESPACE="dw-synthea"',
            source,
        )

        self.assertIn(
            'TARGET_SECRET="dw-synthea-s3-secret"',
            source,
        )

        self.assertIn(
            "SECRET_VALUES_DISPLAYED=NO",
            source,
        )

    def test_runner_does_not_depend_on_task001_runtime(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "runtime/reports/task001",
            source,
        )

        self.assertNotIn(
            "task001-final-validation",
            source,
        )

    def test_runner_is_digest_pinned(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "@sha256:"
            "2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d",
            source,
        )

    def test_runner_supports_render_only(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "--render-only",
            source,
        )

    def test_runner_render_only_executes_with_default_ingest_date(self):
        env = os.environ.copy()

        env.update(
            {
                "BATCH_ID":
                    "task004-unit-render",

                "POPULATION_SIZE":
                    "20",

                "SEED":
                    "20261010",

                "CLINICIAN_SEED":
                    "20261010",

                "REFERENCE_DATE":
                    "20261010",

                "STATE":
                    "Georgia",

                "CITY":
                    "",
            }
        )

        env.pop(
            "LANDING_INGEST_DATE",
            None,
        )

        result = subprocess.run(
            [
                str(RUNNER),
                "--render-only",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "render-only runner failed:\n"
                + result.stderr
            ),
        )

        self.assertIn(
            "namespace: dw-synthea",
            result.stdout,
        )

        self.assertIn(
            'name: LANDING_INGEST_DATE',
            result.stdout,
        )

        self.assertNotIn(
            "bad substitution",
            result.stderr.lower(),
        )


if __name__ == "__main__":
    unittest.main()
