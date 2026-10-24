#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

STEP05_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step05"
STEP06_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step06"

PG_NS="dw-postgre"
PG_POD="dw-postgre-database-0"
PG_DATABASE="omop"
PG_USER="omop_admin"

REPORT="${STEP06_ROOT}/baseline/person-cdm-baseline.json"

mkdir -p "$(dirname "${REPORT}")"


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
    local value

    value="$(
        psql_omop \
            -At \
            -c "${sql}"
    )"

    # Keep only non-empty query result lines.
    value="$(
        printf '%s\n' "${value}" \
        | sed '/^[[:space:]]*$/d' \
        | tail -n 1 \
        | tr -d '\r'
    )"

    printf '%s' "${value}"
}


require_integer() {
    local name="$1"
    local value="$2"

    if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
        echo "ERROR:"
        echo "${name} is not an integer."
        printf '%s=<%s>\n' \
            "${name}" \
            "${value}"
        exit 1
    fi
}


echo "============================================================"
echo "TASK-002 / STEP 06A"
echo "Capture Person CDM Baseline"
echo "============================================================"
echo


# ============================================================
# 1. Resolve latest verified STEP 05
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


if [[ -z "${LATEST_STEP05}" ]]; then
    echo "ERROR: no STEP05 state file found."
    exit 1
fi


readarray -t STEP05_VALUES < <(
python3 - "${LATEST_STEP05}" <<'PY'
import json
import sys
from pathlib import Path


path = Path(sys.argv[1])

data = json.loads(
    path.read_text(
        encoding="utf-8"
    )
)

required = {
    "task": "TASK-002",
    "step": "STEP-05",
    "status": "PASS",
    "entity": "person",
    "omop_version": "v5.4",
    "processed_rows": 113,
    "stable_person_id_map": "PASS",
    "demographic_concepts": "PASS",
    "postgresql_write": False,
    "cdm_person_write": False,
}

for key, expected in required.items():
    actual = data.get(key)

    if actual != expected:
        raise SystemExit(
            f"Invalid STEP05 state: "
            f"{key} expected={expected!r} "
            f"actual={actual!r}"
        )

print(data["batch_id"])
print(data["omop_run_id"])
print(data["processed_data_uri"])
print(data["processed_rows"])
PY
)


BATCH_ID="${STEP05_VALUES[0]}"
OMOP_RUN_ID="${STEP05_VALUES[1]}"
PROCESSED_DATA_URI="${STEP05_VALUES[2]}"
EXPECTED_ROWS="${STEP05_VALUES[3]}"


echo "Verified STEP05:"
echo "  ${LATEST_STEP05}"

echo
echo "Batch:"
echo "  ${BATCH_ID}"

echo
echo "OMOP Run:"
echo "  ${OMOP_RUN_ID}"

echo
echo "Processed Data:"
echo "  ${PROCESSED_DATA_URI}"

echo


# ============================================================
# 2. PostgreSQL prerequisite
# ============================================================

echo "[1/5] PostgreSQL prerequisites..."

kubectl get pod \
    "${PG_POD}" \
    -n "${PG_NS}" \
    >/dev/null


DB_READY="$(
    kubectl get pod \
        "${PG_POD}" \
        -n "${PG_NS}" \
        -o jsonpath='{.status.containerStatuses[0].ready}'
)"


if [[ "${DB_READY}" != "true" ]]; then
    echo "ERROR: PostgreSQL Pod is not ready."
    exit 1
fi


TEST_VALUE="$(
    scalar 'SELECT 1;'
)"

if [[ "${TEST_VALUE}" != "1" ]]; then
    echo "ERROR: PostgreSQL connectivity test failed."
    exit 1
fi

echo "PASS"
echo


# ============================================================
# 3. Stable mapping + CDM counts
# ============================================================

echo "[2/5] Capture Synthea Person counts..."


MAP_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_id_map
    WHERE source_system = 'synthea';
    "
)"


MAP_UNIQUE_SOURCE="$(
    scalar "
    SELECT COUNT(DISTINCT source_person_id)
    FROM etl.person_id_map
    WHERE source_system = 'synthea';
    "
)"


MAP_UNIQUE_PERSON="$(
    scalar "
    SELECT COUNT(DISTINCT person_id)
    FROM etl.person_id_map
    WHERE source_system = 'synthea';
    "
)"


CDM_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.person p
    JOIN etl.person_id_map m
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea';
    "
)"


CDM_UNIQUE="$(
    scalar "
    SELECT COUNT(DISTINCT p.person_id)
    FROM cdm.person p
    JOIN etl.person_id_map m
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea';
    "
)"


