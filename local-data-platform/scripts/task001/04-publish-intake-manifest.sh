#!/usr/bin/env bash
set -Eeuo pipefail


PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

ENV_FILE="${PROJECT_ROOT}/config/local.env"

BUILDER="${PROJECT_ROOT}/apps/task001/build_intake_manifest.py"

GUARD="${PROJECT_ROOT}/apps/task001/landing_guard.py"

DRAFT="${PROJECT_ROOT}/runtime/reports/task001/step01/manifest.draft.json"

STEP03_STATE="${PROJECT_ROOT}/runtime/reports/task001/step03/landing-payload-state.json"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task001/step04"

mkdir -p "${REPORT_DIR}"


FINAL_LOCAL="${REPORT_DIR}/manifest.final.json"

FINAL_REMOTE="${REPORT_DIR}/manifest.remote.json"

CHECKSUM_FILE="${REPORT_DIR}/payload.sha256"

STEP_STATE="${REPORT_DIR}/intake-state.json"


if [[ ! -f "${ENV_FILE}" ]]; then

    echo "ERROR: missing ${ENV_FILE}"

    exit 1

fi


if [[ ! -s "${DRAFT}" ]]; then

    echo "ERROR:"
    echo "STEP 01 draft manifest missing."

    exit 1

fi


if [[ ! -s "${STEP03_STATE}" ]]; then

    echo "ERROR:"
    echo "STEP 03 state missing."
    echo
    echo "Run STEP 03 before STEP 04."

    exit 1

fi


set -a

# shellcheck disable=SC1090
source "${ENV_FILE}"

set +a


: "${BATCH_ID:?missing BATCH_ID}"
: "${S3_NAMESPACE:?missing S3_NAMESPACE}"
: "${S3_SECRET_NAME:?missing S3_SECRET_NAME}"
: "${S3_ENDPOINT:?missing S3_ENDPOINT}"
: "${S3_BUCKET_LANDING:?missing S3_BUCKET_LANDING}"


readarray -t STATE_VALUES < <(
    python3 - "${STEP03_STATE}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

assert data["status"] == "PAYLOAD_VERIFIED"
assert data["verified_file_count"] == 18

print(data["ingest_date"])
print(data["landing_uri"])
print(data["payload_uri"])
PY
)


INGEST_DATE="${STATE_VALUES[0]}"

LANDING_URI="${STATE_VALUES[1]}"

PAYLOAD_URI="${STATE_VALUES[2]}"

MANIFEST_URI="${LANDING_URI}manifest.json"


POD="task001-intake-manifest-$(date -u +%H%M%S)"

STEP_SUCCESS=0


cleanup() {

    if [[ "${STEP_SUCCESS}" -eq 1 ]]; then

        kubectl delete pod \
            "${POD}" \
            -n "${S3_NAMESPACE}" \
            --ignore-not-found=true \
            >/dev/null 2>&1 \
            || true

    else

        echo
        echo "NOTE:"
        echo "STEP 04 failed."
        echo "Temporary Pod preserved:"
        echo "  namespace: ${S3_NAMESPACE}"
        echo "  pod      : ${POD}"

    fi
}


trap cleanup EXIT


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 04"
echo "Publish final INTAKE_VERIFIED manifest"
echo "============================================================"
echo


# ============================================================
# 1. Validate prerequisite state
# ============================================================

echo "[1/9] Validating STEP 03 prerequisite..."

python3 - \
    "${STEP03_STATE}" \
    "${DRAFT}" \
    "${BATCH_ID}" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

draft = json.loads(
    Path(sys.argv[2]).read_text(
        encoding="utf-8"
    )
)

batch_id = sys.argv[3]

assert state["status"] == "PAYLOAD_VERIFIED"
assert state["batch_id"] == batch_id
assert state["verified_file_count"] == 18

assert draft["batch_id"] == batch_id
assert len(draft["files"]) == 18

print("PASS: STEP 03 payload verified")
print(f"Batch ID : {batch_id}")
print("Files    : 18/18")
PY

echo


# ============================================================
# 2. Build checksum inventory
# ============================================================

echo "[2/9] Preparing expected SHA256 inventory..."

python3 - "${DRAFT}" "${CHECKSUM_FILE}" <<'PY'
import json
import sys
from pathlib import Path

draft = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

target = Path(sys.argv[2])

with target.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as fh:

    for item in draft["files"]:

        filename = Path(
            item["path"]
        ).name

        fh.write(
            f"{item['sha256']}  "
            f"{filename}\n"
        )

print(
    f"PASS: {len(draft['files'])}/18 checksums"
)
PY

echo


# ============================================================
# 3. Start verification Pod
# ============================================================

echo "[3/9] Starting S3 verification Pod..."

