#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

TEMPLATE="${ROOT}/kubernetes/manifests/task004/synthea-generate-only-job.yaml.tpl"
RUNNER="${ROOT}/scripts/task004/03b-run-synthea-generate-only.sh"
TEST="${ROOT}/tests/task004/test_synthea_generate_only_runtime.py"

mkdir -p \
  "$(dirname "$TEMPLATE")" \
  "$(dirname "$RUNNER")" \
  "$(dirname "$TEST")"

# ============================================================
# Canonical Kubernetes Job template
# ============================================================

cat > "$TEMPLATE" <<'YAML_TEMPLATE'
apiVersion: batch/v1
kind: Job

metadata:
  name: __JOB_NAME__
  namespace: dw-synthea

  labels:
    app.kubernetes.io/name: synthea-generator
    app.kubernetes.io/part-of: healthcare-data-platform
    healthcare-data-platform/task: task004
    healthcare-data-platform/runtime: generate-only

spec:
  backoffLimit: 0

  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-generator
        healthcare-data-platform/task: task004
        healthcare-data-platform/runtime: generate-only

    spec:
      restartPolicy: Never
      automountServiceAccountToken: false

      nodeSelector:
        kubernetes.io/hostname: worker01

      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001

        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: synthea-generator

          image: __IMAGE_REF_JSON__
          imagePullPolicy: IfNotPresent

          securityContext:
            allowPrivilegeEscalation: false

            capabilities:
              drop:
                - ALL

          resources:
            requests:
              cpu: "250m"
              memory: "1Gi"

            limits:
              cpu: "2"
              memory: "4Gi"

          env:
            - name: BATCH_ID
              value: __BATCH_ID_JSON__

            - name: POPULATION_SIZE
              value: __POPULATION_SIZE_JSON__

            - name: SEED
              value: __SEED_JSON__

            - name: CLINICIAN_SEED
              value: __CLINICIAN_SEED_JSON__

            - name: REFERENCE_DATE
              value: __REFERENCE_DATE_JSON__

            - name: STATE
              value: __STATE_JSON__

            - name: CITY
              value: __CITY_JSON__

          command:
            - /bin/bash
            - -lc

          args:
            - |
              set -Eeuo pipefail

              echo "GENERATE_ONLY_CONTAINER_START=YES"

              /usr/local/bin/healthcare-synthea-generator

              python3 - <<'PY'
              import hashlib
              import json
              from pathlib import Path

              manifest_path = Path(
                  "/work/evidence/manifest.draft.json"
              )

              validation_path = Path(
                  "/work/evidence/validation.json"
              )

              manifest = json.loads(
                  manifest_path.read_text(
                      encoding="utf-8"
                  )
              )

              validation = json.loads(
                  validation_path.read_text(
                      encoding="utf-8"
                  )
              )

              if manifest.get("status") != (
                  "LOCAL_VALIDATED_NOT_UPLOADED"
              ):
                  raise SystemExit(
                      "ERROR: unexpected draft "
                      "manifest status"
                  )

              if validation.get("status") != "PASS":
                  raise SystemExit(
                      "ERROR: local validation "
                      "status is not PASS"
                  )

              if validation.get(
                  "validated_file_count"
              ) != 18:
                  raise SystemExit(
                      "ERROR: validated_file_count "
                      "is not 18"
                  )

              files = manifest.get("files")

              if (
                  not isinstance(files, list)
                  or len(files) != 18
              ):
                  raise SystemExit(
                      "ERROR: draft manifest must "
                      "contain exactly 18 files"
                  )

              names = [
                  Path(item["path"]).name
                  for item in files
              ]

              if len(names) != len(set(names)):
                  raise SystemExit(
                      "ERROR: duplicate file names "
                      "in draft manifest"
                  )

              patients = next(
                  (
                      item
                      for item in files
                      if Path(item["path"]).name
                      == "patients.csv"
                  ),
                  None,
              )

              if patients is None:
                  raise SystemExit(
                      "ERROR: patients.csv missing "
                      "from draft manifest"
                  )

              fingerprint = hashlib.sha256()

              for item in sorted(
                  files,
                  key=lambda value:
                      Path(value["path"]).name,
              ):
                  filename = Path(
                      item["path"]
                  ).name

                  row_count = item[
                      "row_count"
                  ]

                  size_bytes = item[
                      "size_bytes"
                  ]

                  sha256 = item[
                      "sha256"
                  ]

                  print(
                      "FILE_EVIDENCE|"
                      f"{filename}|"
                      f"{row_count}|"
                      f"{size_bytes}|"
                      f"{sha256}"
                  )

                  fingerprint.update(
                      (
                          filename
                          + "|"
                          + sha256
                          + "\n"
                      ).encode("utf-8")
                  )

              print(
                  "MANIFEST_STATUS="
                  + manifest["status"]
              )

              print(
                  "VALIDATION_REPORT_STATUS="
                  + validation["status"]
              )

              print(
                  "VALIDATED_FILE_COUNT="
                  + str(
                      validation[
                          "validated_file_count"
                      ]
                  )
              )

              print(
                  "PATIENT_ROWS="
                  + str(
                      patients[
                          "row_count"
                      ]
                  )
              )

              print(
                  "PAYLOAD_FINGERPRINT="
                  + fingerprint.hexdigest()
              )

              print(
                  "LANDING_PUBLICATION="
                  "NOT_STARTED"
              )

              print(
                  "GENERATE_ONLY_RUNTIME=PASS"
              )
              PY
