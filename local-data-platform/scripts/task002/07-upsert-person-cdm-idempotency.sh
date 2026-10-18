#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data/spark/healthcare-data-platform"

SQL_FILE="${ROOT}/sql/task002/person-upsert.sql"
BASELINE="${ROOT}/runtime/reports/task002/step06/baseline/person-cdm-baseline.json"
STEP06_STAGE_ROOT="${ROOT}/runtime/reports/task002/step06/stage"
RESULT_ROOT="${ROOT}/runtime/reports/task002/step07"

PG_NS="dw-postgre"
PG_POD="dw-postgre-database-0"
PG_DATABASE="omop"
PG_USER="omop_admin"

mkdir -p "${RESULT_ROOT}"


psql_cmd() {
    kubectl exec \
        -n "${PG_NS}" \
        "${PG_POD}" -- \
        psql \
            -X \
            -q \
            -v ON_ERROR_STOP=1 \
            -U "${PG_USER}" \
            -d "${PG_DATABASE}" \
            "$@"
}


psql_stdin() {
    kubectl exec \
        -i \
        -n "${PG_NS}" \
        "${PG_POD}" -- \
        psql \
            -X \
            -qAt \
            -v ON_ERROR_STOP=1 \
            -U "${PG_USER}" \
            -d "${PG_DATABASE}"
}


scalar() {
    local sql="$1"

    psql_cmd \
        -At \
        -c "${sql}" \
    | sed '/^[[:space:]]*$/d' \
    | tail -1 \
    | tr -d '\r'
}


cdm_fingerprint() {
    scalar "
    SELECT md5(
        COALESCE(
            string_agg(
                row_json,
                E'\n'
                ORDER BY person_id
            ),
            ''
        )
    )
    FROM
    (
        SELECT
            p.person_id,
            row_to_json(x)::text AS row_json
        FROM cdm.person p
        JOIN etl.person_id_map m
          ON p.person_id = m.person_id
        CROSS JOIN LATERAL
        (
            SELECT
                p.person_id,
                p.gender_concept_id,
                p.year_of_birth,
                p.month_of_birth,
                p.day_of_birth,
                p.birth_datetime,
                p.race_concept_id,
                p.ethnicity_concept_id,
                p.location_id,
                p.provider_id,
                p.care_site_id,
                p.person_source_value,
                p.gender_source_value,
                p.gender_source_concept_id,
                p.race_source_value,
                p.race_source_concept_id,
                p.ethnicity_source_value,
                p.ethnicity_source_concept_id
        ) x
        WHERE m.source_system = 'synthea'
    ) q;
    "
}


stage_fingerprint() {
    scalar "
    SELECT md5(
        COALESCE(
            string_agg(
                row_json,
                E'\n'
                ORDER BY person_id
            ),
            ''
        )
    )
    FROM
    (
        SELECT
            p.person_id,
            row_to_json(x)::text AS row_json
        FROM etl.person_stage p
        CROSS JOIN LATERAL
        (
            SELECT
                p.person_id,
                p.gender_concept_id,
                p.year_of_birth,
                p.month_of_birth,
                p.day_of_birth,
                p.birth_datetime,
                p.race_concept_id,
                p.ethnicity_concept_id,
                p.location_id,
                p.provider_id,
                p.care_site_id,
                p.person_source_value,
                p.gender_source_value,
                p.gender_source_concept_id,
                p.race_source_value,
                p.race_source_concept_id,
                p.ethnicity_source_value,
                p.ethnicity_source_concept_id
        ) x
    ) q;
    "
}


run_upsert() {
    local label="$1"
    local output="$2"

    echo
    echo "------------------------------------------------------------"
    echo "${label}"
    echo "------------------------------------------------------------"

    psql_stdin \
        < "${SQL_FILE}" \
        | tee "${output}"

    for marker in \
        'UPSERT_PLAN_INSERT_ROWS=0' \
        'UPSERT_PLAN_UPDATE_ROWS=0' \
        'POST_UPSERT_STAGE_MINUS_CDM=0' \
        'POST_UPSERT_CDM_MINUS_STAGE=0'
    do
        if ! grep -Fxq "${marker}" "${output}"
        then
            echo
            echo "ERROR:"
            echo "Missing expected marker:"
            echo "  ${marker}"
            exit 1
        fi
    done
}


echo "============================================================"
echo "TASK-002 / STEP 07B"
echo "Transactional Person UPSERT + Idempotency Replay"
echo "============================================================"
echo


# ============================================================
# 1. Preconditions
# ============================================================

echo "[1/6] Preconditions..."


[[ -s "${SQL_FILE}" ]] || {
    echo "ERROR: UPSERT SQL missing."
    exit 1
}


[[ -s "${BASELINE}" ]] || {
    echo "ERROR: STEP06A baseline missing."
    exit 1
}


