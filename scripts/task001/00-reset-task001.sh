#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Healthcare Data Platform V2.1
# TASK-001
#
# STEP 00 - Reset TASK-001 runtime state
#
# PURPOSE
# -------
# Return TASK-001 to a clean LOCAL EXECUTION state so that
# STEP 01+ can be replayed.
#
# This script evolves together with TASK-001.
#
# CURRENT RESET SCOPE
# -------------------
# - Archive previous TASK-001 reports
# - Remove current TASK-001 reports
# - Remove TASK-001 local work files
# - Remove TASK-001 temporary Kubernetes Pods
# - Remove Python cache files
#
# THIS SCRIPT DOES NOT TOUCH
# --------------------------
# - /data/spark/phase3c
# - Original Synthea source CSV
# - Historical S3 Landing data
# - V2 S3 payload / manifest
# - PostgreSQL
# - OMOP CDM
# - Stable ID maps
# - Kubernetes Secrets
# - PVC / PV
# - Git-tracked source code
#
# Future steps may add OPTIONAL persistent cleanup modes.
# Persistent cleanup must NEVER become the default behavior.
# ============================================================


PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

EXPECTED_PROJECT_ROOT="/data/spark/healthcare-data-platform"

RUNTIME_ROOT="${PROJECT_ROOT}/runtime"
REPORT_ROOT="${RUNTIME_ROOT}/reports/task001"
WORK_ROOT="${RUNTIME_ROOT}/work"
ARCHIVE_ROOT="${RUNTIME_ROOT}/archive/task001"

S3_NAMESPACE="dw-spark"

UTC_NOW="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE_DIR="${ARCHIVE_ROOT}/reset-${UTC_NOW}"


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 00"
echo "Reset local runtime state"
echo "============================================================"
echo


# ============================================================
# 1. Safety guard
# ============================================================

echo "[1/7] Safety checks..."

if [[ "${PROJECT_ROOT}" != "${EXPECTED_PROJECT_ROOT}" ]]; then
    echo "ERROR:"
    echo "Unexpected PROJECT_ROOT:"
    echo "  ${PROJECT_ROOT}"
    echo
    echo "Expected:"
    echo "  ${EXPECTED_PROJECT_ROOT}"
    exit 1
fi


if [[ ! -d "${PROJECT_ROOT}" ]]; then
    echo "ERROR: project root does not exist:"
    echo "  ${PROJECT_ROOT}"
    exit 1
fi


if [[ ! -d "${PROJECT_ROOT}/.git" ]]; then
    echo "ERROR:"
    echo "Git repository not found:"
    echo "  ${PROJECT_ROOT}/.git"
    exit 1
fi


if [[ ! -d /data/spark/phase3c ]]; then
    echo "ERROR:"
    echo "Protected legacy baseline is missing:"
    echo "  /data/spark/phase3c"
    exit 1
fi


echo "PASS: project safety guards"
echo


# ============================================================
# 2. Show reset scope
# ============================================================

echo "[2/7] Reset scope..."
echo
echo "Will reset:"
echo "  ${REPORT_ROOT}"
echo "  ${WORK_ROOT}/task001*"
echo "  TASK-001 temporary Kubernetes Pods"
echo "  Python __pycache__"
echo
echo "Will preserve:"
echo "  /data/spark/phase3c"
echo "  source CSV"
echo "  S3 data"
echo "  PostgreSQL / OMOP"
echo "  Secrets"
echo "  PVC/PV"
echo "  Git source"
echo


# ============================================================
# 3. Archive current reports
# ============================================================

echo "[3/7] Archiving current reports..."

mkdir -p \
    "${REPORT_ROOT}" \
    "${WORK_ROOT}" \
    "${ARCHIVE_ROOT}"


REPORT_FILE_COUNT="$(
    find "${REPORT_ROOT}" \
        -type f \
        2>/dev/null \
        | wc -l \
        | tr -d ' '
)"


if [[ "${REPORT_FILE_COUNT}" -gt 0 ]]; then

    mkdir -p \
        "${ARCHIVE_DIR}/reports"

    cp -a \
        "${REPORT_ROOT}/." \
        "${ARCHIVE_DIR}/reports/"

    echo "Archived ${REPORT_FILE_COUNT} report file(s):"
    echo "  ${ARCHIVE_DIR}/reports"

else

    echo "No previous reports to archive."

fi

echo


# ============================================================
# 4. Clear TASK-001 runtime reports/work
# ============================================================

echo "[4/7] Clearing local TASK-001 runtime..."

rm -rf \
    "${REPORT_ROOT}"

mkdir -p \
    "${REPORT_ROOT}"


find "${WORK_ROOT}" \
    -mindepth 1 \
    -maxdepth 1 \
    -name 'task001*' \
    -exec rm -rf -- {} +


echo "PASS: runtime reset"
echo


# ============================================================
# 5. Remove TASK-001 temporary Kubernetes Pods
# ============================================================

echo "[5/7] Cleaning TASK-001 temporary Kubernetes Pods..."

if kubectl get namespace "${S3_NAMESPACE}" >/dev/null 2>&1; then

    PODS="$(
        kubectl get pod \
            -n "${S3_NAMESPACE}" \
            -l app=healthcare-task001 \
            -o name \
            2>/dev/null \
            || true
    )"

    if [[ -n "${PODS}" ]]; then

        echo "${PODS}"

        kubectl delete \
            -n "${S3_NAMESPACE}" \
            ${PODS} \
            --ignore-not-found=true

    else

        echo "No TASK-001 temporary Pods found."

    fi

else

    echo "WARN:"
    echo "Namespace ${S3_NAMESPACE} not available."
    echo "Skipping temporary Pod cleanup."

fi

echo


# ============================================================
# 6. Remove local Python cache
# ============================================================

echo "[6/7] Cleaning Python cache..."

find "${PROJECT_ROOT}" \
    -type d \
    -name '__pycache__' \
    -prune \
    -exec rm -rf -- {} + \
    2>/dev/null \
    || true

find "${PROJECT_ROOT}" \
    -type f \
    \( -name '*.pyc' -o -name '*.pyo' \) \
    -delete \
    2>/dev/null \
    || true


echo "PASS: Python cache clean"
echo


# ============================================================
# 7. Validate reset result
# ============================================================

echo "[7/7] Reset validation..."

echo
echo "Git branch:"
git -C "${PROJECT_ROOT}" \
    branch --show-current

echo

echo "Git working tree:"
git -C "${PROJECT_ROOT}" \
    status --short

echo

echo "Current TASK-001 reports:"
find "${REPORT_ROOT}" \
    -maxdepth 2 \
    -type f \
    -print \
    2>/dev/null \
    || true

echo

echo "Current TASK-001 work directories:"
find "${WORK_ROOT}" \
    -mindepth 1 \
    -maxdepth 1 \
    -name 'task001*' \
    -print \
    2>/dev/null \
    || true

echo

echo "Protected Phase3C baseline:"
echo "  /data/spark/phase3c"

echo

echo "IMPORTANT:"
echo "S3 persistent data was NOT modified."
echo "PostgreSQL / OMOP was NOT modified."

echo
echo "STEP00=PASS"
echo "LOCAL_RUNTIME_RESET=PASS"
echo "S3_RESET=NOT_RUN"
echo "DATABASE_RESET=NOT_RUN"
echo "LEGACY_PHASE3C_TOUCHED=NO"
echo "============================================================"
