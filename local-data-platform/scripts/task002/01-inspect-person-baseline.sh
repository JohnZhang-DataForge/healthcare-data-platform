#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
LEGACY="/data/spark/phase3c"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task002/step01"

mkdir -p "${REPORT_DIR}"

SUMMARY="${REPORT_DIR}/person-baseline-summary.txt"
LEGACY_INDEX="${REPORT_DIR}/legacy-person-files.txt"
LEGACY_KEY_LINES="${REPORT_DIR}/legacy-person-key-lines.txt"
SPARK_SUMMARY="${REPORT_DIR}/spark-environment.txt"

exec > >(tee "${SUMMARY}") 2>&1

echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-002 / STEP 01"
echo "Person V2 baseline inspection"
echo "READ ONLY"
echo "============================================================"
echo


# ============================================================
# 1. Verify TASK-001 prerequisite
# ============================================================

echo "[1/7] TASK-001 prerequisite..."

TASK001_REPORT="${PROJECT_ROOT}/runtime/reports/task001/step05/task001-final-validation.json"

if [[ ! -f "${TASK001_REPORT}" ]]; then
    echo "ERROR:"
    echo "TASK-001 final report not found:"
    echo "  ${TASK001_REPORT}"
    exit 1
fi

python3 - "${TASK001_REPORT}" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))

assert d["task"] == "TASK-001"
assert d["status"] == "PASS"
assert d["s3_payload"]["objects"] == "18/18"
assert d["s3_payload"]["readback_sha256"] == "18/18"
assert d["manifest"]["status"] == "INTAKE_VERIFIED"

print("TASK001=PASS")
print(f"Batch ID : {d['batch_id']}")
print(f"Landing  : {d['landing_uri']}")
PY

echo


# ============================================================
# 2. Inspect patients.csv
# ============================================================

echo "[2/7] Inspecting source patients.csv..."

PATIENTS="${LEGACY}/source/synthea/csv/patients.csv"

if [[ ! -f "${PATIENTS}" ]]; then
    echo "ERROR: missing ${PATIENTS}"
    exit 1
fi

python3 - "${PATIENTS}" <<'PY'
import csv
import hashlib
import sys
from pathlib import Path

p = Path(sys.argv[1])

h = hashlib.sha256(
    p.read_bytes()
).hexdigest()

with p.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as fh:
    reader = csv.reader(fh)
    header = next(reader)
    rows = sum(1 for _ in reader)

print(f"patients rows   : {rows}")
print(f"patients sha256 : {h}")
print("patients header :")
print(",".join(header))

assert rows == 113
PY

echo


# ============================================================
# 3. Inventory historical Person implementation
# ============================================================

echo "[3/7] Inventorying protected Phase3C Person implementation..."

find "${LEGACY}" \
  -maxdepth 2 \
  -type f \
  \( \
    -name '04-*' -o \
    -name '05-*' -o \
    -name '06-*' -o \
    -name '06b-*' -o \
    -name '07-*' -o \
    -name '08-*' -o \
    -name '09-*' -o \
    -name '10-*' -o \
    -name '11-*' -o \
    -name '12-*' -o \
    -path '*/apps/*.py' -o \
    -path '*/mappings/*' \
  \) \
  -print \
  | sort \
  > "${LEGACY_INDEX}"

while IFS= read -r file
do
    [[ -f "${file}" ]] || continue

    printf '%s  ' "$(sha256sum "${file}" | awk '{print $1}')"
    printf '%s bytes  ' "$(stat -c '%s' "${file}")"
    printf '%s\n' "${file}"

done < "${LEGACY_INDEX}"

echo


# ============================================================
# 4. Extract useful historical mapping / transformation lines
# ============================================================

echo "[4/7] Extracting historical Person transformation clues..."

{
    echo "===== FILE INDEX ====="
    cat "${LEGACY_INDEX}"
    echo

    echo "===== KEY LINES ====="

    while IFS= read -r file
    do
        [[ -f "${file}" ]] || continue

        echo
        echo "----- ${file} -----"

        grep -nEi \
          'patients|person|gender|race|ethnic|birth|death|concept|source_value|mapping|parquet|raw|processed|stage|cdm|person_id|spark|postgres|jdbc|s3a' \
          "${file}" \
          2>/dev/null \
          | grep -Evi \
          'password|secret|token|access[_-]?key|private[_-]?key' \
          || true

    done < "${LEGACY_INDEX}"

} > "${LEGACY_KEY_LINES}"

