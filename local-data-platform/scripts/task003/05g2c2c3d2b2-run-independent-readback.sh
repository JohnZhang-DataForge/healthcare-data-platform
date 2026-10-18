#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$ROOT/runtime/reports/task003/step05"

REPORT=''
FINAL_STATE='UNKNOWN'
VALIDATOR_CM_CREATED=NO
VALIDATOR_APP_CREATED=NO

echo '#### TASK003 STEP05G2C2C3D2B2 INDEPENDENT S3 READBACK OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || \
    echo "INDEPENDENT_READBACK_REPORT=$REPORT"

  echo "FINAL_VALIDATOR_STATE=$FINAL_STATE"
  echo "VALIDATOR_CONFIGMAP_CREATED=$VALIDATOR_CM_CREATED"
  echo "VALIDATOR_SPARKAPPLICATION_CREATED=$VALIDATOR_APP_CREATED"

  echo 'RESERVATION_RELEASED=NO'
  echo 'WRITER_RUNTIME_CONFIGMAP_DELETED=NO'
  echo 'WRITER_SPARKAPPLICATION_DELETED=NO'
  echo 'VALIDATOR_AUTOMATIC_CLEANUP=NO'

  echo "READBACK_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3D2B2 INDEPENDENT S3 READBACK OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 6 ]] || {
  echo "Usage:"
  echo "$0 RUN_ID ATOMIC_LAUNCH_REPORT F2_STATE PLAN C3B_REPORT CONTRACT"
  exit 2
}

RUN_ID="$1"
ATOMIC_REPORT="$2"
F2_STATE="$3"
PLAN="$4"
C3B_REPORT="$5"
CONTRACT="$6"

LAUNCH_STATE="$ATOMIC_REPORT/run-state.json"
C3B_STATE="$C3B_REPORT/run-state.json"
PERSON_SNAPSHOT="$C3B_REPORT/person-map-snapshot.json"
VALIDATOR="$ROOT/spark/apps/visit/validate_persisted_visit_candidate.py"

for path in \
  "$LAUNCH_STATE" \
  "$F2_STATE" \
  "$PLAN" \
  "$C3B_STATE" \
  "$PERSON_SNAPSHOT" \
  "$CONTRACT" \
  "$VALIDATOR"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

for cmd in kubectl python3 sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/persisted-readback.XXXXXXXX"
)

echo '=== 1. Validate all evidence BEFORE Kubernetes mutation ==='

PYTHONPATH="$ROOT/spark/apps/visit" \
python3 - \
  "$PLAN" \
  "$F2_STATE" \
  "$C3B_STATE" \
  "$PERSON_SNAPSHOT" \
  "$CONTRACT" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_PRE'
import json
import sys
from pathlib import Path

from validate_persisted_visit_candidate import (
    validate_static_evidence,
)

plan_path = Path(sys.argv[1])
f2_path = Path(sys.argv[2])
c3b_path = Path(sys.argv[3])
person_path = Path(sys.argv[4])
contract_path = Path(sys.argv[5])
run_id = sys.argv[6]
report = Path(sys.argv[7])

plan = json.loads(plan_path.read_bytes())
f2 = json.loads(f2_path.read_bytes())
c3b = json.loads(c3b_path.read_bytes())
contract = json.loads(contract_path.read_bytes())
person_bytes = person_path.read_bytes()

assert plan['run_id'] == run_id
assert c3b['run_id'] == run_id

fields = validate_static_evidence(
    plan,
    f2,
    c3b,
    contract,
    person_bytes,
    plan['data_uri'],
)

raw_context = f2['input']['raw_context']

assert (
    raw_context['processing_run_id']
    == 'encounter-20261008T234726Z-1658454'
)

assert (
    raw_context['raw_publish_run_id']
    == 'encounter-raw-20261009T005128Z-1681690'
)

assert plan['expected_rows'] == 5799
assert plan['expected_persons'] == 113
assert len(fields) == 36
assert 'visit_occurrence_id' not in fields

report.joinpath('data-uri.txt').write_text(
    plan['data_uri'] + '\n'
)

report.joinpath('expected-processing-run.txt').write_text(
    raw_context['processing_run_id'] + '\n'
)

report.joinpath('expected-raw-run.txt').write_text(
    raw_context['raw_publish_run_id'] + '\n'
)

