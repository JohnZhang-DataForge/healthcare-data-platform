#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G3B2 PROCESSED DQ PUBLICATION SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3B2 PROCESSED DQ PUBLICATION SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from saved Bash file'
  exit 2
}

cd "$ROOT"

for rel in \
  spark/apps/visit/publish_processed_dq.py \
  runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/dq-result.json \
  runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/run-state.json
do
  [[ -s "$rel" && ! -L "$rel" ]] || {
    echo "ERROR: prerequisite missing or unsafe: $rel"
    exit 2
  }
done

STAGE=$(
  mktemp -d \
    /data/spark/temp_shell/g3b2.XXXXXXXX
)

mkdir -p \
  "$STAGE/scripts/task003"

cat > "$STAGE/scripts/task003/05g3b2-publish-processed-dq.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$ROOT/runtime/reports/task003/step05"

EXPECTED_CHECKPOINT=09bc2d89f37dd30c67ab2755682d2d75387a0182

EXPECTED_DQ_SHA=58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2
EXPECTED_DQ_SIZE=2607

REPORT=''
FINAL_STATE='UNKNOWN'
RUNTIME_CM_CREATED=NO
PUBLISHER_APP_CREATED=NO

echo '#### TASK003 STEP05G3B2 PROCESSED DQ PUBLICATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || {
    echo "DQ_PUBLICATION_REPORT=$REPORT"
  }

  echo "FINAL_DQ_PUBLISHER_STATE=$FINAL_STATE"
  echo "DQ_RUNTIME_CONFIGMAP_CREATED=$RUNTIME_CM_CREATED"
  echo "DQ_SPARKAPPLICATION_CREATED=$PUBLISHER_APP_CREATED"

  echo 'RESERVATION_RELEASED=NO'
  echo 'AUTOMATIC_RUNTIME_CONFIGMAP_DELETE=NO'
  echo 'AUTOMATIC_SPARKAPPLICATION_DELETE=NO'
  echo 'MANIFEST_AUTOMATIC_PUBLICATION=NO'

  echo "DQ_PUBLICATION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3B2 PROCESSED DQ PUBLICATION OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

[[ $# -eq 6 ]] || {
  echo "Usage:"
  echo "$0 RUN_ID GIT_CHECKPOINT READBACK_REPORT PLAN DQ_BUILD_DIR C3B_REPORT"
  exit 2
}

RUN_ID="$1"
CHECKPOINT="$2"
READBACK_REPORT="$3"
PLAN="$4"
DQ_BUILD_DIR="$5"
C3B_REPORT="$6"

READBACK_STATE="$READBACK_REPORT/run-state.json"

DQ_FILE="$DQ_BUILD_DIR/dq-result.json"
DQ_BUILD_STATE="$DQ_BUILD_DIR/run-state.json"

C3B_STATE="$C3B_REPORT/run-state.json"

PUBLISHER="$ROOT/spark/apps/visit/publish_processed_dq.py"

for path in \
  "$READBACK_STATE" \
  "$PLAN" \
  "$DQ_FILE" \
  "$DQ_BUILD_STATE" \
  "$C3B_STATE" \
  "$PUBLISHER"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

for cmd in \
  kubectl \
  python3 \
  sha256sum \
  git
do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: required command missing: $cmd"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/processed-dq-publication.XXXXXXXX"
)

# ============================================================
# 1. Exact Git checkpoint
# ============================================================

echo '=== 1. Verify exact DQ pre-publication Git checkpoint ==='

cd "$ROOT"

CURRENT_HEAD=$(
  git rev-parse HEAD
)

echo "CURRENT_HEAD=$CURRENT_HEAD"
echo "EXPECTED_HEAD=$EXPECTED_CHECKPOINT"

