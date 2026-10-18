#!/usr/bin/env bash
set -Eeuo pipefail

echo "#### TASK003 STEP00 RESET OUTPUT BEGIN ####"

CACHE_LIST=""
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${CACHE_LIST}" ]]; then
        rm -f -- "${CACHE_LIST}"
    fi
    echo "RESET_EXIT_CODE=${rc}"
    echo "#### TASK003 STEP00 RESET OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

ROOT="/data/spark/healthcare-data-platform"
MODE="apply"

if [[ "$#" -eq 1 && "$1" == "--dry-run" ]]; then
    MODE="dry-run"
elif [[ "$#" -ne 0 ]]; then
    echo "Usage: $0 [--dry-run]"
    exit 2
fi

[[ -d "${ROOT}" ]] || {
    echo "ERROR: project missing"
    exit 1
}

mkdir -p "${ROOT}/runtime/work"
CACHE_LIST="$(mktemp "${ROOT}/runtime/work/task003-cache-list.XXXXXX")"

# Step03/04 reports are active lineage and recovery inputs.
# Preserve all runtime reports and all Kubernetes resources.
# Utility Pods are cleaned up by their owning runner's EXIT trap.
for relative in apps/task003 spark/apps/visit tests/task003; do
    directory="${ROOT}/${relative}"
    [[ -d "${directory}" ]] || continue

    [[ "$(realpath "${directory}")" == "${directory}" ]] || {
        echo "ERROR: unexpected symlinked cache scope: ${directory}"
        exit 1
    }

    find -P "${directory}" \
      -type d -name __pycache__ -prune -print0 >> "${CACHE_LIST}"
done

count=0
while IFS= read -r -d '' cache; do
    [[ "$(realpath "${cache}")" == "${cache}" ]] || {
        echo "ERROR: unexpected cache path: ${cache}"
        exit 1
    }

    if [[ "${MODE}" == "dry-run" ]]; then
        echo "WOULD_REMOVE_CACHE=${cache}"
    else
        rm -rf -- "${cache}"
        echo "REMOVED_CACHE=${cache}"
    fi

    count=$((count + 1))
done < "${CACHE_LIST}"

echo "MODE=${MODE}"
echo "CACHE_DIRECTORIES=${count}"
echo "TASK003_CACHE_RESET=PASS"
echo "RUNTIME_REPORTS_PRESERVED=YES"
echo "RECOVERY_EVIDENCE_PRESERVED=YES"
echo "KUBERNETES_WRITE=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