cat <<EOF_K8S | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${POD}
  namespace: ${S3_NAMESPACE}

  labels:
    app: healthcare-task001
    task: intake-manifest

spec:
  restartPolicy: Never

  volumes:
    - name: work
      emptyDir: {}

  containers:

    - name: transfer
      image: alpine:3.20

      command:
        - /bin/sh
        - -c

      args:
        - |
          mkdir -p /work/payload
          sleep 3600

      volumeMounts:
        - name: work
          mountPath: /work


    - name: aws-cli
      image: amazon/aws-cli:latest

      command:
        - /bin/sh
        - -c

      args:
        - |
          sleep 3600

      env:

        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: ${S3_SECRET_NAME}
              key: AWS_ACCESS_KEY_ID

        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: ${S3_SECRET_NAME}
              key: AWS_SECRET_ACCESS_KEY

        - name: AWS_DEFAULT_REGION
          value: us-east-1

      volumeMounts:
        - name: work
          mountPath: /work
EOF_K8S


kubectl wait \
    --for=condition=Ready \
    "pod/${POD}" \
    -n "${S3_NAMESPACE}" \
    --timeout=120s


kubectl cp \
    -c transfer \
    "${CHECKSUM_FILE}" \
    "${S3_NAMESPACE}/${POD}:/work/payload.sha256"


echo "PASS: verification Pod READY"
echo


# ============================================================
# 4. Mandatory independent S3 payload reread
# ============================================================

echo "[4/9] Re-reading all 18 payload objects from S3..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c aws-cli -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3 sync \
        "${PAYLOAD_URI}" \
        /work/payload \
        --only-show-errors


PAYLOAD_COUNT="$(
    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c transfer -- \
        sh -c '
            find /work/payload \
                -maxdepth 1 \
                -type f \
            | wc -l
        ' \
    | tr -d '\r[:space:]'
)"


echo "Downloaded payload: ${PAYLOAD_COUNT}/18"


if [[ "${PAYLOAD_COUNT}" != "18" ]]; then

    echo "ERROR:"
    echo "Expected 18 objects."
    echo "Found ${PAYLOAD_COUNT}."

    exit 1

fi


kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c transfer -- \
    sh -c '
        cd /work/payload
        sha256sum -c /work/payload.sha256
    '


echo
echo "PASS: mandatory S3 reread SHA256 18/18"
echo


# ============================================================
# 5. Check whether final manifest already exists
# ============================================================

echo "[5/9] Checking existing final manifest..."

MANIFEST_EXISTS="NO"


if kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c aws-cli -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api \
        head-object \
        --bucket "${S3_BUCKET_LANDING}" \
        --key "$(
            python3 - \
                "${LANDING_URI}" \
                "${S3_BUCKET_LANDING}" <<'PY'
import sys

uri = sys.argv[1]
bucket = sys.argv[2]

prefix = f"s3://{bucket}/"

assert uri.startswith(prefix)

print(
    uri[len(prefix):]
    + "manifest.json"
)
PY
        )" \
        >/dev/null 2>&1
then

    MANIFEST_EXISTS="YES"

fi


echo "Existing manifest: ${MANIFEST_EXISTS}"
echo


# ============================================================
# 6. Existing manifest -> validate and reuse
# ============================================================

if [[ "${MANIFEST_EXISTS}" == "YES" ]]; then

    echo "[6/9] Existing manifest found; validating, NOT overwriting..."

    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c aws-cli -- \
        aws \
            --endpoint-url "${S3_ENDPOINT}" \
            s3 cp \
            "${MANIFEST_URI}" \
            - \
            --only-show-errors \
        > "${FINAL_REMOTE}"


    python3 "${GUARD}" \
        compare-manifest \
        --draft "${DRAFT}" \
        --manifest "${FINAL_REMOTE}"


    python3 - \
        "${FINAL_REMOTE}" \
        "${INGEST_DATE}" \
        "${LANDING_URI}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

expected_date = sys.argv[2]
expected_uri = sys.argv[3]

assert manifest["status"] == "INTAKE_VERIFIED"
assert manifest["ingest_date"] == expected_date
assert manifest["landing_uri"] == expected_uri

assert (
    manifest["verification"][
        "verified_file_count"
    ]
    == 18
)

assert (
    manifest["verification"][
        "s3_readback"
    ]
    == "PASS"
)

print("PASS: existing final manifest valid")
PY


    cp \
        "${FINAL_REMOTE}" \
        "${FINAL_LOCAL}"

    PUBLISH_MODE="REUSE_EXISTING"


else