print('REAL_STATIC_EVIDENCE_VALIDATION=PASS')
print('EXPECTED_ROWS=5799')
print('EXPECTED_UNIQUE_BUSINESS_KEYS=5799')
print('EXPECTED_PERSONS=113')
print('EXPECTED_CONTRACT_FIELDS=36')
print(
    'EXPECTED_PROCESSING_RUN_ID='
    + raw_context['processing_run_id']
)
print(
    'EXPECTED_RAW_PUBLISH_RUN_ID='
    + raw_context['raw_publish_run_id']
)
print(
    'EXPECTED_PERSON_MAP_FINGERPRINT='
    + c3b['person_map_fingerprint']
)
PY_PRE

echo '=== 2. Reverify Writer Reservation remains identical ==='

python3 - \
  "$C3B_STATE" \
  "$REPORT" \
  <<'PY_LOCK_META'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

report = Path(sys.argv[2])

for key in (
    'reservation_name',
    'reservation_uid',
    'reservation_resource_version',
):
    value = state[key]
    report.joinpath(key + '.txt').write_text(
        str(value) + '\n'
    )

print(
    'RESERVATION_NAME='
    + state['reservation_name']
)
PY_LOCK_META

LOCK=$(tr -d '\r\n' < "$REPORT/reservation_name.txt")
LOCK_UID=$(tr -d '\r\n' < "$REPORT/reservation_uid.txt")
LOCK_RV=$(tr -d '\r\n' < "$REPORT/reservation_resource_version.txt")

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-before.json"

python3 - \
  "$REPORT/reservation-before.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_LOCK'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('RESERVATION_BEFORE_READBACK=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK

echo '=== 3. Validate completed Writer SparkApplication ==='

python3 - \
  "$LAUNCH_STATE" \
  "$REPORT" \
  <<'PY_LAUNCH'
import json
import sys
from pathlib import Path

launch = json.loads(
    Path(sys.argv[1]).read_bytes()
)

report = Path(sys.argv[2])

assert launch['status'] == 'SPARK_APPLICATION_SUBMITTED'
assert launch['spark_application_submitted'] is True

report.joinpath('writer-app.txt').write_text(
    launch['spark_application_name'] + '\n'
)

report.joinpath('writer-cm.txt').write_text(
    launch['runtime_configmap_name'] + '\n'
)

report.joinpath('writer-app-uid.txt').write_text(
    launch['spark_application_uid'] + '\n'
)

print(
    'WRITER_SPARK_APPLICATION='
    + launch['spark_application_name']
)

print(
    'WRITER_RUNTIME_CONFIGMAP='
    + launch['runtime_configmap_name']
)
PY_LAUNCH

WRITER_APP=$(tr -d '\r\n' < "$REPORT/writer-app.txt")
WRITER_CM=$(tr -d '\r\n' < "$REPORT/writer-cm.txt")
WRITER_UID=$(tr -d '\r\n' < "$REPORT/writer-app-uid.txt")

kubectl -n dw-spark \
  get sparkapplication "$WRITER_APP" \
  -o json \
  > "$REPORT/writer-sparkapplication.json"

python3 - \
  "$REPORT/writer-sparkapplication.json" \
  "$WRITER_UID" \
  <<'PY_WRITER'
import json
import sys
from pathlib import Path

app = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert app['metadata']['uid'] == sys.argv[2]

state = (
    app.get('status', {})
    .get('applicationState', {})
    .get('state')
)

assert state == 'COMPLETED'

print('WRITER_SPARK_APPLICATION_COMPLETED=PASS')
PY_WRITER

echo '=== 4. Build immutable Validator Runtime ConfigMap and cloned read-only SparkApplication ==='

python3 - \
  "$REPORT/writer-sparkapplication.json" \
  "$WRITER_CM" \
  "$VALIDATOR" \
  "$CONTRACT" \
  "$PLAN" \
  "$F2_STATE" \
  "$C3B_STATE" \
  "$PERSON_SNAPSHOT" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_BUILD'
import copy
import hashlib
import json
import sys
from pathlib import Path

writer_app_path = Path(sys.argv[1])
writer_cm = sys.argv[2]

validator_path = Path(sys.argv[3])
contract_path = Path(sys.argv[4])
plan_path = Path(sys.argv[5])
f2_path = Path(sys.argv[6])
c3b_path = Path(sys.argv[7])
person_path = Path(sys.argv[8])

run_id = sys.argv[9]
report = Path(sys.argv[10])

writer = json.loads(
    writer_app_path.read_bytes()
)

plan = json.loads(
    plan_path.read_bytes()
)