YAML_TEMPLATE

# ============================================================
# Canonical manual runtime runner
# ============================================================

cat > "$RUNNER" <<'RUNNER_SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

TEMPLATE="${ROOT}/kubernetes/manifests/task004/synthea-generate-only-job.yaml.tpl"

NAMESPACE="dw-synthea"
NODE="worker01"

DEFAULT_IMAGE_REF="ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d"

IMAGE_REF="${SYNTHEA_IMAGE_REF:-${DEFAULT_IMAGE_REF}}"

RENDER_ONLY=0
JOB_CREATED=0
JOB_NAME=""
POD_NAME=""

fail() {
  echo "ERROR=$*" >&2

  if [[ "$JOB_CREATED" -eq 1 ]]; then
    echo >&2
    echo "FAILURE_DIAGNOSTICS_BEGIN" >&2

    kubectl get job \
      "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o wide \
      >&2 2>/dev/null || true

    echo >&2

    kubectl get pods \
      -n "$NAMESPACE" \
      -l "job-name=${JOB_NAME}" \
      -o wide \
      >&2 2>/dev/null || true

    if [[ -n "$POD_NAME" ]]; then
      echo >&2

      kubectl describe pod \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true

      echo >&2
      echo "POD_LOG_BEGIN" >&2

      kubectl logs \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true

      echo "POD_LOG_END" >&2
    fi

    echo "FAILED_JOB_RETAINED_FOR_DIAGNOSIS=YES" >&2
    echo "FAILURE_DIAGNOSTICS_END" >&2
  fi

  exit 1
}

usage() {
  cat <<'USAGE'
TASK004 canonical Synthea generate-only runner.

Required environment:
  BATCH_ID
  POPULATION_SIZE       20 or 50
  SEED
  REFERENCE_DATE        YYYYMMDD
  STATE

Optional environment:
  CLINICIAN_SEED        defaults to SEED
  CITY                  defaults to empty
  SYNTHEA_IMAGE_REF     must be digest-pinned @sha256 reference

Options:
  --render-only         render Job YAML only; no Kubernetes mutation

Generate-only means:
  - generate Synthea CSV;
  - validate exact 18-CSV contract;
  - emit row/size/SHA256 evidence;
  - do NOT publish Landing;
  - do NOT write PostgreSQL.
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

[[ -s "$TEMPLATE" ]] \
  || fail "Missing canonical Job template: ${TEMPLATE}"

[[ "$POPULATION_SIZE" == "20" || "$POPULATION_SIZE" == "50" ]] \
  || fail "POPULATION_SIZE must be 20 or 50"

[[ "$SEED" =~ ^-?[0-9]+$ ]] \
  || fail "SEED must be an integer"

[[ "$CLINICIAN_SEED" =~ ^-?[0-9]+$ ]] \
  || fail "CLINICIAN_SEED must be an integer"

[[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]] \
  || fail "SYNTHEA_IMAGE_REF must be digest-pinned"

python3 - \
  "$BATCH_ID" \
  "$REFERENCE_DATE" \
  "$STATE" \
  <<'PY'
import re
import sys
from datetime import datetime

batch_id = sys.argv[1]
reference_date = sys.argv[2]
state = sys.argv[3]

if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",
    batch_id,
):
    raise SystemExit(
        "ERROR: invalid BATCH_ID"
    )

