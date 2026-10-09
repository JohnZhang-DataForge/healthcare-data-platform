#!/usr/bin/env python3

import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

VALIDATOR = (
    PROJECT_ROOT
    / "apps/task001/"
      "validate_synthea_batch.py"
)

CONTRACT = (
    PROJECT_ROOT
    / "contracts/synthea/"
      "v3.3.0/"
      "csv-contract.json"
)


class ValidatorTests(
    unittest.TestCase
):

    def setUp(self):

        self.tmp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.tmp.name
        )

        self.source = (
            self.root / "csv"
        )

        self.source.mkdir()

        self.output = (
            self.root
            / "manifest.json"
        )

        self.report = (
            self.root
            / "report.json"
        )

        self.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

        for item in self.contract[
            "files"
        ]:

            path = (
                self.source
                / item["filename"]
            )

            with path.open(
                "w",
                encoding="utf-8",
                newline=""
            ) as fh:

                writer = csv.writer(
                    fh
                )

                writer.writerow(
                    item["header"]
                )

                writer.writerow(
                    ["x"]
                    * len(
                        item["header"]
                    )
                )

    def tearDown(self):

        self.tmp.cleanup()

    def run_validator(self):

        return subprocess.run(
            [
                "python3",
                str(VALIDATOR),

                "--source-dir",
                str(self.source),

                "--contract",
                str(CONTRACT),

                "--batch-id",
                "test-batch",

                "--seed",
                "1",

                "--population",
                "1",

                "--state",
                "TestState",

                "--city",
                "TestCity",

                "--output",
                str(self.output),

                "--report",
                str(self.report)
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

    def test_happy_path_and_deterministic_output(
        self
    ):

        first = self.run_validator()

        self.assertEqual(
            first.returncode,
            0,
            first.stdout
        )

        first_bytes = (
            self.output.read_bytes()
        )

        second = self.run_validator()

        self.assertEqual(
            second.returncode,
            0,
            second.stdout
        )

        self.assertEqual(
            first_bytes,
            self.output.read_bytes()
        )

        manifest = json.loads(
            self.output.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            len(
                manifest["files"]
            ),
            18
        )

        self.assertEqual(
            manifest["status"],
            "LOCAL_VALIDATED_NOT_UPLOADED"
        )

    def test_missing_file_fails(
        self
    ):

        (
            self.source
            / "supplies.csv"
        ).unlink()

        result = (
            self.run_validator()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )

        self.assertFalse(
            self.output.exists()
        )

    def test_empty_file_fails(
        self
    ):

        (
            self.source
            / "supplies.csv"
        ).write_bytes(b"")

        result = (
            self.run_validator()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )

        self.assertFalse(
            self.output.exists()
        )

    def test_bad_header_fails(
        self
    ):

        item = next(
            x
            for x in self.contract[
                "files"
            ]
            if x["filename"]
            == "patients.csv"
        )

        path = (
            self.source
            / "patients.csv"
        )

        with path.open(
            "w",
            encoding="utf-8",
            newline=""
        ) as fh:

            writer = csv.writer(
                fh
            )

            bad_header = list(
                item["header"]
            )

            bad_header[0] = (
                "BROKEN_ID"
            )

            writer.writerow(
                bad_header
            )

            writer.writerow(
                ["x"]
                * len(
                    bad_header
                )
            )

        result = (
            self.run_validator()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )

        self.assertFalse(
            self.output.exists()
        )

    def test_malformed_row_fails(
        self
    ):

        item = next(
            x
            for x in self.contract[
                "files"
            ]
            if x["filename"]
            == "conditions.csv"
        )

        path = (
            self.source
            / "conditions.csv"
        )

        with path.open(
            "w",
            encoding="utf-8",
            newline=""
        ) as fh:

            writer = csv.writer(
                fh
            )

            writer.writerow(
                item["header"]
            )

            writer.writerow(
                ["x"]
                * (
                    len(
                        item["header"]
                    )
                    - 1
                )
            )

        result = (
            self.run_validator()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )

        self.assertFalse(
            self.output.exists()
        )

    def test_extra_csv_fails(
        self
    ):

        path = (
            self.source
            / "unexpected.csv"
        )

        with path.open(
            "w",
            encoding="utf-8",
            newline=""
        ) as fh:

            csv.writer(
                fh
            ).writerows(
                [
                    ["A"],
                    ["1"]
                ]
            )

        result = (
            self.run_validator()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )

        self.assertFalse(
            self.output.exists()
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
