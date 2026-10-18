#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G2C2C3B POSTLOCK PREFLIGHT SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3B POSTLOCK PREFLIGHT SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must execute from a saved Bash file'
  exit 2
}

for rel in \
  apps/task003/inspect_visit_processed_prefix.py \
  spark/manifests/task003/visit-processed-prefix-reader.yaml.tpl
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite: $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g2c2c3b.XXXXXXXX)
mkdir -p "$STAGE/scripts/task003"

cat > "$STAGE/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REPORT=''
UTILITY_POD=''
UTILITY_POD_CREATED=NO

echo '#### TASK003 STEP05G2C2C3B POSTLOCK PREFLIGHT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  # Only the temporary AWS reader Pod is cleaned up.
  # The Writer Reservation is NEVER removed here.
  if [[ "$UTILITY_POD_CREATED" == YES ]]; then
    if kubectl -n dw-spark delete pod "$UTILITY_POD" \
        --ignore-not-found \
        --wait=true \
        --timeout=90s \
        >/dev/null 2>&1
    then
      echo 'UTILITY_POD_CLEANUP=PASS'
    else
      echo 'UTILITY_POD_CLEANUP=FAIL'
      rc=1
    fi
  fi

  [[ -z "$REPORT" ]] || {
    echo "POSTLOCK_REPORT=$REPORT"
  }

  echo 'RESERVATION_RELEASED=NO'
  echo "POSTLOCK_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3B POSTLOCK PREFLIGHT OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 2 ]] || {
  echo "Usage: $0 PROCESSED_RUN_ID C3A_RESERVATION_REPORT_DIR"
  exit 2
}

RUN_ID="$1"
C3A_REPORT="$2"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && \
   "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

for cmd in kubectl python3 sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"
    exit 2
  }
done

BASE="$ROOT/runtime/reports/task003/step05"

PLAN="$BASE/processed-plans/$RUN_ID/plan.json"
INTENT="$BASE/processed-intents/$RUN_ID/write-intent.json"
SPEC="$BASE/writer-reservations/$RUN_ID/reservation-create.json"
C3A_STATE="$C3A_REPORT/run-state.json"

for path in \
  "$PLAN" \
  "$INTENT" \
  "$SPEC" \
  "$C3A_STATE"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing immutable evidence: $path"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/writer-postlock-preflight.XXXXXXXX"
)

# ==========================================================
# 1. Verify C3A evidence and current live Reservation
# ==========================================================

echo '=== 1. Reverify live Writer Reservation ==='

python3 - \
  "$PLAN" \
  "$INTENT" \
  "$SPEC" \
  "$C3A_STATE" \
  "$REPORT" \
  <<'PY_PREP'
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

plan_path = Path(sys.argv[1])
intent_path = Path(sys.argv[2])
spec_path = Path(sys.argv[3])
state_path = Path(sys.argv[4])
report = Path(sys.argv[5])


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'unsafe evidence: ' + str(path)
        )
    return path.read_bytes()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


plan_bytes = read(plan_path)
intent_bytes = read(intent_path)
spec_bytes = read(spec_path)
state_bytes = read(state_path)

plan = json.loads(plan_bytes)
intent = json.loads(intent_bytes)
spec = json.loads(spec_bytes)
state = json.loads(state_bytes)

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G2C2C3A',
    'RESERVATION_ACQUIRED',
)

assert state['run_id'] == plan['run_id']
assert state['reservation_created_by_k8s_create'] is True
assert state['reservation_verified'] is True
assert state['fresh_s3_relist_passed'] is False
assert state['write_permit_issued'] is False
assert state['write_authorized'] is False

assert state['plan_sha256'] == sha(plan_bytes)
assert state['write_intent_sha256'] == sha(intent_bytes)
assert state['reservation_spec_sha256'] == sha(spec_bytes)

assert intent['plan_sha256'] == sha(plan_bytes)
assert intent['write_authorized'] is False

name = spec['metadata']['name']

assert state['reservation_name'] == name

uid = state['reservation_uid']
version = state['reservation_resource_version']

assert isinstance(uid, str) and len(uid) >= 8
assert isinstance(version, str) and version.isdigit()

parsed = urlsplit(plan['base_uri'])

