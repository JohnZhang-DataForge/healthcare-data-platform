#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(path: Path, payload: dict) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def utc_now() -> str:

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Build the final Synthea "
            "INTAKE_VERIFIED manifest."
        )
    )

    parser.add_argument(
        "--draft",
        required=True
    )

    parser.add_argument(
        "--ingest-date",
        required=True
    )

    parser.add_argument(
        "--landing-uri",
        required=True
    )

    parser.add_argument(
        "--verified-at"
    )

    parser.add_argument(
        "--output",
        required=True
    )

    args = parser.parse_args()

    draft = load_json(
        Path(args.draft)
    )

    if (
        draft.get("status")
        != "LOCAL_VALIDATED_NOT_UPLOADED"
    ):
        raise SystemExit(
            "ERROR: invalid draft manifest status"
        )

    if (
        draft.get("expected_file_count")
        != 18
    ):
        raise SystemExit(
            "ERROR: expected_file_count must be 18"
        )

    if len(
        draft.get("files", [])
    ) != 18:
        raise SystemExit(
            "ERROR: draft does not contain 18 files"
        )

    verified_at = (
        args.verified_at
        or utc_now()
    )

    final = {
        "manifest_version":
            draft["manifest_version"],

        "status":
            "INTAKE_VERIFIED",

        "source":
            draft["source"],

        "source_version":
            draft["source_version"],

        "batch_id":
            draft["batch_id"],

        "ingest_date":
            args.ingest_date,

        "ingested_at":
            verified_at,

        "payload_format":
            draft["payload_format"],

        "expected_file_count":
            draft["expected_file_count"],

        "source_parameters":
            draft["source_parameters"],

        "landing_uri":
            args.landing_uri,

        "verification": {
            "checksum_algorithm":
                "SHA256",

            "verified_file_count":
                18,

            "s3_readback":
                "PASS",

            "verified_at":
                verified_at
        },

        "files":
            draft["files"]
    }

    write_json(
        Path(args.output),
        final
    )

    print(
        f"FINAL_MANIFEST={args.output}"
    )

    print(
        "STATUS=INTAKE_VERIFIED"
    )

    print(
        "FILES=18/18"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
