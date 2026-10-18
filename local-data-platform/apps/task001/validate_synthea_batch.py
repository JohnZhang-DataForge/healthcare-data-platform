#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent)
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as fh:

            json.dump(
                payload,
                fh,
                ensure_ascii=False,
                indent=2
            )

            fh.write("\n")

        os.replace(tmp_name, path)

    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass

        raise


def load_contract(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8"
    ) as fh:
        contract = json.load(fh)

    files = contract.get("files", [])
    expected_count = contract.get("expected_file_count")

    names = [
        item.get("filename")
        for item in files
    ]

    if expected_count != 18:
        raise ValueError(
            f"contract expected_file_count must be 18, "
            f"got {expected_count!r}"
        )

    if len(files) != expected_count:
        raise ValueError(
            f"contract has {len(files)} file entries, "
            f"expected {expected_count}"
        )

    if len(names) != len(set(names)):
        raise ValueError(
            "contract contains duplicate filenames"
        )

    if any(not name for name in names):
        raise ValueError(
            "contract contains empty filename"
        )

    for item in files:

        if not item.get("dataset"):
            raise ValueError(
                f"contract file "
                f"{item.get('filename')} "
                f"has no dataset"
            )

        if (
            not isinstance(item.get("header"), list)
            or not item["header"]
        ):
            raise ValueError(
                f"contract file "
                f"{item.get('filename')} "
                f"has invalid header"
            )

    return contract


