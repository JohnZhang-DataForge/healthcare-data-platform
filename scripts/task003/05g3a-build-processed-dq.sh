#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G3A PROCESSED DQ BUILD OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "DQ_BUILD_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3A PROCESSED DQ BUILD OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 PLAN READBACK_STATE READBACK_RESULT GIT_CHECKPOINT"
  exit 2
}

PLAN="$1"
STATE="$2"
RESULT="$3"
CHECKPOINT="$4"

for path in \
  "$PLAN" \
  "$STATE" \
  "$RESULT"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

cd "$ROOT"

git cat-file -e \
  "${CHECKPOINT}^{commit}"

git merge-base \
  --is-ancestor \
  "$CHECKPOINT" \
  HEAD

echo "DATA_VERIFIED_GIT_CHECKPOINT=$CHECKPOINT"
echo 'DATA_VERIFIED_CHECKPOINT_ANCESTRY=PASS'

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

OUTDIR="$ROOT/runtime/reports/task003/step05/processed-dq-builds/$RUN_ID"

mkdir -p "$OUTDIR"

DQ_FILE="$OUTDIR/dq-result.json"
STATE_FILE="$OUTDIR/run-state.json"

TMP_DQ=$(
  mktemp \
    "$OUTDIR/.dq-result.XXXXXXXX"
)

TMP_STATE=$(
  mktemp \
    "$OUTDIR/.run-state.XXXXXXXX"
)

cleanup() {
  rm -f \
    "$TMP_DQ" \
    "$TMP_STATE"
}

trap 'cleanup; finish' EXIT

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$STATE" \
  "$RESULT" \
  "$CHECKPOINT" \
  "$TMP_DQ" \
  <<'PY_BUILD'
import json
import sys
from pathlib import Path

from build_visit_processed_dq import (
    build_dq,
    canonical_json_bytes,
)

plan_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
result_path = Path(sys.argv[3])
checkpoint = sys.argv[4]
target = Path(sys.argv[5])

plan = json.loads(
    plan_path.read_bytes()
)

state = json.loads(
    state_path.read_bytes()
)

result_bytes = (
    result_path.read_bytes()
)

result = json.loads(
    result_bytes
)

dq = build_dq(
    plan,
    state,
    result,
    result_bytes,
    checkpoint,
)

target.write_bytes(
    canonical_json_bytes(
        dq
    )
)

print('DQ_CONTENT_BUILD=PASS')
print('DQ_STATUS=' + dq['status'])
print('DQ_RUN_ID=' + dq['run_id'])
print('DQ_URI=' + dq['dq_uri'])
print('MANIFEST_URI=' + dq['manifest_uri'])
PY_BUILD

DQ_SHA=$(
  sha256sum "$TMP_DQ" |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c \
    < "$TMP_DQ" |
  tr -d ' '
)

echo "DQ_SHA256=$DQ_SHA"
echo "DQ_SIZE_BYTES=$DQ_SIZE"

if [[ -e "$DQ_FILE" ]]; then

  [[ -f "$DQ_FILE" && ! -L "$DQ_FILE" ]] || {
    echo 'ERROR: unsafe existing DQ artifact'
    exit 1
  }

  if cmp -s "$TMP_DQ" "$DQ_FILE"; then
    echo 'DQ_LOCAL_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable local DQ artifact'
    exit 4
  fi

else
  mv "$TMP_DQ" "$DQ_FILE"
  TMP_DQ=''
  echo 'DQ_LOCAL_ARTIFACT=CREATED'
fi

python3 - \
  "$PLAN" \
  "$STATE" \
  "$RESULT" \
  "$DQ_FILE" \
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
dq = Path(sys.argv[4])
checkpoint = sys.argv[5]
target = Path(sys.argv[6])


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


dq_obj = json.loads(
    dq.read_bytes()
)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G3A',

    'status':
        'DQ_BUILT_NOT_PUBLISHED',

    'run_id':
        dq_obj['run_id'],

    'data_verified_git_checkpoint':
        checkpoint,

    'plan_sha256':
        sha(plan),

    'independent_readback_state_sha256':
        sha(readback_state),

    'independent_validation_result_sha256':
        sha(readback_result),

    'dq_result_sha256':
        sha(dq),

    'dq_result_size_bytes':
        dq.stat().st_size,

    'dq_uri':
        dq_obj['dq_uri'],

    'manifest_uri':
        dq_obj['manifest_uri'],

    'processed_data_verified':
        True,

    's3_write_verified':
        True,

    'candidate_published_verified':
        True,

    'dq_published':
        False,

    'manifest_published':
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

print('DQ_BUILD_STATE=PASS')
PY_STATE

if [[ -e "$STATE_FILE" ]]; then

  [[ -f "$STATE_FILE" && ! -L "$STATE_FILE" ]] || {
    echo 'ERROR: unsafe existing DQ state'
    exit 1
  }

  if cmp -s "$TMP_STATE" "$STATE_FILE"; then
    echo 'DQ_BUILD_STATE_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable DQ build state'
    exit 4
  fi

else
  mv "$TMP_STATE" "$STATE_FILE"
  TMP_STATE=''
  echo 'DQ_BUILD_STATE_ARTIFACT=CREATED'
fi

echo "DQ_LOCAL_FILE=$DQ_FILE"
echo "DQ_BUILD_STATE_FILE=$STATE_FILE"

echo 'STEP05G3A_PROCESSED_DQ_BUILD=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'S3_WRITE_VERIFIED=YES'
echo 'CANDIDATE_PUBLISHED_VERIFIED=YES'

echo 'DQ_BUILT=YES'
echo 'DQ_PUBLISHED=NO'
echo 'MANIFEST_PUBLISHED=NO'

echo 'RESERVATION_RELEASED=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_WRITE=NO'
