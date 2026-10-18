#!/usr/bin/env bash
set -Eeuo pipefail

SYNTHEA_JAR="${SYNTHEA_JAR:-/opt/synthea/synthea-with-dependencies.jar}"
CSV_CONTRACT="${CSV_CONTRACT:-/opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json}"
VALIDATOR="${VALIDATOR:-/opt/healthcare/apps/task004/validate_generated_synthea_batch.py}"

OUTPUT_ROOT="${OUTPUT_ROOT:-/work/output}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-/work/evidence}"

show_help() {
  cat <<'HELP'
Healthcare Data Platform TASK004 Synthea Generator

Required environment:
  BATCH_ID
  POPULATION_SIZE        Initial TASK004 profiles: 20 or 50
  SEED
  REFERENCE_DATE         YYYYMMDD
  STATE

Optional environment:
  CLINICIAN_SEED         Defaults to SEED
  CITY                   Optional Synthea city

Fixed provenance:
  SYNTHEA_VERSION=v3.3.0
  SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

This image stage performs:
  Synthea generation
  exact 18-CSV validation
  SHA256 calculation
  local draft manifest creation

Landing publication is intentionally not performed by STEP03 source.
HELP
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  show_help
  exit 0
fi

: "${BATCH_ID:?BATCH_ID is required}"
: "${POPULATION_SIZE:?POPULATION_SIZE is required}"
: "${SEED:?SEED is required}"
: "${REFERENCE_DATE:?REFERENCE_DATE is required}"
: "${STATE:?STATE is required}"
: "${SYNTHEA_VERSION:?SYNTHEA_VERSION is required}"
: "${SYNTHEA_COMMIT:?SYNTHEA_COMMIT is required}"

CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"
CITY="${CITY:-}"

[[ "${POPULATION_SIZE}" =~ ^[0-9]+$ ]] || {
  echo "ERROR: POPULATION_SIZE must be a positive integer" >&2
  exit 2
}

(( POPULATION_SIZE > 0 )) || {
  echo "ERROR: POPULATION_SIZE must be greater than zero" >&2
  exit 2
}

if [[ "${POPULATION_SIZE}" != "20" && "${POPULATION_SIZE}" != "50" ]]; then
  echo "ERROR: initial TASK004 POPULATION_SIZE must be 20 or 50" >&2
  exit 2
fi

[[ "${SEED}" =~ ^-?[0-9]+$ ]] || {
  echo "ERROR: SEED must be an integer" >&2
  exit 2
}

[[ "${CLINICIAN_SEED}" =~ ^-?[0-9]+$ ]] || {
  echo "ERROR: CLINICIAN_SEED must be an integer" >&2
  exit 2
}

python3 - "${REFERENCE_DATE}" <<'PY'
import sys
from datetime import datetime

value = sys.argv[1]

try:
    datetime.strptime(
        value,
        "%Y%m%d",
    )
except ValueError as exc:
    raise SystemExit(
        "ERROR: REFERENCE_DATE must be "
        "a valid YYYYMMDD date"
    ) from exc
PY

[[ "${SYNTHEA_VERSION}" == "v3.3.0" ]] || {
  echo "ERROR: unexpected SYNTHEA_VERSION=${SYNTHEA_VERSION}" >&2
  exit 2
}

[[ "${SYNTHEA_COMMIT}" == "995cf2fd33e67918d4e33110d9f68ad248002221" ]] || {
  echo "ERROR: unexpected SYNTHEA_COMMIT=${SYNTHEA_COMMIT}" >&2
  exit 2
}

[[ -s "${SYNTHEA_JAR}" ]] || {
  echo "ERROR: missing Synthea JAR: ${SYNTHEA_JAR}" >&2
  exit 2
}

[[ -s "${CSV_CONTRACT}" ]] || {
  echo "ERROR: missing CSV contract: ${CSV_CONTRACT}" >&2
  exit 2
}

[[ -s "${VALIDATOR}" ]] || {
  echo "ERROR: missing validator: ${VALIDATOR}" >&2
  exit 2
}

rm -rf \
  "${OUTPUT_ROOT}" \
  "${EVIDENCE_ROOT}"

mkdir -p \
  "${OUTPUT_ROOT}" \
  "${EVIDENCE_ROOT}"

echo "============================================================"
echo "Healthcare Data Platform TASK004"
echo "Synthea Generator"
echo "============================================================"
echo "BATCH_ID=${BATCH_ID}"
echo "POPULATION_SIZE=${POPULATION_SIZE}"
echo "SEED=${SEED}"
echo "CLINICIAN_SEED=${CLINICIAN_SEED}"
echo "REFERENCE_DATE=${REFERENCE_DATE}"
echo "STATE=${STATE}"
echo "CITY=${CITY}"
echo "SYNTHEA_VERSION=${SYNTHEA_VERSION}"
echo "SYNTHEA_COMMIT=${SYNTHEA_COMMIT}"
echo

SYNTHEA_ARGS=(
  "-s"
  "${SEED}"

  "-cs"
  "${CLINICIAN_SEED}"

  "-p"
  "${POPULATION_SIZE}"

  "-r"
  "${REFERENCE_DATE}"

  "--exporter.baseDirectory=${OUTPUT_ROOT}"

  "--exporter.metadata.export=false"

  "--exporter.csv.export=true"

  "--exporter.csv.append_mode=false"

  "--exporter.csv.folder_per_run=false"

  "--exporter.csv.excluded_files=patient_expenses.csv"

  "--exporter.years_of_history=0"

  "--exporter.ccda.export=false"

  "--exporter.fhir.export=false"

  "--exporter.fhir_stu3.export=false"

  "--exporter.fhir_dstu2.export=false"

  "--exporter.hospital.fhir.export=false"

  "--exporter.hospital.fhir_stu3.export=false"

  "--exporter.hospital.fhir_dstu2.export=false"

  "--exporter.practitioner.fhir.export=false"

  "--exporter.practitioner.fhir_stu3.export=false"

  "--exporter.practitioner.fhir_dstu2.export=false"

  "--exporter.groups.fhir.export=false"

  "--exporter.json.export=false"

  "--exporter.cpcds.export=false"

  "--exporter.bfd.export=false"

  "--exporter.cdw.export=false"

  "--exporter.text.export=false"

  "--exporter.clinical_note.export=false"

  "--exporter.symptoms.csv.export=false"

  "--exporter.symptoms.text.export=false"

  "--generate.thread_pool_size=1"

  "--generate.log_patients.detail=none"
)

if [[ -n "${CITY}" ]]; then
  SYNTHEA_ARGS+=(
    "${STATE}"
    "${CITY}"
  )
else
  SYNTHEA_ARGS+=(
    "${STATE}"
  )
fi

echo "Starting Synthea generation..."

java \
  -jar "${SYNTHEA_JAR}" \
  "${SYNTHEA_ARGS[@]}"

CSV_DIR="${OUTPUT_ROOT}/csv"

[[ -d "${CSV_DIR}" ]] || {
  echo "ERROR: Synthea did not create ${CSV_DIR}" >&2
  exit 1
}

VALIDATOR_ARGS=(
  python3
  "${VALIDATOR}"

  --source-dir
  "${CSV_DIR}"

  --contract
  "${CSV_CONTRACT}"

  --batch-id
  "${BATCH_ID}"

  --synthea-version
  "${SYNTHEA_VERSION}"

  --synthea-commit
  "${SYNTHEA_COMMIT}"

  --population-size
  "${POPULATION_SIZE}"

  --seed
  "${SEED}"

  --clinician-seed
  "${CLINICIAN_SEED}"

  --reference-date
  "${REFERENCE_DATE}"

  --state
  "${STATE}"

  --output
  "${EVIDENCE_ROOT}/manifest.draft.json"

  --report
  "${EVIDENCE_ROOT}/validation.json"
)

if [[ -n "${CITY}" ]]; then
  VALIDATOR_ARGS+=(
    --city
    "${CITY}"
  )
fi

echo
echo "Validating generated CSV batch..."

"${VALIDATOR_ARGS[@]}"

echo
echo "SYNTHEA_GENERATION=PASS"
echo "POPULATION_SIZE=${POPULATION_SIZE}"
echo "BATCH_ID=${BATCH_ID}"
echo "DRAFT_MANIFEST=${EVIDENCE_ROOT}/manifest.draft.json"
echo "VALIDATION_REPORT=${EVIDENCE_ROOT}/validation.json"
echo "LANDING_PUBLICATION=NOT_STARTED"