def inspect_csv(
    path: Path,
    expected_header: list[str],
    require_nonempty: bool
) -> tuple[dict | None, list[str]]:

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
            newline=""
        ) as fh:

            reader = csv.reader(
                fh,
                strict=True
            )

            try:
                header = next(reader)
            except StopIteration:
                return None, [
                    f"file has no CSV header: "
                    f"{path.name}"
                ]

            if header != expected_header:
                errors.append(
                    f"header mismatch: "
                    f"{path.name}\n"
                    f"  expected="
                    f"{expected_header!r}\n"
                    f"  actual  ="
                    f"{header!r}"
                )

            expected_columns = len(
                expected_header
            )

            for record_number, row in enumerate(
                reader,
                start=2
            ):

                row_count += 1

                if len(row) != expected_columns:

                    errors.append(
                        f"column count mismatch: "
                        f"{path.name} "
                        f"CSV record "
                        f"{record_number}: "
                        f"expected "
                        f"{expected_columns}, "
                        f"got {len(row)}"
                    )

                    if len(errors) >= 25:

                        errors.append(
                            f"too many CSV errors "
                            f"in {path.name}; "
                            f"stopped after 25"
                        )

                        break

    except UnicodeDecodeError as exc:

        errors.append(
            f"UTF-8 decode failed: "
            f"{path.name}: {exc}"
        )

    except csv.Error as exc:

        errors.append(
            f"CSV parse failed: "
            f"{path.name}: {exc}"
        )

    except OSError as exc:

        errors.append(
            f"read failed: "
            f"{path.name}: {exc}"
        )

    if require_nonempty and row_count == 0:

        errors.append(
            f"no data rows: "
            f"{path.name}"
        )

    if errors:
        return None, errors

    return {
        "size_bytes": size_bytes,
        "sha256": sha256_file(path),
        "row_count": row_count,
        "header": expected_header
    }, []


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Validate one complete "
            "Synthea v3.3.0 18-CSV batch."
        )
    )

    parser.add_argument(
        "--source-dir",
        required=True
    )

    parser.add_argument(
        "--contract",
        required=True
    )

    parser.add_argument(
        "--batch-id",
        required=True
    )

    parser.add_argument(
        "--seed",
        required=True,
        type=int
    )

    parser.add_argument(
        "--population",
        required=True,
        type=int
    )

    parser.add_argument(
        "--state",
        required=True
    )

    parser.add_argument(
        "--city",
        required=True
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Draft manifest output JSON"
    )

    parser.add_argument(
        "--report",
        required=True,
        help="Validation report JSON"
    )

    args = parser.parse_args()

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

    errors: list[str] = []
    file_results: list[dict] = []

    try:
        contract = load_contract(
            contract_path
        )

    except Exception as exc:

        print(
            f"ERROR: cannot load contract: "
            f"{exc}",
            file=sys.stderr
        )

        return 2

    if not source_dir.is_dir():

        print(
            f"ERROR: source directory "
            f"does not exist: "
            f"{source_dir}",
            file=sys.stderr
        )

        return 2

    expected_names = [
        item["filename"]
        for item in contract["files"]
    ]

    expected_set = set(
        expected_names
    )

    actual_names = sorted(
        p.name
        for p in source_dir.glob("*.csv")
        if p.is_file()
    )

    actual_set = set(
        actual_names
    )

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

    if (
        len(actual_names)
        != contract["expected_file_count"]
    ):

        errors.append(
            "CSV file count mismatch: "
            f"expected "
            f"{contract['expected_file_count']}, "
            f"got {len(actual_names)}"
        )

    if not errors:

        for item in contract["files"]:

            filename = item["filename"]

            info, item_errors = inspect_csv(
                source_dir / filename,
                item["header"],
                bool(
                    contract.get(
                        "require_nonempty_data_rows",
                        True
                    )
                )
            )

            if item_errors:

                errors.extend(
                    item_errors
                )

                print(
                    f"FAIL {filename}"
                )

                continue

            result = {
                "path":
                    f"payload/csv/"
                    f"{filename}",
                "dataset":
                    item["dataset"],
                "size_bytes":
                    info["size_bytes"],
                "sha256":
                    info["sha256"],
                "row_count":
                    info["row_count"],
                "header":
                    info["header"]
            }

            file_results.append(
                result
            )

            print(
                f"PASS "
                f"{filename:<26} "
                f"rows="
                f"{result['row_count']:<7} "
                f"bytes="
                f"{result['size_bytes']:<9} "
                f"sha256="
                f"{result['sha256']}"
            )

    report = {
        "validation_stage":
            "LOCAL_SOURCE_VALIDATION",

        "source_dir":
            str(source_dir),

        "contract":
            str(contract_path),

        "batch_id":
            args.batch_id,

        "expected_file_count":
            contract[
                "expected_file_count"
            ],

        "validated_file_count":
            len(file_results),

        "status":
            (
                "PASS"
                if (
                    not errors
                    and len(file_results)
                    == contract[
                        "expected_file_count"
                    ]
                )
                else "FAIL"
            ),

        "errors":
            errors
    }

    atomic_json_write(
        report_path,
        report
    )

    if (
        errors
        or len(file_results)
        != contract[
            "expected_file_count"
        ]
    ):

        try:
            output_path.unlink()
        except FileNotFoundError:
            pass

        print(
            "\nSTEP01_VALIDATION=FAIL",
            file=sys.stderr
        )

        for error in errors:

            print(
                f"ERROR: {error}",
                file=sys.stderr
            )

        print(
            f"CSV_VALIDATED="
            f"{len(file_results)}/"
            f"{contract['expected_file_count']}",
            file=sys.stderr
        )

        return 1

    manifest = {
        "manifest_version":
            "1.0",

        "status":
            "LOCAL_VALIDATED_NOT_UPLOADED",

        "source":
            contract["source"],

        "source_version":
            contract["source_version"],

        "batch_id":
            args.batch_id,

        "payload_format":
            "csv",

        "expected_file_count":
            contract[
                "expected_file_count"
            ],

        "source_parameters": {
            "seed":
                args.seed,

            "population":
                args.population,

            "state":
                args.state,

            "city":
                args.city
        },

        "files":
            file_results
    }

    atomic_json_write(
        output_path,
        manifest
    )

    print()

    print(
        f"CSV_VALIDATED="
        f"{len(file_results)}/"
        f"{contract['expected_file_count']}"
    )

    print(
        f"DRAFT_MANIFEST="
        f"{output_path}"
    )

    print(
        "STEP01_VALIDATION=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
