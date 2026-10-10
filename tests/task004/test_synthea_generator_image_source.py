import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CONTRACT = (
    ROOT
    / "contracts"
    / "synthea"
    / "v3.3.0"
    / "csv-contract.json"
)

VALIDATOR = (
    ROOT
    / "apps"
    / "task004"
    / "validate_generated_synthea_batch.py"
)

DOCKERFILE = (
    ROOT
    / "images"
    / "synthea"
    / "Dockerfile"
)

ENTRYPOINT = (
    ROOT
    / "images"
    / "synthea"
    / "entrypoint.sh"
)

EXPECTED_COMMIT = (
    "995cf2fd33e67918d4e33110d9f68ad248002221"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class SyntheaGeneratorImageSourceTests(
    unittest.TestCase
):
    def load_contract(self):
        return json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

    def create_complete_csv_batch(
        self,
        directory: Path,
    ):
        contract = self.load_contract()

        for item in contract["files"]:
            path = (
                directory
                / item["filename"]
            )

            with path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.writer(
                    handle,
                    lineterminator="\n",
                )

                writer.writerow(
                    item["header"]
                )

                writer.writerow(
                    [
                        "x"
                        for _ in item["header"]
                    ]
                )

    def run_validator(
        self,
        source: Path,
        draft: Path,
        report: Path,
    ):
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),

                "--source-dir",
                str(source),

                "--contract",
                str(CONTRACT),

                "--batch-id",
                "synthea-test-pop20-seed10001",

                "--synthea-version",
                "v3.3.0",

                "--synthea-commit",
                EXPECTED_COMMIT,

                "--population-size",
                "20",

                "--seed",
                "10001",

                "--clinician-seed",
                "10001",

                "--reference-date",
                "20261010",

                "--state",
                "Georgia",

                "--city",
                "Atlanta",

                "--output",
                str(draft),

                "--report",
                str(report),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    def test_authoritative_contract_has_18_files(
        self,
    ):
        contract = self.load_contract()

        self.assertEqual(
            contract["source"],
            "synthea",
        )

        self.assertEqual(
            contract["source_version"],
            "v3.3.0",
        )

        self.assertEqual(
            contract["expected_file_count"],
            18,
        )

        self.assertEqual(
            len(contract["files"]),
            18,
        )

    def test_validator_accepts_complete_batch(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "csv"
            source.mkdir()

            self.create_complete_csv_batch(
                source
            )

            draft = root / "manifest.draft.json"
            report = root / "validation.json"

            result = self.run_validator(
                source,
                draft,
                report,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stdout,
            )

            manifest = json.loads(
                draft.read_text(
                    encoding="utf-8"
                )
            )

            validation = json.loads(
                report.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                manifest["status"],
                "LOCAL_VALIDATED_NOT_UPLOADED",
            )

            self.assertEqual(
                manifest["expected_file_count"],
                18,
            )

            self.assertEqual(
                len(manifest["files"]),
                18,
            )

            self.assertEqual(
                manifest["source_parameters"],
                {
                    "city": "Atlanta",
                    "clinician_seed": 10001,
                    "population_size": 20,
                    "reference_date": "20261010",
                    "seed": 10001,
                    "state": "Georgia",
                },
            )

            self.assertEqual(
                manifest["source_provenance"],
                {
                    "synthea_commit":
                        EXPECTED_COMMIT,
                    "synthea_version":
                        "v3.3.0",
                },
            )

            self.assertEqual(
                validation["status"],
                "PASS",
            )

            for item in manifest["files"]:
                local = (
                    source
                    / Path(item["path"]).name
                )

                self.assertEqual(
                    item["sha256"],
                    sha256_file(local),
                )

                self.assertEqual(
                    item["row_count"],
                    1,
                )

    def test_validator_rejects_unexpected_csv(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "csv"
            source.mkdir()

            self.create_complete_csv_batch(
                source
            )

            (
                source
                / "unexpected.csv"
            ).write_text(
                "A\nx\n",
                encoding="utf-8",
            )

            draft = root / "manifest.draft.json"
            report = root / "validation.json"

            result = self.run_validator(
                source,
                draft,
                report,
            )

            self.assertNotEqual(
                result.returncode,
                0,
            )

            self.assertFalse(
                draft.exists()
            )

            validation = json.loads(
                report.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                validation["status"],
                "FAIL",
            )

    def test_dockerfile_is_pinned_and_nonroot(
        self,
    ):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        required = [
            "eclipse-temurin:17-jdk-jammy",
            "eclipse-temurin:17-jre-jammy",
            EXPECTED_COMMIT,
            "git fetch --depth=1 origin",
            'test "$(git rev-parse HEAD)" = "${SYNTHEA_COMMIT}"',
            "test -s build/libs/synthea-with-dependencies.jar",
            "USER 10001:10001",
            "contracts/synthea/v3.3.0/csv-contract.json",
            "validate_generated_synthea_batch.py",
            "healthcare-synthea-generator",
        ]

        for value in required:
            self.assertIn(
                value,
                text,
            )

        self.assertNotIn(
            ":latest",
            text,
        )

    def test_entrypoint_pins_deterministic_controls(
        self,
    ):
        text = ENTRYPOINT.read_text(
            encoding="utf-8"
        )

        required = [
            "POPULATION_SIZE",
            "SEED",
            "CLINICIAN_SEED",
            "REFERENCE_DATE",
            "STATE",
            "CITY",
            "--exporter.csv.export=true",
            "--exporter.years_of_history=0",
            "--generate.thread_pool_size=1",
            "--exporter.metadata.export=false",
            "--exporter.fhir.export=false",
            "--exporter.hospital.fhir.export=false",
            "--exporter.practitioner.fhir.export=false",
            "SYNTHEA_GENERATION=PASS",
            "LANDING_PUBLICATION=NOT_STARTED",
        ]

        for value in required:
            self.assertIn(
                value,
                text,
            )


if __name__ == "__main__":
    unittest.main()
