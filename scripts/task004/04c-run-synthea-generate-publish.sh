#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

APP="${ROOT}/apps/task004/publish_synthea_landing.py"

TEMPLATE="${ROOT}/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl"

NAMESPACE="dw-synthea"
NODE="worker01"

SECRET_NAME="dw-synthea-s3-secret"

DEFAULT_IMAGE_REF="ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d"

IMAGE_REF="${SYNTHEA_IMAGE_REF:-${DEFAULT_IMAGE_REF}}"

RENDER_ONLY=0
JOB_CREATED=0
CONFIGMAP_CREATED=0
JOB_NAME=""
POD_NAME=""

fail() {
  echo "ERROR=$*" >&2

  if [[ "$JOB_CREATED" -eq 1 ]]; then

    echo "FAILED_JOB_RETAINED_FOR_DIAGNOSIS=YES" >&2

    kubectl get job \
      "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o wide \
      >&2 2>/dev/null || true

    kubectl get pods \
      -n "$NAMESPACE" \
      -l "job-name=${JOB_NAME}" \
      -o wide \
      >&2 2>/dev/null || true

    if [[ -n "$POD_NAME" ]]; then
      kubectl describe pod \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true

      kubectl logs \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true
    fi
  fi

  exit 1
}

usage() {
  cat <<'USAGE'
TASK004 canonical Synthea generate + Landing publish runner.

Required environment:
  BATCH_ID
  POPULATION_SIZE       20 or 50
  SEED
  REFERENCE_DATE        YYYYMMDD
  STATE

Optional:
  CLINICIAN_SEED        defaults to SEED
  CITY                  defaults empty
  LANDING_INGEST_DATE   defaults current UTC YYYY-MM-DD
  SYNTHEA_IMAGE_REF     digest-pinned image

Prerequisite:
  dw-synthea/dw-synthea-s3-secret

Use scripts/task004/04b-sync-s3-secret-to-synthea.sh
to create/update that namespace-local credential Secret.

Options:
  --render-only
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--render-only" ]]; then
  RENDER_ONLY=1
  shift
fi

[[ "$#" -eq 0 ]] \
  || fail "Unexpected positional arguments"

: "${BATCH_ID:?BATCH_ID is required}"
: "${POPULATION_SIZE:?POPULATION_SIZE is required}"
: "${SEED:?SEED is required}"
: "${REFERENCE_DATE:?REFERENCE_DATE is required}"
: "${STATE:?STATE is required}"

CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"
CITY="${CITY:-}"

LANDING_INGEST_DATE="${LANDING_INGEST_DATE:-$(date -u +%Y-%m-%d)}"

[[ -s "$APP" ]] \
  || fail "Publisher application missing"

[[ -s "$TEMPLATE" ]] \
  || fail "Job template missing"

[[ "$POPULATION_SIZE" == "20" || "$POPULATION_SIZE" == "50" ]] \
  || fail "POPULATION_SIZE must be 20 or 50"

[[ "$SEED" =~ ^-?[0-9]+$ ]] \
  || fail "SEED must be integer"

[[ "$CLINICIAN_SEED" =~ ^-?[0-9]+$ ]] \
  || fail "CLINICIAN_SEED must be integer"

[[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]] \
  || fail "Image must be digest-pinned"

python3 - \
  "$BATCH_ID" \
  "$REFERENCE_DATE" \
  "$LANDING_INGEST_DATE" \
  "$STATE" \
  <<'PY'
import datetime
import re
import sys

batch_id = sys.argv[1]
reference_date = sys.argv[2]
ingest_date = sys.argv[3]
state = sys.argv[4]

if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",
    batch_id,
):
    raise SystemExit(
        "ERROR: invalid BATCH_ID"
    )

datetime.datetime.strptime(
    reference_date,
    "%Y%m%d",
)

datetime.datetime.strptime(
    ingest_date,
    "%Y-%m-%d",
)

if not state.strip():
    raise SystemExit(
        "ERROR: STATE must not be blank"
    )
