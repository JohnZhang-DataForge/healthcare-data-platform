#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G2C2C3A RESERVATION ACQUIRE SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3A RESERVATION ACQUIRE SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must execute from a saved Bash file'
  exit 2
}

cd "$ROOT"

for rel in \
  apps/task003/build_visit_writer_reservation.py \
  spark/contracts/processed/visit-writer-safety-v1.json
do
  [[ -s "$rel" && ! -L "$rel" ]] || {
    echo "ERROR: prerequisite missing: $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g2c2c3a.XXXXXXXX)

mkdir -p "$STAGE/scripts/task003"

# ============================================================
# Permanent acquisition runner
# ============================================================

cat > "$STAGE/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKPOINT=2342d915281ea94537b7784da4f37d714d50b639

REPORT=''
K8S_CREATED=NO

echo '#### TASK003 STEP05G2C2C3A RESERVATION ACQUIRE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  if [[ -n "$REPORT" ]]; then
    echo "RESERVATION_REPORT=$REPORT"
  fi

  echo "K8S_RESERVATION_CREATED=$K8S_CREATED"

  if [[ "$K8S_CREATED" == YES ]]; then
    echo 'AUTOMATIC_RESERVATION_CLEANUP=NO'
  fi

  echo "ACQUIRE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3A RESERVATION ACQUIRE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 1 ]] || {
  echo "Usage: $0 PROCESSED_RUN_ID"
  exit 2
}

RUN_ID="$1"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && \
   "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

for cmd in kubectl python3 sha256sum git; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"
    exit 2
  }
done

cd "$ROOT"

BASE="$ROOT/runtime/reports/task003/step05"

PLAN="$BASE/processed-plans/$RUN_ID/plan.json"

INTENT="$BASE/processed-intents/$RUN_ID/write-intent.json"

SPEC="$BASE/writer-reservations/$RUN_ID/reservation-create.json"

for path in "$PLAN" "$INTENT" "$SPEC"; do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing immutable evidence: $path"
    exit 2
  }
done

mkdir -p "$BASE"

REPORT=$(
  mktemp -d \
    "$BASE/writer-reservation-live.XXXXXXXX"
)

# ============================================================
# 1. Verify Git safety checkpoint still exists in ancestry
# ============================================================

echo '=== 1. Verify pre-write Git checkpoint ==='

git cat-file -e "${CHECKPOINT}^{commit}"

git merge-base --is-ancestor \
  "$CHECKPOINT" \
  HEAD

echo "PREWRITE_CHECKPOINT=$CHECKPOINT"
echo "CURRENT_HEAD=$(git rev-parse HEAD)"
echo 'PREWRITE_CHECKPOINT_ANCESTRY=PASS'

# ============================================================
# 2. Validate local immutable reservation definition
# ============================================================

echo '=== 2. Validate reservation definition and evidence pins ==='

python3 - \
  "$PLAN" \
  "$INTENT" \
  "$SPEC" \
  "$REPORT" \
  <<'PY_LOCAL'
import hashlib
import json
import sys

from pathlib import Path
from urllib.parse import urlsplit

plan_path = Path(sys.argv[1])
intent_path = Path(sys.argv[2])
spec_path = Path(sys.argv[3])
report = Path(sys.argv[4])


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Unsafe evidence path: ' + str(path)
        )

    return path.read_bytes()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


plan_bytes = read(plan_path)
intent_bytes = read(intent_path)
spec_bytes = read(spec_path)

plan = json.loads(plan_bytes)
intent = json.loads(intent_bytes)
spec = json.loads(spec_bytes)

assert (
    plan['task'],
    plan['step'],
    plan['status'],
) == (
    'TASK-003',
    'STEP-05G1',
    'PLANNED',
)

assert (
    intent['task'],
    intent['step'],
    intent['status'],
) == (
    'TASK-003',
    'STEP-05G2C1',
    'PREFLIGHT_SNAPSHOT_ONLY',
)

assert plan['run_id'] == intent['run_id']