# ============================================================
# 7. Build then publish manifest LAST
# ============================================================

    echo "[6/9] No final manifest exists."
    echo "Building final INTAKE_VERIFIED manifest..."

    VERIFIED_AT="$(
        date -u +%Y-%m-%dT%H:%M:%SZ
    )"


    python3 "${BUILDER}" \
        --draft "${DRAFT}" \
        --ingest-date "${INGEST_DATE}" \
        --landing-uri "${LANDING_URI}" \
        --verified-at "${VERIFIED_AT}" \
        --output "${FINAL_LOCAL}"


    echo
    echo "[7/9] Publishing manifest LAST..."

    kubectl cp \
        -c transfer \
        "${FINAL_LOCAL}" \
        "${S3_NAMESPACE}/${POD}:/work/manifest.json"


    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c aws-cli -- \
        aws \
            --endpoint-url "${S3_ENDPOINT}" \
            s3 cp \
            /work/manifest.json \
            "${MANIFEST_URI}" \
            --only-show-errors


    PUBLISH_MODE="PUBLISHED_NEW"

fi


# ============================================================
# 8. Read final manifest back from S3
# ============================================================

echo
echo "[8/9] Reading final manifest back from S3..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c aws-cli -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3 cp \
        "${MANIFEST_URI}" \
        - \
        --only-show-errors \
    > "${FINAL_REMOTE}"


python3 "${GUARD}" \
    compare-manifest \
    --draft "${DRAFT}" \
    --manifest "${FINAL_REMOTE}"


python3 - \
    "${FINAL_REMOTE}" \
    "${INGEST_DATE}" \
    "${LANDING_URI}" \
    "${BATCH_ID}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

expected_date = sys.argv[2]
expected_uri = sys.argv[3]
expected_batch = sys.argv[4]

assert manifest["status"] == "INTAKE_VERIFIED"
assert manifest["batch_id"] == expected_batch
assert manifest["ingest_date"] == expected_date
assert manifest["landing_uri"] == expected_uri

assert manifest["expected_file_count"] == 18
assert len(manifest["files"]) == 18

assert (
    manifest["verification"][
        "verified_file_count"
    ]
    == 18
)

assert (
    manifest["verification"][
        "s3_readback"
    ]
    == "PASS"
)

print("PASS: remote manifest")
print(
    f"Status      : "
    f"{manifest['status']}"
)
print(
    f"Files       : "
    f"{len(manifest['files'])}/18"
)
print(
    f"Ingest date : "
    f"{manifest['ingest_date']}"
)
print(
    f"Ingested at : "
    f"{manifest['ingested_at']}"
)
PY


LOCAL_SHA="$(
    sha256sum "${FINAL_REMOTE}" \
    | awk '{print $1}'
)"


echo
echo "Remote manifest SHA256:"
echo "  ${LOCAL_SHA}"
echo


# ============================================================
# 9. Final state
# ============================================================

echo "[9/9] Writing STEP 04 state..."


python3 - \
    "${STEP_STATE}" \
    "${BATCH_ID}" \
    "${INGEST_DATE}" \
    "${LANDING_URI}" \
    "${MANIFEST_URI}" \
    "${PUBLISH_MODE}" \
    "${LOCAL_SHA}" <<'PY'
import json
import sys
from pathlib import Path

(
    output,
    batch_id,
    ingest_date,
    landing_uri,
    manifest_uri,
    mode,
    manifest_sha
) = sys.argv[1:]

state = {
    "step":
        "TASK-001-STEP-04",

    "status":
        "INTAKE_VERIFIED",

    "batch_id":
        batch_id,

    "ingest_date":
        ingest_date,

    "landing_uri":
        landing_uri,

    "manifest_uri":
        manifest_uri,

    "publish_mode":
        mode,

    "payload_verified":
        "18/18",

    "manifest_sha256":
        manifest_sha
}

Path(output).write_text(
    json.dumps(
        state,
        indent=2
    ) + "\n",
    encoding="utf-8"
)

print(
    f"State: {output}"
)
PY


STEP_SUCCESS=1


echo
echo "============================================================"
echo "TASK-001 STEP 04 RESULT"
echo "============================================================"
echo
echo "Batch ID:"
echo "  ${BATCH_ID}"
echo
echo "Landing:"
echo "  ${LANDING_URI}"
echo
echo "Manifest:"
echo "  ${MANIFEST_URI}"
echo
echo "Publish mode:"
echo "  ${PUBLISH_MODE}"
echo
echo "STEP04=PASS"
echo "S3_PAYLOAD_READBACK_SHA256=18/18"
echo "MANIFEST_STATUS=INTAKE_VERIFIED"
echo "MANIFEST_REMOTE_VALIDATION=PASS"
echo "OLD_LANDING_TOUCHED=NO"
echo "OMOP_TOUCHED=NO"
echo "============================================================"
