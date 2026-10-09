#!/usr/bin/env bash
set -Eeuo pipefail


ROOT="/data/spark/healthcare-data-platform"

STEP05_ROOT="${ROOT}/runtime/reports/task002/step05"
BASELINE="${ROOT}/runtime/reports/task002/step06/baseline/person-cdm-baseline.json"

APP_PY="${ROOT}/spark/apps/person/load_omop_person_stage.py"
TEMPLATE="${ROOT}/spark/manifests/task002/person-stage-load.yaml.tpl"

PG_NS="dw-postgre"
PG_POD="dw-postgre-database-0"
PG_DATABASE="omop"
PG_USER="omop_admin"

SPARK_NS="dw-spark"
CONFIGMAP="task002-person-stage-app"


psql_omop() {
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


scalar() {
    local sql="$1"

    psql_omop \
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

            row_to_json(x)::text
                AS row_json

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

            row_to_json(x)::text
                AS row_json

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


echo "============================================================"
echo "TASK-002 / STEP 06B"
echo "Load V2 OMOP Person into PostgreSQL Stage"
echo "============================================================"
echo


# ============================================================
# 1. Resolve frozen Step05 + Step06A
# ============================================================

LATEST_STEP05="$(
    find \
        "${STEP05_ROOT}" \
        -mindepth 2 \
        -maxdepth 2 \
        -name run-state.json \
        -type f \
        -printf '%T@ %p\n' \
    | sort -nr \
    | head -1 \
    | cut -d' ' -f2-
)"


[[ -n "${LATEST_STEP05}" ]] || {
    echo "ERROR: no STEP05 state."
    exit 1
}


[[ -s "${BASELINE}" ]] || {
    echo "ERROR: STEP06A baseline missing."
    exit 1
}


readarray -t VALUES < <(
python3 - \
    "${LATEST_STEP05}" \
    "${BASELINE}" <<'PY'

import json
import sys
from pathlib import Path


step05 = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

baseline = json.loads(
    Path(sys.argv[2]).read_text(
        encoding="utf-8"
    )
)


if step05.get("status") != "PASS":
    raise SystemExit(
        "STEP05 is not PASS."
    )

if baseline.get("status") != "PASS":
    raise SystemExit(
        "STEP06A baseline is not PASS."
    )

if (
    baseline.get("omop_run_id")
    != step05.get("omop_run_id")
):
    raise SystemExit(
        "Baseline does not belong to latest STEP05 run."
    )


print(
    step05["omop_run_id"]
)

print(
    step05["processed_data_uri"]
)

print(
    step05["processed_rows"]
)

print(
    step05["batch_id"]
)

print(
    baseline["cdm_person"]["fingerprint"]
)
PY
)


OMOP_RUN_ID="${VALUES[0]}"
PROCESSED_DATA_URI="${VALUES[1]}"
EXPECTED_ROWS="${VALUES[2]}"
BATCH_ID="${VALUES[3]}"
BASELINE_FINGERPRINT="${VALUES[4]}"


UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

STAGE_RUN_ID="person-stage-${UTC_STAMP}-$$"

APP_NAME="$(
    printf '%s' \
      "task002-person-stage-${UTC_STAMP,,}-$$"
)"

RUN_DIR="${ROOT}/runtime/reports/task002/step06/stage/${STAGE_RUN_ID}"

mkdir -p "${RUN_DIR}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"


echo "OMOP_RUN_ID=${OMOP_RUN_ID}"
echo "STAGE_RUN_ID=${STAGE_RUN_ID}"
echo "PROCESSED_DATA_URI=${PROCESSED_DATA_URI}"
echo


# ============================================================
# 2. Safety checks before any database write
# ============================================================

echo "[1/7] Safety checks..."


CURRENT_CDM_FINGERPRINT="$(
    cdm_fingerprint
)"


echo \
  "BASELINE_CDM_FINGERPRINT=${BASELINE_FINGERPRINT}"

echo \
  "CURRENT_CDM_FINGERPRINT=${CURRENT_CDM_FINGERPRINT}"


