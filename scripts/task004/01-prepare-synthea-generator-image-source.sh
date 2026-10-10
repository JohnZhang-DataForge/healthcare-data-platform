#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK004 STEP03 GENERATOR SOURCE INSTALL OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  if [[ -n "$STAGE" ]]; then
    rm -rf -- "$STAGE"
  fi

  echo "INSTALL_EXIT_CODE=${rc}"
  echo '#### TASK004 STEP03 GENERATOR SOURCE INSTALL OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: generator must run from a saved Bash file'
  exit 2
}

cd "$ROOT"

STAGE="$(
  mktemp -d \
    /data/spark/temp_shell/task004-step03-source.XXXXXXXX
)"

mkdir -p \
  "$STAGE/apps/task004" \
  "$STAGE/images/synthea" \
  "$STAGE/tests/task004"

# ============================================================
# A. Runtime generated-batch validator
# ============================================================

cat > \
  "$STAGE/apps/task004/validate_generated_synthea_batch.py" \
  <<'PY_VALIDATOR'
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
PY_VALIDATOR

# ============================================================
# B. Synthea image entrypoint
# ============================================================

cat > \
  "$STAGE/images/synthea/entrypoint.sh" \
  <<'ENTRYPOINT'
#!/usr/bin/env bash
set -Eeuo pipefail

SYNTHEA_JAR="${SYNTHEA_JAR:-/opt/synthea/synthea-with-dependencies.jar}"
CSV_CONTRACT="${CSV_CONTRACT:-/opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json}"
VALIDATOR="${VALIDATOR:-/opt/healthcare/apps/task004/validate_generated_synthea_batch.py}"

OUTPUT_ROOT="${OUTPUT_ROOT:-/work/output}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-/work/evidence}"

