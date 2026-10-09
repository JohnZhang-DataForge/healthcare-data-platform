#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

echo '#### TASK003 STEP05F2B RUNTIME SOURCE OUTPUT BEGIN ####'
STAGE=''
finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05F2B RUNTIME SOURCE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
cd "$ROOT"
for rel in \
  spark/manifests/task003/visit-raw-preflight.yaml.tpl \
  spark/apps/visit/validate_visit_candidate_preflight.py \
  spark/apps/visit/map_encounter_to_visit_candidate.py \
  apps/task003/visit_candidate_rules.py \
  apps/task003/resolve_approved_encounter_raw.py \
  apps/task003/verify_encounter_remote_metadata.py \
  spark/common/canonical_gate.py \
  spark/contracts/canonical/encounter-v1.json \
  spark/contracts/omop/visit-class-v1.json \
  spark/contracts/omop/visit-candidate-v1.json
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing required source: $rel"; exit 1;
  }
done

STAGE=$(mktemp -d)
mkdir -p "$STAGE/spark/manifests/task003" "$STAGE/scripts/task003"

# Reuse the verified STEP05E Spark/Kubernetes configuration.
python3 - "$ROOT" "$STAGE" <<'PY_TEMPLATE'
import pathlib, sys
root, stage = map(pathlib.Path, sys.argv[1:3])
old = (root/'spark/manifests/task003/visit-raw-preflight.yaml.tpl').read_text()
repls = {
    'healthcare-step: raw-preflight': 'healthcare-step: candidate-preflight',
    'local:///opt/spark/app/validate_encounter_raw_for_visit.py':
        'local:///opt/spark/app/validate_visit_candidate_preflight.py',
}
for before, after in repls.items():
    if old.count(before) != 1:
        raise ValueError('STEP05E template changed: ' + before)
    old = old.replace(before, after)
for value in ('__APP_NAME__', '__CONFIGMAP_NAME__'):
    if old.count(value) != 1:
        raise ValueError('Invalid template placeholder: ' + value)
for value in ('dw-spark-s3-secret', 'dw-spark-omop-secret',
              'serviceAccount: spark-job', 'spark:3.5.7-python3',
              'name: spark-app', 'mountPath: /opt/spark/app'):
    if value not in old:
        raise ValueError('Missing verified configuration: ' + value)
(stage/'spark/manifests/task003/visit-candidate-preflight.yaml.tpl').write_text(old)
print('VERIFIED_STEP05E_TEMPLATE_REUSED=PASS')
PY_TEMPLATE

cat > "$STAGE/scripts/task003/05f2c-validate-visit-candidate.sh" <<'RUN_F2C'
#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_PAGER=cat PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05F2C SPARK CANDIDATE OUTPUT BEGIN ####'
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT=''
finish() {
  rc=$?
  trap - EXIT
  [[ -z "$REPORT" ]] || echo "RUN_REPORT=$REPORT"
  echo "F2C_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05F2C SPARK CANDIDATE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 1 && -f "$1" ]] || {
  echo "Usage: $0 ABSOLUTE_STEP05E_RUN_STATE_PATH"
  exit 2
}
for cmd in python3 kubectl; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"; exit 2;
  }
done

mkdir -p "$ROOT/runtime/reports/task003/step05"
REPORT=$(mktemp -d "$ROOT/runtime/reports/task003/step05/candidate-preflight.XXXXXXXX")
NAME="visit-cand-check-$(date -u +%Y%m%dt%H%M%Sz)-$$"
CM="${NAME}-app"
echo "SPARK_APPLICATION=$NAME"

# Pin approved STEP05E evidence and copy immutable source bytes.
PYTHONPATH="$ROOT/apps/task003" python3 - "$ROOT" "$1" "$REPORT" "$NAME" "$CM" <<'PY_PREPARE'
import hashlib, json, pathlib, sys
from resolve_approved_encounter_raw import resolve, require

root, previous, report = map(pathlib.Path, sys.argv[1:4])
name, cm = sys.argv[4:]
e = json.loads(previous.read_bytes())

for key, expected in {
    'task': 'TASK-003',
    'step': 'STEP-05E',
    'status': 'PASS',
    'raw_parquet_verified': True,
    'ids_allocated': 0,
    'postgresql_write': False,
    's3_write': False,
}.items():
    require(e.get(key), expected, 'STEP05E.' + key)

r, context = e['result'], e['input_context']
for key in ('status', 'raw_schema', 'raw_metadata',
            'person_references', 'concepts'):
    require(r.get(key), 'PASS', 'STEP05E.result.' + key)

require(
    context,
    resolve(root, context['raw_publish_run_id']),
    'current approved Raw evidence'
)

for key in (
    'raw_publish_run_id',
    'raw_manifest_sha256',
    'dq_sha256',
    'canonical_contract_sha256',
    'mapping_contract_sha256',
):
    require(r.get(key), context[key], 'STEP05E result pin ' + key)