if [[ "${CURRENT_CDM_FINGERPRINT}" != "${BASELINE_FINGERPRINT}" ]]
then
    echo "ERROR:"
    echo "cdm.person changed after STEP06A baseline."
    exit 1
fi


STAGE_EXISTS="$(
    scalar "
    SELECT CASE
        WHEN to_regclass('etl.person_stage') IS NULL
        THEN 0
        ELSE 1
    END;
    "
)"


if [[ "${STAGE_EXISTS}" != "1" ]]; then
    echo "ERROR: etl.person_stage does not exist."
    exit 1
fi


STAGE_COLUMNS="$(
    scalar "
    SELECT string_agg(
        column_name,
        ','
        ORDER BY ordinal_position
    )
    FROM information_schema.columns
    WHERE table_schema = 'etl'
      AND table_name = 'person_stage';
    "
)"


EXPECTED_COLUMNS="person_id,gender_concept_id,year_of_birth,month_of_birth,day_of_birth,birth_datetime,race_concept_id,ethnicity_concept_id,location_id,provider_id,care_site_id,person_source_value,gender_source_value,gender_source_concept_id,race_source_value,race_source_concept_id,ethnicity_source_value,ethnicity_source_concept_id"


if [[ "${STAGE_COLUMNS}" != "${EXPECTED_COLUMNS}" ]]
then
    echo "ERROR:"
    echo "etl.person_stage schema mismatch."
    echo "ACTUAL=${STAGE_COLUMNS}"
    exit 1
fi


kubectl get secret \
    dw-spark-s3-secret \
    -n "${SPARK_NS}" \
    >/dev/null

kubectl get secret \
    dw-spark-omop-secret \
    -n "${SPARK_NS}" \
    >/dev/null

kubectl get serviceaccount \
    spark-job \
    -n "${SPARK_NS}" \
    >/dev/null


echo "PASS"
echo


# ============================================================
# 3. Controlled stage reset
# ============================================================

echo "[2/7] Reset etl.person_stage..."


psql_omop \
    -c "
    TRUNCATE TABLE etl.person_stage;
    " \
    >/dev/null


STAGE_AFTER_TRUNCATE="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_stage;
    "
)"


if [[ "${STAGE_AFTER_TRUNCATE}" != "0" ]]
then
    echo "ERROR: stage truncate failed."
    exit 1
fi


echo "STAGE_AFTER_TRUNCATE=0"
echo "CDM_PERSON_WRITE=NO"
echo "PASS"
echo


# ============================================================
# 4. ConfigMap + rendered SparkApplication
# ============================================================

echo "[3/7] Prepare SparkApplication..."


kubectl create configmap \
    "${CONFIGMAP}" \
    -n "${SPARK_NS}" \
    --from-file=load_omop_person_stage.py="${APP_PY}" \
    --dry-run=client \
    -o yaml \
| kubectl apply -f - \
    >/dev/null


sed \
    -e "s/__APP_NAME__/${APP_NAME}/g" \
    -e "s/__CONFIGMAP_NAME__/${CONFIGMAP}/g" \
    -e "s#__PROCESSED_DATA_URI__#${PROCESSED_DATA_URI}#g" \
    -e "s/__EXPECTED_ROWS__/${EXPECTED_ROWS}/g" \
    "${TEMPLATE}" \
    > "${RENDERED}"


if grep -q \
    '__[A-Z_]*__' \
    "${RENDERED}"
then
    echo "ERROR: unresolved SparkApplication placeholder."
    exit 1
fi


kubectl apply \
    --dry-run=client \
    -f "${RENDERED}" \
    >/dev/null


echo "PASS"
echo


# ============================================================
# 5. Execute Spark JDBC stage load
# ============================================================

echo "[4/7] Submit Spark stage load..."


kubectl apply \
    -f "${RENDERED}"


echo
echo "[5/7] Wait for SparkApplication..."


FINAL_STATE=""


