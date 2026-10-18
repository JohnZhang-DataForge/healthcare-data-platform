#!/usr/bin/env python3

"""Validate one newly generated Synthea v3.3.0 CSV batch.

This is a TASK004 runtime-facing validator.

It does not modify the frozen TASK001/TASK002/TASK003 code.

Responsibilities:
- enforce the authoritative 18-CSV contract;
- verify exact CSV inventory;
- verify headers and column counts;
- require non-empty data rows when the contract requires it;
- calculate size, row count and SHA256;
- write a deterministic local draft manifest;
- record the full Synthea generation provenance.

No S3 or PostgreSQL write occurs here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_SOURCE = "synthea"
EXPECTED_VERSION = "v3.3.0"
EXPECTED_COMMIT = (
    "995cf2fd33e67918d4e33110d9f68ad248002221"
)
EXPECTED_FILE_COUNT = 18


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def atomic_json_write(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")

        os.replace(
            temporary,
            path,
        )

    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if contract.get("source") != EXPECTED_SOURCE:
        raise ValueError(
            "contract source is not synthea"
        )

    if contract.get("source_version") != EXPECTED_VERSION:
        raise ValueError(
            "contract source_version is not v3.3.0"
        )

    if (
        contract.get("expected_file_count")
        != EXPECTED_FILE_COUNT
    ):
        raise ValueError(
            "contract expected_file_count "
            "must be 18"
        )

    files = contract.get("files")

    if not isinstance(files, list):
        raise ValueError(
            "contract files must be a list"
        )

    if len(files) != EXPECTED_FILE_COUNT:
        raise ValueError(
            "contract must contain exactly "
            "18 file definitions"
        )

    names = [
        item.get("filename")
        for item in files
    ]

    if any(
        not isinstance(name, str)
        or not name
        for name in names
    ):
        raise ValueError(
            "contract contains invalid filename"
        )

    if len(names) != len(set(names)):
        raise ValueError(
            "contract contains duplicate filenames"
        )

    for item in files:
        header = item.get("header")

        if (
            not isinstance(header, list)
            or not header
            or not all(
                isinstance(value, str)
                for value in header
            )
        ):
            raise ValueError(
                "invalid header definition for "
                + str(item.get("filename"))
            )

    return contract


def validate_reference_date(value: str) -> None:
    if not re.fullmatch(
        r"\d{8}",
        value,
    ):
        raise ValueError(
            "reference_date must use YYYYMMDD"
        )

    datetime.strptime(
        value,
        "%Y%m%d",
    )


def validate_batch_id(value: str) -> None:
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",
        value,
    ):
        raise ValueError(
            "batch_id must contain only "
            "letters, digits, '.', '_' or '-' "
            "and be 3-128 characters"
        )


def inspect_csv(
    path: Path,
    expected_header: list[str],
    require_nonempty: bool,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []

    if not path.is_file():
        return None, [
            f"missing file: {path.name}"
        ]

    size_bytes = path.stat().st_size

    if size_bytes == 0:
        return None, [
            f"empty file: {path.name}"
        ]

    row_count = 0

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.reader(
                handle,
                strict=True,
            )

            try:
                actual_header = next(reader)
            except StopIteration:
                return None, [
                    "file has no CSV header: "
                    + path.name
                ]

            if actual_header != expected_header:
                errors.append(
                    "header mismatch: "
                    + path.name
                )

            expected_columns = len(
                expected_header
            )

            for record_number, row in enumerate(
                reader,
                start=2,
            ):
                row_count += 1

                if len(row) != expected_columns:
                    errors.append(
                        "column count mismatch: "
                        f"{path.name} "
                        f"record={record_number} "
                        f"expected={expected_columns} "
                        f"actual={len(row)}"
                    )

                    if len(errors) >= 25:
                        errors.append(
                            "too many CSV errors; "
                            "stopping validation for "
                            + path.name
                        )
                        break

    except UnicodeDecodeError as exc:
        errors.append(
            "UTF-8 decode failed: "
            f"{path.name}: {exc}"
        )

    except csv.Error as exc:
        errors.append(
            "CSV parse failed: "
            f"{path.name}: {exc}"
        )

    except OSError as exc:
        errors.append(
            "read failed: "
            f"{path.name}: {exc}"
        )

    if require_nonempty and row_count == 0:
        errors.append(
            "no data rows: "
            + path.name
        )

    if errors:
        return None, errors

    return {
        "size_bytes": size_bytes,
        "sha256": sha256_file(path),
        "row_count": row_count,
        "header": expected_header,
    }, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a newly generated "
            "Synthea TASK004 CSV batch."
        )
    )

    parser.add_argument(
        "--source-dir",
        required=True,
    )

    parser.add_argument(
        "--contract",
        required=True,
    )

    parser.add_argument(
        "--batch-id",
        required=True,
    )

    parser.add_argument(
        "--synthea-version",
        required=True,
    )

    parser.add_argument(
        "--synthea-commit",
        required=True,
    )

    parser.add_argument(
        "--population-size",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--seed",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--clinician-seed",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--reference-date",
        required=True,
    )

    parser.add_argument(
        "--state",
        required=True,
    )

    parser.add_argument(
        "--city",
        default="",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="local draft manifest JSON",
    )

    parser.add_argument(
        "--report",
        required=True,
        help="local validation report JSON",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        validate_batch_id(
            args.batch_id
        )

        validate_reference_date(
            args.reference_date
        )

    except ValueError as exc:
        raise SystemExit(
            f"ERROR: {exc}"
        ) from exc

    if args.population_size <= 0:
        raise SystemExit(
            "ERROR: population_size "
            "must be positive"
        )

    if (
        args.synthea_version
        != EXPECTED_VERSION
    ):
        raise SystemExit(
            "ERROR: unexpected "
            "Synthea version"
        )

    if (
        args.synthea_commit
        != EXPECTED_COMMIT
    ):
        raise SystemExit(
            "ERROR: unexpected "
            "Synthea commit"
        )

    source_dir = Path(
        args.source_dir
    ).resolve()

    contract_path = Path(
        args.contract
    ).resolve()

    output_path = Path(
        args.output
    ).resolve()

    report_path = Path(
        args.report
    ).resolve()

    try:
        contract = load_contract(
            contract_path
        )
    except Exception as exc:
        raise SystemExit(
            "ERROR: cannot load contract: "
            + str(exc)
        ) from exc

    if not source_dir.is_dir():
        raise SystemExit(
            "ERROR: source directory "
            "does not exist: "
            + str(source_dir)
        )

    expected_names = [
        item["filename"]
        for item in contract["files"]
    ]

    expected_set = set(
        expected_names
    )

    actual_names = sorted(
        path.name
        for path in source_dir.glob("*.csv")
        if path.is_file()
    )

    actual_set = set(
        actual_names
    )

    errors: list[str] = []

    missing = sorted(
        expected_set - actual_set
    )

    unexpected = sorted(
        actual_set - expected_set
    )

    if missing:
        errors.append(
            "missing expected CSV files: "
            + ", ".join(missing)
        )

    if unexpected:
        errors.append(
            "unexpected CSV files: "
            + ", ".join(unexpected)
        )

    if len(actual_names) != EXPECTED_FILE_COUNT:
        errors.append(
            "CSV file count mismatch: "
            f"expected={EXPECTED_FILE_COUNT} "
            f"actual={len(actual_names)}"
        )

    file_results: list[dict[str, Any]] = []

    if not errors:
        require_nonempty = bool(
            contract.get(
                "require_nonempty_data_rows",
                True,
            )
        )

        for item in contract["files"]:
            filename = item["filename"]

            result, item_errors = inspect_csv(
                source_dir / filename,
                item["header"],
                require_nonempty,
            )

            if item_errors:
                errors.extend(
                    item_errors
                )
                print(
                    f"FAIL {filename}"
                )
                continue

            assert result is not None

            file_result = {
                "dataset":
                    item["dataset"],
                "header":
                    result["header"],
                "path":
                    "payload/csv/"
                    + filename,
                "row_count":
                    result["row_count"],
                "sha256":
                    result["sha256"],
                "size_bytes":
                    result["size_bytes"],
            }

            file_results.append(
                file_result
            )

            print(
                "PASS "
                f"{filename:<26} "
                f"rows="
                f"{file_result['row_count']:<7} "
                f"bytes="
                f"{file_result['size_bytes']:<9} "
                "sha256="
                f"{file_result['sha256']}"
            )

    status = (
        "PASS"
        if (
            not errors
            and len(file_results)
            == EXPECTED_FILE_COUNT
        )
        else "FAIL"
    )

    contract_sha256 = sha256_file(
        contract_path
    )

    report = {
        "batch_id":
            args.batch_id,
        "contract_sha256":
            contract_sha256,
        "errors":
            errors,
        "expected_file_count":
            EXPECTED_FILE_COUNT,
        "source_dir":
            str(source_dir),
        "status":
            status,
        "synthea_commit":
            args.synthea_commit,
        "synthea_version":
            args.synthea_version,
        "validated_file_count":
            len(file_results),
        "validation_stage":
            "TASK004_GENERATED_SOURCE_VALIDATION",
    }

    atomic_json_write(
        report_path,
        report,
    )

    if status != "PASS":
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass

        print(
            "\nSYNTHEA_LOCAL_VALIDATION=FAIL"
        )

        for error in errors:
            print(
                "ERROR: " + error
            )

        return 1

    manifest = {
        "contract": {
            "path":
                "contracts/synthea/"
                "v3.3.0/csv-contract.json",
            "sha256":
                contract_sha256,
        },
        "expected_file_count":
            EXPECTED_FILE_COUNT,
        "files":
            file_results,
        "manifest_version":
            "1.0",
        "payload_format":
            "csv",
        "source":
            EXPECTED_SOURCE,
        "source_parameters": {
            "city":
                args.city or None,
            "clinician_seed":
                args.clinician_seed,
            "population_size":
                args.population_size,
            "reference_date":
                args.reference_date,
            "seed":
                args.seed,
            "state":
                args.state,
        },
        "source_provenance": {
            "synthea_commit":
                args.synthea_commit,
            "synthea_version":
                args.synthea_version,
        },
        "source_version":
            EXPECTED_VERSION,
        "status":
            "LOCAL_VALIDATED_NOT_UPLOADED",
        "batch_id":
            args.batch_id,
    }

    atomic_json_write(
        output_path,
        manifest,
    )

    print()
    print(
        "CSV_VALIDATED="
        f"{len(file_results)}/"
        f"{EXPECTED_FILE_COUNT}"
    )
    print(
        "DRAFT_MANIFEST="
        + str(output_path)
    )
    print(
        "SYNTHEA_LOCAL_VALIDATION=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
