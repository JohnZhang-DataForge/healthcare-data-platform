#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

EXPECTED_CHECKPOINT=beb6370cddafbe4c4e649f9a6cb9d949af0ee05e
EXPECTED_DQ_SHA=58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2
EXPECTED_DQ_SIZE=2607

echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILD OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "MANIFEST_BUILD_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILD OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 7 ]] || {
  echo "Usage:"
  echo "$0 PLAN READBACK_STATE READBACK_RESULT DQ_PUBLICATION_STATE DQ_PUBLICATION_RESULT DQ_FILE GIT_CHECKPOINT"
  exit 2
}

PLAN="$1"
READBACK_STATE="$2"
READBACK_RESULT="$3"
DQ_STATE="$4"
DQ_RESULT="$5"
DQ_FILE="$6"
CHECKPOINT="$7"

for path in \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

cd "$ROOT"

echo '=== 1. Verify exact DQ-published Git checkpoint ==='

HEAD=$(git rev-parse HEAD)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_CHECKPOINT"

[[ "$CHECKPOINT" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: supplied Git checkpoint drift'
  exit 1
}

[[ "$HEAD" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: repository HEAD drifted after DQ-published checkpoint'
  exit 1
}

git cat-file -e \
  "${CHECKPOINT}^{commit}"

echo 'DQ_PUBLISHED_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify local DQ artifact remains exact ==='

DQ_SHA=$(
  sha256sum "$DQ_FILE" |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c < "$DQ_FILE" |
  tr -d ' '
)

echo "DQ_SHA256=$DQ_SHA"
echo "DQ_SIZE_BYTES=$DQ_SIZE"

[[ "$DQ_SHA" == "$EXPECTED_DQ_SHA" ]] || {
  echo 'ERROR: local DQ SHA drift'
  exit 1
}

[[ "$DQ_SIZE" == "$EXPECTED_DQ_SIZE" ]] || {
  echo 'ERROR: local DQ size drift'
  exit 1
}

echo 'LOCAL_DQ_ARTIFACT=PASS'

RUN_ID=$(
  python3 -c '
import json,sys
print(json.load(open(sys.argv[1]))["run_id"])
' "$PLAN"
)

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

OUTDIR="$ROOT/runtime/reports/task003/step05/processed-manifest-builds/$RUN_ID"

mkdir -p "$OUTDIR"

MANIFEST_FILE="$OUTDIR/manifest.json"
STATE_FILE="$OUTDIR/run-state.json"

TMP_MANIFEST=$(
  mktemp \
    "$OUTDIR/.manifest.XXXXXXXX"
)

TMP_STATE=$(
  mktemp \
    "$OUTDIR/.run-state.XXXXXXXX"
)

cleanup() {
  [[ -z "${TMP_MANIFEST:-}" ]] || rm -f "$TMP_MANIFEST"
  [[ -z "${TMP_STATE:-}" ]] || rm -f "$TMP_STATE"
}

trap 'cleanup; finish' EXIT

echo '=== 3. Build deterministic APPROVED Manifest ==='

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE" \
  "$CHECKPOINT" \
  "$TMP_MANIFEST" \
  <<'PY_BUILD'
import json
import sys
from pathlib import Path

from build_visit_processed_manifest import (
    build_manifest,
    canonical_json_bytes,
)

plan_path = Path(sys.argv[1])
readback_state_path = Path(sys.argv[2])
readback_result_path = Path(sys.argv[3])
dq_state_path = Path(sys.argv[4])
dq_result_path = Path(sys.argv[5])
dq_path = Path(sys.argv[6])

checkpoint = sys.argv[7]
target = Path(sys.argv[8])

plan = json.loads(
    plan_path.read_bytes()
)

readback_state = json.loads(
    readback_state_path.read_bytes()
)

readback_result_bytes = (
    readback_result_path.read_bytes()
)

readback_result = json.loads(
    readback_result_bytes
)

dq_state = json.loads(
    dq_state_path.read_bytes()
)

dq_result_bytes = (
    dq_result_path.read_bytes()
)

dq_result = json.loads(
    dq_result_bytes
)

dq_bytes = dq_path.read_bytes()

manifest = build_manifest(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    dq_state,
    dq_result,
    dq_result_bytes,
    dq_bytes,
    checkpoint,
)

target.write_bytes(
    canonical_json_bytes(
        manifest
    )
)

print('MANIFEST_CONTENT_BUILD=PASS')
print('MANIFEST_STATUS=' + manifest['status'])
print(
    'MANIFEST_PUBLICATION_POLICY='
    + manifest['publication_policy']
)
print('MANIFEST_RUN_ID=' + manifest['run_id'])
print(
    'MANIFEST_URI='
    + manifest['uris']['manifest']
)
print(
    'READY_FOR_MANIFEST_PUBLICATION='
    + str(
        manifest['approval_gate']
        ['ready_for_manifest_publication']
    ).upper()
)
PY_BUILD

MANIFEST_SHA=$(
  sha256sum "$TMP_MANIFEST" |
  awk '{print $1}'
)

MANIFEST_SIZE=$(
  wc -c < "$TMP_MANIFEST" |
  tr -d ' '
)

echo "MANIFEST_SHA256=$MANIFEST_SHA"
echo "MANIFEST_SIZE_BYTES=$MANIFEST_SIZE"

echo '=== 4. Install/reuse immutable local Manifest artifact ==='

if [[ -e "$MANIFEST_FILE" ]]; then

  [[ -f "$MANIFEST_FILE" && ! -L "$MANIFEST_FILE" ]] || {
    echo 'ERROR: unsafe existing Manifest artifact'
    exit 1
  }

  if cmp -s "$TMP_MANIFEST" "$MANIFEST_FILE"; then
    echo 'MANIFEST_LOCAL_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable local Manifest artifact'
    exit 4
  fi

else
  mv "$TMP_MANIFEST" "$MANIFEST_FILE"
  TMP_MANIFEST=''
  echo 'MANIFEST_LOCAL_ARTIFACT=CREATED'
fi

echo '=== 5. Build local G4A state ==='

python3 - \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE" \
  "$MANIFEST_FILE" \
  "$CHECKPOINT" \
  "$TMP_STATE" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path

plan = Path(sys.argv[1])
readback_state = Path(sys.argv[2])
readback_result = Path(sys.argv[3])
dq_state = Path(sys.argv[4])
dq_result = Path(sys.argv[5])
dq_file = Path(sys.argv[6])
manifest = Path(sys.argv[7])

checkpoint = sys.argv[8]
target = Path(sys.argv[9])


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


manifest_obj = json.loads(
    manifest.read_bytes()
)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G4A',

    'status':
        'MANIFEST_BUILT_NOT_PUBLISHED',

    'run_id':
        manifest_obj['run_id'],

    'git_checkpoint':
        checkpoint,

    'plan_sha256':
        sha(plan),

    'independent_readback_state_sha256':
        sha(readback_state),

    'independent_validation_result_sha256':
        sha(readback_result),

    'dq_publication_state_sha256':
        sha(dq_state),

    'dq_publication_result_sha256':
        sha(dq_result),

    'dq_sha256':
        sha(dq_file),

    'manifest_sha256':
        sha(manifest),

    'manifest_size_bytes':
        manifest.stat().st_size,

    'data_uri':
        manifest_obj['uris']['data'],

    'dq_uri':
        manifest_obj['uris']['dq'],

    'manifest_uri':
        manifest_obj['uris']['manifest'],

    'approval_status':
        manifest_obj['status'],

    'publication_policy':
        manifest_obj['publication_policy'],

    'processed_data_verified':
        True,

    'candidate_published_verified':
        True,

    's3_write_verified':
        True,

    'dq_published':
        True,

    'dq_readback_verified':
        True,

    'manifest_built':
        True,

    'manifest_published':
        False,

    'manifest_readback_verified':
        False,

    'reservation_released':
        False,

    'postgresql_write':
        False,
}

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('MANIFEST_BUILD_STATE=PASS')
PY_STATE

if [[ -e "$STATE_FILE" ]]; then

  [[ -f "$STATE_FILE" && ! -L "$STATE_FILE" ]] || {
    echo 'ERROR: unsafe existing Manifest build state'
    exit 1
  }

  if cmp -s "$TMP_STATE" "$STATE_FILE"; then
    echo 'MANIFEST_BUILD_STATE_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable Manifest build state'
    exit 4
  fi

else
  mv "$TMP_STATE" "$STATE_FILE"
  TMP_STATE=''
  echo 'MANIFEST_BUILD_STATE_ARTIFACT=CREATED'
fi

echo '=== 6. Validate final Manifest semantic gate ==='

python3 - \
  "$MANIFEST_FILE" \
  <<'PY_VERIFY'
import json
import sys
from pathlib import Path

manifest = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert manifest['status'] == 'APPROVED'

assert (
    manifest['publication_policy']
    == 'APPROVED_manifest_last'
)

gate = manifest['approval_gate']

assert gate['processed_data_verified'] is True
assert gate['independent_s3_readback_passed'] is True
assert gate['candidate_published_verified'] is True
assert gate['dq_published'] is True
assert gate['dq_readback_verified'] is True

assert gate['manifest_must_be_last'] is True
assert gate['ready_for_manifest_publication'] is True

assert (
    gate[
        'reservation_must_remain_held_until_manifest_verification'
    ]
    is True
)

assert gate['postgresql_write'] is False

assert manifest['metrics']['rows'] == 5799

assert (
    manifest['metrics']['unique_business_keys']
    == 5799
)

assert (
    manifest['metrics']['referenced_persons']
    == 113
)

assert (
    manifest['metrics']['contract_field_count']
    == 36
)

assert (
    manifest['metrics']['visit_occurrence_id_present']
    is False
)

assert (
    manifest['artifacts']['dq']['sha256']
    == '58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2'
)

assert (
    manifest['artifacts']['dq']['size_bytes']
    == 2607
)

print('FINAL_MANIFEST_APPROVAL_GATE=PASS')
print('MANIFEST_STATUS=APPROVED')
print('MANIFEST_MUST_BE_LAST=YES')
print('READY_FOR_MANIFEST_PUBLICATION=YES')
PY_VERIFY

echo "MANIFEST_LOCAL_FILE=$MANIFEST_FILE"
echo "MANIFEST_BUILD_STATE_FILE=$STATE_FILE"

echo 'STEP05G4A_PROCESSED_MANIFEST_BUILD=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'DQ_PUBLISHED=YES'
echo 'DQ_READBACK_VERIFIED=YES'

echo 'MANIFEST_BUILT=YES'
echo 'MANIFEST_APPROVED=YES'
echo 'MANIFEST_PUBLISHED=NO'
echo 'MANIFEST_READBACK_VERIFIED=NO'

echo 'RESERVATION_STILL_HELD=YES'

echo 'S3_MUTATION=NO'
echo 'DATABASE_WRITE=NO'