for _ in $(seq 1 180)
do
    FINAL_STATE="$(
        kubectl get sparkapplication \
            "${APP_NAME}" \
            -n "${SPARK_NS}" \
            -o jsonpath='{.status.applicationState.state}' \
            2>/dev/null \
        || true
    )"


    case "${FINAL_STATE}" in

        COMPLETED)
            break
            ;;

        FAILED|FAILING|UNKNOWN)
            break
            ;;

    esac


    sleep 5
done


echo \
  "FINAL_STATE=${FINAL_STATE}"


kubectl logs \
    -n "${SPARK_NS}" \
    "${APP_NAME}-driver" \
    > "${DRIVER_LOG}" \
    2>&1 \
    || true


if [[ "${FINAL_STATE}" != "COMPLETED" ]]
then
    echo
    tail -200 "${DRIVER_LOG}" || true

    echo
    echo "ERROR:"
    echo "Spark stage load failed."

    exit 1
fi


for marker in \
    'PROCESSED_PERSON_DQ=PASS' \
    'POSTGRESQL_STAGE_WRITE=PASS' \
    'STAGE_READBACK=PASS' \
    'CDM_PERSON_WRITE=NO' \
    'TASK002_PERSON_STAGE_LOAD=PASS'
do
    if ! grep -Fxq \
        "${marker}" \
        "${DRIVER_LOG}"
    then
        echo "ERROR:"
        echo "Missing driver marker: ${marker}"
        exit 1
    fi
done


echo "PASS"
echo


# ============================================================
# 6. PostgreSQL reconciliation
# ============================================================

echo "[6/7] Reconcile Stage vs CDM baseline..."


STAGE_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_stage;
    "
)"


STAGE_UNIQUE="$(
    scalar "
    SELECT COUNT(DISTINCT person_id)
    FROM etl.person_stage;
    "
)"


STAGE_INVALID="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_stage
    WHERE person_id IS NULL
       OR gender_concept_id IS NULL
       OR year_of_birth IS NULL
       OR race_concept_id IS NULL
       OR ethnicity_concept_id IS NULL
       OR person_source_value IS NULL;
    "
)"


STAGE_FINGERPRINT="$(
    stage_fingerprint
)"


STAGE_MINUS_CDM="$(
    scalar "
    SELECT COUNT(*)
    FROM
    (
        SELECT
            person_id,
            gender_concept_id,
            year_of_birth,
            month_of_birth,
            day_of_birth,
            birth_datetime,
            race_concept_id,
            ethnicity_concept_id,
            location_id,
            provider_id,
            care_site_id,
            person_source_value,
            gender_source_value,
            gender_source_concept_id,
            race_source_value,
            race_source_concept_id,
            ethnicity_source_value,
            ethnicity_source_concept_id

        FROM etl.person_stage

        EXCEPT

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

        FROM cdm.person p

        JOIN etl.person_id_map m
          ON p.person_id = m.person_id

        WHERE m.source_system = 'synthea'
    ) d;
    "
)"


CDM_MINUS_STAGE="$(
    scalar "
    SELECT COUNT(*)
    FROM
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

        FROM cdm.person p

        JOIN etl.person_id_map m
          ON p.person_id = m.person_id

        WHERE m.source_system = 'synthea'

        EXCEPT

        SELECT
            person_id,
            gender_concept_id,
            year_of_birth,
            month_of_birth,
            day_of_birth,
            birth_datetime,
            race_concept_id,
            ethnicity_concept_id,
            location_id,
            provider_id,
            care_site_id,
            person_source_value,
            gender_source_value,
            gender_source_concept_id,
            race_source_value,
            race_source_concept_id,
            ethnicity_source_value,
            ethnicity_source_concept_id

        FROM etl.person_stage
    ) d;
    "
)"


CDM_AFTER_FINGERPRINT="$(
    cdm_fingerprint
)"


echo "STAGE_ROWS=${STAGE_ROWS}"
echo "STAGE_UNIQUE_IDS=${STAGE_UNIQUE}"
echo "STAGE_INVALID_REQUIRED=${STAGE_INVALID}"
echo "STAGE_FINGERPRINT=${STAGE_FINGERPRINT}"
echo "STAGE_MINUS_CDM=${STAGE_MINUS_CDM}"
echo "CDM_MINUS_STAGE=${CDM_MINUS_STAGE}"
echo "CDM_AFTER_FINGERPRINT=${CDM_AFTER_FINGERPRINT}"


