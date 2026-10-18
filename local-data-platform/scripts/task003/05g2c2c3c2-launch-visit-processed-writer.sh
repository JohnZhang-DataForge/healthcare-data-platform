#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

BASE="$ROOT/runtime/reports/task003/step05"

C3B_RUNNER="$ROOT/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh"

PERMIT_RUNNER="$ROOT/scripts/task003/05g2c2c3c-issue-write-permit.sh"

BUNDLE_RUNNER="$ROOT/scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh"

REPORT=''

RUNTIME_CONFIGMAP_CREATED=NO
SPARK_APPLICATION_SUBMITTED=NO

echo '#### TASK003 STEP05G2C2C3C2 ATOMIC WRITER LAUNCH OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || {
    echo "ATOMIC_LAUNCH_REPORT=$REPORT"
  }

  echo "RUNTIME_CONFIGMAP_CREATED=$RUNTIME_CONFIGMAP_CREATED"
  echo "SPARK_APPLICATION_SUBMITTED=$SPARK_APPLICATION_SUBMITTED"

  echo 'AUTOMATIC_RESERVATION_DELETE=NO'
  echo 'AUTOMATIC_RUNTIME_CONFIGMAP_DELETE=NO'
  echo 'AUTOMATIC_SPARKAPPLICATION_DELETE=NO'

  echo "ATOMIC_LAUNCH_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3C2 ATOMIC WRITER LAUNCH OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 PROCESSED_RUN_ID C3A_REPORT_DIR F2_RUN_STATE"
  exit 2
}

RUN_ID="$1"
C3A_REPORT="$2"
F2_STATE="$3"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && \
   "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

for cmd in \
  kubectl \
  python3 \
  sha256sum \
  git
do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"
    exit 2
  }
done

for path in \
  "$C3B_RUNNER" \
  "$PERMIT_RUNNER" \
  "$BUNDLE_RUNNER" \
  "$C3A_REPORT/run-state.json" \
  "$F2_STATE"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: prerequisite missing or unsafe: $path"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/writer-atomic-launch.XXXXXXXX"
)

# ============================================================
# 1. Verify source tree / Git safety state
# ============================================================

echo '=== 1. Verify execution prerequisites ==='

cd "$ROOT"

git rev-parse \
  --is-inside-work-tree \
  >/dev/null

echo "CURRENT_GIT_HEAD=$(git rev-parse HEAD)"

python3 - \
  "$C3A_REPORT/run-state.json" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_C3A'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
run_id = sys.argv[2]
report = Path(sys.argv[3])

state = json.loads(
    state_path.read_bytes()
)

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G2C2C3A',
    'RESERVATION_ACQUIRED',
)

assert state['run_id'] == run_id

assert (
    state['reservation_created_by_k8s_create']
    is True
)

assert (
    state['reservation_verified']
    is True
)

assert (
    state['write_authorized']
    is False
)

assert (
    state['spark_application_submitted']
    is False
)

(report / 'reservation-name.txt').write_text(
    state['reservation_name'] + '\n'
)

(report / 'reservation-uid.txt').write_text(
    state['reservation_uid'] + '\n'
)

(report / 'reservation-resource-version.txt').write_text(
    state['reservation_resource_version'] + '\n'
)

print('C3A_STATE=PASS')
print(
    'RESERVATION_NAME='
    + state['reservation_name']
)
print(
    'RESERVATION_UID='
    + state['reservation_uid']
)
print(
    'RESERVATION_RESOURCE_VERSION='
    + state['reservation_resource_version']
)
PY_C3A

LOCK=$(
  tr -d '\r\n' \
    < "$REPORT/reservation-name.txt"
)

EXPECTED_UID=$(
  tr -d '\r\n' \
    < "$REPORT/reservation-uid.txt"
)

EXPECTED_RV=$(
  tr -d '\r\n' \
    < "$REPORT/reservation-resource-version.txt"
)