files = {
    'validator.py':
        validator_path.read_text(),

    'contract.json':
        contract_path.read_text(),

    'plan.json':
        plan_path.read_text(),

    'f2-state.json':
        f2_path.read_text(),

    'c3b-state.json':
        c3b_path.read_text(),

    'person-map-snapshot.json':
        person_path.read_text(),
}

payload_bytes = sum(
    len(key.encode('utf-8'))
    + len(value.encode('utf-8'))
    for key, value in files.items()
)

assert payload_bytes < 750000

fingerprint = hashlib.sha256()

for key in sorted(files):
    fingerprint.update(key.encode('utf-8'))
    fingerprint.update(b'\0')
    fingerprint.update(
        files[key].encode('utf-8')
    )
    fingerprint.update(b'\0')

fingerprint.update(
    writer['metadata']['uid'].encode('utf-8')
)

fingerprint.update(
    run_id.encode('utf-8')
)

token = fingerprint.hexdigest()

cm_name = (
    'visit-proc-readback-runtime-'
    + token[:24]
)

app_name = (
    'visit-proc-readback-'
    + token[:20]
)

spec = copy.deepcopy(
    writer['spec']
)

# Locate exactly the Runtime ConfigMap volume used by
# the already-successful Writer SparkApplication.
matches = []

for volume in spec.get('volumes', []):
    config_map = volume.get('configMap')

    if (
        isinstance(config_map, dict)
        and config_map.get('name') == writer_cm
    ):
        matches.append(volume)

assert len(matches) == 1

runtime_volume = matches[0]
runtime_volume_name = runtime_volume['name']

driver_mounts = [
    mount
    for mount in (
        spec.get('driver', {})
        .get('volumeMounts', [])
    )
    if mount.get('name') == runtime_volume_name
]

assert len(driver_mounts) == 1

mount = driver_mounts[0]

assert not mount.get('subPath')

mount_path = mount['mountPath']

assert isinstance(mount_path, str)
assert mount_path.startswith('/')

# Replace only the Writer runtime bundle volume.
runtime_volume['configMap'] = {
    'name':
        cm_name,

    'items': [
        {
            'key': key,
            'path': key,
        }
        for key in files
    ],
}

def mounted(name):
    return (
        mount_path.rstrip('/')
        + '/'
        + name
    )

spec['mainApplicationFile'] = (
    'local://'
    + mounted('validator.py')
)

spec['arguments'] = [
    '--data-uri',
    plan['data_uri'],

    '--plan',
    mounted('plan.json'),

    '--f2-state',
    mounted('f2-state.json'),

    '--c3b-state',
    mounted('c3b-state.json'),

    '--contract',
    mounted('contract.json'),

    '--person-snapshot',
    mounted('person-map-snapshot.json'),
]

# Independent readback must never restart automatically.
spec['restartPolicy'] = {
    'type': 'Never'
}

# Do not inherit any automatic TTL cleanup.
spec.pop(
    'timeToLiveSeconds',
    None,
)

# Remove labels that could identify old Spark runtime pods.
for role in (
    'driver',
    'executor',
):
    labels = (
        spec.get(role, {})
        .get('labels')
    )

    if isinstance(labels, dict):
        for key in list(labels):
            if (
                key == 'spark-app-selector'
                or key == 'spark-role'
            ):
                labels.pop(key, None)

spark_conf = spec.get('sparkConf')

if isinstance(spark_conf, dict):
    if 'spark.app.name' in spark_conf:
        spark_conf['spark.app.name'] = app_name

configmap = {
    'apiVersion':
        'v1',

    'kind':
        'ConfigMap',

    'metadata': {
        'name':
            cm_name,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task-003',

            'purpose':
                'independent-readback',
        },
    },

    'immutable':
        True,

    'data':
        files,
}

spark_app = {
    'apiVersion':
        writer['apiVersion'],

    'kind':
        writer['kind'],

    'metadata': {
        'name':
            app_name,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task-003',

            'purpose':
                'independent-readback',
        },
    },

    'spec':
        spec,
}

cm_path = (
    report
    / 'validator-runtime-configmap.json'
)

app_path = (
    report
    / 'validator-sparkapplication.json'
)