if [[ "${STAGE_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR: stage row count mismatch."
    exit 1
fi


if [[ "${STAGE_UNIQUE}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR: stage person_id uniqueness failed."
    exit 1
fi


if [[ "${STAGE_INVALID}" != "0" ]]
then
    echo "ERROR: stage required fields failed."
    exit 1
fi


if [[ "${STAGE_MINUS_CDM}" != "0" ]]
then
    echo "ERROR:"
    echo "V2 stage contains rows different from baseline cdm.person."
    exit 1
fi


if [[ "${CDM_MINUS_STAGE}" != "0" ]]
then
    echo "ERROR:"
    echo "Baseline cdm.person contains rows missing/different from V2 stage."
    exit 1
fi


if [[ "${STAGE_FINGERPRINT}" != "${BASELINE_FINGERPRINT}" ]]
then
    echo "ERROR:"
    echo "Stage fingerprint differs from frozen CDM baseline."
    exit 1
fi


if [[ "${CDM_AFTER_FINGERPRINT}" != "${BASELINE_FINGERPRINT}" ]]
then
    echo "ERROR:"
    echo "cdm.person changed during STEP06B."
    exit 1
fi


echo "STAGE_VS_CDM=EXACT_MATCH"
echo "CDM_PERSON_UNCHANGED=PASS"
echo "PASS"
echo


# ============================================================
# 7. Persist state
# ============================================================

echo "[7/7] Persist STEP06B state..."


python3 - \
    "${STATE_FILE}" \
    "${BATCH_ID}" \
    "${OMOP_RUN_ID}" \
    "${STAGE_RUN_ID}" \
    "${APP_NAME}" \
    "${PROCESSED_DATA_URI}" \
    "${EXPECTED_ROWS}" \
    "${STAGE_FINGERPRINT}" \
    "${BASELINE_FINGERPRINT}" \
    "${CDM_AFTER_FINGERPRINT}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    batch_id,
    omop_run_id,
    stage_run_id,
    spark_application,
    processed_data_uri,
    rows,
    stage_fingerprint,
    baseline_fingerprint,
    cdm_after_fingerprint,
) = sys.argv[1:]


state = {
    "task": "TASK-002",
    "step": "STEP-06B",
    "status": "PASS",

    "entity":
        "person",

    "batch_id":
        batch_id,

    "omop_run_id":
        omop_run_id,

    "stage_run_id":
        stage_run_id,

    "spark_application":
        spark_application,

    "processed_data_uri":
        processed_data_uri,

    "stage_table":
        "etl.person_stage",

    "stage_rows":
        int(rows),

    "stage_unique_person_ids":
        int(rows),

    "stage_fingerprint":
        stage_fingerprint,

    "baseline_cdm_fingerprint":
        baseline_fingerprint,

    "cdm_after_fingerprint":
        cdm_after_fingerprint,

    "stage_vs_cdm":
        "EXACT_MATCH",

    "postgresql_stage_write":
        True,

    "cdm_person_write":
        False,

    "phase3c_touched":
        False,

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
echo "TASK-002 STEP 06B RESULT"
echo "============================================================"
echo
echo "STEP06B=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "STAGE_TABLE=etl.person_stage"
echo "STAGE_ROWS=${STAGE_ROWS}"
echo "STAGE_UNIQUE_IDS=${STAGE_UNIQUE}"
echo "STAGE_INVALID_REQUIRED=${STAGE_INVALID}"
echo "STAGE_VS_CDM=EXACT_MATCH"
echo "STAGE_FINGERPRINT=${STAGE_FINGERPRINT}"
echo "BASELINE_CDM_FINGERPRINT=${BASELINE_FINGERPRINT}"
echo "CDM_AFTER_FINGERPRINT=${CDM_AFTER_FINGERPRINT}"
echo "POSTGRESQL_STAGE_WRITE=YES"
echo "CDM_PERSON_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "STAGE_RUN_ID=${STAGE_RUN_ID}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