[[ "$LOCK" =~ ^visit-proc-lock-[0-9a-f]{32}$ ]] || {
  echo 'ERROR: unsafe Reservation name'
  exit 1
}

echo 'EXECUTION_PREREQUISITES=PASS'

# ============================================================
# 2. Verify live Reservation before refreshing evidence
# ============================================================

echo '=== 2. Verify live Reservation before fresh preflight ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/live-reservation-before.json"

python3 - \
  "$REPORT/live-reservation-before.json" \
  "$EXPECTED_UID" \
  "$EXPECTED_RV" \
  <<'PY_LOCK1'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

uid = sys.argv[2]
rv = sys.argv[3]

assert live['apiVersion'] == 'v1'
assert live['kind'] == 'ConfigMap'
assert live.get('immutable') is True

assert live['metadata']['uid'] == uid
assert live['metadata']['resourceVersion'] == rv

print('PRELAUNCH_LIVE_RESERVATION=PASS')
PY_LOCK1

# ============================================================
# 3. Refresh C3B IMMEDIATELY before Permit issuance
# ============================================================

echo '=== 3. Refresh post-lock S3 and Person evidence ==='

set +e

bash "$C3B_RUNNER" \
  "$RUN_ID" \
  "$C3A_REPORT" \
  2>&1 \
  | tee "$REPORT/c3b-refresh.log"

PIPE_RC=${PIPESTATUS[0]}

set -e

[[ "$PIPE_RC" -eq 0 ]] || {
  echo "ERROR: fresh C3B failed with exit=$PIPE_RC"
  exit "$PIPE_RC"
}

C3B_REPORT=$(
  awk -F= \
    '/^POSTLOCK_REPORT=/{value=$2} END{print value}' \
    "$REPORT/c3b-refresh.log"
)

[[ -n "$C3B_REPORT" ]] || {
  echo 'ERROR: unable to locate fresh C3B report'
  exit 1
}

[[ -s "$C3B_REPORT/run-state.json" ]] || {
  echo 'ERROR: fresh C3B state missing'
  exit 1
}

[[ -s "$C3B_REPORT/fresh-s3-listing.json" ]] || {
  echo 'ERROR: fresh S3 listing missing'
  exit 1
}

[[ -s "$C3B_REPORT/person-map-snapshot.json" ]] || {
  echo 'ERROR: fresh Person snapshot missing'
  exit 1
}

echo "FRESH_C3B_REPORT=$C3B_REPORT"
echo 'FRESH_POSTLOCK_PREFLIGHT=PASS'

# ============================================================
# 4. Immediately issue short-lived Permit
# ============================================================

echo '=== 4. Issue short-lived single-write Permit ==='

set +e

bash "$PERMIT_RUNNER" \
  "$RUN_ID" \
  "$C3A_REPORT" \
  "$C3B_REPORT" \
  2>&1 \
  | tee "$REPORT/write-permit.log"

PIPE_RC=${PIPESTATUS[0]}

set -e

[[ "$PIPE_RC" -eq 0 ]] || {
  echo "ERROR: Permit issuance failed with exit=$PIPE_RC"
  exit "$PIPE_RC"
}

PERMIT_REPORT=$(
  awk -F= \
    '/^WRITE_PERMIT_REPORT=/{value=$2} END{print value}' \
    "$REPORT/write-permit.log"
)

[[ -n "$PERMIT_REPORT" ]] || {
  echo 'ERROR: unable to locate Permit report'
  exit 1
}

PERMIT="$PERMIT_REPORT/write-permit.json"

[[ -s "$PERMIT" && ! -L "$PERMIT" ]] || {
  echo 'ERROR: Permit artifact missing'
  exit 1
}

echo "WRITE_PERMIT_REPORT=$PERMIT_REPORT"
echo "WRITE_PERMIT_FILE=$PERMIT"

python3 - "$PERMIT" <<'PY_PERMIT'
import json
import sys
from pathlib import Path