assert intent['plan_sha256'] == sha(plan_bytes)

assert intent['write_authorized'] is False
assert intent['writer_reservation_acquired'] is False

assert plan['persisted'] is False
assert plan['published'] is False
assert plan['s3_write'] is False
assert plan['postgresql_write'] is False
assert plan['visit_ids_allocated'] == 0

assert spec['apiVersion'] == 'v1'
assert spec['kind'] == 'ConfigMap'
assert spec['immutable'] is True

metadata = spec['metadata']

assert metadata['namespace'] == 'dw-spark'

assert metadata['labels']['healthcare-task'] == 'task003'

assert (
    metadata['labels']['healthcare-purpose']
    == 'visit-processed-writer-lock'
)

record = json.loads(
    spec['data']['reservation.json']
)

assert (
    record['reservation_schema']
    == 'task003.visit_processed.writer_reservation.v1'
)

assert record['run_id'] == plan['run_id']

assert (
    record['write_intent_sha256']
    == sha(intent_bytes)
)

assert (
    record['plan_sha256']
    == sha(plan_bytes)
)

assert record['mode'] == 'EXCLUSIVE_CREATE_ONLY'

assert (
    record['on_existing_reservation']
    == 'STOP_MANUAL_RECONCILIATION'
)

assert (
    record['release_policy']
    == 'NO_AUTOMATIC_DELETE'
)

assert (
    record['s3_prefix_must_be_relisted_after_create']
    is True
)

assert record['write_authorized'] is False

parsed = urlsplit(
    plan['base_uri']
)

assert parsed.scheme == 's3'
assert parsed.netloc == 'health-processed'
assert not parsed.query
assert not parsed.fragment

expected_prefix = (
    parsed.path.lstrip('/') + '/'
)

assert record['bucket'] == 'health-processed'
assert record['prefix'] == expected_prefix

scope = (
    record['bucket']
    + '/'
    + record['prefix']
).encode('utf-8')

expected_lock_name = (
    'visit-proc-lock-'
    + hashlib.sha256(scope).hexdigest()[:32]
)

assert (
    metadata['name']
    == expected_lock_name
)

(report / 'reservation-name.txt').write_text(
    metadata['name'] + '\n'
)

(report / 'reservation-spec.json').write_bytes(
    spec_bytes
)

print('LOCAL_RESERVATION_SPEC=PASS')

print(
    'RESERVATION_NAME='
    + metadata['name']
)

print(
    'RESERVATION_SPEC_SHA256='
    + sha(spec_bytes)
)

print(
    'PLAN_SHA256='
    + sha(plan_bytes)
)

print(
    'WRITE_INTENT_SHA256='
    + sha(intent_bytes)
)

print('WRITE_AUTHORIZED=NO')
PY_LOCAL

LOCK=$(
  tr -d '\r\n' \
    < "$REPORT/reservation-name.txt"
)

[[ "$LOCK" =~ ^visit-proc-lock-[0-9a-f]{32}$ ]] || {
  echo 'ERROR: invalid derived reservation name'
  exit 1
}

# ============================================================
# 3. Atomic pre-check
# ============================================================

echo '=== 3. Check for existing reservation ==='

if kubectl -n dw-spark get configmap "$LOCK" \
    -o json \
    > "$REPORT/preexisting-reservation.json" \
    2> "$REPORT/preexisting-reservation.stderr"
then

  echo 'RESERVATION_ALREADY_EXISTS=YES'
  echo 'RESERVATION_ACQUIRE=STOP_MANUAL_RECONCILIATION'
  echo 'WRITE_AUTHORIZED=NO'

  exit 4

else
  if grep -Eqi \
      'notfound|not found' \
      "$REPORT/preexisting-reservation.stderr"
  then

    echo 'RESERVATION_ALREADY_EXISTS=NO'

  else
    echo 'ERROR: unable to determine reservation existence'

    sed -n '1,30p' \
      "$REPORT/preexisting-reservation.stderr"

    exit 1
  fi
fi

# ============================================================
# 4. Atomic Kubernetes CREATE
# ============================================================

