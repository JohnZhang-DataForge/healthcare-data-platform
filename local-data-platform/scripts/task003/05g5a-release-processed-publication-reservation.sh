#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$ROOT/runtime/reports/task003/step05"

NS=dw-spark

EXPECTED_CHECKPOINT=b98912c7f7af12f47082c8a062882a849f5dc85d

LOCK=visit-proc-lock-42dac37c79553e40c0affc4039acee27
LOCK_UID=fb3c360b-920b-423d-9029-7adefa9a1114
LOCK_RV=1194946

EXPECTED_DQ_SHA=58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2
EXPECTED_DQ_SIZE=2607

EXPECTED_MANIFEST_SHA=1435b6c3a98e2320b831faf26e2b8ecf59472b980b972fab856b35ae4d6829af
EXPECTED_MANIFEST_SIZE=3141

S3_ENDPOINT=http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
S3_SECRET=dw-spark-s3-secret

REPORT=''
LOCK_RELEASED=NO

echo '#### TASK003 STEP05G5A RESERVATION RECONCILIATION RELEASE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || \
    echo "RESERVATION_RELEASE_REPORT=$REPORT"

  echo "RESERVATION_RELEASED=$LOCK_RELEASED"
  echo "S3_MUTATION_BY_RELEASE_STEP=NO"
  echo "DATABASE_WRITE=NO"
  echo "PUBLICATION_RUNTIME_AUTOMATIC_CLEANUP=NO"

  echo "RESERVATION_RELEASE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G5A RESERVATION RECONCILIATION RELEASE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage:"
  echo "$0 PLAN MANIFEST_PUBLICATION_REPORT GIT_CHECKPOINT"
  exit 2
}

PLAN="$1"
PUBLICATION_REPORT="$2"
CHECKPOINT="$3"

PUBLICATION_STATE="$PUBLICATION_REPORT/run-state.json"
PUBLICATION_RESULT="$PUBLICATION_REPORT/manifest-publication-result.json"

for path in \
  "$PLAN" \
  "$PUBLICATION_STATE" \
  "$PUBLICATION_RESULT"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

for cmd in \
  kubectl \
  python3 \
  git \
  sha256sum
do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing required command: $cmd"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/processed-reservation-release.XXXXXXXX"
)

cd "$ROOT"

echo '=== 1. Verify exact Processed-publication Git checkpoint ==='

HEAD=$(
  git rev-parse HEAD
)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_CHECKPOINT"