[[ "$CHECKPOINT" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: supplied checkpoint does not match approved checkpoint'
  exit 1
}

[[ "$CURRENT_HEAD" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: repository HEAD changed after DQ pre-publication checkpoint'
  exit 1
}

git cat-file -e \
  "${CHECKPOINT}^{commit}"

echo 'DQ_PREPUBLISH_GIT_CHECKPOINT=PASS'

# ============================================================
# 2. Verify immutable local DQ
# ============================================================

echo '=== 2. Verify immutable local DQ artifact and G3A state ==='

ACTUAL_DQ_SHA=$(
  sha256sum "$DQ_FILE" |
  awk '{print $1}'
)

ACTUAL_DQ_SIZE=$(
  wc -c < "$DQ_FILE" |
  tr -d ' '
)

[[ "$ACTUAL_DQ_SHA" == "$EXPECTED_DQ_SHA" ]] || {
  echo 'ERROR: local DQ SHA drift'
  exit 1
}

[[ "$ACTUAL_DQ_SIZE" == "$EXPECTED_DQ_SIZE" ]] || {
  echo 'ERROR: local DQ size drift'
  exit 1
}

python3 - \
  "$PLAN" \
  "$DQ_BUILD_STATE" \
  "$DQ_FILE" \
  "$RUN_ID" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  <<'PY_DQ'
import hashlib
import json
import sys
from pathlib import Path

plan_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
dq_path = Path(sys.argv[3])

run_id = sys.argv[4]
expected_sha = sys.argv[5]
expected_size = int(sys.argv[6])

plan = json.loads(
    plan_path.read_bytes()
)

state = json.loads(
    state_path.read_bytes()
)

dq_bytes = dq_path.read_bytes()

dq = json.loads(
    dq_bytes
)

actual_sha = hashlib.sha256(
    dq_bytes
).hexdigest()

assert plan['run_id'] == run_id

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G3A',
    'DQ_BUILT_NOT_PUBLISHED',
)

assert state['run_id'] == run_id

assert state['dq_result_sha256'] == expected_sha
assert actual_sha == expected_sha

assert state['dq_result_size_bytes'] == expected_size
assert len(dq_bytes) == expected_size

assert state['processed_data_verified'] is True
assert state['s3_write_verified'] is True
assert state['candidate_published_verified'] is True

assert state['dq_published'] is False
assert state['manifest_published'] is False
assert state['reservation_released'] is False
assert state['postgresql_write'] is False

assert dq['status'] == 'PASS'
assert dq['run_id'] == run_id

assert dq['dq_uri'] == plan['dq_uri']
assert dq['manifest_uri'] == plan['manifest_uri']

assert (
    dq['publication_gate']
    ['manifest_published_at_build_time']
    is False
)

assert (
    dq['publication_gate']
    ['reservation_must_remain_held']
    is True
)

print('LOCAL_DQ_ARTIFACT=PASS')
print('DQ_SHA256=' + actual_sha)
print('DQ_SIZE_BYTES=' + str(len(dq_bytes)))
print('DQ_URI=' + dq['dq_uri'])
print('MANIFEST_URI=' + dq['manifest_uri'])
PY_DQ

# ============================================================
# 3. Verify independent data-readback state
# ============================================================

echo '=== 3. Verify Processed data remains independently verified ==='

python3 - \
  "$READBACK_STATE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_READBACK'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

run_id = sys.argv[2]
report = Path(sys.argv[3])

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G2C2C3D2B2',
    'INDEPENDENT_S3_READBACK_PASS',
)

assert state['run_id'] == run_id
assert state['validator_spark_state'] == 'COMPLETED'

assert state['rows'] == 5799
assert state['unique_business_keys'] == 5799
assert state['referenced_persons'] == 113
assert state['contract_field_count'] == 36

assert state['candidate_published_verified'] is True
assert state['s3_write_verified'] is True

assert state['dq_published'] is False
assert state['manifest_published'] is False
assert state['postgresql_write'] is False
assert state['reservation_released'] is False

report.joinpath(
    'template-app.txt'
).write_text(
    state['validator_spark_application']
    + '\n'
)

report.joinpath(
    'template-cm.txt'
).write_text(
    state['validator_runtime_configmap']
    + '\n'
)

print('INDEPENDENT_DATA_READBACK_STATE=PASS')
print(
    'TEMPLATE_SPARK_APPLICATION='
    + state['validator_spark_application']
)
print(
    'TEMPLATE_RUNTIME_CONFIGMAP='
    + state['validator_runtime_configmap']
)
PY_READBACK

TEMPLATE_APP=$(
  tr -d '\r\n' \
  < "$REPORT/template-app.txt"
)

TEMPLATE_CM=$(
  tr -d '\r\n' \
  < "$REPORT/template-cm.txt"
)

# ============================================================
# 4. Verify live Reservation
# ============================================================

echo '=== 4. Verify live Writer Reservation before DQ publication ==='