echo '=== 4. Atomically create exclusive reservation ==='

if kubectl create \
    -f "$SPEC" \
    -o json \
    > "$REPORT/create-response.json" \
    2> "$REPORT/create.stderr"
then

  K8S_CREATED=YES

else
  echo 'RESERVATION_CREATE=FAIL'

  sed -n '1,40p' \
    "$REPORT/create.stderr"

  echo 'AUTOMATIC_DELETE=NO'

  exit 1
fi

echo 'RESERVATION_CREATE=PASS'

# ============================================================
# 5. Read live ConfigMap back from Kubernetes
# ============================================================

echo '=== 5. Read live reservation from Kubernetes API ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/live-reservation.json"

[[ -s "$REPORT/live-reservation.json" ]] || {
  echo 'ERROR: Kubernetes returned empty live object'
  exit 1
}

echo 'LIVE_RESERVATION_READBACK=PASS'

# ============================================================
# 6. Verify CREATE response + live resource
# ============================================================

echo '=== 6. Verify live UID, resourceVersion and payload ==='

python3 - \
  "$REPORT/reservation-spec.json" \
  "$REPORT/create-response.json" \
  "$REPORT/live-reservation.json" \
  "$PLAN" \
  "$INTENT" \
  "$REPORT" \
  <<'PY_LIVE'
import hashlib
import json
import sys

from datetime import datetime, timezone
from pathlib import Path


paths = [
    Path(value)
    for value in sys.argv[1:6]
]

report = Path(sys.argv[6])


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Unsafe evidence: ' + str(path)
        )

    return path.read_bytes()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


(
    spec_bytes,
    create_bytes,
    live_bytes,
    plan_bytes,
    intent_bytes,
) = [
    read(path)
    for path in paths
]

spec = json.loads(spec_bytes)
created = json.loads(create_bytes)
live = json.loads(live_bytes)
plan = json.loads(plan_bytes)
intent = json.loads(intent_bytes)

name = spec['metadata']['name']
namespace = spec['metadata']['namespace']

for obj, label in (
    (created, 'create response'),
    (live, 'live readback'),
):
    assert obj['apiVersion'] == 'v1', label

    assert obj['kind'] == 'ConfigMap', label

    assert obj['metadata']['name'] == name, label

    assert (
        obj['metadata']['namespace']
        == namespace
    ), label

    assert obj.get('immutable') is True, label

    assert (
        obj['metadata']['labels']['healthcare-task']
        == 'task003'
    ), label

    assert (
        obj['metadata']['labels']['healthcare-purpose']
        == 'visit-processed-writer-lock'
    ), label

    assert (
        obj['data']['reservation.json']
        == spec['data']['reservation.json']
    ), label


uid = live['metadata'].get('uid')

resource_version = live['metadata'].get(
    'resourceVersion'
)

created_uid = created['metadata'].get(
    'uid'
)

created_version = created['metadata'].get(
    'resourceVersion'
)

assert isinstance(uid, str)
assert len(uid) >= 8

assert uid == created_uid

assert isinstance(
    resource_version,
    str,
)

assert resource_version

assert resource_version == created_version

# Current Writer Core expects numeric Kubernetes
# resourceVersion in this cluster.
assert resource_version.isdigit()

record = json.loads(
    live['data']['reservation.json']
)

assert record['run_id'] == plan['run_id']
assert record['write_intent_sha256'] == sha(intent_bytes)
assert record['plan_sha256'] == sha(plan_bytes)
assert record['write_authorized'] is False

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G2C2C3A',

    'status':
        'RESERVATION_ACQUIRED',

    'run_id':
        plan['run_id'],

    'reservation_name':
        name,

    'reservation_uid':
        uid,

    'reservation_resource_version':
        resource_version,

    'reservation_spec_sha256':
        sha(spec_bytes),

    'create_response_sha256':
        sha(create_bytes),

    'live_reservation_sha256':
        sha(live_bytes),

    'plan_sha256':
        sha(plan_bytes),

    'write_intent_sha256':
        sha(intent_bytes),

    'reservation_created_by_k8s_create':
        True,

    'reservation_verified':
        True,

    'fresh_s3_relist_passed':
        False,

    'person_map_fingerprint_captured':
        False,

    'write_permit_issued':
        False,

    'write_authorized':
        False,

    'spark_application_submitted':
        False,

    's3_write':
        False,

    'postgresql_write':
        False,

    'automatic_reservation_cleanup':
        False,

    'verified_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