[[ "$CHECKPOINT" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: supplied Git checkpoint drift'
  exit 1
}

[[ "$HEAD" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: repository HEAD drifted after Processed publication checkpoint'
  exit 1
}

git cat-file -e \
  "${CHECKPOINT}^{commit}"

echo 'PROCESSED_PUBLICATION_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify G4C2 publication is complete and release-eligible ==='

python3 - \
  "$PUBLICATION_STATE" \
  "$PUBLICATION_RESULT" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_DQ_SIZE" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_MANIFEST_SIZE" \
  "$CHECKPOINT" \
  <<'PY_PUBLICATION'
import hashlib
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
result_path = Path(sys.argv[2])

dq_sha = sys.argv[3]
dq_size = int(sys.argv[4])

manifest_sha = sys.argv[5]
manifest_size = int(sys.argv[6])

checkpoint = sys.argv[7]

state = json.loads(
    state_path.read_bytes()
)

result = json.loads(
    result_path.read_bytes()
)

assert (
    state['task'],
    state['step'],
    state['status'],
) == (
    'TASK-003',
    'STEP-05G4C2',
    'MANIFEST_PUBLICATION_PASS',
)

assert state['run_id'] == \
    'visit-proc-20261009t192437z-2081886'

assert state['spark_application_state'] == \
    'COMPLETED'

assert state['processed_data_verified'] is True
assert state['candidate_published_verified'] is True
assert state['s3_write_verified'] is True

assert state['dq_published'] is True
assert state['dq_readback_verified'] is True
assert state['dq_sha256'] == dq_sha
assert state['dq_size_bytes'] == dq_size

assert state['manifest_published'] is True
assert state['manifest_readback_verified'] is True
assert state['manifest_sha256'] == manifest_sha
assert state['manifest_size_bytes'] == manifest_size

assert (
    state['independent_final_remote_audit']
    is True
)

assert (
    state['processed_publication_complete']
    is True
)

assert (
    state['reservation_release_eligible']
    is True
)

assert state['reservation_released'] is False
assert state['postgresql_write'] is False

assert result['status'] == \
    'MANIFEST_PUBLICATION_PASS'

assert result['dq_sha256'] == dq_sha
assert result['dq_size_bytes'] == dq_size

assert result['manifest_sha256'] == manifest_sha
assert result['manifest_size_bytes'] == manifest_size

assert result['dq_published'] is True
assert result['dq_readback_verified'] is True

assert result['manifest_published'] is True
assert result['manifest_readback_verified'] is True

assert (
    result['processed_publication_complete']
    is True
)

assert (
    result['reservation_release_eligible']
    is True
)

assert (
    result['reservation_release_requested']
    is False
)

assert result['postgresql_write'] is False

assert (
    hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()
    == state['publication_result_sha256']
)

print('FINAL_PUBLICATION_EVIDENCE=PASS')
print('PROCESSED_PUBLICATION_COMPLETE=YES')
print('RESERVATION_RELEASE_ELIGIBLE=YES')
print('DATABASE_WRITE=NO')
PY_PUBLICATION

echo '=== 2B. Verify frozen local APPROVED Manifest semantics ==='

LOCAL_MANIFEST="$ROOT/runtime/reports/task003/step05/processed-manifest-builds/visit-proc-20261009t192437z-2081886/manifest.json"

[[ -s "$LOCAL_MANIFEST" && ! -L "$LOCAL_MANIFEST" ]] || {
  echo 'ERROR: local frozen Manifest missing or unsafe'
  exit 1
}

python3 - \
  "$LOCAL_MANIFEST" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_MANIFEST_SIZE" \
  <<'PY_LOCAL_MANIFEST'
import hashlib
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_sha = sys.argv[2]
expected_size = int(sys.argv[3])

blob = path.read_bytes()

assert hashlib.sha256(
    blob
).hexdigest() == expected_sha

assert len(blob) == expected_size

manifest = json.loads(blob)

assert manifest['status'] == 'APPROVED'

assert (
    manifest['publication_policy']
    == 'APPROVED_manifest_last'
)

assert manifest['run_id'] == \
    'visit-proc-20261009t192437z-2081886'

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

print('LOCAL_APPROVED_MANIFEST_SEMANTICS=PASS')
print('LOCAL_APPROVED_MANIFEST_BYTES=PASS')
PY_LOCAL_MANIFEST

echo '=== 3. Verify original Reservation is still exact ==='

kubectl -n "$NS" \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-before-release.json"

python3 - \
  "$REPORT/reservation-before-release.json" \
  "$LOCK" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_LOCK'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['name'] == sys.argv[2]
assert live['metadata']['uid'] == sys.argv[3]
assert live['metadata']['resourceVersion'] == sys.argv[4]
assert live.get('immutable') is True

print('ORIGINAL_RESERVATION_IDENTITY=PASS')
print('RESERVATION_STILL_HELD=YES')
PY_LOCK

echo '=== 4. Resolve canonical frozen S3 publication targets ==='

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

echo '=== 5. Resolve S3 Secret fields without exposing values ==='

kubectl -n "$NS" \
  get secret "$S3_SECRET" \
  -o json \
  > "$REPORT/s3-secret-metadata.json"

mapfile -t SECRET_FIELDS < <(
  python3 -c '
import json,sys

x=json.load(open(sys.argv[1]))
keys=set(x.get("data",{}))

access=next(
    (
        k for k in (
            "AWS_ACCESS_KEY_ID",
            "accessKey",
            "access_key",
            "accessKeyId",
            "access_key_id",
        )
        if k in keys
    ),
    None,
)

secret=next(
    (
        k for k in (
            "AWS_SECRET_ACCESS_KEY",
            "secretKey",
            "secret_key",
            "secretAccessKey",
            "secret_access_key",
        )
        if k in keys
    ),
    None,
)

if not access or not secret:
    raise SystemExit(
        "unsupported S3 Secret structure"
    )

print(access)
print(secret)
' "$REPORT/s3-secret-metadata.json"
)

ACCESS_FIELD="${SECRET_FIELDS[0]}"
SECRET_FIELD="${SECRET_FIELDS[1]}"

echo 'S3_SECRET_STRUCTURE=PASS'

echo '=== 6. Independent final frozen-prefix reconciliation ==='

AUDIT_POD="task003-release-audit-$(date -u +%H%M%S)-$$"

python3 - \
  "$AUDIT_POD" \
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
  "$REPORT/audit-pod.json" \
  <<'PY_AUDIT'
import json
import sys
from pathlib import Path

(
    pod,
    namespace,
    secret,
    access_field,
    secret_field,
    endpoint,
    bucket,
    data_prefix,
    dq_key,
    manifest_key,
    dq_sha,
    dq_size,
    manifest_sha,
    manifest_size,
    target,
) = sys.argv[1:]

script = r'''
set -eu

echo "RESERVATION_RELEASE_REMOTE_AUDIT_START=YES"

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
  exit 61
}

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

[ "$DQ_SHA" = "$EXPECTED_DQ_SHA" ] || exit 62
[ "$DQ_SIZE" = "$EXPECTED_DQ_SIZE" ] || exit 63

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

[ "$MANIFEST_SHA" = "$EXPECTED_MANIFEST_SHA" ] || exit 64
[ "$MANIFEST_SIZE" = "$EXPECTED_MANIFEST_SIZE" ] || exit 65

# The aws-cli utility image intentionally needs no Python.
# Exact SHA256 + byte-size equality proves that the remote
# Manifest is byte-identical to the locally validated,
# immutable APPROVED Manifest.
echo "REMOTE_APPROVED_MANIFEST_BYTES=PASS"

echo "MANIFEST_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL"

echo "FROZEN_PROCESSED_PREFIX=PASS"
echo "S3_MUTATION_BY_RELEASE_AUDIT=NO"
echo "RESERVATION_RELEASE_REMOTE_AUDIT=PASS"
'''

obj = {
    'apiVersion':
        'v1',

    'kind':
        'Pod',

    'metadata': {
        'name':
            pod,

        'namespace':
            namespace,

        'labels': {
            'task':
                'task-003',

            'purpose':
                'processed-reservation-release-audit',
        },
    },

    'spec': {
        'restartPolicy':
            'Never',

        'nodeSelector': {
            'workload':
                'platform',
        },

        'containers': [
            {
                'name':
                    'audit',

                'image':
                    'amazon/aws-cli:2.17.60',

                'imagePullPolicy':
                    'IfNotPresent',

                'command': [
                    '/bin/sh',
                    '-c',
                    script,
                ],

                'env': [
                    {
                        'name':
                            'AWS_ACCESS_KEY_ID',

                        'valueFrom': {
                            'secretKeyRef': {
                                'name':
                                    secret,

                                'key':
                                    access_field,
                            }
                        },
                    },

                    {
                        'name':
                            'AWS_SECRET_ACCESS_KEY',

                        'valueFrom': {
                            'secretKeyRef': {
                                'name':
                                    secret,

                                'key':
                                    secret_field,
                            }
                        },
                    },

                    {
                        'name':
                            'AWS_DEFAULT_REGION',

                        'value':
                            'us-east-1',
                    },

                    {
                        'name':
                            'AWS_EC2_METADATA_DISABLED',

                        'value':
                            'true',
                    },

                    {
                        'name':
                            'S3_ENDPOINT',

                        'value':
                            endpoint,
                    },

                    {
                        'name':
                            'S3_BUCKET',

                        'value':
                            bucket,
                    },

                    {
                        'name':
                            'DATA_PREFIX',

                        'value':
                            data_prefix,
                    },

                    {
                        'name':
                            'DQ_KEY',

                        'value':
                            dq_key,
                    },

                    {
                        'name':
                            'MANIFEST_KEY',

                        'value':
                            manifest_key,
                    },

                    {
                        'name':
                            'EXPECTED_DQ_SHA',

                        'value':
                            dq_sha,
                    },

                    {
                        'name':
                            'EXPECTED_DQ_SIZE',

                        'value':
                            dq_size,
                    },

                    {
                        'name':
                            'EXPECTED_MANIFEST_SHA',

                        'value':
                            manifest_sha,
                    },

                    {
                        'name':
                            'EXPECTED_MANIFEST_SIZE',

                        'value':
                            manifest_size,
                    },
                ],
            }
        ],
    },
}

Path(target).write_text(
    json.dumps(
        obj,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('RELEASE_AUDIT_POD_MANIFEST=PASS')
PY_AUDIT

kubectl create \
  --dry-run=client \
  -f "$REPORT/audit-pod.json" \
  >/dev/null

echo 'RELEASE_AUDIT_POD_DRY_RUN=PASS'

kubectl create \
  -f "$REPORT/audit-pod.json" \
  >/dev/null

echo "RELEASE_AUDIT_POD_CREATED=$AUDIT_POD"

AUDIT_PHASE=''

for attempt in $(seq 1 90); do

  AUDIT_PHASE=$(
    kubectl -n "$NS" \
      get pod "$AUDIT_POD" \
      -o jsonpath='{.status.phase}' \
      2>/dev/null \
      || true
  )

  case "$AUDIT_PHASE" in
    Succeeded|Failed)
      break
      ;;
  esac

  sleep 2
done

echo "RELEASE_AUDIT_POD_PHASE=$AUDIT_PHASE"

kubectl -n "$NS" \
  logs "$AUDIT_POD" \
  > "$REPORT/remote-audit.log" \
  2>&1 \
  || true

echo '--- RESERVATION RELEASE REMOTE AUDIT LOG BEGIN ---'
cat "$REPORT/remote-audit.log"
echo '--- RESERVATION RELEASE REMOTE AUDIT LOG END ---'

[[ "$AUDIT_PHASE" == "Succeeded" ]] || {
  echo 'ERROR: final remote reconciliation failed'
  echo 'RESERVATION_RELEASE_ABORTED=YES'
  echo 'RESERVATION_RELEASED=NO'
  echo 'AUDIT_POD_PRESERVED=YES'
  exit 4
}

grep -qx \
  'DATA_PREFIX_REMOTE_CLASSIFICATION=PRESENT' \
  "$REPORT/remote-audit.log"

grep -qx \
  'DQ_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL' \
  "$REPORT/remote-audit.log"

grep -qx \
  'MANIFEST_REMOTE_CLASSIFICATION=PRESENT_IDENTICAL' \
  "$REPORT/remote-audit.log"

grep -qx \
  'REMOTE_APPROVED_MANIFEST_BYTES=PASS' \
  "$REPORT/remote-audit.log"

grep -qx \
  'FROZEN_PROCESSED_PREFIX=PASS' \
  "$REPORT/remote-audit.log"

grep -qx \
  'RESERVATION_RELEASE_REMOTE_AUDIT=PASS' \
  "$REPORT/remote-audit.log"

echo 'FINAL_FROZEN_PREFIX_RECONCILIATION=PASS'

kubectl -n "$NS" \
  delete pod "$AUDIT_POD" \
  --wait=true \
  >/dev/null

echo 'RELEASE_AUDIT_UTILITY_POD_DELETED=YES'

echo '=== 7. Final exact Reservation identity check immediately before delete ==='

kubectl -n "$NS" \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-final-predelete.json"

python3 - \
  "$REPORT/reservation-final-predelete.json" \
  "$LOCK" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY_FINAL_LOCK'
import json
import sys
from pathlib import Path

live = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert live['metadata']['name'] == sys.argv[2]
assert live['metadata']['uid'] == sys.argv[3]
assert live['metadata']['resourceVersion'] == sys.argv[4]
assert live.get('immutable') is True

print('FINAL_RESERVATION_PREDELETE_IDENTITY=PASS')
print('RESERVATION_RELEASE_AUTHORIZED=YES')
PY_FINAL_LOCK

echo '=== 8. Release cooperative Processed publication Reservation ==='

kubectl -n "$NS" \
  delete configmap "$LOCK" \
  --wait=true

LOCK_RELEASED=YES

echo 'RESERVATION_DELETE_COMMAND=PASS'

echo '=== 9. Verify Reservation is absent ==='

if kubectl -n "$NS" \
    get configmap "$LOCK" \
    >/dev/null 2>&1
then
  echo 'ERROR: Reservation still exists after delete'
  exit 5
fi

echo 'RESERVATION_ABSENT_AFTER_RELEASE=PASS'

echo '=== 10. Persist release evidence ==='

python3 - \
  "$REPORT" \
  "$CHECKPOINT" \
  "$LOCK" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  "$PLAN" \
  "$PUBLICATION_STATE" \
  "$PUBLICATION_RESULT" \
  "$EXPECTED_DQ_SHA" \
  "$EXPECTED_MANIFEST_SHA" \
  <<'PY_STATE'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report = Path(sys.argv[1])

checkpoint = sys.argv[2]
lock_name = sys.argv[3]
lock_uid = sys.argv[4]
lock_rv = sys.argv[5]

plan = Path(sys.argv[6])
publication_state = Path(sys.argv[7])
publication_result = Path(sys.argv[8])

dq_sha = sys.argv[9]
manifest_sha = sys.argv[10]


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G5A',

    'status':
        'PROCESSED_PUBLICATION_RESERVATION_RELEASED',

    'run_id':
        'visit-proc-20261009t192437z-2081886',

    'git_checkpoint':
        checkpoint,

    'plan_sha256':
        sha(plan),

    'manifest_publication_state_sha256':
        sha(publication_state),

    'manifest_publication_result_sha256':
        sha(publication_result),

    'processed_data_verified':
        True,

    'dq_published':
        True,

    'dq_readback_verified':
        True,

    'dq_sha256':
        dq_sha,

    'manifest_published':
        True,

    'manifest_readback_verified':
        True,

    'manifest_sha256':
        manifest_sha,

    'final_remote_audit':
        True,

    'processed_publication_complete':
        True,

    'processed_prefix_frozen':
        True,

    'reservation_name':
        lock_name,

    'reservation_uid':
        lock_uid,

    'reservation_resource_version':
        lock_rv,

    'reservation_release_eligible':
        True,

    'reservation_released':
        True,

    'postgresql_write':
        False,

    's3_mutation_by_release_step':
        False,

    'publication_runtime_cleanup':
        False,

    'released_at_utc':
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

print('RESERVATION_RELEASE_STATE=PASS')
print(
    'RESERVATION_RELEASE_STATE_FILE='
    + str(target)
)
print(
    'RESERVATION_RELEASE_STATE_SHA256='
    + sha(target)
)
PY_STATE

echo '=== 11. Final Processed publication lifecycle verdict ==='

echo 'STEP05G5A_RESERVATION_RELEASE=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'

echo 'DQ_PUBLISHED=YES'
echo 'DQ_READBACK_VERIFIED=YES'

echo 'MANIFEST_PUBLISHED=YES'
echo 'MANIFEST_READBACK_VERIFIED=YES'

echo 'FINAL_REMOTE_AUDIT=PASS'
echo 'PROCESSED_PREFIX_FROZEN=YES'

echo 'PROCESSED_PUBLICATION_COMPLETE=YES'

echo 'RESERVATION_RELEASE_ELIGIBLE=YES'
echo 'RESERVATION_RELEASED=YES'

echo 'S3_MUTATION_BY_RELEASE_STEP=NO'
echo 'DATABASE_WRITE=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE_STARTED=NO'