python3 - \
  "$C3B_STATE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_LOCK_META'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

run_id = sys.argv[2]
report = Path(sys.argv[3])

assert state['run_id'] == run_id

assert state['status'] == \
    'POSTLOCK_PREFLIGHT_PASS'

assert state['fresh_s3_relist_passed'] is True
assert state['reservation_still_held'] is True

for key in (
    'reservation_name',
    'reservation_uid',
    'reservation_resource_version',
):
    report.joinpath(
        key + '.txt'
    ).write_text(
        str(state[key]) + '\n'
    )

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
PY_LOCK_META

LOCK=$(
  tr -d '\r\n' \
  < "$REPORT/reservation_name.txt"
)

LOCK_UID=$(
  tr -d '\r\n' \
  < "$REPORT/reservation_uid.txt"
)

LOCK_RV=$(
  tr -d '\r\n' \
  < "$REPORT/reservation_resource_version.txt"
)

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

print('RESERVATION_BEFORE_DQ_PUBLICATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK

# ============================================================
# 5. Capture successful readback SparkApplication as template
# ============================================================

echo '=== 5. Validate successful Spark runtime template ==='

kubectl -n dw-spark \
  get sparkapplication "$TEMPLATE_APP" \
  -o json \
  > "$REPORT/template-sparkapplication.json"

python3 - \
  "$REPORT/template-sparkapplication.json" \
  <<'PY_TEMPLATE'
import json
import sys
from pathlib import Path

app = json.loads(
    Path(sys.argv[1]).read_bytes()
)

state = (
    app.get('status', {})
    .get('applicationState', {})
    .get('state')
)

assert state == 'COMPLETED'

assert (
    app['metadata']['namespace']
    == 'dw-spark'
)

print('SPARK_RUNTIME_TEMPLATE=PASS')
PY_TEMPLATE

# ============================================================
# 6. Build new immutable Runtime ConfigMap + SparkApplication
# ============================================================

echo '=== 6. Build DQ publication Runtime ConfigMap and SparkApplication ==='

python3 - \
  "$REPORT/template-sparkapplication.json" \
  "$TEMPLATE_CM" \
  "$PUBLISHER" \
  "$DQ_FILE" \
  "$DQ_BUILD_STATE" \
  "$PLAN" \
  "$RUN_ID" \
  "$CHECKPOINT" \
  "$REPORT" \
  <<'PY_BUILD'
import copy
import hashlib
import json
import sys
from pathlib import Path

template_path = Path(sys.argv[1])
template_cm = sys.argv[2]

publisher_path = Path(sys.argv[3])
dq_path = Path(sys.argv[4])
build_state_path = Path(sys.argv[5])
plan_path = Path(sys.argv[6])

run_id = sys.argv[7]
checkpoint = sys.argv[8]
report = Path(sys.argv[9])

template = json.loads(
    template_path.read_bytes()
)

files = {
    'publisher.py':
        publisher_path.read_text(),

    'dq-result.json':
        dq_path.read_text(),

    'build-state.json':
        build_state_path.read_text(),

    'plan.json':
        plan_path.read_text(),
}

payload_bytes = sum(
    len(name.encode('utf-8'))
    + len(content.encode('utf-8'))
    for name, content in files.items()
)

assert payload_bytes < 750000

fingerprint = hashlib.sha256()

for name in sorted(files):
    fingerprint.update(
        name.encode('utf-8')
    )
    fingerprint.update(b'\0')
    fingerprint.update(
        files[name].encode('utf-8')
    )
    fingerprint.update(b'\0')

fingerprint.update(
    run_id.encode('utf-8')
)

fingerprint.update(
    checkpoint.encode('utf-8')
)

token = fingerprint.hexdigest()

runtime_cm = (
    'visit-proc-dq-runtime-'
    + token[:24]
)

spark_app_name = (
    'visit-proc-dq-publish-'
    + token[:20]
)

spec = copy.deepcopy(
    template['spec']
)

matches = []

for volume in spec.get(
    'volumes',
    [],
):
    config_map = volume.get(
        'configMap'
    )

    if (
        isinstance(config_map, dict)
        and config_map.get('name')
        == template_cm
    ):
        matches.append(
            volume
        )

assert len(matches) == 1

runtime_volume = matches[0]

runtime_volume_name = (
    runtime_volume['name']
)

driver_mounts = [
    mount
    for mount in (
        spec.get(
            'driver',
            {}
        )
        .get(
            'volumeMounts',
            []
        )
    )
    if (
        mount.get('name')
        == runtime_volume_name
    )
]

assert len(driver_mounts) == 1

mount = driver_mounts[0]

assert not mount.get(
    'subPath'
)

mount_path = mount[
    'mountPath'
]

assert isinstance(
    mount_path,
    str,
)

assert mount_path.startswith(
    '/'
)

runtime_volume['configMap'] = {
    'name':
        runtime_cm,

    'items': [
        {
            'key':
                name,

            'path':
                name,
        }
        for name in files
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
    + mounted(
        'publisher.py'
    )
)

spec['arguments'] = [
    '--dq-file',
    mounted(
        'dq-result.json'
    ),

    '--build-state',
    mounted(
        'build-state.json'
    ),

    '--plan',
    mounted(
        'plan.json'
    ),
]

spec['restartPolicy'] = {
    'type':
        'Never'
}

spec.pop(
    'timeToLiveSeconds',
    None,
)

spark_conf = spec.get(
    'sparkConf'
)

if isinstance(
    spark_conf,
    dict,
):
    if (
        'spark.app.name'
        in spark_conf
    ):
        spark_conf[
            'spark.app.name'
        ] = spark_app_name

configmap = {
    'apiVersion':
        'v1',

    'kind':
        'ConfigMap',

    'metadata': {
        'name':
            runtime_cm,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task-003',

            'purpose':
                'processed-dq-publication',
        },
    },

    'immutable':
        True,

    'data':
        files,
}

spark_app = {
    'apiVersion':
        template['apiVersion'],

    'kind':
        template['kind'],

    'metadata': {
        'name':
            spark_app_name,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task-003',

            'purpose':
                'processed-dq-publication',
        },
    },

    'spec':
        spec,
}