assert parsed.scheme == 's3'
assert parsed.netloc == 'health-processed'
assert not parsed.query
assert not parsed.fragment

prefix = parsed.path.lstrip('/') + '/'

(report / 'reservation-name.txt').write_text(
    name + '\n'
)

(report / 'reservation-uid.txt').write_text(
    uid + '\n'
)

(report / 'reservation-version.txt').write_text(
    version + '\n'
)

(report / 's3-target.tsv').write_text(
    'health-processed\t' + prefix + '\n'
)

print('C3A_EVIDENCE_REVALIDATED=PASS')
print('RESERVATION_NAME=' + name)
print('RESERVATION_UID=' + uid)
print('RESERVATION_RESOURCE_VERSION=' + version)
PY_PREP

LOCK=$(tr -d '\r\n' < "$REPORT/reservation-name.txt")
EXPECTED_UID=$(tr -d '\r\n' < "$REPORT/reservation-uid.txt")
EXPECTED_VERSION=$(tr -d '\r\n' < "$REPORT/reservation-version.txt")

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/live-reservation.json"

python3 - \
  "$SPEC" \
  "$C3A_STATE" \
  "$REPORT/live-reservation.json" \
  <<'PY_LOCK'
import json
import sys
from pathlib import Path

spec = json.loads(
    Path(sys.argv[1]).read_bytes()
)

state = json.loads(
    Path(sys.argv[2]).read_bytes()
)

live = json.loads(
    Path(sys.argv[3]).read_bytes()
)

assert live['apiVersion'] == 'v1'
assert live['kind'] == 'ConfigMap'

assert (
    live['metadata']['name']
    == spec['metadata']['name']
)

assert (
    live['metadata']['namespace']
    == 'dw-spark'
)

assert live.get('immutable') is True

assert (
    live['metadata']['uid']
    == state['reservation_uid']
)

assert (
    live['metadata']['resourceVersion']
    == state['reservation_resource_version']
)

assert (
    live['metadata']['labels']
    == spec['metadata']['labels']
)

assert (
    live['data']['reservation.json']
    == spec['data']['reservation.json']
)

print('LIVE_RESERVATION_STILL_IDENTICAL=PASS')
print('RESERVATION_LOCK_HELD=YES')
PY_LOCK

# ==========================================================
# 2. Fresh S3 listing AFTER reservation acquisition
# ==========================================================

echo '=== 2. Fresh S3 listing after Reservation acquisition ==='

IFS=$'\t' read -r BUCKET PREFIX < "$REPORT/s3-target.tsv"

[[ "$BUCKET" == health-processed ]] || {
  echo 'ERROR: unexpected bucket'
  exit 1
}

[[ -n "$PREFIX" ]] || {
  echo 'ERROR: empty S3 prefix'
  exit 1
}

TEMPLATE="$ROOT/spark/manifests/task003/visit-processed-prefix-reader.yaml.tpl"

UTILITY_POD="visit-proc-postlock-$(date -u +%Y%m%dt%H%M%Sz)-$$"

sed \
  "s/__POD_NAME__/$UTILITY_POD/g" \
  "$TEMPLATE" \
  > "$REPORT/aws-reader-pod.yaml"

kubectl -n dw-spark get secret \
  dw-spark-s3-secret \
  -o name >/dev/null

kubectl -n dw-spark apply \
  --dry-run=client \
  -f "$REPORT/aws-reader-pod.yaml" \
  >/dev/null

kubectl -n dw-spark create \
  -f "$REPORT/aws-reader-pod.yaml"

UTILITY_POD_CREATED=YES

kubectl -n dw-spark wait \
  --for=condition=Ready \
  "pod/$UTILITY_POD" \
  --timeout=180s

if ! kubectl -n dw-spark exec "$UTILITY_POD" -- \
  aws \
    --no-cli-pager \
    --cli-connect-timeout 15 \
    --cli-read-timeout 45 \
    --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
    s3api list-objects-v2 \
    --bucket "$BUCKET" \
    --prefix "$PREFIX" \
    --max-keys 1000 \
    --no-paginate \
    --output json \
    > "$REPORT/fresh-s3-listing.json" \
    2> "$REPORT/fresh-s3-listing.stderr"
then
  echo 'FRESH_S3_LISTING=FAIL'
  exit 1
fi