try:
    datetime.strptime(
        reference_date,
        "%Y%m%d",
    )
except ValueError as exc:
    raise SystemExit(
        "ERROR: REFERENCE_DATE must be "
        "valid YYYYMMDD"
    ) from exc

if not state.strip():
    raise SystemExit(
        "ERROR: STATE must not be blank"
    )
PY

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

if not slug:
    slug = "batch"

digest = hashlib.sha256(
    value.encode("utf-8")
).hexdigest()[:10]

slug = slug[:36].rstrip("-")

print(
    f"task004-syn-{slug}-{digest}"
)
PY
)"

[[ "$JOB_NAME" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] \
  || fail "Generated Job name is not DNS-safe"

[[ "${#JOB_NAME}" -le 63 ]] \
  || fail "Generated Job name exceeds 63 characters"

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
  "$IMAGE_REF" \
  "$BATCH_ID" \
  "$POPULATION_SIZE" \
  "$SEED" \
  "$CLINICIAN_SEED" \
  "$REFERENCE_DATE" \
  "$STATE" \
  "$CITY" \
  <<'PY'
import json
import sys
from pathlib import Path

(
    template_path,
    output_path,
    job_name,
    image_ref,
    batch_id,
    population_size,
    seed,
    clinician_seed,
    reference_date,
    state,
    city,
) = sys.argv[1:]

text = Path(
    template_path
).read_text(
    encoding="utf-8"
)

mapping = {
    "__JOB_NAME__":
        job_name,

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
}

for key, value in mapping.items():
    count = text.count(key)

    if count != 1:
        raise SystemExit(
            "ERROR: template placeholder "
            f"{key} count={count}"
        )

    text = text.replace(
        key,
        value,
    )

if "__" in text:
    unresolved = sorted(
        {
            token
            for token in text.split()
            if token.startswith("__")
        }
    )

    if unresolved:
        raise SystemExit(
            "ERROR: unresolved template "
            "placeholders: "
            + ", ".join(unresolved)
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
  || fail "Namespace ${NAMESPACE} missing"

NODE_READY="$(
  kubectl get node "$NODE" \
    -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}'
)"

[[ "$NODE_READY" == "True" ]] \
  || fail "${NODE} is not Ready"

echo "============================================================"
echo "TASK004 canonical generate-only runtime"
echo "============================================================"
echo "JOB_NAME=${JOB_NAME}"
echo "NAMESPACE=${NAMESPACE}"
echo "NODE=${NODE}"
echo "BATCH_ID=${BATCH_ID}"
echo "POPULATION_SIZE=${POPULATION_SIZE}"
echo "SEED=${SEED}"
echo "CLINICIAN_SEED=${CLINICIAN_SEED}"
echo "REFERENCE_DATE=${REFERENCE_DATE}"
echo "STATE=${STATE}"
echo "CITY=${CITY}"
echo "IMAGE_REF=${IMAGE_REF}"
echo

if kubectl get job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    >/dev/null 2>&1
then
  echo "STALE_JOB=FOUND"

  kubectl delete job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    --cascade=foreground \
    --wait=true

  echo "STALE_JOB=DELETED"
fi

kubectl create \
  -f "$RENDERED"

JOB_CREATED=1

echo "JOB_CREATED=YES"

TERMINAL=""

for _ in $(seq 1 240); do
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

echo "JOB_TERMINAL_STATE=${TERMINAL:-TIMEOUT}"

[[ "$TERMINAL" == "COMPLETE" ]] \
  || fail "Generate-only Job did not complete"

POD_NAME="$(
  kubectl get pods \
    -n "$NAMESPACE" \
    -l "job-name=${JOB_NAME}" \
    -o jsonpath='{.items[0].metadata.name}'
)"

