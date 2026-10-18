#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$ROOT/runtime/reports/task003/step05"
NS=dw-spark

EXPECTED_CHECKPOINT=755512a89cd8f4f7b67c422ca1544589ea7e4a6b

EXPECTED_MANIFEST_SHA=1435b6c3a98e2320b831faf26e2b8ecf59472b980b972fab856b35ae4d6829af
EXPECTED_MANIFEST_SIZE=3141

EXPECTED_DQ_SHA=58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2
EXPECTED_DQ_SIZE=2607

S3_ENDPOINT=http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
S3_SECRET=dw-spark-s3-secret

REPORT=''
FINAL_STATE='UNKNOWN'
RUNTIME_CM_CREATED=NO
PUBLISHER_APP_CREATED=NO

echo '#### TASK003 STEP05G4C2 PROCESSED MANIFEST PUBLICATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || \
    echo "MANIFEST_PUBLICATION_REPORT=$REPORT"

  echo "FINAL_MANIFEST_PUBLISHER_STATE=$FINAL_STATE"
  echo "MANIFEST_RUNTIME_CONFIGMAP_CREATED=$RUNTIME_CM_CREATED"
  echo "MANIFEST_SPARKAPPLICATION_CREATED=$PUBLISHER_APP_CREATED"

  echo 'RESERVATION_RELEASED=NO'
  echo 'PUBLISHER_RUNTIME_AUTOMATIC_DELETE=NO'
  echo 'PUBLISHER_SPARKAPPLICATION_AUTOMATIC_DELETE=NO'
  echo 'DATABASE_WRITE=NO'

  echo "MANIFEST_PUBLICATION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G4C2 PROCESSED MANIFEST PUBLICATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 7 ]] || {
  echo "Usage:"
  echo "$0 RUN_ID GIT_CHECKPOINT PLAN MANIFEST_BUILD_DIR DQ_PUBLICATION_REPORT C3B_REPORT READBACK_REPORT"
  exit 2
}

RUN_ID="$1"
CHECKPOINT="$2"
PLAN="$3"
MANIFEST_BUILD_DIR="$4"
DQ_PUBLICATION_REPORT="$5"
C3B_REPORT="$6"
READBACK_REPORT="$7"

MANIFEST_FILE="$MANIFEST_BUILD_DIR/manifest.json"
MANIFEST_BUILD_STATE="$MANIFEST_BUILD_DIR/run-state.json"

DQ_PUBLICATION_STATE="$DQ_PUBLICATION_REPORT/run-state.json"
DQ_PUBLICATION_RESULT="$DQ_PUBLICATION_REPORT/dq-publication-result.json"

C3B_STATE="$C3B_REPORT/run-state.json"
READBACK_STATE="$READBACK_REPORT/run-state.json"

PUBLISHER="$ROOT/spark/apps/visit/publish_processed_manifest.py"

for path in \
  "$PLAN" \
  "$MANIFEST_FILE" \
  "$MANIFEST_BUILD_STATE" \
  "$DQ_PUBLICATION_STATE" \
  "$DQ_PUBLICATION_RESULT" \
  "$C3B_STATE" \
  "$READBACK_STATE" \
  "$PUBLISHER"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

for cmd in kubectl python3 git sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing required command: $cmd"
    exit 2
  }
done

REPORT=$(mktemp -d "$BASE/processed-manifest-publication.XXXXXXXX")

echo '=== 1. Verify exact Manifest Publisher Git checkpoint ==='

cd "$ROOT"

HEAD=$(git rev-parse HEAD)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_CHECKPOINT"

