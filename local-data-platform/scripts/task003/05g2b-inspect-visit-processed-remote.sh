#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REPORT=''
POD=''
POD_CREATED=NO

echo '#### TASK003 STEP05G2B REMOTE S3 PREFIX OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  if [[ "$POD_CREATED" == YES ]]; then
    if kubectl -n dw-spark delete pod "$POD" \
        --ignore-not-found --wait=true --timeout=90s \
        > "$REPORT/pod-cleanup.log" 2>&1; then
      echo 'UTILITY_POD_CLEANUP=PASS'
    else
      echo "WARNING: Pod cleanup failed: $REPORT/pod-cleanup.log"
      rc=1
    fi
  fi

  [[ -z "$REPORT" ]] || echo "INSPECTION_REPORT=$REPORT"

  echo "G2B_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2B REMOTE S3 PREFIX OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 2 ]] || {
  echo "Usage: $0 STEP05F2_RUN_STATE PROCESSED_RUN_ID"
  exit 2
}

F2="$1"
RUN_ID="$2"

[[ -s "$F2" && ! -L "$F2" ]] || {
  echo 'ERROR: STEP05F2 evidence missing'
  exit 2
}

[[ "$RUN_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$ && \
   "$RUN_ID" != . && "$RUN_ID" != .. ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

for cmd in python3 kubectl sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command $cmd"
    exit 2
  }
done

PLAN="$ROOT/runtime/reports/task003/step05/processed-plans/$RUN_ID/plan.json"

[[ -s "$PLAN" && ! -L "$PLAN" ]] || {
  echo "ERROR: immutable plan missing: $PLAN"
  exit 2
}

mkdir -p "$ROOT/runtime/reports/task003/step05"

REPORT=$(
  mktemp -d \
    "$ROOT/runtime/reports/task003/step05/processed-prefix.XXXXXXXX"
)

# ==================================================
# 3. Revalidate immutable plan against F2 evidence
# ==================================================

python3 "$ROOT/apps/task003/verify_visit_processed_plan.py" \
  --root "$ROOT" \
  --f2-state "$F2" \
  --plan "$PLAN" \
  --run-id "$RUN_ID"

# ==================================================
# 4. Pin source and derive exact S3 prefix
# ==================================================

PYTHONPATH="$ROOT/apps/task003" \
python3 - "$ROOT" "$PLAN" "$F2" "$REPORT" <<'PY_PIN'
import hashlib
import json
import sys
from pathlib import Path
from inspect_visit_processed_prefix import get_prefix

root, planfile, f2file, report = map(Path, sys.argv[1:])

plan = json.loads(planfile.read_bytes())
bucket, prefix = get_prefix(plan)

sources = (
    (
        'spark/apps/visit/map_encounter_to_visit_candidate.py',
        'mapper_sha256'
    ),
    (
        'spark/contracts/omop/visit-candidate-v1.json',
        'contract_sha256'
    ),
    (
        'spark/contracts/omop/visit-class-v1.json',
        'mapping_contract_sha256'
    ),
)

for rel, key in sources:
    path = root / rel
    actual = hashlib.sha256(path.read_bytes()).hexdigest()

    if actual != plan[key]:
        raise ValueError('Pinned source changed: ' + rel)

(report / 'plan.json').write_bytes(planfile.read_bytes())
(report / 'input-step05f2.json').write_bytes(f2file.read_bytes())

(report / 'target.tsv').write_text(
    bucket + '\t' + prefix + '\n'
)

print('SOURCE_AND_PLAN_PINS=PASS')
PY_PIN

IFS=$'\t' read -r BUCKET PREFIX < "$REPORT/target.tsv"

[[ "$BUCKET" == health-processed && -n "$PREFIX" ]] || {
  echo 'ERROR: invalid S3 target'
  exit 1
}

echo "S3_BUCKET=$BUCKET"
echo "S3_PREFIX=$PREFIX"

echo "PLAN_SHA256=$(sha256sum "$PLAN" | awk '{print $1}')"

# ==================================================
# 5. Create temporary AWS CLI reader Pod
# ==================================================

TEMPLATE="$ROOT/spark/manifests/task003/visit-processed-prefix-reader.yaml.tpl"

[[ -s "$TEMPLATE" ]] || {
  echo 'ERROR: reader template missing'
  exit 1
}

POD="visit-proc-read-$(date -u +%Y%m%dt%H%M%Sz)-$$"

sed "s/__POD_NAME__/$POD/g" "$TEMPLATE" \
  > "$REPORT/utility-pod.yaml"

kubectl -n dw-spark get secret dw-spark-s3-secret >/dev/null

kubectl -n dw-spark apply --dry-run=client \
  -f "$REPORT/utility-pod.yaml" >/dev/null

POD_CREATED=YES

kubectl -n dw-spark create -f "$REPORT/utility-pod.yaml"

kubectl -n dw-spark wait \
  --for=condition=Ready "pod/$POD" --timeout=180s

# ==================================================
# 6. Read actual S3 listing, without pagination
# ==================================================

# One page is intentionally requested.
# Truncated responses are rejected by the formal guard.
# Never interpret AWS errors as an empty prefix.

if ! kubectl -n dw-spark exec "$POD" -- \
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
    > "$REPORT/s3-listing.json" \
    2> "$REPORT/s3-listing.stderr.log"; then

  echo 'REMOTE_S3_LISTING=FAIL'
  echo "S3_LISTING_STDERR_LOG=$REPORT/s3-listing.stderr.log"
  exit 1
fi

[[ -s "$REPORT/s3-listing.json" ]] || {
  echo 'ERROR: S3 returned empty response bytes'
  exit 1
}

echo 'REMOTE_S3_LISTING=CAPTURED'

echo "LISTING_SHA256=$(sha256sum "$REPORT/s3-listing.json" | awk '{print $1}')"

# ==================================================
# 7. Reuse frozen G2A validation
# ==================================================

if bash "$ROOT/scripts/task003/05g2a-inspect-visit-processed-prefix.sh" \
    "$F2" \
    "$RUN_ID" \
    "$PLAN" \
    "$REPORT/s3-listing.json" \
    > "$REPORT/guard.log" 2>&1; then

  cat "$REPORT/guard.log"

else
  code=$?
  cat "$REPORT/guard.log"
  echo "PREFIX_PREFLIGHT=STOP (guard exit $code)"
  exit "$code"
fi

# ==================================================
# 8. Clean up Pod before recording PASS
# ==================================================

kubectl -n dw-spark delete pod "$POD" \
  --ignore-not-found --wait=true --timeout=90s \
  > "$REPORT/pod-cleanup.log" 2>&1

POD_CREATED=NO
echo 'UTILITY_POD_CLEANUP=PASS'

# ==================================================
# 9. Save read-only evidence
# ==================================================

PYTHONPATH="$ROOT/apps/task003" \
python3 - "$REPORT" "$POD" <<'PY_REPORT'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from inspect_visit_processed_prefix import classify

report = Path(sys.argv[1])
pod = sys.argv[2]

plan_bytes = (report / 'plan.json').read_bytes()
listing_bytes = (report / 's3-listing.json').read_bytes()

result = classify(
    json.loads(plan_bytes),
    json.loads(listing_bytes)
)

if (
    result['classification'] != 'EMPTY'
    or result['new_write_guard'] != 'PASS'
):
    raise ValueError('Target prefix is not empty')

state = {
    'task': 'TASK-003',
    'step': 'STEP-05G2B',
    'status': 'PASS',
    'validation_scope': 'remote_s3_prefix_snapshot',
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'utility_pod': pod,
    'plan_sha256': hashlib.sha256(plan_bytes).hexdigest(),
    's3_listing_sha256': hashlib.sha256(listing_bytes).hexdigest(),
    'inspection': result,
    's3_write': False,
    'postgresql_write': False,
    'spark_application_submitted': False,
    'publication_verified': False,
    'exclusive_writer_lock_acquired': False,
    'write_authorized': False
}

(report / 'run-state.json').write_text(
    json.dumps(state, indent=2) + '\n'
)

print('REAL_REMOTE_PREFIX_CLASSIFICATION=EMPTY')
print('READONLY_PREFIX_PREFLIGHT=PASS')
print('WRITER_LOCK_ACQUIRED=NO')
print('WRITE_AUTHORIZED=NO')
print('RUN_STATE=' + str(report / 'run-state.json'))
PY_REPORT

echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
