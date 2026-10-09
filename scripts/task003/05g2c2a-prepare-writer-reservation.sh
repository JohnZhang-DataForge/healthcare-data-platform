#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C2A RESERVATION PREPARATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2A RESERVATION PREPARATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 1 ]] || {
  echo 'Usage: $0 PROCESSED_RUN_ID'
  exit 2
}

[[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$1" != '.' && "$1" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

python3 "$ROOT/apps/task003/build_visit_writer_reservation.py" \
  --root "$ROOT" \
  --run-id "$1"

echo 'STEP05G2C2A_RESERVATION_PREPARED=PASS'
echo 'K8S_RESOURCE_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