[[ "$CHECKPOINT" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: supplied Git checkpoint drift'
  exit 1
}

[[ "$HEAD" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: HEAD drifted after Manifest Publisher checkpoint'
  exit 1
}

git cat-file -e "${CHECKPOINT}^{commit}"

git diff --quiet -- \
  spark/apps/visit/publish_processed_manifest.py \
  tests/task003/test_processed_manifest_publisher.py \
  scripts/task003/05g4c1-prepare-processed-manifest-publisher-source.sh || {
    echo 'ERROR: committed Manifest Publisher source has local drift'
    exit 1
  }

echo 'MANIFEST_PUBLISHER_GIT_CHECKPOINT=PASS'
echo 'MANIFEST_PUBLISHER_SOURCE_UNCHANGED=PASS'

echo '=== 2. Verify immutable APPROVED local Manifest ==='

ACTUAL_MANIFEST_SHA=$(sha256sum "$MANIFEST_FILE" | awk '{print $1}')
ACTUAL_MANIFEST_SIZE=$(wc -c < "$MANIFEST_FILE" | tr -d ' ')

echo "MANIFEST_SHA256=$ACTUAL_MANIFEST_SHA"
echo "MANIFEST_SIZE_BYTES=$ACTUAL_MANIFEST_SIZE"

[[ "$ACTUAL_MANIFEST_SHA" == "$EXPECTED_MANIFEST_SHA" ]] || {
  echo 'ERROR: Manifest SHA drift'
  exit 1
}

[[ "$ACTUAL_MANIFEST_SIZE" == "$EXPECTED_MANIFEST_SIZE" ]] || {
  echo 'ERROR: Manifest size drift'
  exit 1
}

PYTHONPATH="$ROOT/spark/apps/visit" \
python3 - \
  "$PLAN" \
  "$MANIFEST_BUILD_STATE" \
  "$MANIFEST_FILE" \
  <<'PY_LOCAL'
import json
import sys
from pathlib import Path

from publish_processed_manifest import (
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_MANIFEST_SIZE_BYTES,
    sha256_bytes,
    validate_publication_inputs,
)

plan = json.loads(Path(sys.argv[1]).read_bytes())
state = json.loads(Path(sys.argv[2]).read_bytes())
blob = Path(sys.argv[3]).read_bytes()

manifest = validate_publication_inputs(
    plan,
    state,
    blob,
)

assert sha256_bytes(blob) == EXPECTED_MANIFEST_SHA256
assert len(blob) == EXPECTED_MANIFEST_SIZE_BYTES

print('LOCAL_APPROVED_MANIFEST=PASS')
print('MANIFEST_STATUS=' + manifest['status'])
print(
    'MANIFEST_PUBLICATION_POLICY='
    + manifest['publication_policy']
)
print('READY_FOR_MANIFEST_PUBLICATION=YES')
PY_LOCAL

echo '=== 3. Verify successful DQ publication evidence ==='

python3 - \
  "$DQ_PUBLICATION_STATE" \
  "$DQ_PUBLICATION_RESULT" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$REPORT" \
  <<'PY_DQ_STATE'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_bytes())
result = json.loads(Path(sys.argv[2]).read_bytes())

expected_sha = sys.argv[3]
expected_size = int(sys.argv[4])
report = Path(sys.argv[5])

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G3B2',
    'DQ_PUBLICATION_PASS',
)

assert state['run_id'] == \
    'visit-proc-20261009t192437z-2081886'

assert state['spark_application_state'] == 'COMPLETED'
assert state['dq_published'] is True
assert state['dq_readback_verified'] is True
assert state['dq_sha256'] == expected_sha
assert state['dq_size_bytes'] == expected_size
assert state['manifest_published'] is False
assert state['reservation_released'] is False
assert state['postgresql_write'] is False

assert result['status'] == 'DQ_PUBLICATION_PASS'
assert result['dq_published'] is True
assert result['dq_readback_verified'] is True
assert result['dq_sha256'] == expected_sha
assert result['dq_size_bytes'] == expected_size
assert result['manifest_published'] is False

report.joinpath('template-app.txt').write_text(
    state['spark_application'] + '\n'
)

report.joinpath('template-cm.txt').write_text(
    state['runtime_configmap'] + '\n'
)

print('DQ_PUBLICATION_EVIDENCE=PASS')
print('DQ_PUBLISHED=YES')
print('DQ_READBACK_VERIFIED=YES')
PY_DQ_STATE

TEMPLATE_APP=$(tr -d '\r\n' < "$REPORT/template-app.txt")
TEMPLATE_CM=$(tr -d '\r\n' < "$REPORT/template-cm.txt")

echo '=== 4. Verify independent Processed data state ==='

python3 - \
  "$READBACK_STATE" \
  "$RUN_ID" \
  <<'PY_READBACK'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_bytes())

assert state['run_id'] == sys.argv[2]
assert state['status'] == 'INDEPENDENT_S3_READBACK_PASS'
assert state['validator_spark_state'] == 'COMPLETED'

assert state['rows'] == 5799
assert state['unique_business_keys'] == 5799
assert state['referenced_persons'] == 113
assert state['contract_field_count'] == 36

assert state['s3_write_verified'] is True
assert state['candidate_published_verified'] is True
assert state['postgresql_write'] is False

print('PROCESSED_DATA_READBACK_EVIDENCE=PASS')
PY_READBACK

echo '=== 5. Verify live Reservation ==='

python3 - \
  "$C3B_STATE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY_LOCK_META'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_bytes())

assert state['run_id'] == sys.argv[2]
assert state['status'] == 'POSTLOCK_PREFLIGHT_PASS'
assert state['reservation_still_held'] is True

report = Path(sys.argv[3])

for key in (
    'reservation_name',
    'reservation_uid',
    'reservation_resource_version',
):
    report.joinpath(key + '.txt').write_text(
        str(state[key]) + '\n'
    )

print('RESERVATION_EVIDENCE=PASS')
PY_LOCK_META

LOCK=$(tr -d '\r\n' < "$REPORT/reservation_name.txt")
LOCK_UID=$(tr -d '\r\n' < "$REPORT/reservation_uid.txt")
LOCK_RV=$(tr -d '\r\n' < "$REPORT/reservation_resource_version.txt")

kubectl -n "$NS" get configmap "$LOCK" -o json \
  > "$REPORT/reservation-before.json"

python3 - \
  "$REPORT/reservation-before.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_LOCK'
import json
import sys
from pathlib import Path