for pair in \
    "MAP_ROWS:${MAP_ROWS}" \
    "MAP_UNIQUE_SOURCE_IDS:${MAP_UNIQUE_SOURCE}" \
    "MAP_UNIQUE_PERSON_IDS:${MAP_UNIQUE_PERSON}" \
    "CDM_PERSON_ROWS:${CDM_ROWS}" \
    "CDM_PERSON_UNIQUE_IDS:${CDM_UNIQUE}"
do
    require_integer \
        "${pair%%:*}" \
        "${pair#*:}"
done


echo "MAP_ROWS=${MAP_ROWS}"
echo "MAP_UNIQUE_SOURCE_IDS=${MAP_UNIQUE_SOURCE}"
echo "MAP_UNIQUE_PERSON_IDS=${MAP_UNIQUE_PERSON}"
echo "CDM_PERSON_ROWS=${CDM_ROWS}"
echo "CDM_PERSON_UNIQUE_IDS=${CDM_UNIQUE}"

echo


# ============================================================
# 4. Reconciliation + baseline fingerprint
# ============================================================

echo "[3/5] Reconcile stable IDs and fingerprint cdm.person..."


MISSING_CDM="$(
    scalar "
    SELECT COUNT(*)
    FROM etl.person_id_map m
    LEFT JOIN cdm.person p
      ON p.person_id = m.person_id
    WHERE m.source_system = 'synthea'
      AND p.person_id IS NULL;
    "
)"


DUPLICATE_SOURCE_MAP="$(
    scalar "
    SELECT COUNT(*)
    FROM
    (
        SELECT source_person_id
        FROM etl.person_id_map
        WHERE source_system = 'synthea'
        GROUP BY source_person_id
        HAVING COUNT(*) > 1
    ) d;
    "
)"


DUPLICATE_PERSON_MAP="$(
    scalar "
    SELECT COUNT(*)
    FROM
    (
        SELECT person_id
        FROM etl.person_id_map
        WHERE source_system = 'synthea'
        GROUP BY person_id
        HAVING COUNT(*) > 1
    ) d;
    "
)"


CDM_FINGERPRINT="$(
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
)"


require_integer \
    "MISSING_CDM_PERSON_ROWS" \
    "${MISSING_CDM}"

require_integer \
    "DUPLICATE_SOURCE_MAP" \
    "${DUPLICATE_SOURCE_MAP}"

require_integer \
    "DUPLICATE_PERSON_MAP" \
    "${DUPLICATE_PERSON_MAP}"


if [[ ! "${CDM_FINGERPRINT}" =~ ^[0-9a-f]{32}$ ]]; then
    echo "ERROR: invalid CDM fingerprint."
    echo "VALUE=<${CDM_FINGERPRINT}>"
    exit 1
fi


echo "MISSING_CDM_PERSON_ROWS=${MISSING_CDM}"
echo "DUPLICATE_SOURCE_MAP=${DUPLICATE_SOURCE_MAP}"
echo "DUPLICATE_PERSON_MAP=${DUPLICATE_PERSON_MAP}"
echo "CDM_PERSON_FINGERPRINT=${CDM_FINGERPRINT}"

echo


# ============================================================
# 5. Inspect stage — strictly read-only
# ============================================================

echo "[4/5] Inspect existing person_stage..."


STAGE_EXISTS="$(
    scalar "
    SELECT CASE
        WHEN to_regclass('etl.person_stage') IS NULL
        THEN 0
        ELSE 1
    END;
    "
)"


require_integer \
    "PERSON_STAGE_EXISTS" \
    "${STAGE_EXISTS}"


STAGE_ROWS="0"
STAGE_COLUMNS="0"


if [[ "${STAGE_EXISTS}" == "1" ]]; then

    STAGE_ROWS="$(
        scalar "
        SELECT COUNT(*)
        FROM etl.person_stage;
        "
    )"

    STAGE_COLUMNS="$(
        scalar "
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = 'etl'
          AND table_name = 'person_stage';
        "
    )"

fi


require_integer \
    "PERSON_STAGE_ROWS" \
    "${STAGE_ROWS}"

require_integer \
    "PERSON_STAGE_COLUMNS" \
    "${STAGE_COLUMNS}"


echo "PERSON_STAGE_EXISTS=${STAGE_EXISTS}"
echo "PERSON_STAGE_ROWS=${STAGE_ROWS}"
echo "PERSON_STAGE_COLUMNS=${STAGE_COLUMNS}"

echo


# ============================================================
# 6. Baseline acceptance
# ============================================================

echo "[5/5] Validate baseline..."