[[ -s "$REPORT/fresh-s3-listing.json" ]] || {
  echo 'ERROR: empty S3 response bytes'
  exit 1
}

echo 'FRESH_S3_LISTING=CAPTURED'

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$REPORT/fresh-s3-listing.json" \
  <<'PY_S3'
import json
import sys
from pathlib import Path

from inspect_visit_processed_prefix import classify

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

listing = json.loads(
    Path(sys.argv[2]).read_bytes()
)

result = classify(
    plan,
    listing,
)

assert result['classification'] == 'EMPTY'
assert result['object_count'] == 0
assert result['new_write_guard'] == 'PASS'
assert result['publication_verified'] is False
assert result['resume_authorized'] is False

print('FRESH_PREFIX_CLASSIFICATION=EMPTY')
print('FRESH_PREFIX_OBJECT_COUNT=0')
print('FRESH_S3_RELIST_PASSED=YES')
print('WRITE_AUTHORIZED=NO')
PY_S3

echo "FRESH_S3_LISTING_SHA256=$(sha256sum "$REPORT/fresh-s3-listing.json" | awk '{print $1}')"

# Remove ONLY the temporary reader Pod now.
kubectl -n dw-spark delete pod "$UTILITY_POD" \
  --ignore-not-found \
  --wait=true \
  --timeout=90s \
  >/dev/null

UTILITY_POD_CREATED=NO

echo 'UTILITY_POD_CLEANUP=PASS'

# ==========================================================
# 3. Capture current Synthea Person ID Map
# ==========================================================

echo '=== 3. Capture current Synthea Person Map ==='

DB_POD=$(
  kubectl -n dw-postgre get pods \
    -o json \
  | python3 -c '
import json, sys

data = json.load(sys.stdin)

matches = []

for item in data.get("items", []):
    name = item.get("metadata", {}).get("name", "")
    phase = item.get("status", {}).get("phase")

    if (
        name.startswith("dw-postgre-database-")
        and phase == "Running"
    ):
        matches.append(name)

if len(matches) != 1:
    raise SystemExit(
        "Expected exactly one Running dw-postgre-database pod; "
        f"found {matches}"
    )

print(matches[0])
'
)

echo "POSTGRES_POD=$DB_POD"

SQL="
SELECT
  source_system,
  source_person_id,
  person_id
FROM etl.person_id_map
WHERE source_system = 'synthea'
ORDER BY
  source_person_id,
  person_id;
"

if ! kubectl -n dw-postgre exec "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U omop_admin \
    -d omop \
    -At \
    -F $'\t' \
    -c "$SQL" \
    > "$REPORT/person-map.tsv" \
    2> "$REPORT/person-map.stderr"
then
  echo 'PERSON_MAP_QUERY=FAIL'
  echo "PERSON_MAP_STDERR=$REPORT/person-map.stderr"
  exit 1
fi

echo 'PERSON_MAP_QUERY=PASS'

python3 - \
  "$PLAN" \
  "$REPORT/person-map.tsv" \
  "$REPORT/person-map-snapshot.json" \
  <<'PY_PERSON'
import hashlib
import json
import sys
from pathlib import Path

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

tsv = Path(sys.argv[2])
snapshot = Path(sys.argv[3])

rows = []
identities = set()
person_ids = set()

for line_number, raw in enumerate(
    tsv.read_text().splitlines(),
    start=1,
):
    if not raw:
        continue

    fields = raw.split('\t')

    if len(fields) != 3:
        raise ValueError(
            f'Bad Person map row {line_number}: {raw!r}'
        )

    source_system, source_person_id, person_id_raw = fields

    if source_system != 'synthea':
        raise ValueError(
            'Unexpected source system'
        )

    if not source_person_id:
        raise ValueError(
            'Blank source_person_id'
        )

    try:
        person_id = int(person_id_raw)

    except ValueError as exc:
        raise ValueError(
            'Invalid person_id'
        ) from exc

    if person_id <= 0:
        raise ValueError(
            'Non-positive person_id'
        )

    identity = (
        source_system,
        source_person_id,
    )

    if identity in identities:
        raise ValueError(
            'Duplicate Synthea Person identity'
        )

    if person_id in person_ids:
        raise ValueError(
            'Duplicate OMOP person_id'
        )

    identities.add(identity)
    person_ids.add(person_id)

    rows.append([
        source_system,
        source_person_id,
        person_id,
    ])