PY

SOURCE_HASH="$(
  sha256sum "$APP" \
  | awk '{print $1}'
)"

CONFIGMAP_NAME="$(
  printf 'task004-syn-publisher-%s' \
    "${SOURCE_HASH:0:12}"
)"

JOB_NAME="$(
  python3 - "$BATCH_ID" <<'PY'
import hashlib
import re
import sys

value = sys.argv[1]

slug = re.sub(
    r"[^a-z0-9]+",
    "-",
    value.lower(),
).strip("-")

slug = (
    slug[:32].rstrip("-")
    or "batch"
)

digest = hashlib.sha256(
    value.encode("utf-8")
).hexdigest()[:10]

print(
    f"task004-syn-pub-{slug}-{digest}"
)
PY
)"

TMP_DIR="$(mktemp -d)"
RENDERED="${TMP_DIR}/job.yaml"

cleanup_tmp() {
  rm -rf "$TMP_DIR"
}

trap cleanup_tmp EXIT

python3 - \
  "$TEMPLATE" \
  "$RENDERED" \
  "$JOB_NAME" \
  "$CONFIGMAP_NAME" \
  "$IMAGE_REF" \
  "$BATCH_ID" \
  "$POPULATION_SIZE" \
  "$SEED" \
  "$CLINICIAN_SEED" \
  "$REFERENCE_DATE" \
  "$STATE" \
  "$CITY" \
  "$LANDING_INGEST_DATE" \
  <<'PY'
import json
import sys
from pathlib import Path

(
    template_path,
    output_path,
    job_name,
    configmap_name,
    image_ref,
    batch_id,
    population_size,
    seed,
    clinician_seed,
    reference_date,
    state,
    city,
    ingest_date,
) = sys.argv[1:]

text = Path(
    template_path
).read_text(
    encoding="utf-8"
)

mapping = {
    "__JOB_NAME__":
        job_name,
    "__CONFIGMAP_NAME__":
        configmap_name,
    "__IMAGE_REF_JSON__":
        json.dumps(image_ref),
    "__BATCH_ID_JSON__":
        json.dumps(batch_id),
    "__POPULATION_SIZE_JSON__":
        json.dumps(population_size),
    "__SEED_JSON__":
        json.dumps(seed),
    "__CLINICIAN_SEED_JSON__":
        json.dumps(clinician_seed),
    "__REFERENCE_DATE_JSON__":
        json.dumps(reference_date),
    "__STATE_JSON__":
        json.dumps(state),
    "__CITY_JSON__":
        json.dumps(city),
    "__INGEST_DATE_JSON__":
        json.dumps(ingest_date),
}

for key, value in mapping.items():

    count = text.count(
        key
    )

    if count != 1:
        raise SystemExit(
            f"ERROR: placeholder {key} "
            f"count={count}"
        )

    text = text.replace(
        key,
        value,
    )

Path(
    output_path
).write_text(
    text,
    encoding="utf-8",
)
PY

if [[ "$RENDER_ONLY" -eq 1 ]]; then
  cat "$RENDERED"
  exit 0
fi

kubectl get namespace \
  "$NAMESPACE" \
  >/dev/null \
  || fail "dw-synthea namespace missing"

kubectl get secret \
  "$SECRET_NAME" \
  -n "$NAMESPACE" \
  >/dev/null \
  || fail "Run 04b secret sync first"

NODE_READY="$(
  kubectl get node "$NODE" \
    -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}'
)"

[[ "$NODE_READY" == "True" ]] \
  || fail "worker01 is not Ready"

kubectl create configmap \
  "$CONFIGMAP_NAME" \
  -n "$NAMESPACE" \
  --from-file=publish_synthea_landing.py="$APP" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
    -f - \
    >/dev/null

CONFIGMAP_CREATED=1

if kubectl get job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    >/dev/null 2>&1
then
  kubectl delete job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    --cascade=foreground \
    --wait=true
fi

kubectl create \
  -f "$RENDERED"