[[ -n "$POD_NAME" ]] \
  || fail "Unable to resolve Job Pod"

PHASE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.status.phase}'
)"

ACTUAL_NODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.nodeName}'
)"

SPEC_IMAGE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.containers[0].image}'
)"

EXIT_CODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.status.containerStatuses[0].state.terminated.exitCode}'
)"

echo "POD_NAME=${POD_NAME}"
echo "POD_PHASE=${PHASE}"
echo "ACTUAL_NODE=${ACTUAL_NODE}"
echo "SPEC_IMAGE=${SPEC_IMAGE}"
echo "CONTAINER_EXIT_CODE=${EXIT_CODE}"

[[ "$PHASE" == "Succeeded" ]] \
  || fail "Pod phase is not Succeeded"

[[ "$ACTUAL_NODE" == "$NODE" ]] \
  || fail "Pod was not scheduled to worker01"

[[ "$SPEC_IMAGE" == "$IMAGE_REF" ]] \
  || fail "Pod image differs from requested digest"

[[ "$EXIT_CODE" == "0" ]] \
  || fail "Container exit code is non-zero"

if git check-ignore \
    -q \
    --no-index \
    "runtime/reports/task004/generate-only/probe"
then
  REPORT_DIR="${ROOT}/runtime/reports/task004/generate-only"
else
  REPORT_DIR="/data/spark/runtime/task004/generate-only"
fi

mkdir -p "$REPORT_DIR"

LOG_FILE="${REPORT_DIR}/${JOB_NAME}.log"
JSON_FILE="${REPORT_DIR}/${JOB_NAME}.json"

kubectl logs \
  "$POD_NAME" \
  -n "$NAMESPACE" \
  | tee "$LOG_FILE"

LOG="$(cat "$LOG_FILE")"

REQUIRED_MARKERS=(
  "SYNTHEA_GENERATION=PASS"
  "CSV_VALIDATED=18/18"
  "SYNTHEA_LOCAL_VALIDATION=PASS"
  "MANIFEST_STATUS=LOCAL_VALIDATED_NOT_UPLOADED"
  "VALIDATION_REPORT_STATUS=PASS"
  "VALIDATED_FILE_COUNT=18"
  "LANDING_PUBLICATION=NOT_STARTED"
  "GENERATE_ONLY_RUNTIME=PASS"
)

for marker in "${REQUIRED_MARKERS[@]}"; do
  grep -F \
    "$marker" \
    <<<"$LOG" \
    >/dev/null \
    || fail "Missing runtime marker: ${marker}"
done

grep -F \
  "BATCH_ID=${BATCH_ID}" \
  <<<"$LOG" \
  >/dev/null \
  || fail "Runtime BATCH_ID mismatch"

grep -F \
  "POPULATION_SIZE=${POPULATION_SIZE}" \
  <<<"$LOG" \
  >/dev/null \
  || fail "Runtime POPULATION_SIZE mismatch"

FILE_COUNT="$(
  grep -c '^FILE_EVIDENCE|' \
    <<<"$LOG"
)"

[[ "$FILE_COUNT" == "18" ]] \
  || fail "Expected exactly 18 FILE_EVIDENCE records"

PAYLOAD_FINGERPRINT="$(
  awk -F= '
    /^PAYLOAD_FINGERPRINT=/ {
      print $2
      exit
    }
  ' <<<"$LOG"
)"

[[ "$PAYLOAD_FINGERPRINT" =~ ^[0-9a-f]{64}$ ]] \
  || fail "Invalid payload fingerprint"

PATIENT_ROWS="$(
  awk -F= '
    /^PATIENT_ROWS=/ {
      print $2
      exit
    }
  ' <<<"$LOG"
)"

[[ "$PATIENT_ROWS" == "$POPULATION_SIZE" ]] \
  || fail "patients.csv row count differs from POPULATION_SIZE"

python3 - \
  "$LOG_FILE" \
  "$JSON_FILE" \
  "$BATCH_ID" \
  "$POPULATION_SIZE" \
  "$SEED" \
  "$CLINICIAN_SEED" \
  "$REFERENCE_DATE" \
  "$STATE" \
  "$CITY" \
  "$IMAGE_REF" \
  "$PAYLOAD_FINGERPRINT" \
  <<'PY'