live = json.loads(Path(sys.argv[1]).read_bytes())

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('RESERVATION_BEFORE_MANIFEST_PUBLICATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK

echo '=== 6. Resolve canonical S3 targets ==='

mapfile -t TARGETS < <(
  python3 -c '
import json,sys
from urllib.parse import urlparse

p=json.load(open(sys.argv[1]))

def split(uri):
    u=urlparse(uri)
    assert u.scheme=="s3"
    assert u.netloc
    return u.netloc,u.path.lstrip("/")

db,dk=split(p["data_uri"])
qb,qk=split(p["dq_uri"])
mb,mk=split(p["manifest_uri"])

assert db==qb==mb

print(db)
print(dk)
print(qk)
print(mk)
' "$PLAN"
)

BUCKET="${TARGETS[0]}"
DATA_PREFIX="${TARGETS[1]}"
DQ_KEY="${TARGETS[2]}"
MANIFEST_KEY="${TARGETS[3]}"

echo "S3_BUCKET=$BUCKET"
echo "DATA_PREFIX=$DATA_PREFIX"
echo "DQ_KEY=$DQ_KEY"
echo "MANIFEST_KEY=$MANIFEST_KEY"

echo '=== 7. Resolve S3 Secret fields ==='

kubectl -n "$NS" get secret "$S3_SECRET" -o json \
  > "$REPORT/s3-secret-metadata.json"

mapfile -t SECRET_FIELDS < <(
  python3 -c '
import json,sys

x=json.load(open(sys.argv[1]))
keys=set(x.get("data",{}))

a=next((k for k in (
  "AWS_ACCESS_KEY_ID",
  "accessKey",
  "access_key",
  "accessKeyId",
  "access_key_id",
) if k in keys),None)

s=next((k for k in (
  "AWS_SECRET_ACCESS_KEY",
  "secretKey",
  "secret_key",
  "secretAccessKey",
  "secret_access_key",
) if k in keys),None)

if not a or not s:
    raise SystemExit("unsupported S3 Secret structure")

print(a)
print(s)
' "$REPORT/s3-secret-metadata.json"
)

ACCESS_FIELD="${SECRET_FIELDS[0]}"
SECRET_FIELD="${SECRET_FIELDS[1]}"

echo 'S3_SECRET_STRUCTURE=PASS'

echo '=== 8. Fresh remote pre-publication audit ==='

PREFLIGHT_POD="task003-manifest-preflight-$(date -u +%H%M%S)-$$"

python3 - \
  "$PREFLIGHT_POD" \
  "$NS" \
  "$S3_SECRET" \
  "$ACCESS_FIELD" \
  "$SECRET_FIELD" \
  "$S3_ENDPOINT" \
  "$BUCKET" \
  "$DATA_PREFIX" \
  "$DQ_KEY" \
  "$MANIFEST_KEY" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$REPORT/preflight-pod.json" \
  <<'PY_PREFLIGHT'
import json
import sys
from pathlib import Path

(
    pod, namespace, secret, access_field, secret_field,
    endpoint, bucket, data_prefix, dq_key, manifest_key,
    dq_sha, dq_size, target,
) = sys.argv[1:]

script=r'''
set -eu

echo "FINAL_MANIFEST_PREFLIGHT_START=YES"

DATA_COUNT=$(
  aws \
    --endpoint-url "$S3_ENDPOINT" \
    s3api list-objects-v2 \
    --bucket "$S3_BUCKET" \
    --prefix "$DATA_PREFIX" \
    --max-keys 1 \
    --query KeyCount \
    --output text
)

echo "DATA_PREFIX_KEYCOUNT_SAMPLE=$DATA_COUNT"

[ "$DATA_COUNT" -gt 0 ] || {
  echo "DATA_PREFIX_REMOTE_CLASSIFICATION=ABSENT"
  exit 41
}

echo "DATA_PREFIX_REMOTE_CLASSIFICATION=PRESENT"

aws \
  --endpoint-url "$S3_ENDPOINT" \
  s3api get-object \
  --bucket "$S3_BUCKET" \
  --key "$DQ_KEY" \
  /tmp/dq-result.json \
  >/tmp/dq-get.json

DQ_SHA=$(
  sha256sum /tmp/dq-result.json |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c < /tmp/dq-result.json |
  tr -d ' '
)

echo "DQ_REMOTE_SHA256=$DQ_SHA"
echo "DQ_REMOTE_SIZE_BYTES=$DQ_SIZE"

[ "$DQ_SHA" = "$EXPECTED_DQ_SHA" ] || {
  echo "DQ_REMOTE_CLASSIFICATION=PRESENT_CONFLICT"
  exit 42
}

[ "$DQ_SIZE" = "$EXPECTED_DQ_SIZE" ] || {
  echo "DQ_REMOTE_CLASSIFICATION=PRESENT_CONFLICT"
  exit 43
}

echo "DQ_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL"

if aws \
    --endpoint-url "$S3_ENDPOINT" \
    s3api head-object \
    --bucket "$S3_BUCKET" \
    --key "$MANIFEST_KEY" \
    >/tmp/manifest-head.json \
    2>/tmp/manifest-head.err
then
  echo "MANIFEST_REMOTE_CLASSIFICATION=PRESENT"
  exit 44
else
  if grep -Eqi '404|Not Found|NoSuchKey' /tmp/manifest-head.err
  then
    echo "MANIFEST_REMOTE_CLASSIFICATION=ABSENT"
  else
    cat /tmp/manifest-head.err
    echo "MANIFEST_REMOTE_CLASSIFICATION=INSPECTION_ERROR"
    exit 45
  fi
fi

echo "S3_MUTATION_BY_PREFLIGHT=NO"
echo "FINAL_MANIFEST_PREFLIGHT=PASS"
'''

obj={
  "apiVersion":"v1",
  "kind":"Pod",
  "metadata":{
    "name":pod,
    "namespace":namespace,
    "labels":{
      "task":"task-003",
      "purpose":"manifest-final-preflight",
    },
  },
  "spec":{
    "restartPolicy":"Never",
    "nodeSelector":{
      "workload":"platform",
    },
    "containers":[
      {
        "name":"audit",
        "image":"amazon/aws-cli:2.17.60",
        "imagePullPolicy":"IfNotPresent",
        "command":["/bin/sh","-c",script],
        "env":[
          {
            "name":"AWS_ACCESS_KEY_ID",
            "valueFrom":{
              "secretKeyRef":{
                "name":secret,
                "key":access_field,
              }
            },
          },
          {
            "name":"AWS_SECRET_ACCESS_KEY",
            "valueFrom":{
              "secretKeyRef":{
                "name":secret,
                "key":secret_field,
              }
            },
          },
          {"name":"AWS_DEFAULT_REGION","value":"us-east-1"},
          {"name":"AWS_EC2_METADATA_DISABLED","value":"true"},
          {"name":"S3_ENDPOINT","value":endpoint},
          {"name":"S3_BUCKET","value":bucket},
          {"name":"DATA_PREFIX","value":data_prefix},
          {"name":"DQ_KEY","value":dq_key},
          {"name":"MANIFEST_KEY","value":manifest_key},
          {"name":"EXPECTED_DQ_SHA","value":dq_sha},
          {"name":"EXPECTED_DQ_SIZE","value":dq_size},
        ],
      }
    ],
  },
}

Path(target).write_text(
  json.dumps(obj,indent=2,sort_keys=True) + "\n"
)

print("FINAL_PREFLIGHT_POD_MANIFEST=PASS")
PY_PREFLIGHT

kubectl create --dry-run=client \
  -f "$REPORT/preflight-pod.json" >/dev/null

echo 'FINAL_PREFLIGHT_POD_DRY_RUN=PASS'

kubectl create -f "$REPORT/preflight-pod.json" >/dev/null

PREFLIGHT_PHASE=''

for attempt in $(seq 1 90); do
  PREFLIGHT_PHASE=$(
    kubectl -n "$NS" get pod "$PREFLIGHT_POD" \
      -o jsonpath='{.status.phase}' 2>/dev/null || true
  )

  case "$PREFLIGHT_PHASE" in
    Succeeded|Failed)
      break
      ;;
  esac

  sleep 2