sed -n '1,320p' "${LEGACY_KEY_LINES}"

echo
echo "Detailed extract saved:"
echo "  ${LEGACY_KEY_LINES}"
echo


# ============================================================
# 5. Print demographic mapping if present
# ============================================================

echo "[5/7] Historical demographic mapping..."

MAPPING="${LEGACY}/mappings/person-demographic-mapping.csv"

if [[ -f "${MAPPING}" ]]; then

    echo "----- ${MAPPING} -----"
    cat "${MAPPING}"

else

    echo "WARN: mapping file not found."

fi

echo


# ============================================================
# 6. Inspect Spark / Kubernetes execution environment
# ============================================================

echo "[6/7] Inspecting Spark/Kubernetes environment..."

{
    echo "===== Kubernetes context ====="
    kubectl config current-context
    echo

    echo "===== dw-spark namespace ====="
    kubectl get ns dw-spark
    echo

    echo "===== Spark Operator Pods ====="
    kubectl get pods -A \
      -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,IMAGE:.spec.containers[*].image,STATUS:.status.phase' \
      | grep -Ei 'spark-operator|NAMESPACE' \
      || true
    echo

    echo "===== SparkApplication CRD ====="
    kubectl get crd sparkapplications.sparkoperator.k8s.io \
      -o custom-columns='NAME:.metadata.name,CREATED:.metadata.creationTimestamp'
    echo

    echo "===== Existing SparkApplications ====="
    kubectl get sparkapplications \
      -n dw-spark \
      -o custom-columns='NAME:.metadata.name,STATE:.status.applicationState.state,IMAGE:.spec.image,MAIN:.spec.mainApplicationFile' \
      2>/dev/null \
      || true
    echo

    echo "===== ServiceAccounts ====="
    kubectl get serviceaccounts -n dw-spark
    echo

    echo "===== Secrets: names/types only ====="
    kubectl get secrets \
      -n dw-spark \
      -o custom-columns='NAME:.metadata.name,TYPE:.type' \
      | grep -E 'NAME|spark|s3|postgres|omop' \
      || true
    echo

    echo "===== ConfigMaps: names only ====="
    kubectl get configmaps \
      -n dw-spark \
      -o name \
      | sort
    echo

    echo "===== StorageClasses ====="
    kubectl get storageclass
    echo

    echo "===== dw-spark Pods ====="
    kubectl get pods \
      -n dw-spark \
      -o wide
    echo

} | tee "${SPARK_SUMMARY}"

echo


# ============================================================
# 7. Current project state
# ============================================================

echo "[7/7] Current Git/project state..."

echo "Branch:"
git -C "${PROJECT_ROOT}" branch --show-current

echo
echo "Git status:"
git -C "${PROJECT_ROOT}" status --short

echo
echo "TASK-002 directories:"
find \
  "${PROJECT_ROOT}/spark/apps/person" \
  "${PROJECT_ROOT}/spark/common" \
  "${PROJECT_ROOT}/spark/manifests/task002" \
  "${PROJECT_ROOT}/scripts/task002" \
  "${PROJECT_ROOT}/tests/task002" \
  -maxdepth 2 \
  -print \
  | sort

echo
echo "============================================================"
echo "TASK-002 STEP 01 RESULT"
echo "============================================================"
echo
echo "STEP01=PASS"
echo "TASK001_PREREQUISITE=PASS"
echo "PATIENT_SOURCE_ROWS=113"
echo "LEGACY_PERSON_BASELINE=DISCOVERED"
echo "SPARK_ENVIRONMENT=INSPECTED"
echo "S3_WRITE=NOT_RUN"
echo "SPARK_JOB=NOT_RUN"
echo "DATABASE_WRITE=NOT_RUN"
echo "PHASE3C_TOUCHED=NO"
echo
echo "Reports:"
echo "  ${SUMMARY}"
echo "  ${LEGACY_INDEX}"
echo "  ${LEGACY_KEY_LINES}"
echo "  ${SPARK_SUMMARY}"
echo "============================================================"