show_help() {
  cat <<'HELP'
Healthcare Data Platform TASK004 Synthea Generator

Required environment:
  BATCH_ID
  POPULATION_SIZE        Initial TASK004 profiles: 20 or 50
  SEED
  REFERENCE_DATE         YYYYMMDD
  STATE

Optional environment:
  CLINICIAN_SEED         Defaults to SEED
  CITY                   Optional Synthea city

Fixed provenance:
  SYNTHEA_VERSION=v3.3.0
  SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

This image stage performs:
  Synthea generation
  exact 18-CSV validation
  SHA256 calculation
  local draft manifest creation

Landing publication is intentionally not performed by STEP03 source.
HELP
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  show_help
  exit 0
fi

: "${BATCH_ID:?BATCH_ID is required}"
: "${POPULATION_SIZE:?POPULATION_SIZE is required}"
: "${SEED:?SEED is required}"
: "${REFERENCE_DATE:?REFERENCE_DATE is required}"
: "${STATE:?STATE is required}"
: "${SYNTHEA_VERSION:?SYNTHEA_VERSION is required}"
: "${SYNTHEA_COMMIT:?SYNTHEA_COMMIT is required}"

CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"
CITY="${CITY:-}"

[[ "${POPULATION_SIZE}" =~ ^[0-9]+$ ]] || {
  echo "ERROR: POPULATION_SIZE must be a positive integer" >&2
  exit 2
}

(( POPULATION_SIZE > 0 )) || {
  echo "ERROR: POPULATION_SIZE must be greater than zero" >&2
  exit 2
}

if [[ "${POPULATION_SIZE}" != "20" && "${POPULATION_SIZE}" != "50" ]]; then
  echo "ERROR: initial TASK004 POPULATION_SIZE must be 20 or 50" >&2
  exit 2
fi

[[ "${SEED}" =~ ^-?[0-9]+$ ]] || {
  echo "ERROR: SEED must be an integer" >&2
  exit 2
}

[[ "${CLINICIAN_SEED}" =~ ^-?[0-9]+$ ]] || {
  echo "ERROR: CLINICIAN_SEED must be an integer" >&2
  exit 2
}

python3 - "${REFERENCE_DATE}" <<'PY'
import sys
from datetime import datetime

value = sys.argv[1]

try:
    datetime.strptime(
        value,
        "%Y%m%d",
    )
except ValueError as exc:
    raise SystemExit(
        "ERROR: REFERENCE_DATE must be "
        "a valid YYYYMMDD date"
    ) from exc
PY

[[ "${SYNTHEA_VERSION}" == "v3.3.0" ]] || {
  echo "ERROR: unexpected SYNTHEA_VERSION=${SYNTHEA_VERSION}" >&2
  exit 2
}

[[ "${SYNTHEA_COMMIT}" == "995cf2fd33e67918d4e33110d9f68ad248002221" ]] || {
  echo "ERROR: unexpected SYNTHEA_COMMIT=${SYNTHEA_COMMIT}" >&2
  exit 2
}

[[ -s "${SYNTHEA_JAR}" ]] || {
  echo "ERROR: missing Synthea JAR: ${SYNTHEA_JAR}" >&2
  exit 2
}

[[ -s "${CSV_CONTRACT}" ]] || {
  echo "ERROR: missing CSV contract: ${CSV_CONTRACT}" >&2
  exit 2
}

[[ -s "${VALIDATOR}" ]] || {
  echo "ERROR: missing validator: ${VALIDATOR}" >&2
  exit 2
}

rm -rf \
  "${OUTPUT_ROOT}" \
  "${EVIDENCE_ROOT}"

mkdir -p \
  "${OUTPUT_ROOT}" \
  "${EVIDENCE_ROOT}"

echo "============================================================"
echo "Healthcare Data Platform TASK004"
echo "Synthea Generator"
echo "============================================================"
echo "BATCH_ID=${BATCH_ID}"
echo "POPULATION_SIZE=${POPULATION_SIZE}"
echo "SEED=${SEED}"
echo "CLINICIAN_SEED=${CLINICIAN_SEED}"
echo "REFERENCE_DATE=${REFERENCE_DATE}"
echo "STATE=${STATE}"
echo "CITY=${CITY}"
echo "SYNTHEA_VERSION=${SYNTHEA_VERSION}"
echo "SYNTHEA_COMMIT=${SYNTHEA_COMMIT}"
echo

SYNTHEA_ARGS=(
  "-s"
  "${SEED}"

  "-cs"
  "${CLINICIAN_SEED}"

  "-p"
  "${POPULATION_SIZE}"

  "-r"
  "${REFERENCE_DATE}"

  "--exporter.baseDirectory=${OUTPUT_ROOT}"

  "--exporter.metadata.export=false"

  "--exporter.csv.export=true"

  "--exporter.csv.append_mode=false"

  "--exporter.csv.folder_per_run=false"

  "--exporter.csv.excluded_files=patient_expenses.csv"

  "--exporter.years_of_history=0"

  "--exporter.ccda.export=false"

  "--exporter.fhir.export=false"

  "--exporter.fhir_stu3.export=false"

  "--exporter.fhir_dstu2.export=false"

  "--exporter.hospital.fhir.export=false"

  "--exporter.hospital.fhir_stu3.export=false"

  "--exporter.hospital.fhir_dstu2.export=false"

  "--exporter.practitioner.fhir.export=false"

  "--exporter.practitioner.fhir_stu3.export=false"

  "--exporter.practitioner.fhir_dstu2.export=false"

  "--exporter.groups.fhir.export=false"

  "--exporter.json.export=false"

  "--exporter.cpcds.export=false"

  "--exporter.bfd.export=false"

  "--exporter.cdw.export=false"

  "--exporter.text.export=false"

  "--exporter.clinical_note.export=false"

  "--exporter.symptoms.csv.export=false"

  "--exporter.symptoms.text.export=false"

  "--generate.thread_pool_size=1"

  "--generate.log_patients.detail=none"
)

if [[ -n "${CITY}" ]]; then
  SYNTHEA_ARGS+=(
    "${STATE}"
    "${CITY}"
  )
else
  SYNTHEA_ARGS+=(
    "${STATE}"
  )
fi

echo "Starting Synthea generation..."

java \
  -jar "${SYNTHEA_JAR}" \
  "${SYNTHEA_ARGS[@]}"

CSV_DIR="${OUTPUT_ROOT}/csv"

[[ -d "${CSV_DIR}" ]] || {
  echo "ERROR: Synthea did not create ${CSV_DIR}" >&2
  exit 1
}

VALIDATOR_ARGS=(
  python3
  "${VALIDATOR}"

  --source-dir
  "${CSV_DIR}"

  --contract
  "${CSV_CONTRACT}"

  --batch-id
  "${BATCH_ID}"

  --synthea-version
  "${SYNTHEA_VERSION}"

  --synthea-commit
  "${SYNTHEA_COMMIT}"

  --population-size
  "${POPULATION_SIZE}"

  --seed
  "${SEED}"

  --clinician-seed
  "${CLINICIAN_SEED}"

  --reference-date
  "${REFERENCE_DATE}"

  --state
  "${STATE}"

  --output
  "${EVIDENCE_ROOT}/manifest.draft.json"

  --report
  "${EVIDENCE_ROOT}/validation.json"
)

if [[ -n "${CITY}" ]]; then
  VALIDATOR_ARGS+=(
    --city
    "${CITY}"
  )
fi

echo
echo "Validating generated CSV batch..."

"${VALIDATOR_ARGS[@]}"

echo
echo "SYNTHEA_GENERATION=PASS"
echo "POPULATION_SIZE=${POPULATION_SIZE}"
echo "BATCH_ID=${BATCH_ID}"
echo "DRAFT_MANIFEST=${EVIDENCE_ROOT}/manifest.draft.json"
echo "VALIDATION_REPORT=${EVIDENCE_ROOT}/validation.json"
echo "LANDING_PUBLICATION=NOT_STARTED"
ENTRYPOINT

# ============================================================
# C. Synthea container build source
# ============================================================

cat > \
  "$STAGE/images/synthea/Dockerfile" \
  <<'DOCKERFILE'
# syntax=docker/dockerfile:1

ARG BUILDER_IMAGE=eclipse-temurin:17-jdk-jammy
ARG RUNTIME_IMAGE=eclipse-temurin:17-jre-jammy

FROM ${BUILDER_IMAGE} AS synthea-builder

ARG SYNTHEA_REPOSITORY=https://github.com/synthetichealth/synthea.git
ARG SYNTHEA_VERSION=v3.3.0
ARG SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git init synthea \
    && cd synthea \
    && git remote add origin "${SYNTHEA_REPOSITORY}" \
    && git fetch --depth=1 origin "${SYNTHEA_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${SYNTHEA_COMMIT}" \
    && test "$(git describe --tags --exact-match HEAD)" = "${SYNTHEA_VERSION}"

WORKDIR /src/synthea

RUN ./gradlew --no-daemon clean uberJar \
    && test -s build/libs/synthea-with-dependencies.jar


FROM ${RUNTIME_IMAGE}

ARG PROJECT_GIT_SHA=unknown
ARG SYNTHEA_VERSION=v3.3.0
ARG SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

LABEL org.opencontainers.image.title="healthcare-data-platform-synthea"
LABEL org.opencontainers.image.description="Pinned Synthea generator for Healthcare Data Platform TASK004"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
LABEL org.opencontainers.image.version="${SYNTHEA_VERSION}"
LABEL io.healthcare-data-platform.synthea.commit="${SYNTHEA_COMMIT}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       python3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 hdp \
    && useradd \
       --uid 10001 \
       --gid 10001 \
       --create-home \
       --home-dir /home/hdp \
       --shell /usr/sbin/nologin \
       hdp

COPY --from=synthea-builder \
  /src/synthea/build/libs/synthea-with-dependencies.jar \
  /opt/synthea/synthea-with-dependencies.jar

COPY --from=synthea-builder \
  /src/synthea/LICENSE \
  /opt/synthea/LICENSE

COPY --from=synthea-builder \
  /src/synthea/NOTICE \
  /opt/synthea/NOTICE

COPY \
  contracts/synthea/v3.3.0/csv-contract.json \
  /opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json

COPY \
  apps/task004/validate_generated_synthea_batch.py \
  /opt/healthcare/apps/task004/validate_generated_synthea_batch.py

COPY \
  images/synthea/entrypoint.sh \
  /usr/local/bin/healthcare-synthea-generator

RUN chmod 0755 \
      /usr/local/bin/healthcare-synthea-generator \
      /opt/healthcare/apps/task004/validate_generated_synthea_batch.py \
    && mkdir -p \
      /work/output \
      /work/evidence \
    && chown -R 10001:10001 \
      /work \
      /opt/healthcare \
      /opt/synthea

ENV SYNTHEA_VERSION=v3.3.0
ENV SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221
ENV SYNTHEA_JAR=/opt/synthea/synthea-with-dependencies.jar
ENV CSV_CONTRACT=/opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json
ENV VALIDATOR=/opt/healthcare/apps/task004/validate_generated_synthea_batch.py
ENV OUTPUT_ROOT=/work/output
ENV EVIDENCE_ROOT=/work/evidence

WORKDIR /work

USER 10001:10001

ENTRYPOINT ["/usr/local/bin/healthcare-synthea-generator"]
DOCKERFILE

# ============================================================
# D. Static + validator tests
# ============================================================

cat > \
  "$STAGE/tests/task004/test_synthea_generator_image_source.py" \
  <<'PY_TEST'
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

    def test_runtime_image_arg_is_global(
        self,
    ):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        runtime_arg = (
            "ARG RUNTIME_IMAGE="
            "eclipse-temurin:17-jre-jammy"
        )

        builder_from = (
            "FROM ${BUILDER_IMAGE}"
        )

        runtime_from = (
            "FROM ${RUNTIME_IMAGE}"
        )

        runtime_arg_position = text.index(
            runtime_arg
        )

        builder_from_position = text.index(
            builder_from
        )

        runtime_from_position = text.index(
            runtime_from
        )

        self.assertLess(
            runtime_arg_position,
            builder_from_position,
        )

        self.assertLess(
            builder_from_position,
            runtime_from_position,
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
PY_TEST

# ============================================================
# E. Install canonical source
# ============================================================

mkdir -p \
  "$ROOT/apps/task004" \
  "$ROOT/images/synthea" \
  "$ROOT/tests/task004"

install \
  -m 0755 \
  "$STAGE/apps/task004/validate_generated_synthea_batch.py" \
  "$ROOT/apps/task004/validate_generated_synthea_batch.py"

install \
  -m 0644 \
  "$STAGE/images/synthea/Dockerfile" \
  "$ROOT/images/synthea/Dockerfile"

install \
  -m 0755 \
  "$STAGE/images/synthea/entrypoint.sh" \
  "$ROOT/images/synthea/entrypoint.sh"

install \
  -m 0644 \
  "$STAGE/tests/task004/test_synthea_generator_image_source.py" \
  "$ROOT/tests/task004/test_synthea_generator_image_source.py"

echo "CANONICAL_SOURCE_INSTALLED=YES"