LATEST_STAGE_STATE="$(
    find \
        "${STEP06_STAGE_ROOT}" \
        -mindepth 2 \
        -maxdepth 2 \
        -name run-state.json \
        -type f \
        -printf '%T@ %p\n' \
    | sort -nr \
    | head -1 \
    | cut -d' ' -f2-
)"


[[ -n "${LATEST_STAGE_STATE}" ]] || {
    echo "ERROR: STEP06B state missing."
    exit 1
}


readarray -t VALUES < <(
python3 - \
    "${BASELINE}" \
    "${LATEST_STAGE_STATE}" <<'PY'

import json
import sys
from pathlib import Path

baseline = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

stage = json.loads(
    Path(sys.argv[2]).read_text(encoding="utf-8")
)

if baseline.get("status") != "PASS":
    raise SystemExit("STEP06A baseline is not PASS.")

if stage.get("status") != "PASS":
    raise SystemExit("STEP06B is not PASS.")

if stage.get("stage_vs_cdm") != "EXACT_MATCH":
    raise SystemExit("STEP06B Stage/CDM reconciliation not PASS.")

if stage.get("cdm_person_write") is not False:
    raise SystemExit("Unexpected CDM write in STEP06B.")

print(baseline["cdm_person"]["synthea_rows"])
print(baseline["cdm_person"]["fingerprint"])
print(stage["stage_rows"])
print(stage["stage_fingerprint"])
print(stage["stage_run_id"])
print(stage["omop_run_id"])
PY
)


EXPECTED_ROWS="${VALUES[0]}"
BASELINE_FP="${VALUES[1]}"
STAGE_ROWS_STATE="${VALUES[2]}"
STAGE_FP_STATE="${VALUES[3]}"
STAGE_RUN_ID="${VALUES[4]}"
OMOP_RUN_ID="${VALUES[5]}"


if [[ "${EXPECTED_ROWS}" != "${STAGE_ROWS_STATE}" ]]
then
    echo "ERROR: baseline/stage row mismatch."
    exit 1
fi


if [[ "${BASELINE_FP}" != "${STAGE_FP_STATE}" ]]
then
    echo "ERROR: baseline/stage fingerprint mismatch."
    exit 1
fi


echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
echo "BASELINE_FINGERPRINT=${BASELINE_FP}"
echo "STAGE_RUN_ID=${STAGE_RUN_ID}"
echo "OMOP_RUN_ID=${OMOP_RUN_ID}"
echo "PASS"
echo


# ============================================================
# 2. Runtime pre-UPSERT verification
# ============================================================

echo "[2/6] Runtime pre-UPSERT verification..."


PRE_CDM_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.person p
    JOIN etl.person_id_map m
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea';
    "
)"


PRE_STAGE_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_stage;
    "
)"


PRE_CDM_FP="$(
    cdm_fingerprint
)"


PRE_STAGE_FP="$(
    stage_fingerprint
)"


echo "PRE_CDM_ROWS=${PRE_CDM_ROWS}"
echo "PRE_STAGE_ROWS=${PRE_STAGE_ROWS}"
echo "PRE_CDM_FINGERPRINT=${PRE_CDM_FP}"
echo "PRE_STAGE_FINGERPRINT=${PRE_STAGE_FP}"


if [[ "${PRE_CDM_ROWS}" != "${EXPECTED_ROWS}" ]] \
   || [[ "${PRE_STAGE_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR: runtime row-count baseline changed."
    exit 1
fi


if [[ "${PRE_CDM_FP}" != "${BASELINE_FP}" ]] \
   || [[ "${PRE_STAGE_FP}" != "${BASELINE_FP}" ]]
then
    echo "ERROR: runtime fingerprint baseline changed."
    exit 1
fi


echo "PASS"
echo


# ============================================================
# 3. First transactional UPSERT
# ============================================================

UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

RUN_ID="person-upsert-${UTC_STAMP}-$$"
RUN_DIR="${RESULT_ROOT}/${RUN_ID}"

mkdir -p "${RUN_DIR}"

FIRST_LOG="${RUN_DIR}/upsert-first.log"
SECOND_LOG="${RUN_DIR}/upsert-second.log"
STATE_FILE="${RUN_DIR}/run-state.json"


echo "[3/6] First transactional UPSERT..."

run_upsert \
    "FIRST UPSERT" \
    "${FIRST_LOG}"


FIRST_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.person p
    JOIN etl.person_id_map m
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea';
    "
)"


FIRST_FP="$(
    cdm_fingerprint
)"


echo "FIRST_CDM_ROWS=${FIRST_ROWS}"
echo "FIRST_CDM_FINGERPRINT=${FIRST_FP}"


