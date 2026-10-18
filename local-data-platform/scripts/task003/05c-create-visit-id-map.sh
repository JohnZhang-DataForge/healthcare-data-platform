#!/usr/bin/env bash
set -Eeuo pipefail

echo '#### TASK003 STEP05C ID MAP OUTPUT BEGIN ####'
trap 'rc=$?; echo "FOUNDATION_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05C ID MAP OUTPUT END ####"; exit "${rc}"' EXIT

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05B_BASELINE_JSON"
    exit 2
}

SQL="${ROOT}/sql/task003/visit-id-map-foundation.sql"
mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/id-map.XXXXXX")"
echo "FOUNDATION_REPORT=${REPORT}"

python3 - "$1" "${REPORT}" "${ROOT}" <<'PY'
import hashlib, json, sys
from pathlib import Path

source, report, root = map(Path, sys.argv[1:])
raw = source.read_bytes()
b = json.loads(raw)

if (b.get('task'), b.get('step'), b.get('status')) != (
    'TASK-003', 'STEP-05B', 'CAPTURED'
):
    raise SystemExit('ERROR: invalid STEP05B baseline')

if (
    b['database']['read_only'] != 'on'
    or b['database']['database'] != 'omop'
):
    raise SystemExit('ERROR: unexpected baseline database')

query = root / 'sql/task003/visit-mapping-baseline.sql'
if hashlib.sha256(query.read_bytes()).hexdigest() != b['sql_sha256']:
    raise SystemExit('ERROR: baseline SQL changed')

(report / 'input-baseline.json').write_bytes(raw)
print('STEP05B_BASELINE=PASS')
PY

# Both executions use transactional DDL. No source keys are inserted.
for attempt in first replay; do
    echo "FOUNDATION_ATTEMPT=${attempt}"

    if kubectl exec -i -n dw-postgre dw-postgre-database-0 -- \
        psql -X -qAt -v ON_ERROR_STOP=1 -P pager=off \
        -U omop_admin -d omop \
        < "${SQL}" \
        > "${REPORT}/${attempt}.json" \
        2> "${REPORT}/${attempt}.stderr.log"
    then
        cat "${REPORT}/${attempt}.json"
    else
        cat "${REPORT}/${attempt}.stderr.log"
        exit 1
    fi
done

python3 - "${REPORT}" "${SQL}" <<'PY'
import hashlib, json, sys
from pathlib import Path

report, sql = map(Path, sys.argv[1:])
a = json.loads((report / 'first.json').read_text())
b = json.loads((report / 'replay.json').read_text())

if a.get('status') != 'PASS' or b.get('status') != 'PASS':
    raise SystemExit('ERROR: database validation failed')

if (
    a.get('action') not in ('CREATED', 'REUSED')
    or b.get('action') != 'REUSED'
):
    raise SystemExit('ERROR: unexpected replay action')

first_state = {k: v for k, v in a.items() if k != 'action'}
replay_state = {k: v for k, v in b.items() if k != 'action'}
if first_state != replay_state:
    raise SystemExit('ERROR: schema/rows/sequence changed between runs')

if a['ids_allocated'] != 0:
    raise SystemExit('ERROR: unexpected ID allocation')

if a['action'] == 'CREATED' and (
    a['map_rows'] != 0
    or a['cdm_visit_rows'] != 0
    or a['sequence_state'] != {'last_value': 1, 'is_called': False}
):
    raise SystemExit('ERROR: unexpected fresh foundation state')

state = dict(
    task='TASK-003',
    step='STEP-05C',
    status='PASS',
    scope='stable_id_map_foundation',
    first=a,
    replay=b,
    sql_sha256=hashlib.sha256(sql.read_bytes()).hexdigest(),
    input_baseline_sha256=hashlib.sha256(
        (report / 'input-baseline.json').read_bytes()
    ).hexdigest(),
    raw_remote_verified=False,
    cdm_write=False,
)
(report / 'run-state.json').write_text(
    json.dumps(state, indent=2) + '\n'
)

print('ID_MAP_SCHEMA=PASS')
print('ID_MAP_REPLAY=PASS')
print('SEQUENCE_UNCHANGED_ON_REPLAY=PASS')
print('MAP_ROWS=' + str(b['map_rows']))
print('CDM_VISIT_ROWS=' + str(b['cdm_visit_rows']))
print(
    'PERSISTENT_DDL='
    + ('CREATED' if a['action'] == 'CREATED' else 'REUSED')
)
PY

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'IDS_ALLOCATED=0'
echo 'CDM_WRITE=NO'
echo 'S3_WRITE=NO'
echo 'REMOTE_RAW_REVALIDATION=PENDING'