require(r['raw_rows'], context['expected_rows'], 'Raw rows')
require(r['raw_unique_keys'], context['expected_rows'], 'Raw unique keys')

if sum(r['encounter_classes'].values()) != context['expected_rows']:
    raise ValueError('STEP05E class counts inconsistent')

if type(r.get('referenced_persons')) is not int or r['referenced_persons'] <= 0:
    raise ValueError('Invalid STEP05E referenced Person count')

files = {
  'validate_visit_candidate_preflight.py':
      'spark/apps/visit/validate_visit_candidate_preflight.py',
  'map_encounter_to_visit_candidate.py':
      'spark/apps/visit/map_encounter_to_visit_candidate.py',
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

mount = report / 'configmap-files'
mount.mkdir()
digests = {}

for filename, rel in files.items():
    src = root / rel
    if not src.is_file() or src.is_symlink():
        raise ValueError('Invalid source path: ' + rel)

    content = src.read_bytes()
    (mount / filename).write_bytes(content)
    digests[filename] = hashlib.sha256(content).hexdigest()

require(
    digests['encounter-v1.json'],
    context['canonical_contract_sha256'],
    'Canonical contract pin'
)
require(
    digests['visit-class-v1.json'],
    context['mapping_contract_sha256'],
    'Visit mapping contract pin'
)

state = {
    'raw_context': context,
    'expected_persons': r['referenced_persons'],
    'expected_class_counts': r['encounter_classes'],
    'candidate_contract_sha256': digests['visit-candidate-v1.json'],
    'mapper_sha256': digests['map_encounter_to_visit_candidate.py'],
    'step05e_state_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
    'mounted_file_sha256': digests,
}

(mount/'candidate-preflight-input.json').write_text(
    json.dumps(state, indent=2) + '\n'
)
(report/'candidate-preflight-input.json').write_text(
    json.dumps(state, indent=2) + '\n'
)
(report/'step05e-input.json').write_bytes(previous.read_bytes())
(report/'mount-sha256.json').write_text(
    json.dumps(digests, indent=2) + '\n'
)

base = (
    root/'spark/manifests/task003/visit-candidate-preflight.yaml.tpl'
).read_text()

for placeholder, actual in (
    ('__APP_NAME__', name),
    ('__CONFIGMAP_NAME__', cm),
):
    if base.count(placeholder) != 1:
        raise ValueError('Invalid template placeholder: ' + placeholder)
    base = base.replace(placeholder, actual)

if '__APP_NAME__' in base or '__CONFIGMAP_NAME__' in base:
    raise ValueError('Unresolved template placeholder')

(report/'sparkapplication.yaml').write_text(base)
print('PINNED_STEP05E_EVIDENCE=PASS')
print('CONFIGMAP_SOURCE_SNAPSHOT=PASS')
PY_PREPARE

kubectl get serviceaccount spark-job -n dw-spark >/dev/null
kubectl get secret dw-spark-s3-secret dw-spark-omop-secret \
  -n dw-spark >/dev/null

kubectl apply --dry-run=client \
  -f "$REPORT/sparkapplication.yaml" >/dev/null

CM_ARGS=()
for src in "$REPORT"/configmap-files/*; do
  CM_ARGS+=(--from-file="$src")
done

kubectl create configmap "$CM" -n dw-spark "${CM_ARGS[@]}"
kubectl create -f "$REPORT/sparkapplication.yaml"

FINAL_STATE=''
for ((n=0; n<180; n++)); do
  FINAL_STATE=$(
    kubectl get sparkapplication "$NAME" -n dw-spark \
      -o jsonpath='{.status.applicationState.state}' 2>/dev/null || true
  )
  case "$FINAL_STATE" in
    COMPLETED|FAILED|FAILING|SUBMISSION_FAILED|UNKNOWN) break ;;
  esac
  sleep 5
done

echo "FINAL_STATE=$FINAL_STATE"

kubectl logs -n dw-spark "${NAME}-driver" \
  > "$REPORT/driver.log" 2>&1 || true

if [[ "$FINAL_STATE" != 'COMPLETED' ]]; then
  kubectl get sparkapplication "$NAME" -n dw-spark -o yaml \
    > "$REPORT/application-status.yaml" 2>&1 || true
  tail -100 "$REPORT/driver.log" || true
  echo 'ERROR: Spark Candidate preflight did not complete'
  exit 1
fi

python3 - "$REPORT" "$NAME" "$CM" <<'PY_VERIFY'
import json, sys
from pathlib import Path

report = Path(sys.argv[1])
prefix = 'VISIT_CANDIDATE_PREFLIGHT_RESULT='

lines = [
    v[len(prefix):]
    for v in (report/'driver.log').read_text().splitlines()
    if v.startswith(prefix)
]

if len(lines) != 1:
    raise SystemExit(
        'ERROR: missing or multiple Spark preflight result markers'
    )

r = json.loads(lines[0])
pinned = json.loads(
    (report/'candidate-preflight-input.json').read_text()
)
ctx = pinned['raw_context']

checks = {
    'status': 'PASS',
    'step': 'STEP-05F2',
    'raw_publish_run_id': ctx['raw_publish_run_id'],
    'raw_manifest_sha256': ctx['raw_manifest_sha256'],
    'dq_sha256': ctx['dq_sha256'],
    'mapping_contract_sha256': ctx['mapping_contract_sha256'],
    'candidate_contract_sha256': pinned['candidate_contract_sha256'],
    'mapper_sha256': pinned['mapper_sha256'],
    'expected_rows': ctx['expected_rows'],
    'candidate_rows': ctx['expected_rows'],
    'unique_source_keys': ctx['expected_rows'],
    'referenced_persons': pinned['expected_persons'],
    'candidate_schema': 'PASS',
    'person_mapping': 'PASS',
    'visit_concepts': 'PASS',
    'dates': 'PASS',
    'nullability': 'PASS',
    'deferred_fields': 'PASS',
    'ids_allocated': 0,
    's3_write': False,
    'postgresql_write': False,
    'candidate_published': False,
    'class_counts': pinned['expected_class_counts'],
}

for key, expected in checks.items():
    if type(r.get(key)) is not type(expected) or r[key] != expected:
        raise SystemExit(
            'ERROR: Spark preflight result mismatch: ' + key
        )

state = {
    'task': 'TASK-003',
    'step': 'STEP-05F2',
    'status': 'PASS',
    'validation_scope': 'in_memory_visit_candidate',
    'spark_application': sys.argv[2],
    'configmap': sys.argv[3],
    'input': pinned,
    'result': r,
    'ids_allocated': 0,
    's3_write': False,
    'postgresql_write': False,
    'candidate_published': False,
}

(report/'run-state.json').write_text(
    json.dumps(state, indent=2) + '\n'
)

print('CANDIDATE_ROWS=' + str(r['candidate_rows']))
print('UNIQUE_KEYS=' + str(r['unique_source_keys']))
print('REFERENCED_PERSONS=' + str(r['referenced_persons']))
print('CLASS_COUNTS=' + json.dumps(r['class_counts'], sort_keys=True))
print('VISIT_CANDIDATE_IN_MEMORY=PASS')
print('CANDIDATE_PUBLISHED=NO')
print('RUN_STATE=' + str(report/'run-state.json'))
PY_VERIFY

echo 'VISIT_ID_ALLOCATED=NO'
echo 'POSTGRESQL_WRITE=NO'
echo 'S3_WRITE=NO'
RUN_F2C

echo '=== 1. Static validation ==='

bash -n "$STAGE/scripts/task003/05f2c-validate-visit-candidate.sh"

python3 - "$STAGE" <<'PY_CHECK'
from pathlib import Path
import sys

stage = Path(sys.argv[1])
tpl = (
    stage/'spark/manifests/task003/visit-candidate-preflight.yaml.tpl'
).read_text()
run = (
    stage/'scripts/task003/05f2c-validate-visit-candidate.sh'
).read_text()

assert 'healthcare-step: candidate-preflight' in tpl
assert '__APP_NAME__' in tpl
assert '__CONFIGMAP_NAME__' in tpl
assert 'validate_visit_candidate_preflight.py' in tpl

for item in (
    'PINNED_STEP05E_EVIDENCE=PASS',
    'CONFIGMAP_SOURCE_SNAPSHOT=PASS',
    'VISIT_CANDIDATE_IN_MEMORY=PASS',
    'POSTGRESQL_WRITE=NO',
):
    assert item in run, item

assert 'kubectl create -f ' in run
print('F2B_RUNTIME_STATIC_CHECKS=PASS')
PY_CHECK

echo '=== 2. Canonical source conflict check ==='

FILES=(
  spark/manifests/task003/visit-candidate-preflight.yaml.tpl
  scripts/task003/05f2c-validate-visit-candidate.sh
)

GEN=scripts/task003/05f2b-prepare-visit-candidate-runtime.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: canonical source conflicts: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflicts: $GEN"
  exit 1
fi

echo '=== 3. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"
  mode=644
  [[ "$rel" != *.sh ]] || mode=755
  install -m "$mode" "$STAGE/$rel" "$ROOT/$rel"
  echo "CANONICAL_SOURCE_READY=$rel"
done

if [[ -e "$ROOT/$GEN" && "${BASH_SOURCE[0]}" -ef "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GEN"
  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05F2B_RUNTIME_SOURCE=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'DATABASE_WRITE=NO'
echo 'S3_WRITE=NO'
echo 'VISIT_ID_ALLOCATED=NO'
echo 'GIT_COMMIT=NO'