cm_path = (
    report
    / 'dq-runtime-configmap.json'
)

app_path = (
    report
    / 'dq-sparkapplication.json'
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
    'dq-runtime-cm-name.txt'
).write_text(
    runtime_cm + '\n'
)

report.joinpath(
    'dq-app-name.txt'
).write_text(
    spark_app_name + '\n'
)

print(
    'DQ_RUNTIME_PAYLOAD_BYTES='
    + str(payload_bytes)
)

print(
    'DQ_RUNTIME_VOLUME='
    + runtime_volume_name
)

print(
    'DQ_RUNTIME_MOUNT_PATH='
    + mount_path
)

print(
    'DQ_RUNTIME_CONFIGMAP_NAME='
    + runtime_cm
)

print(
    'DQ_SPARK_APPLICATION_NAME='
    + spark_app_name
)

print(
    'DQ_MAIN_APPLICATION_FILE='
    + spec['mainApplicationFile']
)

print(
    'DQ_RUNTIME_BUILD=PASS'
)
PY_BUILD

RUNTIME_CM=$(
  tr -d '\r\n' \
  < "$REPORT/dq-runtime-cm-name.txt"
)

PUBLISHER_APP=$(
  tr -d '\r\n' \
  < "$REPORT/dq-app-name.txt"
)

CM_MANIFEST="$REPORT/dq-runtime-configmap.json"
APP_MANIFEST="$REPORT/dq-sparkapplication.json"

# ============================================================
# 7. Client dry-run
# ============================================================

echo '=== 7. Kubernetes client dry-run ==='

kubectl create \
  --dry-run=client \
  -f "$CM_MANIFEST" \
  >/dev/null

kubectl create \
  --dry-run=client \
  -f "$APP_MANIFEST" \
  >/dev/null

echo 'DQ_KUBERNETES_DRY_RUN=PASS'

# ============================================================
# 8. No runtime collision
# ============================================================

echo '=== 8. Ensure DQ publication runtime objects do not exist ==='

if kubectl -n dw-spark \
    get configmap "$RUNTIME_CM" \
    >/dev/null 2>&1
then
  echo 'ERROR: DQ Runtime ConfigMap already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

if kubectl -n dw-spark \
    get sparkapplication "$PUBLISHER_APP" \
    >/dev/null 2>&1
then
  echo 'ERROR: DQ SparkApplication already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 4
fi

echo 'DQ_RUNTIME_CONFLICTS=NONE'