done

echo "FINAL_PREFLIGHT_POD_PHASE=$PREFLIGHT_PHASE"

kubectl -n "$NS" logs "$PREFLIGHT_POD" \
  > "$REPORT/preflight.log" 2>&1 || true

echo '--- FINAL MANIFEST PREFLIGHT LOG BEGIN ---'
cat "$REPORT/preflight.log"
echo '--- FINAL MANIFEST PREFLIGHT LOG END ---'

[[ "$PREFLIGHT_PHASE" == "Succeeded" ]] || {
  echo 'ERROR: final Manifest preflight failed'
  echo 'PREFLIGHT_UTILITY_POD_PRESERVED=YES'
  exit 4
}

grep -qx 'DATA_PREFIX_REMOTE_CLASSIFICATION=PRESENT' \
  "$REPORT/preflight.log"

grep -qx 'DQ_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL' \
  "$REPORT/preflight.log"

grep -qx 'MANIFEST_REMOTE_CLASSIFICATION=ABSENT' \
  "$REPORT/preflight.log"

grep -qx 'FINAL_MANIFEST_PREFLIGHT=PASS' \
  "$REPORT/preflight.log"

echo 'DATA_REMOTE_PREFLIGHT=PASS'
echo 'DQ_REMOTE_PREFLIGHT=PASS'
echo 'MANIFEST_REMOTE_PREFLIGHT=ABSENT'
echo 'MANIFEST_LAST_REMOTE_GATE=PASS'

kubectl -n "$NS" delete pod "$PREFLIGHT_POD" \
  --wait=true >/dev/null

echo 'PREFLIGHT_UTILITY_POD_DELETED=YES'

echo '=== 9. Verify successful Spark runtime template ==='

kubectl -n "$NS" get sparkapplication "$TEMPLATE_APP" -o json \
  > "$REPORT/template-sparkapplication.json"

python3 - \
  "$REPORT/template-sparkapplication.json" \
  <<'PY_TEMPLATE'
import json
import sys
from pathlib import Path

app=json.loads(Path(sys.argv[1]).read_bytes())

state=(
  app.get('status',{})
     .get('applicationState',{})
     .get('state')
)

assert state == 'COMPLETED'
assert app['metadata']['namespace'] == 'dw-spark'

print('SPARK_RUNTIME_TEMPLATE=PASS')
PY_TEMPLATE

echo '=== 10. Build immutable Manifest Runtime ConfigMap and SparkApplication ==='

python3 - \
  "$REPORT/template-sparkapplication.json" \
  "$TEMPLATE_CM" \
  "$PUBLISHER" \
  "$MANIFEST_FILE" \
  "$MANIFEST_BUILD_STATE" \
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

template=json.loads(Path(sys.argv[1]).read_bytes())
template_cm=sys.argv[2]

publisher=Path(sys.argv[3])
manifest=Path(sys.argv[4])
build_state=Path(sys.argv[5])
plan=Path(sys.argv[6])

run_id=sys.argv[7]
checkpoint=sys.argv[8]
report=Path(sys.argv[9])

files={
  'publisher.py':publisher.read_text(),
  'manifest.json':manifest.read_text(),
  'build-state.json':build_state.read_text(),
  'plan.json':plan.read_text(),
}

payload_bytes=sum(
  len(k.encode()) + len(v.encode())
  for k,v in files.items()
)

assert payload_bytes < 750000

fingerprint=hashlib.sha256()

for key in sorted(files):
  fingerprint.update(key.encode())
  fingerprint.update(b'\0')
  fingerprint.update(files[key].encode())
  fingerprint.update(b'\0')

fingerprint.update(run_id.encode())
fingerprint.update(checkpoint.encode())

token=fingerprint.hexdigest()

runtime_cm='visit-proc-manifest-runtime-' + token[:24]
app_name='visit-proc-manifest-publish-' + token[:20]

spec=copy.deepcopy(template['spec'])

matches=[]

for volume in spec.get('volumes',[]):
  cm=volume.get('configMap')

  if isinstance(cm,dict) and cm.get('name') == template_cm:
    matches.append(volume)

assert len(matches) == 1

