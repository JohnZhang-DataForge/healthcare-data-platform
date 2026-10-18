#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REPORT=''

echo '#### TASK003 STEP05G2C2C3C WRITE PERMIT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || {
    echo "WRITE_PERMIT_REPORT=$REPORT"
  }

  echo "PERMIT_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3C WRITE PERMIT OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 PROCESSED_RUN_ID C3A_REPORT_DIR C3B_REPORT_DIR"
  exit 2
}

RUN_ID="$1"
C3A_REPORT="$2"
C3B_REPORT="$3"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && \
   "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

BASE="$ROOT/runtime/reports/task003/step05"

SPEC="$BASE/writer-reservations/$RUN_ID/reservation-create.json"

C3A_STATE="$C3A_REPORT/run-state.json"
C3B_STATE="$C3B_REPORT/run-state.json"

for path in \
  "$SPEC" \
  "$C3A_STATE" \
  "$C3B_STATE" \
  "$C3B_REPORT/fresh-s3-listing.json" \
  "$C3B_REPORT/person-map-snapshot.json"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing Permit prerequisite: $path"
    exit 2
  }
done

LOCK=$(
  python3 - "$SPEC" <<'PY'
import json
import sys
from pathlib import Path

spec = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    spec['metadata']['name']
)
PY
)

[[ "$LOCK" =~ ^visit-proc-lock-[0-9a-f]{32}$ ]] || {
  echo 'ERROR: unsafe Reservation name'
  exit 1
}

# Fresh LIVE Kubernetes read immediately before issuance.
LIVE=$(
  mktemp \
    /data/spark/temp_shell/visit-permit-live.XXXXXXXX.json
)

cleanup() {
  rm -f -- "$LIVE"
}

trap 'cleanup' RETURN

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$LIVE"

STAMP=$(date -u +%Y%m%dt%H%M%Sz)

REPORT=$(
  mktemp -d \
    "$BASE/write-permit.${STAMP}.XXXXXXXX"
)

OUTPUT="$REPORT/write-permit.json"

PYTHONPATH="$ROOT/apps/task003:$ROOT/spark/apps/visit" \
python3 "$ROOT/apps/task003/issue_visit_processed_write_permit.py" \
  --root "$ROOT" \
  --run-id "$RUN_ID" \
  --c3a-report "$C3A_REPORT" \
  --c3b-report "$C3B_REPORT" \
  --live-reservation "$LIVE" \
  --ttl-seconds 180 \
  --output "$OUTPUT"

cleanup

echo 'STEP05G2C2C3C_WRITE_PERMIT=PASS'
echo 'RUNTIME_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