rows = sorted(rows)

expected = plan['expected_persons']

if len(rows) != expected:
    raise ValueError(
        f'Person map count drift: '
        f'expected={expected} actual={len(rows)}'
    )

# IMPORTANT:
# This is byte-for-byte the same canonical representation
# used by processed_visit_writer_core.person_snapshot_fingerprint().
blob = json.dumps(
    rows,
    separators=(',', ':'),
    ensure_ascii=False,
).encode('utf-8')

snapshot.write_bytes(blob)

fingerprint = hashlib.sha256(
    blob
).hexdigest()

print(
    'PERSON_MAP_ROWS='
    + str(len(rows))
)

print(
    'PERSON_MAP_UNIQUE_SOURCE_IDS='
    + str(len(identities))
)

print(
    'PERSON_MAP_UNIQUE_PERSON_IDS='
    + str(len(person_ids))
)

print(
    'PERSON_MAP_FINGERPRINT='
    + fingerprint
)

print('PERSON_MAP_FINGERPRINT_CAPTURED=YES')
PY_PERSON

PERSON_FINGERPRINT=$(
  sha256sum \
    "$REPORT/person-map-snapshot.json" \
  | awk '{print $1}'
)

echo "PERSON_MAP_SNAPSHOT_SHA256=$PERSON_FINGERPRINT"

# ==========================================================
# 4. Verify Reservation AGAIN after both reads
# ==========================================================

echo '=== 4. Reverify Reservation after S3 and DB reads ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/live-reservation-after.json"

python3 - \
  "$REPORT/live-reservation.json" \
  "$REPORT/live-reservation-after.json" \
  <<'PY_LOCK2'
import json
import sys
from pathlib import Path

before = json.loads(
    Path(sys.argv[1]).read_bytes()
)

after = json.loads(
    Path(sys.argv[2]).read_bytes()
)

assert (
    before['metadata']['uid']
    == after['metadata']['uid']
)

assert (
    before['metadata']['resourceVersion']
    == after['metadata']['resourceVersion']
)

assert before['immutable'] is True
assert after['immutable'] is True

assert before['data'] == after['data']
assert before['metadata']['labels'] == after['metadata']['labels']

print('POSTREAD_RESERVATION_VERIFICATION=PASS')
print('RESERVATION_LOCK_HELD=YES')
PY_LOCK2

# ==========================================================
# 5. Build immutable C3B evidence
# ==========================================================

echo '=== 5. Build C3B immutable evidence ==='

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$INTENT" \
  "$SPEC" \
  "$C3A_STATE" \
  "$REPORT/live-reservation-after.json" \
  "$REPORT/fresh-s3-listing.json" \
  "$REPORT/person-map-snapshot.json" \
  "$REPORT" \
  <<'PY_STATE'
import hashlib
import json
import sys

from datetime import datetime, timezone
from pathlib import Path

from inspect_visit_processed_prefix import classify


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'unsafe state input: ' + str(path)
        )

    return path.read_bytes()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


(
    plan_path,
    intent_path,
    spec_path,
    c3a_path,
    live_path,
    listing_path,
    person_path,
    report_path,
) = [
    Path(value)
    for value in sys.argv[1:]
]

report = report_path

plan_bytes = read(plan_path)
intent_bytes = read(intent_path)
spec_bytes = read(spec_path)
c3a_bytes = read(c3a_path)
live_bytes = read(live_path)
listing_bytes = read(listing_path)
person_bytes = read(person_path)

plan = json.loads(plan_bytes)
intent = json.loads(intent_bytes)
spec = json.loads(spec_bytes)
c3a = json.loads(c3a_bytes)
live = json.loads(live_bytes)
listing = json.loads(listing_bytes)

inspection = classify(
    plan,
    listing,
)

assert inspection['classification'] == 'EMPTY'
assert inspection['object_count'] == 0
assert inspection['new_write_guard'] == 'PASS'

assert c3a['reservation_verified'] is True

assert (
    live['metadata']['uid']
    == c3a['reservation_uid']
)

assert (
    live['metadata']['resourceVersion']
    == c3a['reservation_resource_version']
)

assert (
    live['metadata']['name']
    == spec['metadata']['name']
)