runtime_volume=matches[0]
volume_name=runtime_volume['name']

driver_mounts=[
  m
  for m in spec.get('driver',{}).get('volumeMounts',[])
  if m.get('name') == volume_name
]

assert len(driver_mounts) == 1

mount=driver_mounts[0]

assert not mount.get('subPath')

mount_path=mount['mountPath']

assert mount_path.startswith('/')

runtime_volume['configMap']={
  'name':runtime_cm,
  'items':[
    {'key':key,'path':key}
    for key in files
  ],
}

def mounted(name):
  return mount_path.rstrip('/') + '/' + name

spec['mainApplicationFile']='local://' + mounted('publisher.py')

spec['arguments']=[
  '--manifest-file',
  mounted('manifest.json'),
  '--build-state',
  mounted('build-state.json'),
  '--plan',
  mounted('plan.json'),
]

spec['restartPolicy']={'type':'Never'}
spec.pop('timeToLiveSeconds',None)

spark_conf=spec.get('sparkConf')

if isinstance(spark_conf,dict) and 'spark.app.name' in spark_conf:
  spark_conf['spark.app.name']=app_name

configmap={
  'apiVersion':'v1',
  'kind':'ConfigMap',
  'metadata':{
    'name':runtime_cm,
    'namespace':'dw-spark',
    'labels':{
      'task':'task-003',
      'purpose':'processed-manifest-publication',
    },
  },
  'immutable':True,
  'data':files,
}

spark_app={
  'apiVersion':template['apiVersion'],
  'kind':template['kind'],
  'metadata':{
    'name':app_name,
    'namespace':'dw-spark',
    'labels':{
      'task':'task-003',
      'purpose':'processed-manifest-publication',
    },
  },
  'spec':spec,
}

(report/'manifest-runtime-configmap.json').write_text(
  json.dumps(configmap,indent=2,sort_keys=True) + '\n'
)

(report/'manifest-sparkapplication.json').write_text(
  json.dumps(spark_app,indent=2,sort_keys=True) + '\n'
)

(report/'runtime-cm-name.txt').write_text(runtime_cm + '\n')
(report/'app-name.txt').write_text(app_name + '\n')

print('MANIFEST_RUNTIME_PAYLOAD_BYTES=' + str(payload_bytes))
print('MANIFEST_RUNTIME_CONFIGMAP_NAME=' + runtime_cm)
print('MANIFEST_SPARK_APPLICATION_NAME=' + app_name)
print(
  'MANIFEST_MAIN_APPLICATION_FILE='
  + spec['mainApplicationFile']
)
print('MANIFEST_RUNTIME_BUILD=PASS')
PY_BUILD

RUNTIME_CM=$(tr -d '\r\n' < "$REPORT/runtime-cm-name.txt")
PUBLISHER_APP=$(tr -d '\r\n' < "$REPORT/app-name.txt")

CM_MANIFEST="$REPORT/manifest-runtime-configmap.json"
APP_MANIFEST="$REPORT/manifest-sparkapplication.json"

echo '=== 11. Kubernetes dry-run and collision guard ==='

kubectl create --dry-run=client -f "$CM_MANIFEST" >/dev/null
kubectl create --dry-run=client -f "$APP_MANIFEST" >/dev/null

echo 'MANIFEST_KUBERNETES_DRY_RUN=PASS'

if kubectl -n "$NS" get configmap "$RUNTIME_CM" >/dev/null 2>&1; then
  echo 'ERROR: Manifest Runtime ConfigMap already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 5
fi

if kubectl -n "$NS" get sparkapplication "$PUBLISHER_APP" >/dev/null 2>&1; then
  echo 'ERROR: Manifest SparkApplication already exists'
  echo 'STOP_MANUAL_RECONCILIATION=YES'
  exit 5
fi

echo 'MANIFEST_RUNTIME_CONFLICTS=NONE'

echo '=== 12. Final Reservation check immediately before final S3 mutation ==='

kubectl -n "$NS" get configmap "$LOCK" -o json \
  > "$REPORT/reservation-final-precreate.json"

python3 - \
  "$REPORT/reservation-final-precreate.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_FINAL_LOCK'
import json
import sys
from pathlib import Path

