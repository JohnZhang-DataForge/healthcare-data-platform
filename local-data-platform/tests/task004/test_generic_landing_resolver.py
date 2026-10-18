import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

APP = (
    ROOT
    / "apps/task004/"
    "resolve_verified_landing_file.py"
)

SPEC = importlib.util.spec_from_file_location(
    "task004_generic_resolver",
    APP,
)

module = importlib.util.module_from_spec(
    SPEC
)

assert SPEC.loader is not None

SPEC.loader.exec_module(
    module
)


DATASETS = [
    "allergies",
    "careplans",
    "claims",
    "claims_transactions",
    "conditions",
    "devices",
    "encounters",
    "imaging_studies",
    "immunizations",
    "medications",
    "observations",
    "organizations",
    "patients",
    "payer_transitions",
    "payers",
    "procedures",
    "providers",
    "supplies",
]


def sample_manifest():
    files = []

    for index, dataset in enumerate(
        DATASETS,
        start=1,
    ):
        filename = (
            dataset
            + ".csv"
        )

        file_sha = hashlib.sha256(
            filename.encode(
                "utf-8"
            )
        ).hexdigest()

        files.append(
            {
                "path":
                    "payload/csv/"
                    + filename,

                "dataset":
                    dataset,

                "size_bytes":
                    1000
                    + index,

                "sha256":
                    file_sha,

                "row_count":
                    index,

                "header":
                    [
                        "COL_A",
                        "COL_B",
                    ],
            }
        )

    fingerprint = (
        module.payload_fingerprint(
            [
                module.normalize_file(
                    item
                )
                for item in files
            ]
        )
    )

    return {
        "manifest_version":
            "1.0",

        "status":
            "INTAKE_VERIFIED",

        "source":
            "synthea",

        "source_version":
            "v3.3.0",

        "batch_id":
            "batch-001",

        "ingest_date":
            "2026-10-11",

        "landing_uri":
            (
                "s3://health-landing/"
                "source=synthea/"
                "source_version=v3.3.0/"
                "ingest_date=2026-10-11/"
                "batch_id=batch-001/"
            ),

        "expected_file_count":
            18,

        "payload_fingerprint":
            fingerprint,

        "verification": {
            "verified_file_count":
                18,

            "s3_readback":
                "PASS",
        },

        "files":
            files,
    }


def manifest_uri():
    return (
        "s3://health-landing/"
        "source=synthea/"
        "source_version=v3.3.0/"
        "ingest_date=2026-10-11/"
        "batch_id=batch-001/"
        "manifest.json"
    )


class GenericLandingResolverTests(
    unittest.TestCase
):

    def test_parse_manifest_uri(self):
        bucket, key = (
            module.parse_manifest_uri(
                manifest_uri()
            )
        )

        self.assertEqual(
            bucket,
            "health-landing",
        )

        self.assertTrue(
            key.endswith(
                "/manifest.json"
            )
        )


    def test_rejects_non_s3_manifest_uri(self):
        with self.assertRaises(
            module.ResolverError
        ):
            module.parse_manifest_uri(
                "https://example/manifest.json"
            )


    def test_valid_manifest_passes(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        self.assertEqual(
            len(files),
            18,
        )


    def test_rejects_non_verified_manifest(self):
        manifest = sample_manifest()

        manifest[
            "status"
        ] = "LOCAL_VALIDATED_NOT_UPLOADED"

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_batch_mismatch(self):
        manifest = sample_manifest()

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "wrong-batch",
                manifest_uri(),
            )


    def test_rejects_landing_uri_mismatch(self):
        manifest = sample_manifest()

        manifest[
            "landing_uri"
        ] = (
            "s3://health-landing/wrong/"
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_wrong_file_count(self):
        manifest = sample_manifest()

        manifest[
            "files"
        ] = manifest[
            "files"
        ][:-1]

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_duplicate_dataset(self):
        manifest = sample_manifest()

        manifest[
            "files"
        ][1][
            "dataset"
        ] = manifest[
            "files"
        ][0][
            "dataset"
        ]

        manifest[
            "payload_fingerprint"
        ] = module.payload_fingerprint(
            [
                module.normalize_file(
                    item
                )
                for item in manifest[
                    "files"
                ]
            ]
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_resolves_patients_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "patients",
                manifest_uri(),
                "a" * 64,
            )
        )

        self.assertEqual(
            result[
                "dataset"
            ],
            "patients",
        )

        self.assertTrue(
            result[
                "source_uri"
            ].endswith(
                "/payload/csv/patients.csv"
            )
        )


    def test_resolves_encounters_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "encounters",
                manifest_uri(),
                "b" * 64,
            )
        )

        self.assertEqual(
            result[
                "dataset"
            ],
            "encounters",
        )

        self.assertGreater(
            result[
                "row_count"
            ],
            0,
        )


    def test_rejects_missing_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.resolve_dataset(
                manifest,
                files,
                "not_real",
                manifest_uri(),
                "c" * 64,
            )


    def test_resolve_from_bytes_checks_manifest_sha(self):
        manifest = sample_manifest()

        payload = json.dumps(
            manifest,
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.resolve_from_bytes(
                payload,
                "patients",
                "batch-001",
                manifest_uri(),
                "0" * 64,
            )


    def test_resolve_from_bytes_success(self):
        manifest = sample_manifest()

        payload = json.dumps(
            manifest,
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        manifest_sha = hashlib.sha256(
            payload
        ).hexdigest()

        result = (
            module.resolve_from_bytes(
                payload,
                "patients",
                "batch-001",
                manifest_uri(),
                manifest_sha,
            )
        )

        self.assertEqual(
            result[
                "manifest_sha256"
            ],
            manifest_sha,
        )

        self.assertEqual(
            result[
                "batch_id"
            ],
            "batch-001",
        )


    def test_rejects_payload_fingerprint_mismatch(self):
        manifest = sample_manifest()

        manifest[
            "payload_fingerprint"
        ] = "f" * 64

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_shell_output_has_runtime_contract(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "encounters",
                manifest_uri(),
                "a" * 64,
            )
        )

        output = "\n".join(
            module.shell_lines(
                result
            )
        )

        for name in (
            "MANIFEST_STATUS=",
            "MANIFEST_URI=",
            "MANIFEST_SHA256=",
            "BATCH_ID=",
            "LANDING_URI=",
            "SOURCE_DATASET=",
            "SOURCE_FILE=",
            "SOURCE_URI=",
            "EXPECTED_ROWS=",
            "SOURCE_FILE_SIZE_BYTES=",
            "SOURCE_FILE_SHA256=",
        ):
            self.assertIn(
                name,
                output,
            )


    def test_no_task001_runtime_dependency(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "runtime/reports/task001",
            source,
        )

        self.assertNotIn(
            "TASK-001 final report",
            source,
        )


    def test_resolver_is_remote_read_only(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'method="GET"',
            source,
        )

        self.assertNotIn(
            'method="PUT"',
            source,
        )

        self.assertNotIn(
            'method="DELETE"',
            source,
        )

        self.assertNotIn(
            "psycopg",
            source.lower(),
        )

        self.assertNotIn(
            "postgres",
            source.lower(),
        )


if __name__ == "__main__":
    unittest.main()
