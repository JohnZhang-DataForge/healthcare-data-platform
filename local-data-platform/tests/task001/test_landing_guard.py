#!/usr/bin/env python3

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

GUARD = (
    PROJECT_ROOT
    / "apps/task001/landing_guard.py"
)


class LandingGuardTests(unittest.TestCase):

    def setUp(self):

        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        )

        self.keys = (
            self.root / "keys.txt"
        )

        self.output = (
            self.root / "output.json"
        )


    def tearDown(self):

        self.temp.cleanup()


    def run_resolve(self):

        return subprocess.run(
            [
                "python3",
                str(GUARD),

                "resolve-prefix",

                "--keys",
                str(self.keys),

                "--root-prefix",
                (
                    "source=synthea/"
                    "source_version=v3.3.0/"
                ),

                "--batch-id",
                (
                    "synthea-20261005-"
                    "pop100-atlanta"
                ),

                "--default-ingest-date",
                "2026-10-08",

                "--output",
                str(self.output)
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )


    def test_new_prefix(self):

        self.keys.write_text(
            "",
            encoding="utf-8"
        )

        result = (
            self.run_resolve()
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout
        )

        data = json.loads(
            self.output.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            data["mode"],
            "CREATE_NEW"
        )

        self.assertEqual(
            data["ingest_date"],
            "2026-10-08"
        )


    def test_reuse_existing_prefix(self):

        self.keys.write_text(
            (
                "source=synthea/"
                "source_version=v3.3.0/"
                "ingest_date=2026-10-07/"
                "batch_id=synthea-20261005-"
                "pop100-atlanta/"
                "payload/csv/patients.csv\n"
            ),
            encoding="utf-8"
        )

        result = (
            self.run_resolve()
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout
        )

        data = json.loads(
            self.output.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            data["mode"],
            "REUSE_EXISTING"
        )

        self.assertEqual(
            data["ingest_date"],
            "2026-10-07"
        )


    def test_multiple_prefixes_fail(self):

        self.keys.write_text(
            (
                "source=synthea/"
                "source_version=v3.3.0/"
                "ingest_date=2026-10-07/"
                "batch_id=synthea-20261005-"
                "pop100-atlanta/"
                "payload/csv/patients.csv\n"

                "source=synthea/"
                "source_version=v3.3.0/"
                "ingest_date=2026-10-08/"
                "batch_id=synthea-20261005-"
                "pop100-atlanta/"
                "payload/csv/patients.csv\n"
            ),
            encoding="utf-8"
        )

        result = (
            self.run_resolve()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