import json
import sys
from pathlib import Path

(
    log_file,
    json_file,
    batch_id,
    population_size,
    seed,
    clinician_seed,
    reference_date,
    state,
    city,
    image_ref,
    fingerprint,
) = sys.argv[1:]

files = []

for line in Path(
    log_file
).read_text(
    encoding="utf-8"
).splitlines():

    if not line.startswith(
        "FILE_EVIDENCE|"
    ):
        continue

    _, filename, rows, size, sha = (
        line.split("|", 4)
    )

    files.append(
        {
            "filename":
                filename,
            "row_count":
                int(rows),
            "size_bytes":
                int(size),
            "sha256":
                sha,
        }
    )

files.sort(
    key=lambda item:
        item["filename"]
)

if len(files) != 18:
    raise SystemExit(
        "ERROR: evidence must contain 18 files"
    )

payload = {
    "schema":
        "task004-generate-only-runtime-evidence-v1",

    "status":
        "PASS",

    "batch_id":
        batch_id,

    "image_ref":
        image_ref,

    "source_parameters": {
        "population_size":
            int(population_size),

        "seed":
            int(seed),

        "clinician_seed":
            int(clinician_seed),

        "reference_date":
            reference_date,

        "state":
            state,

        "city":
            city or None,
    },

    "payload_fingerprint":
        fingerprint,

    "files":
        files,

    "landing_publication":
        "NOT_STARTED",

    "postgresql_write":
        False,
}

Path(
    json_file
).write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)

print(
    f"RUNTIME_EVIDENCE_JSON={json_file}"
)

print(
    "RUNTIME_EVIDENCE_FILE_COUNT="
    f"{len(files)}"
)

print(
    "RUNTIME_EVIDENCE_GATE=PASS"
)
PY

kubectl delete job \
  "$JOB_NAME" \
  -n "$NAMESPACE" \
  --cascade=foreground \
  --wait=true

JOB_CREATED=0

if kubectl get job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    >/dev/null 2>&1
then
  fail "Job remains after cleanup"
fi

if kubectl get pods \
    -n "$NAMESPACE" \
    -l "job-name=${JOB_NAME}" \
    --no-headers \
    2>/dev/null \
    | grep -q .
then
  fail "Pod remains after cleanup"
fi

echo
echo "GENERATE_ONLY_RUNNER=PASS"
echo "CSV_VALIDATED=18/18"
echo "PATIENT_ROWS=${PATIENT_ROWS}"
echo "PAYLOAD_FINGERPRINT=${PAYLOAD_FINGERPRINT}"
echo "LANDING_PUBLICATION=NOT_STARTED"
echo "POSTGRESQL_WRITE=NO"
echo "KUBERNETES_RESIDUAL_RESOURCE=NO"
echo "RESULT=PASS"
RUNNER_SCRIPT

chmod 0755 \
  "$RUNNER"

# ============================================================
# Static/unit tests
# ============================================================