permit = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert permit['status'] == 'AUTHORIZED_FOR_SINGLE_WRITE'
assert permit['write_authorized'] is True
assert permit['fresh_s3_relist_passed'] is True
assert permit['fresh_prefix_classification'] == 'EMPTY'
assert permit['ttl_seconds'] == 180

print('WRITE_PERMIT_VALIDATED=PASS')
print('WRITE_AUTHORIZED=YES')
print(
    'PERSON_MAP_FINGERPRINT='
    + permit['person_map_fingerprint']
)
PY_PERMIT

# ============================================================
# 5. Immediately build immutable Runtime Bundle
# ============================================================

echo '=== 5. Build Runtime ConfigMap and SparkApplication files ==='

set +e

bash "$BUNDLE_RUNNER" \
  "$F2_STATE" \
  "$RUN_ID" \
  "$C3B_REPORT/fresh-s3-listing.json" \
  "$PERMIT" \
  2>&1 \
  | tee "$REPORT/runtime-bundle.log"

PIPE_RC=${PIPESTATUS[0]}

set -e

[[ "$PIPE_RC" -eq 0 ]] || {
  echo "ERROR: Runtime Bundle failed with exit=$PIPE_RC"
  exit "$PIPE_RC"
}

BUNDLE_DIR=$(
  awk -F= \
    '/^RUNTIME_BUNDLE_DIR=/{value=$2} END{print value}' \
    "$REPORT/runtime-bundle.log"
)

[[ -n "$BUNDLE_DIR" ]] || {
  echo 'ERROR: unable to locate Runtime Bundle directory'
  exit 1
}

CONFIGMAP_FILE="$BUNDLE_DIR/runtime-configmap.json"
SPARK_FILE="$BUNDLE_DIR/sparkapplication.yaml"
BUNDLE_STATE="$BUNDLE_DIR/bundle-state.json"

for path in \
  "$CONFIGMAP_FILE" \
  "$SPARK_FILE" \
  "$BUNDLE_STATE"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: Runtime Bundle artifact missing: $path"
    exit 1
  }
done

echo "RUNTIME_BUNDLE_DIR=$BUNDLE_DIR"

# ============================================================
# 6. Validate generated bundle and extract object names
# ============================================================

echo '=== 6. Validate Runtime Bundle before Kubernetes mutation ==='

python3 - \
  "$BUNDLE_STATE" \
  "$CONFIGMAP_FILE" \
  "$SPARK_FILE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_BUNDLE'
import hashlib
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
config_path = Path(sys.argv[2])
spark_path = Path(sys.argv[3])
run_id = sys.argv[4]
report = Path(sys.argv[5])


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


state_bytes = state_path.read_bytes()
config_bytes = config_path.read_bytes()
spark_bytes = spark_path.read_bytes()

state = json.loads(state_bytes)
config = json.loads(config_bytes)

assert state['task'] == 'TASK-003'
assert state['step'] == 'STEP-05G2C2C2B2'
assert state['status'] == 'PREPARED_NOT_CREATED'
assert state['run_id'] == run_id

assert state['runtime_configmap_sha256'] == sha(config_bytes)
assert state['spark_application_sha256'] == sha(spark_bytes)

assert state['configmap_created'] is False
assert state['spark_application_submitted'] is False

assert config['apiVersion'] == 'v1'
assert config['kind'] == 'ConfigMap'
assert config['immutable'] is True
assert config['metadata']['namespace'] == 'dw-spark'

cm_name = config['metadata']['name']
app_name = state['spark_application_name']

assert cm_name == state['runtime_configmap_name']

(report / 'runtime-configmap-name.txt').write_text(
    cm_name + '\n'
)

(report / 'sparkapplication-name.txt').write_text(
    app_name + '\n'
)

