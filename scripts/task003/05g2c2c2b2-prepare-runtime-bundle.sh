#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "BUNDLE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 F2_RUN_STATE PROCESSED_RUN_ID FRESH_S3_LISTING WRITE_PERMIT"
  exit 2
}

PYTHONPATH="$ROOT/apps/task003:$ROOT/spark/apps/visit" \
python3 "$ROOT/apps/task003/build_visit_processed_runtime_bundle.py" \
  --root "$ROOT" \
  --f2-state "$1" \
  --run-id "$2" \
  --fresh-listing "$3" \
  --write-permit "$4"

echo 'RUNTIME_BUNDLE_PREPARED=PASS'
echo 'K8S_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