live=json.loads(Path(sys.argv[1]).read_bytes())

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('FINAL_RESERVATION_BEFORE_MANIFEST_MUTATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_FINAL_LOCK

echo '=== 13. CREATE immutable Manifest Runtime ConfigMap ==='

kubectl create -f "$CM_MANIFEST" -o json \
  > "$REPORT/manifest-runtime-configmap-create.json"

RUNTIME_CM_CREATED=YES

echo 'MANIFEST_RUNTIME_CONFIGMAP_CREATE=PASS'

echo '=== 14. CREATE final Manifest Publisher SparkApplication ==='

if kubectl create -f "$APP_MANIFEST" -o json \
    > "$REPORT/manifest-sparkapplication-create.json"
then
  PUBLISHER_APP_CREATED=YES
else
  echo 'MANIFEST_SPARKAPPLICATION_CREATE=FAIL'
  echo 'AUTOMATIC_RUNTIME_DELETE=NO'
  echo 'AUTOMATIC_RESERVATION_RELEASE=NO'
  exit 6
fi

echo 'MANIFEST_SPARKAPPLICATION_CREATE=PASS'

echo '=== 15. Observe final Manifest Publisher ==='

LAST_STATE=''

for attempt in $(seq 1 180); do

  kubectl -n "$NS" get sparkapplication "$PUBLISHER_APP" -o json \
    > "$REPORT/manifest-sparkapplication-current.json"

  STATE=$(
    python3 -c '
import json,sys

x=json.load(open(sys.argv[1]))

print(
  x.get("status",{})
   .get("applicationState",{})
   .get("state","NOT_REPORTED")
)
' "$REPORT/manifest-sparkapplication-current.json"
  )

  if [[ "$STATE" != "$LAST_STATE" ]]; then
    echo "MANIFEST_SPARK_APPLICATION_STATE=$STATE"
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
  echo 'ERROR: Manifest Publisher did not reach terminal state'
  exit 7
fi

kubectl -n "$NS" get sparkapplication "$PUBLISHER_APP" -o json \
  > "$REPORT/manifest-sparkapplication-final.json"

echo "MANIFEST_PUBLISHER_TERMINAL_STATE=$FINAL_STATE"

echo '=== 16. Capture Manifest Publisher Driver log ==='

DRIVER=$(
  python3 -c '
import json,sys

x=json.load(open(sys.argv[1]))

print(
  x.get("status",{})
   .get("driverInfo",{})
   .get("podName","")
)
' "$REPORT/manifest-sparkapplication-final.json"
)

[[ -n "$DRIVER" ]] || {
  echo 'ERROR: Manifest Publisher Driver pod not reported'
  exit 8
}

echo "MANIFEST_PUBLISHER_DRIVER_POD=$DRIVER"

kubectl -n "$NS" get pod "$DRIVER" -o json \
  > "$REPORT/manifest-driver-pod.json"

kubectl -n "$NS" logs "$DRIVER" --timestamps \
  > "$REPORT/manifest-driver.log"

echo 'MANIFEST_PUBLISHER_DRIVER_LOG_CAPTURE=PASS'

if [[ "$FINAL_STATE" != COMPLETED ]]; then
  echo '--- MANIFEST PUBLISHER DRIVER LOG TAIL BEGIN ---'
  tail -n 140 "$REPORT/manifest-driver.log"
  echo '--- MANIFEST PUBLISHER DRIVER LOG TAIL END ---'

  echo 'MANIFEST_PUBLICATION_STATUS=AMBIGUOUS_UNTIL_RECONCILED'
  echo 'MANIFEST_PUBLISHED=DO_NOT_CLAIM'
  echo 'RESERVATION_RELEASED=NO'
  echo 'AUTOMATIC_CLEANUP=NO'

  exit 9
fi

echo '=== 17. Parse Manifest Publisher result ==='

python3 - \
  "$REPORT/manifest-driver.log" \
  "$PLAN" \
  "$RUN_ID" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_MANIFEST_SIZE" \
  "$REPORT" \
  <<'PY_RESULT'
import hashlib
import json
import sys
from pathlib import Path

log=Path(sys.argv[1])
plan=json.loads(Path(sys.argv[2]).read_bytes())

run_id=sys.argv[3]
dq_sha=sys.argv[4]
dq_size=int(sys.argv[5])
manifest_sha=sys.argv[6]
manifest_size=int(sys.argv[7])
report=Path(sys.argv[8])

marker='PROCESSED_MANIFEST_PUBLICATION_RESULT='

matches=[]

for line in log.read_text(errors='replace').splitlines():
  if marker in line:
    matches.append(
      json.loads(
        line.split(marker,1)[1].strip()
      )
    )

assert len(matches) == 1, (
  'expected exactly one Manifest publication result; '
  f'found {len(matches)}'
)

result=matches[0]

assert result['status'] == 'MANIFEST_PUBLICATION_PASS'

assert result['publication_status'] in (
  'CREATED',
  'REUSED_IDENTICAL',
)

assert result['run_id'] == run_id

assert result['dq_uri'] == plan['dq_uri']
assert result['dq_sha256'] == dq_sha
assert result['dq_size_bytes'] == dq_size
assert result['dq_published'] is True
assert result['dq_readback_verified'] is True

assert result['manifest_uri'] == plan['manifest_uri']
assert result['manifest_sha256'] == manifest_sha
assert result['manifest_size_bytes'] == manifest_size
assert result['manifest_published'] is True
assert result['manifest_readback_verified'] is True

assert result['processed_publication_complete'] is True
assert result['reservation_release_eligible'] is True
assert result['reservation_release_requested'] is False
assert result['postgresql_write'] is False

target=report/'manifest-publication-result.json'

target.write_text(
  json.dumps(result,indent=2,sort_keys=True) + '\n'
)

print('MANIFEST_PUBLICATION_RESULT_PARSE=PASS')
print(
  'MANIFEST_PUBLICATION_STATUS='
  + result['publication_status']
)
print('DQ_REMOTE_VERIFIED=YES')
print('MANIFEST_PUBLISHED=YES')
print('MANIFEST_READBACK_VERIFIED=YES')
print('PROCESSED_PUBLICATION_COMPLETE=YES')
print('RESERVATION_RELEASE_ELIGIBLE=YES')
PY_RESULT

echo '=== 18. Independent post-publication remote audit ==='

POST_POD="task003-manifest-postaudit-$(date -u +%H%M%S)-$$"

python3 - \
  "$POST_POD" \
  "$NS" \
  "$S3_SECRET" \
  "$ACCESS_FIELD" \
  "$SECRET_FIELD" \
  "$S3_ENDPOINT" \
  "$BUCKET" \
  "$DATA_PREFIX" \
  "$DQ_KEY" \
  "$MANIFEST_KEY" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_MANIFEST_SIZE" \
  "$REPORT/postaudit-pod.json" \
  <<'PY_POST'
import json
import sys
from pathlib import Path

(
  pod, namespace, secret, access_field, secret_field,
  endpoint, bucket, data_prefix, dq_key, manifest_key,
  dq_sha, dq_size, manifest_sha, manifest_size, target,
)=sys.argv[1:]

script=r'''
set -eu

echo "FINAL_POST_PUBLICATION_AUDIT_START=YES"

DATA_COUNT=$(
  aws \
    --endpoint-url "$S3_ENDPOINT" \
    s3api list-objects-v2 \
    --bucket "$S3_BUCKET" \
    --prefix "$DATA_PREFIX" \
    --max-keys 1 \
    --query KeyCount \
    --output text
)

[ "$DATA_COUNT" -gt 0 ] || exit 51

echo "DATA_PREFIX_REMOTE_CLASSIFICATION=PRESENT"

aws \
  --endpoint-url "$S3_ENDPOINT" \
  s3api get-object \
  --bucket "$S3_BUCKET" \
  --key "$DQ_KEY" \
  /tmp/dq.json \
  >/tmp/dq-get.json

DQ_SHA=$(
  sha256sum /tmp/dq.json |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c < /tmp/dq.json |
  tr -d ' '
)

echo "DQ_REMOTE_SHA256=$DQ_SHA"
echo "DQ_REMOTE_SIZE_BYTES=$DQ_SIZE"

[ "$DQ_SHA" = "$EXPECTED_DQ_SHA" ] || exit 52
[ "$DQ_SIZE" = "$EXPECTED_DQ_SIZE" ] || exit 53

echo "DQ_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL"

aws \
  --endpoint-url "$S3_ENDPOINT" \
  s3api get-object \
  --bucket "$S3_BUCKET" \
  --key "$MANIFEST_KEY" \
  /tmp/manifest.json \
  >/tmp/manifest-get.json

MANIFEST_SHA=$(
  sha256sum /tmp/manifest.json |
  awk '{print $1}'
)

MANIFEST_SIZE=$(
  wc -c < /tmp/manifest.json |
  tr -d ' '
)

echo "MANIFEST_REMOTE_SHA256=$MANIFEST_SHA"
echo "MANIFEST_REMOTE_SIZE_BYTES=$MANIFEST_SIZE"

[ "$MANIFEST_SHA" = "$EXPECTED_MANIFEST_SHA" ] || exit 54
[ "$MANIFEST_SIZE" = "$EXPECTED_MANIFEST_SIZE" ] || exit 55

echo "MANIFEST_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL"

echo "FINAL_POST_PUBLICATION_AUDIT=PASS"
echo "S3_MUTATION_BY_POST_AUDIT=NO"
'''

obj={
  "apiVersion":"v1",
  "kind":"Pod",
  "metadata":{
    "name":pod,
    "namespace":namespace,
    "labels":{
      "task":"task-003",
      "purpose":"manifest-final-postaudit",
    },
  },
  "spec":{
    "restartPolicy":"Never",
    "nodeSelector":{
      "workload":"platform",
    },
    "containers":[
      {
        "name":"audit",
        "image":"amazon/aws-cli:2.17.60",
        "imagePullPolicy":"IfNotPresent",
        "command":["/bin/sh","-c",script],
        "env":[
          {
            "name":"AWS_ACCESS_KEY_ID",
            "valueFrom":{
              "secretKeyRef":{
                "name":secret,
                "key":access_field,
              }
            },
          },
          {
            "name":"AWS_SECRET_ACCESS_KEY",
            "valueFrom":{
              "secretKeyRef":{
                "name":secret,
                "key":secret_field,
              }
            },
          },
          {"name":"AWS_DEFAULT_REGION","value":"us-east-1"},
          {"name":"AWS_EC2_METADATA_DISABLED","value":"true"},
          {"name":"S3_ENDPOINT","value":endpoint},
          {"name":"S3_BUCKET","value":bucket},
          {"name":"DATA_PREFIX","value":data_prefix},
          {"name":"DQ_KEY","value":dq_key},
          {"name":"MANIFEST_KEY","value":manifest_key},
          {"name":"EXPECTED_DQ_SHA","value":dq_sha},
          {"name":"EXPECTED_DQ_SIZE","value":dq_size},
          {"name":"EXPECTED_MANIFEST_SHA","value":manifest_sha},
          {"name":"EXPECTED_MANIFEST_SIZE","value":manifest_size},
        ],
      }
    ],
  },
}

Path(target).write_text(
  json.dumps(obj,indent=2,sort_keys=True) + '\n'
)

print('POST_AUDIT_POD_MANIFEST=PASS')
PY_POST

kubectl create --dry-run=client \
  -f "$REPORT/postaudit-pod.json" >/dev/null

kubectl create -f "$REPORT/postaudit-pod.json" >/dev/null

POST_PHASE=''

for attempt in $(seq 1 90); do
  POST_PHASE=$(
    kubectl -n "$NS" get pod "$POST_POD" \
      -o jsonpath='{.status.phase}' 2>/dev/null || true
  )

  case "$POST_PHASE" in
    Succeeded|Failed)
      break
      ;;
  esac

  sleep 2
