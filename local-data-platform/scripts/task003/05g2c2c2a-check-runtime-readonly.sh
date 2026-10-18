#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT=''

echo '#### TASK003 STEP05G2C2C2A RUNTIME READONLY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$REPORT" ]] || echo "RUNTIME_PREFLIGHT_REPORT=$REPORT"
  echo "PREFLIGHT_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2A RUNTIME READONLY OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 2 ]] || {
  echo "Usage: $0 STEP05F2_STATE PROCESSED_RUN_ID"
  exit 2
}

F2="$1"
RUN_ID="$2"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

[[ -s "$F2" && ! -L "$F2" ]] || {
  echo 'ERROR: F2 state missing or symlink'
  exit 2
}

for command_name in kubectl python3 sha256sum; do
  command -v "$command_name" >/dev/null || {
    echo "ERROR: missing $command_name"
    exit 2
  }
done

BASE="$ROOT/runtime/reports/task003/step05"
PLAN="$BASE/processed-plans/$RUN_ID/plan.json"
INTENT="$BASE/processed-intents/$RUN_ID/write-intent.json"
RESERVATION="$BASE/writer-reservations/$RUN_ID/reservation-create.json"
DRIVER="$ROOT/spark/apps/visit/run_visit_processed_writer.py"
CORE="$ROOT/spark/apps/visit/processed_visit_writer_core.py"

for path in "$PLAN" "$INTENT" "$RESERVATION" "$DRIVER" "$CORE"; do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing source: $path"
    exit 2
  }
done

mkdir -p "$BASE"

REPORT=$(mktemp -d "$BASE/writer-runtime-readonly.XXXXXXXX")

echo '=== 1. Verify pinned evidence and future mount inventory ==='

python3 - "$ROOT" "$F2" "$PLAN" "$INTENT" "$RESERVATION" "$REPORT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root, f2path, planpath, intentpath, lockpath, report = map(
    Path, sys.argv[1:]
)

def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('unsafe source: ' + str(path))
    return path.read_bytes()

def digest(data):
    return hashlib.sha256(data).hexdigest()

f2bytes, planbytes, intentbytes, lockbytes = map(
    read, (f2path, planpath, intentpath, lockpath)
)

f2, plan, intent, lock = map(
    json.loads, (f2bytes, planbytes, intentbytes, lockbytes)
)

assert (f2['task'], f2['step'], f2['status']) == (
    'TASK-003', 'STEP-05F2', 'PASS'
)
assert (plan['task'], plan['step'], plan['status']) == (
    'TASK-003', 'STEP-05G1', 'PLANNED'
)
assert (intent['task'], intent['step'], intent['status']) == (
    'TASK-003', 'STEP-05G2C1', 'PREFLIGHT_SNAPSHOT_ONLY'
)

assert plan['source_f2_evidence_sha256'] == digest(f2bytes)
assert intent['step05f2_sha256'] == digest(f2bytes)
assert intent['plan_sha256'] == digest(planbytes)
assert intent['write_authorized'] is False

assert lock['apiVersion'] == 'v1'
assert lock['kind'] == 'ConfigMap'
assert lock['immutable'] is True
assert lock['metadata']['namespace'] == 'dw-spark'

record = json.loads(lock['data']['reservation.json'])

assert record['write_intent_sha256'] == digest(intentbytes)
assert record['plan_sha256'] == digest(planbytes)
assert record['run_id'] == plan['run_id'] == intent['run_id']
assert record['write_authorized'] is False
assert record['mode'] == 'EXCLUSIVE_CREATE_ONLY'

from_paths = {
    'map_encounter_to_visit_candidate.py':
        'spark/apps/visit/map_encounter_to_visit_candidate.py',
    'validate_visit_candidate_preflight.py':
        'spark/apps/visit/validate_visit_candidate_preflight.py',
    'canonical_gate.py':
        'spark/common/canonical_gate.py',
    'visit_candidate_rules.py':
        'apps/task003/visit_candidate_rules.py',
    'verify_encounter_remote_metadata.py':
        'apps/task003/verify_encounter_remote_metadata.py',
    'resolve_approved_encounter_raw.py':
        'apps/task003/resolve_approved_encounter_raw.py',
    'encounter-v1.json':
        'spark/contracts/canonical/encounter-v1.json',
    'visit-class-v1.json':
        'spark/contracts/omop/visit-class-v1.json',
    'visit-candidate-v1.json':
        'spark/contracts/omop/visit-candidate-v1.json',
}