# ============================================================
# 9. Final Reservation verification
# ============================================================

echo '=== 9. Final Reservation verification before DQ mutation ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-final-precreate.json"

python3 - \
  "$REPORT/reservation-final-precreate.json" \
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

print('FINAL_RESERVATION_BEFORE_DQ_MUTATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_FINAL_LOCK

# ============================================================
# 10. Create immutable Runtime ConfigMap
# ============================================================

echo '=== 10. CREATE immutable DQ Runtime ConfigMap ==='

kubectl create \
  -f "$CM_MANIFEST" \
  -o json \
  > "$REPORT/dq-runtime-configmap-create.json"

RUNTIME_CM_CREATED=YES

echo 'DQ_RUNTIME_CONFIGMAP_CREATE=PASS'

# ============================================================
# 11. Submit DQ Publisher SparkApplication
# ============================================================

echo '=== 11. CREATE DQ Publisher SparkApplication ==='

if kubectl create \
    -f "$APP_MANIFEST" \
    -o json \
    > "$REPORT/dq-sparkapplication-create.json"
then
  PUBLISHER_APP_CREATED=YES
else
  echo 'DQ_SPARKAPPLICATION_CREATE=FAIL'
  echo 'AUTOMATIC_RUNTIME_CONFIGMAP_DELETE=NO'
  echo 'AUTOMATIC_RESERVATION_DELETE=NO'
  exit 1
fi

echo 'DQ_SPARKAPPLICATION_CREATE=PASS'

# ============================================================
# 12. Observe to terminal state
# ============================================================

echo '=== 12. Observe DQ Publisher SparkApplication ==='

LAST_STATE=''

for attempt in $(seq 1 180); do

  kubectl -n dw-spark \
    get sparkapplication "$PUBLISHER_APP" \
    -o json \
    > "$REPORT/dq-sparkapplication-current.json"

  STATE=$(
    python3 - \
      "$REPORT/dq-sparkapplication-current.json" \
      <<'PY_STATE'
import json
import sys
from pathlib import Path

obj = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    obj.get(
        'status',
        {},
    )
    .get(
        'applicationState',
        {},
    )
    .get(
        'state',
        'NOT_REPORTED',
    )
)
PY_STATE
  )

  if [[ "$STATE" != "$LAST_STATE" ]]; then
    echo "DQ_SPARK_APPLICATION_STATE=$STATE"
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
  echo 'ERROR: DQ Publisher did not reach terminal state'
  exit 3
fi

kubectl -n dw-spark \
  get sparkapplication "$PUBLISHER_APP" \
  -o json \
  > "$REPORT/dq-sparkapplication-final.json"

echo "DQ_PUBLISHER_TERMINAL_STATE=$FINAL_STATE"

# ============================================================
# 13. Capture Driver log
# ============================================================

echo '=== 13. Capture DQ Publisher Driver log ==='

DRIVER=$(
  python3 - \
    "$REPORT/dq-sparkapplication-final.json" \
    <<'PY_DRIVER'
import json
import sys
from pathlib import Path

obj = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    obj.get(
        'status',
        {},
    )
    .get(
        'driverInfo',
        {},
    )
    .get(
        'podName',
        '',
    )
)
PY_DRIVER
)

[[ -n "$DRIVER" ]] || {
  echo 'ERROR: DQ Publisher Driver pod not reported'
  exit 1
}

echo "DQ_PUBLISHER_DRIVER_POD=$DRIVER"

kubectl -n dw-spark \
  get pod "$DRIVER" \
  -o json \
  > "$REPORT/dq-driver-pod.json"

kubectl -n dw-spark \
  logs "$DRIVER" \
  --timestamps \
  > "$REPORT/dq-driver.log"

echo 'DQ_PUBLISHER_DRIVER_LOG_CAPTURE=PASS'

if [[ "$FINAL_STATE" != COMPLETED ]]; then

  echo '--- DQ PUBLISHER DRIVER LOG TAIL BEGIN ---'
  tail -n 120 \
    "$REPORT/dq-driver.log"
  echo '--- DQ PUBLISHER DRIVER LOG TAIL END ---'

  echo 'DQ_PUBLICATION_VERIFIED=NO'
  echo 'MANIFEST_PUBLISHED=NO'
  echo 'AUTOMATIC_CLEANUP=NO'

  exit 4
fi