done

echo "POST_AUDIT_POD_PHASE=$POST_PHASE"

kubectl -n "$NS" logs "$POST_POD" \
  > "$REPORT/postaudit.log" 2>&1 || true

echo '--- FINAL POST PUBLICATION AUDIT LOG BEGIN ---'
cat "$REPORT/postaudit.log"
echo '--- FINAL POST PUBLICATION AUDIT LOG END ---'

[[ "$POST_PHASE" == "Succeeded" ]] || {
  echo 'ERROR: independent final post-publication audit failed'
  echo 'MANIFEST_PUBLICATION_STATUS=REQUIRES_RECONCILIATION'
  echo 'RESERVATION_RELEASED=NO'
  echo 'POST_AUDIT_UTILITY_POD_PRESERVED=YES'
  exit 10
}

grep -qx 'DATA_PREFIX_REMOTE_CLASSIFICATION=PRESENT' \
  "$REPORT/postaudit.log"

grep -qx 'DQ_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL' \
  "$REPORT/postaudit.log"

grep -qx 'MANIFEST_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL' \
  "$REPORT/postaudit.log"

grep -qx 'FINAL_POST_PUBLICATION_AUDIT=PASS' \
  "$REPORT/postaudit.log"

echo 'FINAL_REMOTE_DATA_AUDIT=PASS'
echo 'FINAL_REMOTE_DQ_AUDIT=PASS'
echo 'FINAL_REMOTE_MANIFEST_AUDIT=PASS'

