#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

FINAL_REPORT_RELATIVE = Path(
    "runtime/reports/task001/step05/"
    "task001-final-validation.json"
)

TASK001_RUNTIME_RELATIVE = Path(
    "runtime/reports/task001"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def is_verified_manifest(doc) -> bool:
    if not isinstance(doc, dict):
        return False

    if doc.get("status") != "INTAKE_VERIFIED":
        return False

    if doc.get("manifest_version") != "1.0":
        return False

    if doc.get("source") != "synthea":
        return False

    files = doc.get("files")

    if not isinstance(files, list):
        return False

    if len(files) != 18:
        return False

    return True


def find_manifest(
    runtime_root: Path,
    expected_sha256: str,
    expected_batch_id: str,
):
    matches = []

    for path in runtime_root.rglob("*.json"):

        try:
            if sha256_file(path) != expected_sha256:
                continue

            doc = load_json(path)

        except Exception:
            continue

        if not is_verified_manifest(doc):
            continue

        if doc.get("batch_id") != expected_batch_id:
            continue

        matches.append(
            (
                path,
                doc,
            )
        )

    if not matches:
        raise RuntimeError(
            "Unable to find local TASK-001 manifest "
            "matching the frozen remote manifest SHA256."
        )

    if len(matches) > 1:
        # Identical bytes are acceptable.
        # Pick deterministic path ordering.
        matches.sort(
            key=lambda item: str(item[0])
        )

    return matches[0]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "dataset",
        help=(
            "TASK-001 dataset name, "
            "for example encounters"
        ),
    )

    parser.add_argument(
        "--project-root",
        default=str(DEFAULT_ROOT),
    )

    parser.add_argument(
        "--format",
        choices=[
            "json",
            "shell",
        ],
        default="json",
    )

    args = parser.parse_args()

    project_root = Path(
        args.project_root
    )

    final_report_path = (
        project_root
        / FINAL_REPORT_RELATIVE
    )

    runtime_root = (
        project_root
        / TASK001_RUNTIME_RELATIVE
    )

    if not final_report_path.is_file():
        raise RuntimeError(
            f"TASK-001 final report missing: "
            f"{final_report_path}"
        )

    final_report = load_json(
        final_report_path
    )

    if final_report.get("task") != "TASK-001":
        raise RuntimeError(
            "Invalid TASK-001 final report."
        )

    if final_report.get("status") != "PASS":
        raise RuntimeError(
            "TASK-001 final report is not PASS."
        )

    batch_id = final_report.get(
        "batch_id"
    )

    manifest_uri = final_report.get(
        "manifest_uri"
    )

    expected_manifest_sha = (
        final_report.get(
            "manifest_sha256"
        )
    )

    if not batch_id:
        raise RuntimeError(
            "TASK-001 final report missing batch_id."
        )

    if not manifest_uri:
        raise RuntimeError(
            "TASK-001 final report missing manifest_uri."
        )

    if (
        not isinstance(
            expected_manifest_sha,
            str,
        )
        or len(expected_manifest_sha) != 64
    ):
        raise RuntimeError(
            "TASK-001 final report has invalid "
            "manifest_sha256."
        )

    manifest_path, manifest = (
        find_manifest(
            runtime_root,
            expected_manifest_sha,
            batch_id,
        )
    )

    actual_manifest_sha = sha256_file(
        manifest_path
    )

    if actual_manifest_sha != expected_manifest_sha:
        raise RuntimeError(
            "TASK-001 manifest SHA256 mismatch."
        )

    if manifest.get("batch_id") != batch_id:
        raise RuntimeError(
            "TASK-001 batch_id mismatch."
        )

    files = manifest["files"]

    candidates = [
        item
        for item in files
        if (
            item.get("dataset")
            == args.dataset
        )
    ]

    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one dataset "
            f"{args.dataset!r}; "
            f"found {len(candidates)}."
        )

    item = candidates[0]

    required_file_fields = [
        "path",
        "dataset",
        "size_bytes",
        "sha256",
        "row_count",
        "header",
    ]

    for field in required_file_fields:
        if field not in item:
            raise RuntimeError(
                f"Manifest file entry missing "
                f"{field!r}."
            )

    if item["row_count"] <= 0:
        raise RuntimeError(
            "Manifest row_count must be > 0."
        )

    if item["size_bytes"] <= 0:
        raise RuntimeError(
            "Manifest size_bytes must be > 0."
        )

    if (
        not isinstance(
            item["sha256"],
            str,
        )
        or len(item["sha256"]) != 64
    ):
        raise RuntimeError(
            "Manifest file SHA256 is invalid."
        )

    landing_uri = manifest.get(
        "landing_uri"
    )

    if not landing_uri:
        raise RuntimeError(
            "Verified manifest missing landing_uri."
        )

    if not landing_uri.endswith("/"):
        landing_uri += "/"

    source_uri = (
        landing_uri
        + item["path"]
    )

    result = {
        "manifest_status":
            manifest["status"],

        "manifest_version":
            manifest["manifest_version"],

        "manifest_uri":
            manifest_uri,

        "manifest_sha256":
            actual_manifest_sha,

        "manifest_local_path":
            str(manifest_path),

        "source":
            manifest["source"],

        "source_version":
            manifest["source_version"],

        "batch_id":
            manifest["batch_id"],

        "ingest_date":
            manifest["ingest_date"],

        "landing_uri":
            landing_uri,

        "dataset":
            item["dataset"],

        "path":
            item["path"],

        "source_uri":
            source_uri,

        "row_count":
            int(item["row_count"]),

        "size_bytes":
            int(item["size_bytes"]),

        "sha256":
            item["sha256"],

        "header":
            item["header"],
    }

    if args.format == "json":

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

        return

    shell_values = {
        "MANIFEST_STATUS":
            result["manifest_status"],

        "MANIFEST_VERSION":
            result["manifest_version"],

        "MANIFEST_URI":
            result["manifest_uri"],

        "MANIFEST_SHA256":
            result["manifest_sha256"],

        "SOURCE":
            result["source"],

        "SOURCE_VERSION":
            result["source_version"],

        "BATCH_ID":
            result["batch_id"],

        "INGEST_DATE":
            result["ingest_date"],

        "SOURCE_DATASET":
            result["dataset"],

        "SOURCE_FILE":
            result["path"],

        "SOURCE_URI":
            result["source_uri"],

        "EXPECTED_ROWS":
            result["row_count"],

        "SOURCE_FILE_SIZE_BYTES":
            result["size_bytes"],

        "SOURCE_FILE_SHA256":
            result["sha256"],
    }

    for key, value in shell_values.items():

        value = str(value)

        if any(
            ch in value
            for ch in "\n\r"
        ):
            raise RuntimeError(
                f"Unsafe shell value for {key}."
            )

        print(
            f"{key}={value}"
        )


if __name__ == "__main__":
    main()