JOB_CREATED=1

TERMINAL=""

for _ in $(seq 1 300); do

  COMPLETE="$(
    kubectl get job "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o jsonpath='{range .status.conditions[?(@.type=="Complete")]}{.status}{end}' \
      2>/dev/null || true
  )"

  FAILED="$(
    kubectl get job "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o jsonpath='{range .status.conditions[?(@.type=="Failed")]}{.status}{end}' \
      2>/dev/null || true
  )"

  if [[ "$COMPLETE" == "True" ]]; then
    TERMINAL="COMPLETE"
    break
  fi

  if [[ "$FAILED" == "True" ]]; then
    TERMINAL="FAILED"
    break
  fi

  sleep 5
done

[[ "$TERMINAL" == "COMPLETE" ]] \
  || fail "Generate-publish Job failed or timed out"

POD_NAME="$(
  kubectl get pods \
    -n "$NAMESPACE" \
    -l "job-name=${JOB_NAME}" \
    -o jsonpath='{.items[0].metadata.name}'
)"

[[ -n "$POD_NAME" ]] \
  || fail "Unable to resolve Job pod"

ACTUAL_NODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.nodeName}'
)"

EXIT_CODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.status.containerStatuses[0].state.terminated.exitCode}'
)"

[[ "$ACTUAL_NODE" == "$NODE" ]] \
  || fail "Job did not run on worker01"

[[ "$EXIT_CODE" == "0" ]] \
  || fail "Container exited non-zero"

if git check-ignore \
    -q \
    --no-index \
    "runtime/reports/task004/landing/probe"
then
  REPORT_DIR="${ROOT}/runtime/reports/task004/landing"
else
  REPORT_DIR="/data/spark/runtime/task004/landing"
fi

mkdir -p "$REPORT_DIR"

LOG_FILE="${REPORT_DIR}/${JOB_NAME}.log"
REPORT_FILE="${REPORT_DIR}/${JOB_NAME}.json"

kubectl logs \
  "$POD_NAME" \
  -n "$NAMESPACE" \
| tee "$LOG_FILE"

for marker in \
  "SYNTHEA_GENERATION=PASS" \
  "CSV_VALIDATED=18/18" \
  "LANDING_PUBLICATION=PASS" \
  "MANIFEST_STATUS=INTAKE_VERIFIED" \
  "S3_PAYLOAD_READBACK_SHA256=18/18" \
  "POSTGRESQL_WRITE=NO" \
  "TASK004_GENERATE_PUBLISH_RUNTIME=PASS"
do
  grep -F "$marker" \
    "$LOG_FILE" \
    >/dev/null \
    || fail "Missing runtime marker: ${marker}"
done

kubectl exec \
  "$POD_NAME" \
  -n "$NAMESPACE" \
  -- \
  cat \
    /work/evidence/landing-publication.json \
  > "$REPORT_FILE"

python3 - "$REPORT_FILE" "$BATCH_ID" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

if data["status"] != "INTAKE_VERIFIED":
    raise SystemExit(
        "ERROR: landing report not verified"
    )

if data["batch_id"] != sys.argv[2]:
    raise SystemExit(
        "ERROR: report batch mismatch"
    )

if data["verified_file_count"] != 18:
    raise SystemExit(
        "ERROR: report file count mismatch"
    )

print(
    "LANDING_REPORT_GATE=PASS"
)
PY

kubectl delete job \
  "$JOB_NAME" \
  -n "$NAMESPACE" \
  --cascade=foreground \
  --wait=true

JOB_CREATED=0

kubectl delete configmap \
  "$CONFIGMAP_NAME" \
  -n "$NAMESPACE" \
  --ignore-not-found=true \
  >/dev/null

CONFIGMAP_CREATED=0

echo "GENERATE_PUBLISH_RUNNER=PASS"
echo "KUBERNETES_RESIDUAL_JOB=NO"
echo "POSTGRESQL_WRITE=NO"
echo "RESULT=PASS"