print('RUNTIME_BUNDLE_VALIDATION=PASS')
print('RUNTIME_CONFIGMAP_NAME=' + cm_name)
print('SPARK_APPLICATION_NAME=' + app_name)
PY_BUNDLE

RUNTIME_CM=$(
  tr -d '\r\n' \
    < "$REPORT/runtime-configmap-name.txt"
)

SPARK_APP=$(
  tr -d '\r\n' \
    < "$REPORT/sparkapplication-name.txt"
)

[[ "$RUNTIME_CM" =~ ^visit-proc-runtime-[0-9a-f]{24}$ ]] || {
  echo 'ERROR: unsafe Runtime ConfigMap name'
  exit 1
}

[[ "$SPARK_APP" =~ ^visit-proc-write-[0-9a-f]{20}$ ]] || {
  echo 'ERROR: unsafe SparkApplication name'
  exit 1
}

kubectl create \
  --dry-run=client \
  -f "$CONFIGMAP_FILE" \
  >/dev/null

kubectl create \
  --dry-run=client \
  -f "$SPARK_FILE" \
  >/dev/null

echo 'KUBERNETES_CLIENT_DRY_RUN=PASS'

# ============================================================
# 7. Reverify live Reservation immediately before CREATE
# ============================================================

echo '=== 7. Final live Reservation verification ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/live-reservation-final.json"

python3 - \
  "$REPORT/live-reservation-final.json" \
  "$EXPECTED_UID" \
  "$EXPECTED_RV" \
  <<'PY_LOCK2'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['uid'] == sys.argv[2]

assert (
    live['metadata']['resourceVersion']
    == sys.argv[3]
)

assert live.get('immutable') is True