if [[ "${CDM_ROWS}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR:"
    echo "Expected cdm.person baseline=${EXPECTED_ROWS}"
    echo "Actual=${CDM_ROWS}"
    exit 1
fi


if [[ "${CDM_UNIQUE}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR: cdm.person person_id uniqueness failed."
    exit 1
fi


if [[ "${MAP_UNIQUE_SOURCE}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR: stable source mapping baseline mismatch."
    exit 1
fi


if [[ "${MAP_UNIQUE_PERSON}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR: stable person mapping baseline mismatch."
    exit 1
fi


if [[ "${MISSING_CDM}" != "0" ]]; then
    echo "ERROR: mapped person IDs missing from cdm.person."
    exit 1
fi


if [[ "${DUPLICATE_SOURCE_MAP}" != "0" ]]; then
    echo "ERROR: duplicate source_person_id mapping."
    exit 1
fi


if [[ "${DUPLICATE_PERSON_MAP}" != "0" ]]; then
    echo "ERROR: duplicate person_id mapping."
    exit 1
fi


# Current legacy stage, when present, must still have
# the OMOP Person 18-column shape.
if [[ "${STAGE_EXISTS}" == "1" ]] \
   && [[ "${STAGE_COLUMNS}" != "18" ]]
then
    echo "ERROR:"
    echo "etl.person_stage does not have 18 columns."
    exit 1
fi


# ============================================================
# 7. Write local baseline report
# ============================================================

python3 - \
    "${REPORT}" \
    "${BATCH_ID}" \
    "${OMOP_RUN_ID}" \
    "${PROCESSED_DATA_URI}" \
    "${MAP_ROWS}" \
    "${MAP_UNIQUE_SOURCE}" \
    "${MAP_UNIQUE_PERSON}" \
    "${CDM_ROWS}" \
    "${CDM_UNIQUE}" \
    "${MISSING_CDM}" \
    "${DUPLICATE_SOURCE_MAP}" \
    "${DUPLICATE_PERSON_MAP}" \
    "${CDM_FINGERPRINT}" \
    "${STAGE_EXISTS}" \
    "${STAGE_ROWS}" \
    "${STAGE_COLUMNS}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    batch_id,
    omop_run_id,
    processed_data_uri,
    map_rows,
    map_unique_source,
    map_unique_person,
    cdm_rows,
    cdm_unique,
    missing_cdm,
    duplicate_source,
    duplicate_person,
    fingerprint,
    stage_exists,
    stage_rows,
    stage_columns,
) = sys.argv[1:]


report = {
    "task": "TASK-002",
    "step": "STEP-06A",
    "status": "PASS",

    "purpose":
        "idempotency_baseline",

    "batch_id":
        batch_id,

    "omop_run_id":
        omop_run_id,

    "processed_data_uri":
        processed_data_uri,

    "person_id_map": {
        "rows":
            int(map_rows),

        "unique_source_person_ids":
            int(map_unique_source),

        "unique_person_ids":
            int(map_unique_person),

        "duplicate_source_person_ids":
            int(duplicate_source),

        "duplicate_person_ids":
            int(duplicate_person),
    },

    "cdm_person": {
        "synthea_rows":
            int(cdm_rows),

        "unique_person_ids":
            int(cdm_unique),

        "missing_mapped_person_ids":
            int(missing_cdm),

        "fingerprint":
            fingerprint,
    },

    "person_stage": {
        "exists":
            stage_exists == "1",

        "rows":
            int(stage_rows),

        "columns":
            int(stage_columns),
    },

    "database_write":
        False,

    "captured_at":
        (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
}


Path(output).write_text(
    json.dumps(
        report,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY


python3 -m json.tool \
    "${REPORT}" \
    >/dev/null


echo "PASS"
echo

echo "============================================================"
echo "TASK-002 STEP 06A RESULT"
echo "============================================================"
echo
echo "STEP06A=PASS"
echo "IDEMPOTENCY_BASELINE=FROZEN"
echo "CDM_PERSON_ROWS=${CDM_ROWS}"
echo "CDM_PERSON_UNIQUE_IDS=${CDM_UNIQUE}"
echo "STABLE_MAP_MISSING=${MISSING_CDM}"
echo "STABLE_MAP_DUPLICATE_SOURCE=${DUPLICATE_SOURCE_MAP}"
echo "STABLE_MAP_DUPLICATE_PERSON=${DUPLICATE_PERSON_MAP}"
echo "CDM_PERSON_FINGERPRINT=${CDM_FINGERPRINT}"
echo "PERSON_STAGE_EXISTS=${STAGE_EXISTS}"
echo "PERSON_STAGE_ROWS=${STAGE_ROWS}"
echo "PERSON_STAGE_COLUMNS=${STAGE_COLUMNS}"
echo "DATABASE_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "BASELINE_REPORT=${REPORT}"
echo "============================================================"