kubectl -n "$NS" delete pod "$POST_POD" \
  --wait=true >/dev/null

echo 'POST_AUDIT_UTILITY_POD_DELETED=YES'

echo '=== 19. Reservation must remain held after final publication ==='

kubectl -n "$NS" get configmap "$LOCK" -o json \
  > "$REPORT/reservation-after.json"

python3 - \
  "$REPORT/reservation-after.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_LOCK_AFTER'
import json
import sys
from pathlib import Path

live=json.loads(Path(sys.argv[1]).read_bytes())

assert live['metadata']['uid'] == sys.argv[2]
assert live['metadata']['resourceVersion'] == sys.argv[3]
assert live.get('immutable') is True

print('RESERVATION_AFTER_MANIFEST_PUBLICATION=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK_AFTER

echo '=== 20. Persist final G4C2 evidence ==='

python3 - \
  "$REPORT" \
  "$RUN_ID" \
  "$CHECKPOINT" \
  "$RUNTIME_CM" \
  "$PUBLISHER_APP" \
  "$DRIVER" \
  "$PLAN" \
  "$MANIFEST_BUILD_STATE" \
  "$MANIFEST_FILE" \
  <<'PY_FINAL'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report=Path(sys.argv[1])
run_id=sys.argv[2]
checkpoint=sys.argv[3]
runtime_cm=sys.argv[4]
app=sys.argv[5]
driver=sys.argv[6]

plan=Path(sys.argv[7])
build_state=Path(sys.argv[8])
manifest=Path(sys.argv[9])

result_path=report/'manifest-publication-result.json'
result=json.loads(result_path.read_bytes())

def sha(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()

state={
  'task':'TASK-003',
  'step':'STEP-05G4C2',
  'status':'MANIFEST_PUBLICATION_PASS',
  'run_id':run_id,

  'git_checkpoint':checkpoint,

  'runtime_configmap':runtime_cm,
  'spark_application':app,
  'driver_pod':driver,
  'spark_application_state':'COMPLETED',

  'plan_sha256':sha(plan),
  'manifest_build_state_sha256':sha(build_state),

  'local_manifest_sha256':sha(manifest),
  'publication_result_sha256':sha(result_path),

  'publication_status':result['publication_status'],

  'dq_uri':result['dq_uri'],
  'dq_sha256':result['dq_sha256'],
  'dq_size_bytes':result['dq_size_bytes'],

  'manifest_uri':result['manifest_uri'],
  'manifest_sha256':result['manifest_sha256'],
  'manifest_size_bytes':result['manifest_size_bytes'],

  'processed_data_verified':True,
  'candidate_published_verified':True,
  's3_write_verified':True,

  'dq_published':True,
  'dq_readback_verified':True,

  'manifest_published':True,
  'manifest_readback_verified':True,

  'independent_final_remote_audit':True,

  'processed_publication_complete':True,

  'reservation_release_eligible':True,
  'reservation_released':False,

  'postgresql_write':False,
  'automatic_publisher_cleanup':False,

  'verified_at_utc':datetime.now(
    timezone.utc
  ).isoformat(),
}

target=report/'run-state.json'

target.write_text(
  json.dumps(state,indent=2,sort_keys=True) + '\n'
)

print('MANIFEST_PUBLICATION_STATE=PASS')
print('MANIFEST_PUBLICATION_STATE_FILE=' + str(target))
print('MANIFEST_PUBLICATION_STATE_SHA256=' + sha(target))
PY_FINAL

echo '=== 21. FINAL Processed publication verdict ==='

echo 'STEP05G4C2_MANIFEST_PUBLICATION=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'CANDIDATE_PUBLISHED_VERIFIED=YES'
echo 'S3_WRITE_VERIFIED=YES'

echo 'DQ_PUBLISHED=YES'
echo 'DQ_READBACK_VERIFIED=YES'

echo 'MANIFEST_PUBLISHED=YES'
echo 'MANIFEST_READBACK_VERIFIED=YES'

echo "MANIFEST_SHA256=$EXPECTED_MANIFEST_SHA"
echo "MANIFEST_SIZE_BYTES=$EXPECTED_MANIFEST_SIZE"

echo 'FINAL_REMOTE_AUDIT=PASS'

echo 'PROCESSED_PUBLICATION_COMPLETE=YES'

echo 'RESERVATION_RELEASE_ELIGIBLE=YES'
echo 'RESERVATION_RELEASED=NO'

echo 'DATABASE_WRITE=NO'

echo '--- MANIFEST PUBLISHER DRIVER LOG TAIL BEGIN ---'
tail -n 100 "$REPORT/manifest-driver.log"
echo '--- MANIFEST PUBLISHER DRIVER LOG TAIL END ---'