cat > "$TEST" <<'PY_TEST'
"""Static tests for TASK004 canonical Synthea generate-only runtime."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

TEMPLATE = (
    ROOT
    / "kubernetes/manifests/task004/"
      "synthea-generate-only-job.yaml.tpl"
)

RUNNER = (
    ROOT
    / "scripts/task004/"
      "03b-run-synthea-generate-only.sh"
)

GENERATOR = (
    ROOT
    / "scripts/task004/"
      "03a-prepare-synthea-generate-only-runtime.sh"
)

EXPECTED_DIGEST = (
    "sha256:"
    "2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d"
)


class SyntheaGenerateOnlyRuntimeTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text(
            encoding="utf-8"
        )

        cls.runner = RUNNER.read_text(
            encoding="utf-8"
        )

        cls.generator = GENERATOR.read_text(
            encoding="utf-8"
        )

    def test_source_files_exist(self):
        self.assertTrue(
            TEMPLATE.is_file()
        )

        self.assertTrue(
            RUNNER.is_file()
        )

        self.assertTrue(
            GENERATOR.is_file()
        )

    def test_namespace_is_dw_synthea(self):
        self.assertIn(
            "namespace: dw-synthea",
            self.template,
        )

    def test_worker01_is_mandatory(self):
        self.assertIn(
            "kubernetes.io/hostname: worker01",
            self.template,
        )

        self.assertIn(
            'NODE="worker01"',
            self.runner,
        )

    def test_job_is_non_retrying(self):
        self.assertIn(
            "backoffLimit: 0",
            self.template,
        )

        self.assertIn(
            "restartPolicy: Never",
            self.template,
        )

    def test_service_account_token_not_mounted(self):
        self.assertIn(
            "automountServiceAccountToken: false",
            self.template,
        )

    def test_runtime_is_non_root(self):
        for token in (
            "runAsNonRoot: true",
            "runAsUser: 10001",
            "runAsGroup: 10001",
            "allowPrivilegeEscalation: false",
        ):
            self.assertIn(
                token,
                self.template,
            )

    def test_image_is_digest_pinned(self):
        self.assertIn(
            EXPECTED_DIGEST,
            self.runner,
        )

        self.assertIn(
            r'@sha256:[0-9a-f]{64}',
            self.runner,
        )

    def test_supported_profiles_are_20_and_50(self):
        self.assertIn(
            '"20" || "$POPULATION_SIZE" == "50"',
            self.runner,
        )

    def test_clinician_seed_defaults_to_seed(self):
        self.assertIn(
            'CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"',
            self.runner,
        )

    def test_generate_only_invokes_canonical_entrypoint(self):
        self.assertIn(
            "/usr/local/bin/healthcare-synthea-generator",
            self.template,
        )

    def test_exact_18_file_evidence_is_required(self):
        self.assertIn(
            '[[ "$FILE_COUNT" == "18" ]]',
            self.runner,
        )

        self.assertIn(
            '"validated_file_count"',
            self.template,
        )

        self.assertIn(
            '"ERROR: validated_file_count "',
            self.template,
        )

        self.assertIn(
            '"is not 18"',
            self.template,
        )

        self.assertIn(
            '"VALIDATED_FILE_COUNT="',
            self.template,
        )

    def test_patients_match_requested_population(self):
        self.assertIn(
            '[[ "$PATIENT_ROWS" == "$POPULATION_SIZE" ]]',
            self.runner,
        )

    def test_generate_only_does_not_publish_landing(self):
        combined = (
            self.template
            + "\n"
            + self.runner
        )

        self.assertIn(
            "LANDING_PUBLICATION=NOT_STARTED",
            combined,
        )

        forbidden = (
            "aws s3",
            "s3api",
            "mc cp",
            "boto3",
            "psql ",
            "jdbc:postgresql",
        )

        lowered = combined.lower()

        for token in forbidden:
            self.assertNotIn(
                token.lower(),
                lowered,
            )

    def test_runner_supports_render_only(self):
        self.assertIn(
            "--render-only",
            self.runner,
        )

        self.assertIn(
            'if [[ "$RENDER_ONLY" -eq 1 ]]',
            self.runner,
        )

    def test_success_cleanup_is_required(self):
        self.assertIn(
            'kubectl delete job',
            self.runner,
        )

        self.assertIn(
            "KUBERNETES_RESIDUAL_RESOURCE=NO",
            self.runner,
        )

    def test_template_placeholders_are_explicit(self):
        placeholders = set(
            re.findall(
                r"__[A-Z0-9_]+__",
                self.template,
            )
        )

        self.assertEqual(
            placeholders,
            {
                "__JOB_NAME__",
                "__IMAGE_REF_JSON__",
                "__BATCH_ID_JSON__",
                "__POPULATION_SIZE_JSON__",
                "__SEED_JSON__",
                "__CLINICIAN_SEED_JSON__",
                "__REFERENCE_DATE_JSON__",
                "__STATE_JSON__",
                "__CITY_JSON__",
            },
        )


if __name__ == "__main__":
    unittest.main()
PY_TEST

echo "GENERATE_ONLY_RUNTIME_SOURCE=INSTALLED"
echo "TEMPLATE=${TEMPLATE}"
echo "RUNNER=${RUNNER}"
echo "TEST=${TEST}"
