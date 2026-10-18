#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05E SPARK RAW PREFLIGHT OUTPUT BEGIN ####'
trap 'rc=$?; echo "PREFLIGHT_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05E SPARK RAW PREFLIGHT OUTPUT END ####"; exit "${rc}"' EXIT

[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05D_RUN_STATE"
    exit 2
}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/raw-preflight.XXXXXX")"
NAME="visit-raw-check-$(date -u +%Y%m%dt%H%M%Sz)-$$"
CM="${NAME}-app"

echo "PREFLIGHT_REPORT=${REPORT}"
echo "SPARK_APPLICATION=${NAME}"

PYTHONPATH="${ROOT}/apps/task003" \
python3 - "${ROOT}" "$1" "${REPORT}" "${NAME}" "${CM}" <<'PY'
import json, sys
from pathlib import Path
from resolve_approved_encounter_raw import resolve, require
from verify_encounter_remote_metadata import verify_metadata

root, statefile, report = map(Path, sys.argv[1:4])
name, cm = sys.argv[4:]
state = json.loads(statefile.read_bytes())

for key, value in dict(
    task='TASK-003', step='STEP-05D', status='PASS',
    validation_scope='remote_manifest_and_dq_bytes',
    remote_metadata_verified=True,
).items():
    require(state.get(key), value, key)

context = state['input_context']
require(
    context, resolve(root, context['raw_publish_run_id']),
    'fresh local evidence',
)
verify_metadata(
    context,
    (statefile.parent / 'manifest.remote.json').read_bytes(),
    (statefile.parent / 'dq.remote.json').read_bytes(),
)
(report / 'input-step05d.json').write_bytes(statefile.read_bytes())
(report / 'input-context.json').write_text(
    json.dumps(context, indent=2) + '\n'
)

template = (
    root / 'spark/manifests/task003/visit-raw-preflight.yaml.tpl'
).read_text()
for old, value in (('__APP_NAME__', name), ('__CONFIGMAP_NAME__', cm)):
    if template.count(old) != 1:
        raise ValueError('Unexpected template placeholder: ' + old)
    template = template.replace(old, value)
if '__' in template:
    raise ValueError('Unresolved template placeholder')
(report / 'sparkapplication.yaml').write_text(template)
print('PINNED_INPUT_CONTEXT=PASS')
PY

kubectl get secret dw-spark-s3-secret dw-spark-omop-secret \
    -n dw-spark >/dev/null
kubectl get serviceaccount spark-job -n dw-spark >/dev/null
kubectl apply --dry-run=client \
    -f "${REPORT}/sparkapplication.yaml" >/dev/null

kubectl create configmap "${CM}" -n dw-spark \
    --from-file="${ROOT}/spark/apps/visit/validate_encounter_raw_for_visit.py" \
    --from-file="${ROOT}/spark/common/canonical_gate.py" \
    --from-file="${ROOT}/apps/task003/verify_encounter_remote_metadata.py" \
    --from-file="${ROOT}/apps/task003/resolve_approved_encounter_raw.py" \
    --from-file="${ROOT}/spark/contracts/canonical/encounter-v1.json" \
    --from-file="${ROOT}/spark/contracts/omop/visit-class-v1.json" \
    --from-file="${REPORT}/input-context.json"

kubectl create -f "${REPORT}/sparkapplication.yaml"

FINAL_STATE=''
for ((attempt=0; attempt<180; attempt++)); do
    FINAL_STATE="$(kubectl get sparkapplication "${NAME}" -n dw-spark \
        -o jsonpath='{.status.applicationState.state}' 2>/dev/null || true)"
    case "${FINAL_STATE}" in
        COMPLETED|FAILED|FAILING|SUBMISSION_FAILED|UNKNOWN) break ;;
    esac
    sleep 5
done

echo "FINAL_STATE=${FINAL_STATE}"
kubectl logs -n dw-spark "${NAME}-driver" \
    > "${REPORT}/driver.log" 2>&1 || true

if [[ "${FINAL_STATE}" != COMPLETED ]]; then
    tail -160 "${REPORT}/driver.log"
    kubectl get sparkapplication "${NAME}" -n dw-spark -o yaml \
        > "${REPORT}/application-status.yaml" || true
    echo 'ERROR: Spark preflight did not complete'
    exit 1
fi

python3 - "${REPORT}" "${NAME}" "${CM}" <<'PY'
import json, sys
from pathlib import Path

report = Path(sys.argv[1])
prefix = 'VISIT_RAW_PREFLIGHT_RESULT='
lines = [
    line[len(prefix):]
    for line in (report / 'driver.log').read_text().splitlines()
    if line.startswith(prefix)
]
if len(lines) != 1:
    raise SystemExit('ERROR: missing or ambiguous Spark validation result')
r = json.loads(lines[0])
c = json.loads((report / 'input-context.json').read_text())

for key in (
    'raw_publish_run_id', 'raw_manifest_sha256', 'dq_sha256',
    'canonical_contract_sha256', 'mapping_contract_sha256',
):
    if r[key] != c[key]:
        raise SystemExit('ERROR: Spark result context mismatch: ' + key)

if (
    r['raw_rows'] != c['expected_rows']
    or r['raw_unique_keys'] != c['expected_rows']
):
    raise SystemExit('ERROR: Spark result row/key mismatch')

for key in ('status', 'raw_schema', 'raw_metadata', 'person_references', 'concepts'):
    if r.get(key) != 'PASS':
        raise SystemExit('ERROR: Spark check failed: ' + key)

if r.get('postgresql_write') is not False or r.get('s3_write') is not False:
    raise SystemExit('ERROR: unexpected write status')

state = dict(
    task='TASK-003', step='STEP-05E', status='PASS',
    spark_application=sys.argv[2], configmap=sys.argv[3],
    validation_scope='raw_parquet_and_person_references',
    raw_parquet_verified=True, input_context=c, result=r,
    ids_allocated=0, postgresql_write=False, s3_write=False,
)
(report / 'run-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(r, indent=2))
print('REMOTE_PARQUET_REVALIDATION=PASS')
print('PERSON_REFERENCES=PASS')
print('VISIT_MAPPING_CONCEPTS=PASS')
PY

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'IDS_ALLOCATED=0'
echo 'DATABASE_WRITE=NO'
echo 'S3_WRITE=NO'