expected = f2['input']['mounted_file_sha256']

assert set(expected) == set(from_paths), 'F2 mount inventory drift'

total_size = 0

for name, relative in from_paths.items():
    data = read(root / relative)
    assert digest(data) == expected[name], (
        'F2 source SHA drift: ' + relative
    )
    total_size += len(data)

for relative in (
    'spark/apps/visit/run_visit_processed_writer.py',
    'spark/apps/visit/processed_visit_writer_core.py',
):
    total_size += len(read(root / relative))

total_size += sum(map(
    len, (f2bytes, planbytes, intentbytes, lockbytes)
))

# Preliminary ConfigMap budget. The actual runtime bundle
# will be checked again after the permit is generated.
assert total_size < 650000, (
    'projected ConfigMap bundle too large'
)

name = lock['metadata']['name']

assert name.startswith('visit-proc-lock-')
assert len(name) <= 63

(report / 'lock-name.txt').write_text(name + '\n')
(report / 'source-size.txt').write_text(str(total_size) + '\n')

print('PINNED_SOURCE_INVENTORY=PASS')
print('F2_MOUNTED_SOURCE_COUNT=' + str(len(from_paths)))
print('PRELIMINARY_BUNDLE_BYTES=' + str(total_size))
print('RESERVATION_NAME=' + name)
print('LOCK_ACQUIRED=NO')
PY

LOCK=$(cat "$REPORT/lock-name.txt")

echo '=== 2. Kubernetes ServiceAccount and credential references ==='

kubectl -n dw-spark get serviceaccount spark-job \
  -o json > "$REPORT/serviceaccount.json"

python3 - "$REPORT/serviceaccount.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    sa = json.load(f)

assert sa['metadata']['name'] == 'spark-job'
assert sa['metadata']['namespace'] == 'dw-spark'
assert sa.get('automountServiceAccountToken') is not False, (
    'SA token automount disabled'
)

print('SPARK_JOB_SERVICEACCOUNT=PASS')
print('SERVICEACCOUNT_TOKEN_AUTOMOUNT_NOT_DISABLED=PASS')
PY

# Verify Secret references without printing credential values.
for secret in dw-spark-s3-secret dw-spark-omop-secret; do
  kubectl -n dw-spark get secret "$secret" -o name >/dev/null
  echo "SECRET_REFERENCE_EXISTS=$secret"
done

echo '=== 3. Named reservation RBAC authorization ==='

SA='system:serviceaccount:dw-spark:spark-job'

# This is a read-only authorization review.
if kubectl auth can-i get "configmaps/$LOCK" \
    --as="$SA" \
    -n dw-spark \
    > "$REPORT/named-configmap-can-i.txt" \
    2> "$REPORT/named-configmap-can-i.stderr"; then
  AUTH_RC=0
else
  AUTH_RC=$?
fi

ANSWER=$(tr -d '[:space:]' < "$REPORT/named-configmap-can-i.txt")

if [[ "$AUTH_RC" -eq 0 && "$ANSWER" == yes ]]; then
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=PASS'
elif [[ "$ANSWER" == no ]]; then
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=NO'
  echo 'RUNTIME_PREFLIGHT=STOP_RBAC'
  echo 'NO_RBAC_CHANGED=YES'
  exit 3
else
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=CHECK_FAILED'
  echo "AUTH_EXIT_CODE=$AUTH_RC"
  echo 'ERROR: Kubernetes authorization review failed'
  sed -n '1,20p' "$REPORT/named-configmap-can-i.stderr"
  exit 1
fi

echo '=== 4. Existing lock conflict check ==='

if kubectl -n dw-spark get configmap "$LOCK" \
    -o name \
    > "$REPORT/reservation-existing.txt" \
    2> "$REPORT/reservation-get.stderr"; then

  echo 'RESERVATION_ALREADY_EXISTS=YES'
  echo 'RUNTIME_PREFLIGHT=STOP_EXISTING_LOCK'
  exit 4

else
  if grep -Eqi 'notfound|not found' \
      "$REPORT/reservation-get.stderr"; then

    echo 'RESERVATION_ALREADY_EXISTS=NO'

  else
    echo 'ERROR: cannot determine live reservation existence'
    exit 1
  fi
fi

echo 'RUNTIME_PREFLIGHT_READONLY=PASS'
echo 'K8S_RESERVATION_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