state_bytes = (
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
).encode('utf-8')

state_path = (
    report / 'run-state.json'
)

with state_path.open('xb') as handle:
    handle.write(
        state_bytes
    )

print('LIVE_RESERVATION_VERIFICATION=PASS')

print(
    'RESERVATION_UID='
    + uid
)

print(
    'RESERVATION_RESOURCE_VERSION='
    + resource_version
)

print(
    'LIVE_RESERVATION_SHA256='
    + sha(live_bytes)
)

print(
    'RESERVATION_STATE_SHA256='
    + sha(state_bytes)
)

print(
    'RESERVATION_STATE_FILE='
    + str(state_path)
)

print('RESERVATION_ACQUIRED=YES')
print('RESERVATION_VERIFIED=YES')

print('FRESH_S3_RELIST_PASSED=NO')

print(
    'PERSON_MAP_FINGERPRINT_CAPTURED=NO'
)

print('WRITE_PERMIT_ISSUED=NO')
print('WRITE_AUTHORIZED=NO')

print('SPARK_APPLICATION_SUBMITTED=NO')
print('S3_WRITE=NO')
print('DATABASE_WRITE=NO')
PY_LIVE

# ============================================================
# 7. Final safety state
# ============================================================

echo '=== 7. Final reservation state ==='

echo "RESERVATION_NAME=$LOCK"

echo 'STEP05G2C2C3A_RESERVATION_ACQUIRE=PASS'

echo 'RESERVATION_RELEASED=NO'
echo 'AUTOMATIC_RESERVATION_CLEANUP=NO'

echo 'RUNTIME_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'

echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ============================================================
# Installer static checks
# ============================================================

echo '=== 1. Static validation ==='

bash -n \
  "$STAGE/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh"

python3 - \
  "$STAGE/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh" \
  <<'PY_STATIC'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    'kubectl create',
    'RESERVATION_ACQUIRED=YES',
    'RESERVATION_VERIFIED=YES',
    'AUTOMATIC_RESERVATION_CLEANUP=NO',
    'fresh_s3_relist_passed',
    'person_map_fingerprint_captured',
    'write_permit_issued',
    'WRITE_AUTHORIZED=NO',
)

for item in required:
    assert item in source, item

for forbidden in (
    'kubectl apply',
    'kubectl delete configmap',
    'mode("overwrite")',
    "mode('overwrite')",
):
    assert forbidden not in source, forbidden

print('RESERVATION_ACQUIRE_STATIC_CHECK=PASS')
print('CREATE_ONLY_SEMANTICS=PASS')
print('AUTOMATIC_DELETE_ABSENT=PASS')
PY_STATIC

# ============================================================
# Canonical source conflict check
# ============================================================

echo '=== 2. Canonical source conflict check ==='

FILES=(
  scripts/task003/05g2c2c3a-acquire-writer-reservation.sh
)

GEN=scripts/task003/05g2c2c3a-prepare-writer-reservation-acquire.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then

    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "$SOURCE" "$ROOT/$GEN"
}; then

  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

# ============================================================
# Install permanent runner and generator
# ============================================================

echo '=== 3. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then

    echo "CANONICAL_SOURCE_REUSED=$rel"

  else
    install \
      -m 755 \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    echo "CANONICAL_SOURCE_READY=$rel"
  fi
done

if [[ -f "$ROOT/$GEN" ]]; then

  echo "CANONICAL_GENERATOR_REUSED=$GEN"

else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2C3A_SOURCE=PASS'
echo 'K8S_RESERVATION_CREATED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