cm_path.write_text(
    json.dumps(
        configmap,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

app_path.write_text(
    json.dumps(
        spark_app,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

report.joinpath(
    'validator-cm-name.txt'
).write_text(
    cm_name + '\n'
)

report.joinpath(
    'validator-app-name.txt'
).write_text(
    app_name + '\n'
)

print(
    'VALIDATOR_RUNTIME_PAYLOAD_BYTES='
    + str(payload_bytes)
)

print(
    'WRITER_RUNTIME_VOLUME='
    + runtime_volume_name
)

print(
    'VALIDATOR_MOUNT_PATH='
    + mount_path
)

print(
    'VALIDATOR_RUNTIME_CONFIGMAP_NAME='
    + cm_name
)

print(
    'VALIDATOR_SPARK_APPLICATION_NAME='
    + app_name
)

print(
    'VALIDATOR_MAIN_APPLICATION_FILE='
    + spec['mainApplicationFile']
)

print(
    'VALIDATOR_RUNTIME_BUILD=PASS'
)
PY_BUILD

VALIDATOR_CM=$(
  tr -d '\r\n' \
  < "$REPORT/validator-cm-name.txt"
)

VALIDATOR_APP=$(
  tr -d '\r\n' \
  < "$REPORT/validator-app-name.txt"
)

CM_MANIFEST="$REPORT/validator-runtime-configmap.json"
APP_MANIFEST="$REPORT/validator-sparkapplication.json"

echo '=== 5. Client dry-run before any CREATE ==='

kubectl create \
  --dry-run=client \
  -f "$CM_MANIFEST" \
  >/dev/null

kubectl create \
  --dry-run=client \
  -f "$APP_MANIFEST" \
  >/dev/null

echo 'VALIDATOR_KUBERNETES_DRY_RUN=PASS'

echo '=== 6. Ensure no runtime-name conflict exists ==='

if kubectl -n dw-spark \
    get configmap "$VALIDATOR_CM" \
    >/dev/null 2>&1
then
  echo 'ERROR: Validator Runtime ConfigMap already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

if kubectl -n dw-spark \
    get sparkapplication "$VALIDATOR_APP" \
    >/dev/null 2>&1
then
  echo 'ERROR: Validator SparkApplication already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

echo 'VALIDATOR_RUNTIME_CONFLICTS=NONE'

echo '=== 7. Final Reservation verification before independent read ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-final-before-create.json"

python3 - \
  "$REPORT/reservation-final-before-create.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_FINAL_LOCK'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('FINAL_RESERVATION_PRECREATE=PASS')
PY_FINAL_LOCK

echo '=== 8. CREATE immutable Validator Runtime ConfigMap ==='

kubectl create \
  -f "$CM_MANIFEST" \
  -o json \
  > "$REPORT/validator-configmap-create.json"

VALIDATOR_CM_CREATED=YES

echo 'VALIDATOR_CONFIGMAP_CREATE=PASS'

echo '=== 9. CREATE independent read-only SparkApplication ==='

if kubectl create \
    -f "$APP_MANIFEST" \
    -o json \
    > "$REPORT/validator-sparkapplication-create.json"
then
  VALIDATOR_APP_CREATED=YES
else
  echo 'VALIDATOR_SPARKAPPLICATION_CREATE=FAIL'
  echo 'AUTOMATIC_CONFIGMAP_DELETE=NO'
  echo 'AUTOMATIC_RESERVATION_DELETE=NO'
  exit 1
fi

echo 'VALIDATOR_SPARKAPPLICATION_CREATE=PASS'

echo '=== 10. Observe Validator SparkApplication ==='

LAST_STATE=''

for attempt in $(seq 1 180); do

  kubectl -n dw-spark \
    get sparkapplication "$VALIDATOR_APP" \
    -o json \
    > "$REPORT/validator-sparkapplication-current.json"

  STATE=$(
    python3 - \
      "$REPORT/validator-sparkapplication-current.json" \
      <<'PY_STATE'
import json
import sys
from pathlib import Path

obj = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    obj.get('status', {})
       .get('applicationState', {})
       .get('state', 'NOT_REPORTED')
)
PY_STATE
  )

  if [[ "$STATE" != "$LAST_STATE" ]]; then
    echo "VALIDATOR_SPARK_APPLICATION_STATE=$STATE"
    LAST_STATE="$STATE"
  fi

  case "$STATE" in
    COMPLETED)
      FINAL_STATE=COMPLETED
      break
      ;;

    FAILED|SUBMISSION_FAILED|INVALIDATING)
      FINAL_STATE="$STATE"
      break
      ;;
  esac

  sleep 5
done

if [[ "$FINAL_STATE" == UNKNOWN ]]; then
  echo 'ERROR: Validator did not reach terminal state'
  exit 3
fi

kubectl -n dw-spark \
  get sparkapplication "$VALIDATOR_APP" \
  -o json \
  > "$REPORT/validator-sparkapplication-final.json"

echo "VALIDATOR_TERMINAL_STATE=$FINAL_STATE"

echo '=== 11. Capture independent Validator Driver log ==='

DRIVER=$(
  python3 - \
    "$REPORT/validator-sparkapplication-final.json" \
    <<'PY_DRIVER'
import json
import sys
from pathlib import Path

obj = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    obj.get('status', {})
       .get('driverInfo', {})
       .get('podName', '')
)
PY_DRIVER
)

