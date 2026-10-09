#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

RUNTIME_ROOT="${PROJECT_ROOT}/runtime"
REPORT_ROOT="${RUNTIME_ROOT}/reports/task002"
WORK_ROOT="${RUNTIME_ROOT}/work"
ARCHIVE_ROOT="${RUNTIME_ROOT}/archive/task002"

NAMESPACE="dw-spark"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
ARCHIVE_DIR="${ARCHIVE_ROOT}/${STAMP}"

echo "============================================================"
echo "TASK-002 / STEP 00"
echo "Reset Person V2 local runtime"
echo "============================================================"
echo

if [[ "${PROJECT_ROOT}" != "/data/spark/healthcare-data-platform" ]]; then
    echo "ERROR: unexpected PROJECT_ROOT=${PROJECT_ROOT}"
    exit 1
fi

mkdir -p \
  "${REPORT_ROOT}" \
  "${WORK_ROOT}" \
  "${ARCHIVE_ROOT}"

if find "${REPORT_ROOT}" -type f -print -quit 2>/dev/null | grep -q .; then
    mkdir -p "${ARCHIVE_DIR}/reports"
    cp -a "${REPORT_ROOT}/." "${ARCHIVE_DIR}/reports/"
    echo "Archived old TASK-002 reports:"
    echo "  ${ARCHIVE_DIR}/reports"
fi

rm -rf "${REPORT_ROOT}"
mkdir -p "${REPORT_ROOT}"

find "${WORK_ROOT}" \
  -mindepth 1 \
  -maxdepth 1 \
  -name 'task002*' \
  -exec rm -rf -- {} + \
  2>/dev/null || true

find "${PROJECT_ROOT}" \
  -type d \
  -name '__pycache__' \
  -prune \
  -exec rm -rf -- {} + \
  2>/dev/null || true

echo
echo "Cleaning TASK-002 temporary Pods..."

kubectl delete pod \
  -n "${NAMESPACE}" \
  -l healthcare-task=task002 \
  --ignore-not-found=true \
  >/dev/null 2>&1 || true

echo
echo "Cleaning TASK-002 SparkApplications..."

kubectl delete sparkapplication \
  -n "${NAMESPACE}" \
  -l healthcare-task=task002 \
  --ignore-not-found=true \
  >/dev/null 2>&1 || true

echo
echo "Protected:"
echo "  TASK-001 Landing"
echo "  /data/spark/phase3c"
echo "  PostgreSQL / OMOP"
echo "  Secrets"
echo "  PVC / PV"
echo

echo "STEP00=PASS"
echo "TASK002_LOCAL_RUNTIME_RESET=PASS"
echo "PERSISTENT_DATA_TOUCHED=NO"