if [[ "${FIRST_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR: first UPSERT changed row count."
    exit 1
fi


if [[ "${FIRST_FP}" != "${BASELINE_FP}" ]]
then
    echo "ERROR: first UPSERT changed CDM content."
    exit 1
fi


echo "FIRST_UPSERT=PASS"
echo


# ============================================================
# 4. Second UPSERT — explicit idempotency replay
# ============================================================

echo "[4/6] Second UPSERT / idempotency replay..."

run_upsert \
    "SECOND UPSERT / IDEMPOTENCY REPLAY" \
    "${SECOND_LOG}"


SECOND_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.person p
    JOIN etl.person_id_map m
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea';
    "
)"


SECOND_FP="$(
    cdm_fingerprint
)"


echo "SECOND_CDM_ROWS=${SECOND_ROWS}"
echo "SECOND_CDM_FINGERPRINT=${SECOND_FP}"


if [[ "${SECOND_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR: idempotency replay changed row count."
    exit 1
fi


if [[ "${SECOND_FP}" != "${BASELINE_FP}" ]]
then
    echo "ERROR: idempotency replay changed CDM content."
    exit 1
fi


echo "SECOND_UPSERT=PASS"
echo "RERUN_IDEMPOTENCY=PASS"
echo


# ============================================================
# 5. Final reconciliation
# ============================================================

echo "[5/6] Final reconciliation..."


FINAL_STAGE_MINUS_CDM="$(
    scalar "
    SELECT COUNT(*)
    FROM
    (
        SELECT *
        FROM etl.person_stage

        EXCEPT

        SELECT p.*
        FROM cdm.person p
        JOIN etl.person_id_map m
          ON p.person_id = m.person_id
        WHERE m.source_system = 'synthea'
    ) d;
    "
)"


FINAL_CDM_MINUS_STAGE="$(
    scalar "
    SELECT COUNT(*)
    FROM
    (
        SELECT p.*
        FROM cdm.person p
        JOIN etl.person_id_map m
          ON p.person_id = m.person_id
        WHERE m.source_system = 'synthea'

        EXCEPT

        SELECT *
        FROM etl.person_stage
    ) d;
    "
)"


echo "FINAL_STAGE_MINUS_CDM=${FINAL_STAGE_MINUS_CDM}"
echo "FINAL_CDM_MINUS_STAGE=${FINAL_CDM_MINUS_STAGE}"


if [[ "${FINAL_STAGE_MINUS_CDM}" != "0" ]] \
   || [[ "${FINAL_CDM_MINUS_STAGE}" != "0" ]]
then
    echo "ERROR: final Stage/CDM reconciliation failed."
    exit 1
fi


echo "FINAL_STAGE_VS_CDM=EXACT_MATCH"
echo "PASS"
echo


# ============================================================
# 6. Persist final state
# ============================================================

echo "[6/6] Persist STEP07B state..."


python3 - \
    "${STATE_FILE}" \
    "${RUN_ID}" \
    "${OMOP_RUN_ID}" \
    "${STAGE_RUN_ID}" \
    "${EXPECTED_ROWS}" \
    "${BASELINE_FP}" \
    "${FIRST_FP}" \
    "${SECOND_FP}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    run_id,
    omop_run_id,
    stage_run_id,
    rows,
    baseline_fp,
    first_fp,
    second_fp,
) = sys.argv[1:]


state = {
    "task": "TASK-002",
    "step": "STEP-07B",
    "status": "PASS",

    "entity": "person",

    "upsert_run_id":
        run_id,

    "omop_run_id":
        omop_run_id,

    "stage_run_id":
        stage_run_id,

    "cdm_person_rows":
        int(rows),

    "baseline_fingerprint":
        baseline_fp,

    "first_upsert_fingerprint":
        first_fp,

    "second_upsert_fingerprint":
        second_fp,

    "first_upsert":
        "PASS",

    "second_upsert":
        "PASS",

    "rerun_idempotency":
        "PASS",

    "stage_vs_cdm":
        "EXACT_MATCH",

    "completed_at":
        (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
}


Path(output).write_text(
    json.dumps(
        state,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY


python3 -m json.tool \
    "${STATE_FILE}" \
    >/dev/null


echo "PASS"
echo

echo "============================================================"
echo "TASK-002 STEP 07B RESULT"
echo "============================================================"
echo
echo "STEP07B=PASS"
echo "FIRST_UPSERT=PASS"
echo "SECOND_UPSERT=PASS"
echo "RERUN_IDEMPOTENCY=PASS"
echo "CDM_PERSON_ROWS=${SECOND_ROWS}"
echo "BASELINE_FINGERPRINT=${BASELINE_FP}"
echo "FIRST_UPSERT_FINGERPRINT=${FIRST_FP}"
echo "SECOND_UPSERT_FINGERPRINT=${SECOND_FP}"
echo "FINAL_STAGE_MINUS_CDM=0"
echo "FINAL_CDM_MINUS_STAGE=0"
echo "FINAL_STAGE_VS_CDM=EXACT_MATCH"
echo
echo "UPSERT_RUN_ID=${RUN_ID}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