[[ -n "$DRIVER" ]] || {
  echo 'ERROR: Validator Driver pod not reported'
  exit 1
}

echo "VALIDATOR_DRIVER_POD=$DRIVER"

kubectl -n dw-spark \
  get pod "$DRIVER" \
  -o json \
  > "$REPORT/validator-driver-pod.json"

kubectl -n dw-spark \
  logs "$DRIVER" \
  > "$REPORT/validator-driver.log"

echo 'VALIDATOR_DRIVER_LOG_CAPTURE=PASS'

if [[ "$FINAL_STATE" != COMPLETED ]]; then
  echo '--- VALIDATOR DRIVER LOG TAIL BEGIN ---'
  tail -n 120 "$REPORT/validator-driver.log"
  echo '--- VALIDATOR DRIVER LOG TAIL END ---'

  echo 'INDEPENDENT_READBACK_RESULT=FAILED'
  echo 'S3_WRITE_VERIFIED=NO'
  echo 'CANDIDATE_PUBLISHED_VERIFIED=NO'

  exit 4
fi

echo '=== 12. Parse and independently verify Validator result ==='

python3 - \
  "$REPORT/validator-driver.log" \
  "$PLAN" \
  "$F2_STATE" \
  "$C3B_STATE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_RESULT'
import hashlib
import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
f2_path = Path(sys.argv[3])
c3b_path = Path(sys.argv[4])
run_id = sys.argv[5]
report = Path(sys.argv[6])

plan = json.loads(
    plan_path.read_bytes()
)

f2 = json.loads(
    f2_path.read_bytes()
)

c3b = json.loads(
    c3b_path.read_bytes()
)

marker = (
    'VISIT_PERSISTED_VALIDATION_RESULT='
)

matches = []

for line in log_path.read_text(
    errors='replace'
).splitlines():

    if marker in line:
        payload = line.split(
            marker,
            1,
        )[1].strip()

        matches.append(
            json.loads(payload)
        )

assert len(matches) == 1, (
    'expected exactly one validation result, '
    f'found {len(matches)}'
)

result = matches[0]

raw_context = (
    f2['input']['raw_context']
)

expected_classes = plan['class_counts']

assert result['status'] == \
    'INDEPENDENT_S3_READBACK_PASS'

assert result['data_uri'] == plan['data_uri']

assert result['rows'] == 5799
assert result['rows'] == plan['expected_rows']

assert result['unique_business_keys'] == 5799

assert result['business_key'] == [
    'source_system',
    'source_encounter_id',
]

assert result['referenced_persons'] == 113
assert result['referenced_persons'] == \
    plan['expected_persons']

assert (
    result['person_map_fingerprint']
    == c3b['person_map_fingerprint']
)

assert (
    result['person_map_fingerprint']
    == 'e4f63203932043bd7a2a64a5241740faf93494b7e7421699b5b462583ba5dbb8'
)

assert result['class_counts'] == \
    expected_classes

assert result['contract_field_count'] == 36

assert (
    result['visit_occurrence_id_present']
    is False
)

assert (
    result['processing_run_id']
    == raw_context['processing_run_id']
)

assert (
    result['processing_run_id']
    == 'encounter-20261008T234726Z-1658454'
)

assert (
    result['raw_publish_run_id']
    == raw_context['raw_publish_run_id']
)

assert (
    result['raw_publish_run_id']
    == 'encounter-raw-20261009T005128Z-1681690'
)

assert result['source_system'] == 'synthea'

assert result['s3_write_verified'] is True
assert result['candidate_published_verified'] is True

assert result['dq_published'] is False
assert result['manifest_published'] is False
assert result['postgresql_write'] is False

result_path = (
    report
    / 'independent-validation-result.json'
)

result_path.write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

