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

BUILDER = (
    PROJECT_ROOT
    / "apps/task001/"
      "build_intake_manifest.py"
)


class BuildManifestTests(
    unittest.TestCase
):

    def setUp(self):

        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        )

        self.draft = (
            self.root
            / "draft.json"
        )

        self.output = (
            self.root
            / "manifest.json"
        )

        files = []

        for i in range(18):

            files.append({
                "path":
                    f"payload/csv/file{i}.csv",

                "dataset":
                    f"file{i}",

                "size_bytes":
                    10,

                "sha256":
                    f"{i:064x}",

                "row_count":
                    1,

                "header":
                    ["A"]
            })

        draft = {
            "manifest_version":
                "1.0",

            "status":
                "LOCAL_VALIDATED_NOT_UPLOADED",

            "source":
                "synthea",

            "source_version":
                "v3.3.0",

            "batch_id":
                "test-batch",

            "payload_format":
                "csv",

            "expected_file_count":
                18,

            "source_parameters": {
                "seed": 1,
                "population": 1,
                "state": "Test",
                "city": "Test"
            },

            "files":
                files
        }

        self.draft.write_text(
            json.dumps(draft),
            encoding="utf-8"
        )


    def tearDown(self):

        self.temp.cleanup()


    def run_builder(
        self,
        verified_at="2026-10-08T18:00:00Z"
    ):

        return subprocess.run(
            [
                "python3",
                str(BUILDER),

                "--draft",
                str(self.draft),

                "--ingest-date",
                "2026-10-08",

                "--landing-uri",
                "s3://bucket/batch/",

                "--verified-at",
                verified_at,

                "--output",
                str(self.output)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )


    def test_build_final_manifest(
        self
    ):

        result = (
            self.run_builder()
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
            data["status"],
            "INTAKE_VERIFIED"
        )

        self.assertEqual(
            len(data["files"]),
            18
        )

        self.assertEqual(
            data["verification"][
                "verified_file_count"
            ],
            18
        )

        self.assertEqual(
            data["verification"][
                "s3_readback"
            ],
            "PASS"
        )


    def test_deterministic_given_timestamp(
        self
    ):

        first = (
            self.run_builder()
        )

        self.assertEqual(
            first.returncode,
            0
        )

        first_bytes = (
            self.output.read_bytes()
        )

        second = (
            self.run_builder()
        )

        self.assertEqual(
            second.returncode,
            0
        )

        self.assertEqual(
            first_bytes,
            self.output.read_bytes()
        )


    def test_wrong_draft_status_fails(
        self
    ):

        data = json.loads(
            self.draft.read_text(
                encoding="utf-8"
            )
        )

        data["status"] = "BROKEN"

        self.draft.write_text(
            json.dumps(data),
            encoding="utf-8"
        )

        result = (
            self.run_builder()
        )

        self.assertNotEqual(
            result.returncode,
            0
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