print('FINAL_LIVE_RESERVATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK2

# ============================================================
# 8. Ensure generated runtime objects do NOT already exist
# ============================================================

echo '=== 8. Check runtime object conflicts ==='

if kubectl -n dw-spark \
    get configmap "$RUNTIME_CM" \
    >/dev/null 2>&1
then
  echo 'ERROR: Runtime ConfigMap already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

if kubectl -n dw-spark \
    get sparkapplication "$SPARK_APP" \
    >/dev/null 2>&1
then
  echo 'ERROR: SparkApplication already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

echo 'RUNTIME_OBJECT_CONFLICTS=NONE'

# ============================================================
# 9. CREATE immutable Runtime ConfigMap
# ============================================================

echo '=== 9. Create immutable Runtime ConfigMap ==='

if kubectl create \
    -f "$CONFIGMAP_FILE" \
    -o json \
    > "$REPORT/runtime-configmap-create.json" \
    2> "$REPORT/runtime-configmap-create.stderr"
then
  RUNTIME_CONFIGMAP_CREATED=YES
else
  echo 'RUNTIME_CONFIGMAP_CREATE=FAIL'
  sed -n '1,40p' \
    "$REPORT/runtime-configmap-create.stderr"

  echo 'AUTOMATIC_RUNTIME_CONFIGMAP_DELETE=NO'
  exit 1
fi

echo 'RUNTIME_CONFIGMAP_CREATE=PASS'

# ============================================================
# 10. CREATE SparkApplication
# ============================================================

echo '=== 10. Submit SparkApplication ==='

if kubectl create \
    -f "$SPARK_FILE" \
    -o json \
    > "$REPORT/sparkapplication-create.json" \
    2> "$REPORT/sparkapplication-create.stderr"
then
  SPARK_APPLICATION_SUBMITTED=YES
else
  echo 'SPARK_APPLICATION_CREATE=FAIL'
  sed -n '1,60p' \
    "$REPORT/sparkapplication-create.stderr"

  echo 'AUTOMATIC_RUNTIME_CONFIGMAP_DELETE=NO'
  echo 'AUTOMATIC_RESERVATION_DELETE=NO'

  exit 1
fi

echo 'SPARK_APPLICATION_CREATE=PASS'

# ============================================================
# 11. Verify live SparkApplication identity
# ============================================================

echo '=== 11. Verify submitted SparkApplication ==='

kubectl -n dw-spark \
  get sparkapplication "$SPARK_APP" \
  -o json \
  > "$REPORT/sparkapplication-live.json"

python3 - \
  "$REPORT/sparkapplication-create.json" \
  "$REPORT/sparkapplication-live.json" \
  "$SPARK_APP" \
  <<'PY_APP'
import json
import sys
from pathlib import Path

created = json.loads(
    Path(sys.argv[1]).read_bytes()
)

live = json.loads(
    Path(sys.argv[2]).read_bytes()
)

name = sys.argv[3]

assert created['metadata']['name'] == name
assert live['metadata']['name'] == name

assert (
    created['metadata']['uid']
    == live['metadata']['uid']
)

uid = live['metadata']['uid']

assert isinstance(uid, str)
assert len(uid) >= 8

print('SPARK_APPLICATION_LIVE=PASS')
print('SPARK_APPLICATION_UID=' + uid)
PY_APP

# ============================================================
# 12. Persist atomic-launch evidence
# ============================================================

echo '=== 12. Persist launch evidence ==='

python3 - \
  "$REPORT" \
  "$RUN_ID" \
  "$C3A_REPORT/run-state.json" \
  "$C3B_REPORT/run-state.json" \
  "$PERMIT" \
  "$BUNDLE_STATE" \
  "$RUNTIME_CM" \
  "$SPARK_APP" \
  <<'PY_STATE'
import hashlib
import json
import sys

from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


report = Path(sys.argv[1])

run_id = sys.argv[2]

c3a = Path(sys.argv[3])
c3b = Path(sys.argv[4])
permit = Path(sys.argv[5])
bundle = Path(sys.argv[6])

runtime_cm = sys.argv[7]
spark_app = sys.argv[8]

app_live = json.loads(
    (
        report
        / 'sparkapplication-live.json'
    ).read_bytes()
)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G2C2C3C2',

    'status':
        'SPARK_APPLICATION_SUBMITTED',

    'run_id':
        run_id,

    'c3a_state_sha256':
        sha(c3a),

    'fresh_c3b_state_sha256':
        sha(c3b),

    'write_permit_sha256':
        sha(permit),

    'runtime_bundle_state_sha256':
        sha(bundle),

    'runtime_configmap_name':
        runtime_cm,

    'runtime_configmap_created':
        True,

    'spark_application_name':
        spark_app,

    'spark_application_uid':
        app_live['metadata']['uid'],

    'spark_application_submitted':
        True,

    'reservation_released':
        False,

    'automatic_cleanup':
        False,

    # Submission does NOT claim persistence success.
    'candidate_published':
        False,

    's3_write_verified':
        False,

    'postgresql_write':
        False,

    'submitted_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

target = report / 'run-state.json'

with target.open('xb') as handle:
    handle.write(
        (
            json.dumps(
                state,
                indent=2,
                sort_keys=True,
            )
            + '\n'
        ).encode('utf-8')
    )

print('ATOMIC_LAUNCH_STATE=PASS')
print('ATOMIC_LAUNCH_STATE_FILE=' + str(target))
print('ATOMIC_LAUNCH_STATE_SHA256=' + sha(target))
print('CANDIDATE_PUBLISHED=NOT_YET_VERIFIED')
print('S3_WRITE_VERIFIED=NO')
print('DATABASE_WRITE=NO')
PY_STATE

echo 'STEP05G2C2C3C2_ATOMIC_LAUNCH=PASS'

echo "RUNTIME_CONFIGMAP_NAME=$RUNTIME_CM"
echo "SPARK_APPLICATION_NAME=$SPARK_APP"

echo 'RESERVATION_STILL_HELD=YES'

echo 'CANDIDATE_PUBLISHED=NOT_YET_VERIFIED'
echo 'S3_WRITE_VERIFIED=NO'
echo 'DATABASE_WRITE=NO'
