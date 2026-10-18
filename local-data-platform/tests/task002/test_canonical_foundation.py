import importlib.util
import json
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

HELPER_PATH = (
    PROJECT_ROOT
    / "spark/common/batch_manifest.py"
)

CONTRACT_PATH = (
    PROJECT_ROOT
    / "spark/contracts/canonical/patient-v1.json"
)


spec = importlib.util.spec_from_file_location(
    "batch_manifest",
    HELPER_PATH,
)

helper = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(helper)


def make_manifest():
    files = []

    files.append({
        "path": "payload/csv/patients.csv",
        "dataset": "patients",
        "size_bytes": 32785,
        "sha256": "abc123",
        "row_count": 113,
        "header": [
            "Id",
            "BIRTHDATE",
            "DEATHDATE"
        ]
    })

    for index in range(17):
        files.append({
            "path":
                f"payload/csv/file{index}.csv",

            "dataset":
                f"file{index}",

            "size_bytes":
                1,

            "sha256":
                f"sha{index}",

            "row_count":
                1,

            "header":
                ["x"]
        })

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
            "synthea-test",

        "ingest_date":
            "2026-10-08",

        "landing_uri":
            (
                "s3://health-landing/"
                "source=synthea/"
                "batch_id=synthea-test/"
            ),

        "expected_file_count":
            18,

        "verification": {
            "verified_file_count":
                18,

            "s3_readback":
                "PASS"
        },

        "files":
            files
    }


class ManifestTests(unittest.TestCase):

    def test_verified_manifest_passes(self):
        manifest = make_manifest()

        result = (
            helper
            .validate_intake_manifest(
                manifest,
                expected_batch_id="synthea-test",
            )
        )

        self.assertEqual(
            result["status"],
            "INTAKE_VERIFIED",
        )


    def test_wrong_status_fails(self):
        manifest = make_manifest()

        manifest["status"] = "INVALID"

        with self.assertRaises(
            RuntimeError
        ):
            helper.validate_intake_manifest(
                manifest
            )


    def test_wrong_batch_fails(self):
        manifest = make_manifest()

        with self.assertRaises(
            RuntimeError
        ):
            helper.validate_intake_manifest(
                manifest,
                expected_batch_id="other",
            )


    def test_patient_file_lookup(self):
        manifest = make_manifest()

        patient = (
            helper.find_dataset_file(
                manifest,
                "patients",
                "patients.csv",
            )
        )

        self.assertEqual(
            patient["row_count"],
            113,
        )

        self.assertEqual(
            patient["size_bytes"],
            32785,
        )


    def test_s3_conversion(self):
        self.assertEqual(
            helper.s3_to_s3a(
                "s3://bucket/path"
            ),
            "s3a://bucket/path",
        )


class ContractTests(unittest.TestCase):

    def test_patient_contract(self):
        contract = json.loads(
            CONTRACT_PATH.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            contract["contract_name"],
            "canonical.patient",
        )

        self.assertEqual(
            contract["canonical_version"],
            "v1",
        )

        self.assertEqual(
            contract["entity"],
            "patient",
        )

        fields = contract["fields"]

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

        required = {
            "source_record_id",
            "birth_date",
            "gender_code",
            "race_code",
            "ethnicity_code",
            "source_system",
            "source_batch_id",
            "processing_run_id",
        }

        self.assertTrue(
            required.issubset(
                set(names)
            )
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