# ============================================================
# 14. Parse publisher result
# ============================================================

echo '=== 14. Parse and verify DQ publication result ==='

python3 - \
  "$REPORT/dq-driver.log" \
  "$PLAN" \
  "$RUN_ID" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$REPORT" \
  <<'PY_RESULT'
import hashlib
import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
run_id = sys.argv[3]
expected_sha = sys.argv[4]
expected_size = int(sys.argv[5])
report = Path(sys.argv[6])

plan = json.loads(
    plan_path.read_bytes()
)

marker = (
    'PROCESSED_DQ_PUBLICATION_RESULT='
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
            json.loads(
                payload
            )
        )

assert len(matches) == 1, (
    'expected exactly one DQ publication result, '
    f'found {len(matches)}'
)

result = matches[0]

assert result['status'] == \
    'DQ_PUBLICATION_PASS'

assert result[
    'publication_status'
] in (
    'CREATED',
    'REUSED_IDENTICAL',
)

assert result['run_id'] == run_id

assert result['dq_uri'] == \
    plan['dq_uri']

assert result['dq_sha256'] == \
    expected_sha

assert result['dq_size_bytes'] == \
    expected_size

assert result['dq_published'] is True
assert result['dq_readback_verified'] is True

assert result['manifest_uri'] == \
    plan['manifest_uri']

assert result['manifest_published'] is False

assert (
    result['reservation_release_requested']
    is False
)

assert result['postgresql_write'] is False

target = (
    report
    / 'dq-publication-result.json'
)

target.write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

result_sha = hashlib.sha256(
    target.read_bytes()
).hexdigest()

print('DQ_PUBLICATION_RESULT_PARSE=PASS')

print(
    'DQ_PUBLICATION_STATUS='
    + result['publication_status']
)

print(
    'DQ_SHA256='
    + result['dq_sha256']
)

print(
    'DQ_SIZE_BYTES='
    + str(result['dq_size_bytes'])
)

print(
    'DQ_PUBLICATION_RESULT_SHA256='
    + result_sha
)

print('DQ_PUBLISHED=YES')
print('DQ_READBACK_VERIFIED=YES')
print('MANIFEST_PUBLISHED=NO')
print('DATABASE_WRITE=NO')
PY_RESULT

# ============================================================
# 15. Reservation must still be held after DQ write
# ============================================================

echo '=== 15. Verify Reservation after DQ publication ==='

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