expected_persons = plan['expected_persons']

person_rows = json.loads(
    person_bytes
)

assert isinstance(person_rows, list)
assert len(person_rows) == expected_persons

fingerprint = sha(person_bytes)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G2C2C3B',

    'status':
        'POSTLOCK_PREFLIGHT_PASS',

    'run_id':
        plan['run_id'],

    'reservation_name':
        live['metadata']['name'],

    'reservation_uid':
        live['metadata']['uid'],

    'reservation_resource_version':
        live['metadata']['resourceVersion'],

    'reservation_spec_sha256':
        sha(spec_bytes),

    'reservation_live_sha256':
        sha(live_bytes),

    'plan_sha256':
        sha(plan_bytes),

    'write_intent_sha256':
        sha(intent_bytes),

    'c3a_state_sha256':
        sha(c3a_bytes),

    'fresh_s3_listing_sha256':
        sha(listing_bytes),

    'fresh_s3_classification':
        inspection['classification'],

    'fresh_s3_object_count':
        inspection['object_count'],

    'fresh_s3_relist_passed':
        True,

    'expected_persons':
        expected_persons,

    'person_map_rows':
        len(person_rows),

    'person_map_fingerprint':
        fingerprint,

    'person_map_fingerprint_captured':
        True,

    'reservation_still_held':
        True,

    'write_permit_issued':
        False,

    'write_authorized':
        False,

    'runtime_configmap_created':
        False,

    'spark_application_submitted':
        False,

    's3_write':
        False,

    'postgresql_write':
        False,

    'captured_at_utc':
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

print('C3B_STATE=PASS')
print('FRESH_S3_RELIST_PASSED=YES')
print('FRESH_PREFIX_CLASSIFICATION=EMPTY')
print('PERSON_MAP_ROWS=' + str(len(person_rows)))
print('PERSON_MAP_FINGERPRINT=' + fingerprint)
print('RESERVATION_STILL_HELD=YES')
print('WRITE_PERMIT_ISSUED=NO')
print('WRITE_AUTHORIZED=NO')
print('RUNTIME_CONFIGMAP_CREATED=NO')
print('SPARK_APPLICATION_SUBMITTED=NO')
print('S3_WRITE=NO')
print('DATABASE_WRITE=NO')
print('C3B_STATE_FILE=' + str(target))
print('C3B_STATE_SHA256=' + sha(target.read_bytes()))
PY_STATE

echo 'STEP05G2C2C3B_POSTLOCK_PREFLIGHT=PASS'
RUNNER

# ==========================================================
# Installer checks
# ==========================================================

echo '=== 1. Static validation ==='

bash -n \
  "$STAGE/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh"

python3 - \
  "$STAGE/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh" \
  <<'PY_STATIC'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    'FRESH_S3_RELIST_PASSED=YES',
    'PERSON_MAP_FINGERPRINT_CAPTURED=YES',
    'POSTREAD_RESERVATION_VERIFICATION=PASS',
    'etl.person_id_map',
    "source_system = 'synthea'",
    'RESERVATION_RELEASED=NO',
    'WRITE_PERMIT_ISSUED=NO',
    'WRITE_AUTHORIZED=NO',
)

for item in required:
    assert item in source, item

for forbidden in (
    'kubectl delete configmap',
    'aws s3 rm',
    'aws s3 cp',
    'aws s3api put-object',
    'INSERT INTO',
    'UPDATE etl.person_id_map',
    'DELETE FROM etl.person_id_map',
):
    assert forbidden not in source, forbidden

print('POSTLOCK_STATIC_CHECK=PASS')
print('RESERVATION_DELETE_ABSENT=PASS')
print('S3_WRITE_COMMAND_ABSENT=PASS')
print('DATABASE_MUTATION_ABSENT=PASS')
PY_STATIC

# ==========================================================
# Install canonical source
# ==========================================================

echo '=== 2. Canonical source conflict check ==='

FILES=(
  scripts/task003/05g2c2c3b-capture-postlock-preflight.sh
)

GEN=scripts/task003/05g2c2c3b-prepare-postlock-preflight.sh

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

echo 'STEP05G2C2C3B_SOURCE=PASS'
echo 'RESERVATION_ALREADY_HELD=YES'
echo 'WRITE_PERMIT_ISSUED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
