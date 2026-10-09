#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

ENV_FILE="${PROJECT_ROOT}/config/local.env"
CONTRACT="${PROJECT_ROOT}/contracts/synthea/v3.3.0/csv-contract.json"
VALIDATOR="${PROJECT_ROOT}/apps/task001/validate_synthea_batch.py"
TEST_FILE="${PROJECT_ROOT}/tests/task001/test_validate_synthea_batch.py"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task001/step01"
WORK_DIR="${PROJECT_ROOT}/runtime/work/task001-step01"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: missing ${ENV_FILE}"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${SYNTHEA_SOURCE_DIR:?missing SYNTHEA_SOURCE_DIR}"
: "${SOURCE_VERSION:?missing SOURCE_VERSION}"
: "${BATCH_ID:?missing BATCH_ID}"
: "${SYNTHEA_SEED:?missing SYNTHEA_SEED}"
: "${SYNTHEA_POPULATION:?missing SYNTHEA_POPULATION}"
: "${SYNTHEA_STATE:?missing SYNTHEA_STATE}"
: "${SYNTHEA_CITY:?missing SYNTHEA_CITY}"

mkdir -p "${REPORT_DIR}" "${WORK_DIR}"

DRAFT="${REPORT_DIR}/manifest.draft.json"
REPORT="${REPORT_DIR}/validation-report.json"

FIRST_COPY="${WORK_DIR}/manifest.first.json"
SECOND_COPY="${WORK_DIR}/manifest.second.json"

rm -f \
    "${FIRST_COPY}" \
    "${SECOND_COPY}"

echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 01"
echo "Local Synthea 18-file validation + draft manifest"
echo "============================================================"
echo

# ------------------------------------------------------------
# 1. Static validation
# ------------------------------------------------------------

echo "[1/5] Python syntax and contract JSON checks..."

python3 -m py_compile \
    "${VALIDATOR}" \
    "${TEST_FILE}"

python3 -m json.tool \
    "${CONTRACT}" \
    >/dev/null

echo "PASS"
echo

# ------------------------------------------------------------
# 2. Unit / negative tests
# ------------------------------------------------------------

echo "[2/5] Running offline unit/negative tests..."

python3 "${TEST_FILE}"

echo
echo "PASS: offline tests"
echo

# ------------------------------------------------------------
# 3. Validate actual source
# ------------------------------------------------------------

echo "[3/5] Validating real Synthea source batch..."

python3 "${VALIDATOR}" \
    --source-dir "${SYNTHEA_SOURCE_DIR}" \
    --contract "${CONTRACT}" \
    --batch-id "${BATCH_ID}" \
    --seed "${SYNTHEA_SEED}" \
    --population "${SYNTHEA_POPULATION}" \
    --state "${SYNTHEA_STATE}" \
    --city "${SYNTHEA_CITY}" \
    --output "${DRAFT}" \
    --report "${REPORT}"

cp "${DRAFT}" "${FIRST_COPY}"

echo

# ------------------------------------------------------------
# 4. Deterministic rerun
# ------------------------------------------------------------

echo "[4/5] Re-running against the same local batch..."

python3 "${VALIDATOR}" \
    --source-dir "${SYNTHEA_SOURCE_DIR}" \
    --contract "${CONTRACT}" \
    --batch-id "${BATCH_ID}" \
    --seed "${SYNTHEA_SEED}" \
    --population "${SYNTHEA_POPULATION}" \
    --state "${SYNTHEA_STATE}" \
    --city "${SYNTHEA_CITY}" \
    --output "${DRAFT}" \
    --report "${REPORT}" \
    >/dev/null

cp "${DRAFT}" "${SECOND_COPY}"

if ! cmp -s "${FIRST_COPY}" "${SECOND_COPY}"; then
    echo
    echo "ERROR: Draft manifest changed between identical runs."
    echo

    diff -u \
        "${FIRST_COPY}" \
        "${SECOND_COPY}" \
        || true

    exit 1
fi

echo "PASS: deterministic/idempotent local draft"
echo

# ------------------------------------------------------------
# 5. Summary
# ------------------------------------------------------------

echo "[5/5] Summary..."

python3 - "${DRAFT}" <<'PY_SUMMARY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

data = json.loads(
    path.read_text(
        encoding="utf-8"
    )
)

print(f"Batch ID           : {data['batch_id']}")
print(
    f"Source             : "
    f"{data['source']} {data['source_version']}"
)
print(
    f"CSV validated      : "
    f"{len(data['files'])}/{data['expected_file_count']}"
)
print(
    f"Total source rows  : "
    f"{sum(x['row_count'] for x in data['files'])}"
)
print(f"Draft status       : {data['status']}")
print(f"Draft manifest     : {path}")

print("Core row counts:")

for name in [
    "patients",
    "encounters",
    "conditions",
    "procedures",
    "medications",
    "observations"
]:
    item = next(
        x
        for x in data["files"]
        if x["dataset"] == name
    )

    print(
        f"  {name:<14} "
        f"{item['row_count']}"
    )
PY_SUMMARY

echo
echo "Git branch/status:"

cd "${PROJECT_ROOT}"

printf "  branch: "
git branch --show-current || true

git status --short

echo
echo "STEP01=PASS"
echo "AC-01(local)=PASS"
echo "AC-03(draft)=PASS"
echo "NEGATIVE_TESTS(local)=PASS"
echo "S3_UPLOAD=NOT_RUN"
echo "INTAKE_VERIFIED=NOT_PUBLISHED"
echo "============================================================"