print('RESERVATION_AFTER_DQ_PUBLICATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK_AFTER

# ============================================================
# 16. Persist G3B2 evidence
# ============================================================

echo '=== 16. Persist DQ publication evidence ==='

python3 - \
  "$REPORT" \
  "$RUN_ID" \
  "$RUNTIME_CM" \
  "$PUBLISHER_APP" \
  "$DRIVER" \
  "$CHECKPOINT" \
  "$PLAN" \
  "$DQ_BUILD_STATE" \
  "$DQ_FILE" \
  <<'PY_FINAL'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report = Path(sys.argv[1])
run_id = sys.argv[2]

runtime_cm = sys.argv[3]
publisher_app = sys.argv[4]
driver = sys.argv[5]
checkpoint = sys.argv[6]

plan = Path(sys.argv[7])
build_state = Path(sys.argv[8])
dq_file = Path(sys.argv[9])

result_path = (
    report
    / 'dq-publication-result.json'
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
        'STEP-05G3B2',

    'status':
        'DQ_PUBLICATION_PASS',

    'run_id':
        run_id,

    'git_checkpoint':
        checkpoint,

    'runtime_configmap':
        runtime_cm,

    'spark_application':
        publisher_app,

    'driver_pod':
        driver,

    'spark_application_state':
        'COMPLETED',

    'plan_sha256':
        sha(plan),

    'dq_build_state_sha256':
        sha(build_state),

    'local_dq_sha256':
        sha(dq_file),

    'publication_result_sha256':
        sha(result_path),

    'publication_status':
        result['publication_status'],

    'dq_uri':
        result['dq_uri'],

    'dq_sha256':
        result['dq_sha256'],

    'dq_size_bytes':
        result['dq_size_bytes'],

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

    'manifest_published':
        False,

    'reservation_released':
        False,

    'postgresql_write':
        False,

    'automatic_cleanup':
        False,

    'verified_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

target = (
    report
    / 'run-state.json'
)

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('DQ_PUBLICATION_STATE=PASS')

print(
    'DQ_PUBLICATION_STATE_FILE='
    + str(target)
)

print(
    'DQ_PUBLICATION_STATE_SHA256='
    + sha(target)
)
PY_FINAL

# ============================================================
# 17. Final verdict
# ============================================================

echo '=== 17. Final DQ publication verdict ==='

echo 'STEP05G3B2_DQ_PUBLICATION=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'CANDIDATE_PUBLISHED_VERIFIED=YES'
echo 'S3_WRITE_VERIFIED=YES'

echo 'DQ_BUILT=YES'
echo 'DQ_PUBLISHED=YES'
echo 'DQ_READBACK_VERIFIED=YES'

echo "DQ_SHA256=$EXPECTED_DQ_SHA"
echo "DQ_SIZE_BYTES=$EXPECTED_DQ_SIZE"

echo 'MANIFEST_PUBLISHED=NO'
echo 'RESERVATION_STILL_HELD=YES'
echo 'DATABASE_WRITE=NO'

echo '--- DQ PUBLISHER DRIVER LOG TAIL BEGIN ---'
tail -n 80 \
  "$REPORT/dq-driver.log"
echo '--- DQ PUBLISHER DRIVER LOG TAIL END ---'
RUNNER

# ============================================================
# Static validation
# ============================================================

echo '=== 1. Runner syntax and safety checks ==='

bash -n \
  "$STAGE/scripts/task003/05g3b2-publish-processed-dq.sh"

python3 - \
  "$STAGE/scripts/task003/05g3b2-publish-processed-dq.sh" \
  <<'PY_STATIC'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    'DQ_PREPUBLISH_GIT_CHECKPOINT=PASS',
    'FINAL_RESERVATION_BEFORE_DQ_MUTATION=PASS',
    'DQ_RUNTIME_CONFIGMAP_CREATE=PASS',
    'DQ_SPARKAPPLICATION_CREATE=PASS',
    'DQ_PUBLICATION_RESULT_PARSE=PASS',
    'DQ_PUBLISHED=YES',
    'DQ_READBACK_VERIFIED=YES',
    'MANIFEST_PUBLISHED=NO',
    'RESERVATION_STILL_HELD=YES',
)

for token in required:
    assert token in source, token

for forbidden in (
    'kubectl apply',
    'kubectl delete',
    'aws s3 rm',
    'aws s3 cp',
    'manifest.json" >',
    'RESERVATION_RELEASED=YES',
):
    assert forbidden not in source, forbidden

print('G3B2_RUNNER_STATIC_CHECK=PASS')
print('CREATE_ONLY_K8S_MUTATION=PASS')
print('AUTOMATIC_CLEANUP_ABSENT=PASS')
print('MANIFEST_PUBLICATION_PATH_ABSENT=PASS')
PY_STATIC

# ============================================================
# Canonical install
# ============================================================

echo '=== 2. Canonical conflict check ==='

FILE=scripts/task003/05g3b2-publish-processed-dq.sh
GEN=scripts/task003/05g3b2-prepare-processed-dq-publication.sh

if [[ -L "$ROOT/$FILE" ]] || {
  [[ -e "$ROOT/$FILE" ]] &&
  ! cmp -s "$STAGE/$FILE" "$ROOT/$FILE"
}; then
  echo "ERROR: canonical source conflict: $FILE"
  exit 1
fi

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "$SOURCE" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

echo '=== 3. Install canonical runner and generator ==='

mkdir -p \
  "$ROOT/scripts/task003"

if [[ -f "$ROOT/$FILE" ]] &&
   cmp -s "$STAGE/$FILE" "$ROOT/$FILE"
then
  echo "CANONICAL_SOURCE_REUSED=$FILE"
else
  install \
    -m 755 \
    "$STAGE/$FILE" \
    "$ROOT/$FILE"

  echo "CANONICAL_SOURCE_READY=$FILE"
fi

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G3B2_SOURCE=PASS'

echo 'DQ_PUBLICATION_EXECUTED_BY_INSTALLER=NO'
echo 'DQ_PUBLISHED_BY_INSTALLER=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'RESERVATION_RELEASED=NO'
echo 'S3_MUTATION_BY_INSTALLER=NO'
echo 'DATABASE_MUTATION=NO'