sha = hashlib.sha256(
    result_path.read_bytes()
).hexdigest()

print('INDEPENDENT_RESULT_PARSE=PASS')
print('ROWS=5799')
print('UNIQUE_BUSINESS_KEYS=5799')
print('REFERENCED_PERSONS=113')
print('CONTRACT_FIELD_COUNT=36')
print('VISIT_OCCURRENCE_ID_PRESENT=NO')
print(
    'PROCESSING_RUN_ID='
    + result['processing_run_id']
)
print(
    'RAW_PUBLISH_RUN_ID='
    + result['raw_publish_run_id']
)
print(
    'PERSON_MAP_FINGERPRINT='
    + result['person_map_fingerprint']
)
print(
    'INDEPENDENT_RESULT_SHA256='
    + sha
)
PY_RESULT

echo '=== 13. Verify Reservation remains held after readback ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-after.json"

python3 - \
  "$REPORT/reservation-after.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_LOCK_AFTER'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('RESERVATION_AFTER_READBACK=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK_AFTER

echo '=== 14. Persist independent readback state ==='

python3 - \
  "$REPORT" \
  "$RUN_ID" \
  "$VALIDATOR_CM" \
  "$VALIDATOR_APP" \
  "$DRIVER" \
  "$LAUNCH_STATE" \
  "$PLAN" \
  "$F2_STATE" \
  "$C3B_STATE" \
  <<'PY_FINAL'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report = Path(sys.argv[1])
run_id = sys.argv[2]
cm_name = sys.argv[3]
app_name = sys.argv[4]
driver = sys.argv[5]

launch = Path(sys.argv[6])
plan = Path(sys.argv[7])
f2 = Path(sys.argv[8])
c3b = Path(sys.argv[9])

result_path = (
    report
    / 'independent-validation-result.json'
)

result = json.loads(
    result_path.read_bytes()
)

def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G2C2C3D2B2',

    'status':
        'INDEPENDENT_S3_READBACK_PASS',

    'run_id':
        run_id,

    'validator_runtime_configmap':
        cm_name,

    'validator_spark_application':
        app_name,

    'validator_driver_pod':
        driver,

    'validator_spark_state':
        'COMPLETED',

    'atomic_launch_state_sha256':
        sha(launch),

    'plan_sha256':
        sha(plan),

    'f2_state_sha256':
        sha(f2),

    'c3b_state_sha256':
        sha(c3b),

    'validation_result_sha256':
        sha(result_path),

    'rows':
        result['rows'],

    'unique_business_keys':
        result['unique_business_keys'],

    'referenced_persons':
        result['referenced_persons'],

    'contract_field_count':
        result['contract_field_count'],

    'person_map_fingerprint':
        result['person_map_fingerprint'],

    'processing_run_id':
        result['processing_run_id'],

    'raw_publish_run_id':
        result['raw_publish_run_id'],

    'class_counts':
        result['class_counts'],

    'visit_occurrence_id_present':
        False,

    'candidate_published_verified':
        True,

    's3_write_verified':
        True,

    'dq_published':
        False,

    'manifest_published':
        False,

    'postgresql_write':
        False,

    'reservation_released':
        False,

    'automatic_cleanup':
        False,

    'verified_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

target = report / 'run-state.json'

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('INDEPENDENT_READBACK_STATE=PASS')
print(
    'INDEPENDENT_READBACK_STATE_FILE='
    + str(target)
)
print(
    'INDEPENDENT_READBACK_STATE_SHA256='
    + sha(target)
)
PY_FINAL

echo '=== 15. Independent persisted-data verdict ==='

echo 'INDEPENDENT_S3_READBACK=PASS'

echo 'ROWS=5799'
echo 'UNIQUE_BUSINESS_KEYS=5799'
echo 'REFERENCED_PERSONS=113'
echo 'CONTRACT_FIELD_COUNT=36'

echo 'CANDIDATE_PUBLISHED_VERIFIED=YES'
echo 'S3_WRITE_VERIFIED=YES'

echo 'DQ_PUBLISHED=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'DATABASE_WRITE=NO'

echo 'RESERVATION_STILL_HELD=YES'

echo 'STEP05G2C2C3D2B2_INDEPENDENT_READBACK=PASS'

echo '--- VALIDATOR DRIVER LOG TAIL BEGIN ---'
tail -n 80 "$REPORT/validator-driver.log"
echo '--- VALIDATOR DRIVER LOG TAIL END ---'
