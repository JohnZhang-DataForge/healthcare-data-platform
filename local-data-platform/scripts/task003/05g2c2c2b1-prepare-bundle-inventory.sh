#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C2C2B1 BUNDLE INVENTORY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "INVENTORY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2B1 BUNDLE INVENTORY OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 2 ]] || {
  echo "Usage: $0 F2_RUN_STATE PROCESSED_RUN_ID"
  exit 2
}

[[ "$2" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$2" != '.' && "$2" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

PYTHONPATH="$ROOT/apps/task003" \
python3 "$ROOT/apps/task003/prepare_visit_writer_bundle_inventory.py" \
  --root "$ROOT" \
  --f2-state "$1" \
  --run-id "$2"

echo 'BUNDLE_INVENTORY_VERIFIED=PASS'
echo 'RUNTIME_CONFIGMAP_CREATED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
