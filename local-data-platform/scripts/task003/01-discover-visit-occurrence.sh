#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data/spark/healthcare-data-platform"

SOURCE_CSV="/data/spark/phase3c/source/synthea/csv/encounters.csv"

PG_NS="dw-postgre"
PG_POD="dw-postgre-database-0"
PG_DATABASE="omop"
PG_USER="omop_admin"

REPORT_DIR="${ROOT}/runtime/reports/task003/discovery"

mkdir -p "${REPORT_DIR}"


psql_omop() {
    kubectl exec \
        -n "${PG_NS}" \
        "${PG_POD}" -- \
        psql \
            -X \
            -v ON_ERROR_STOP=1 \
            -U "${PG_USER}" \
            -d "${PG_DATABASE}" \
            "$@"
}


scalar() {
    local sql="$1"

    psql_omop \
        -qAt \
        -c "${sql}" \
    | sed '/^[[:space:]]*$/d' \
    | tail -1 \
    | tr -d '\r'
}


echo "============================================================"
echo "TASK-003 / STEP 01"
echo "Visit Occurrence Discovery"
echo "============================================================"
echo


# ============================================================
# 1. Source CSV inspection
# ============================================================

echo "[1/6] Inspect Synthea encounters.csv..."

[[ -s "${SOURCE_CSV}" ]] || {
    echo "ERROR:"
    echo "Missing source:"
    echo "  ${SOURCE_CSV}"
    exit 1
}


python3 - "${SOURCE_CSV}" <<'PY'
import csv
import sys
from collections import Counter
from pathlib import Path


path = Path(sys.argv[1])


with path.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:

    reader = csv.DictReader(f)

    columns = reader.fieldnames or []

    rows = list(reader)


print(
    "SOURCE_COLUMNS="
    + ",".join(columns)
)

print(
    "SOURCE_ROWS="
    + str(len(rows))
)


def detect(*names):
    lookup = {
        c.lower(): c
        for c in columns
    }

    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]

    return None


id_col = detect("Id", "ID")
patient_col = detect(
    "Patient",
    "PATIENT"
)
start_col = detect(
    "Start",
    "START"
)
stop_col = detect(
    "Stop",
    "STOP"
)
class_col = detect(
    "EncounterClass",
    "ENCOUNTERCLASS"
)


required = {
    "ID_COLUMN":
        id_col,

    "PATIENT_COLUMN":
        patient_col,

    "START_COLUMN":
        start_col,

    "STOP_COLUMN":
        stop_col,

    "ENCOUNTER_CLASS_COLUMN":
        class_col,
}


for key, value in required.items():

    print(
        f"{key}="
        + (
            value
            if value is not None
            else "NOT_FOUND"
        )
    )


missing = [
    key
    for key, value
    in required.items()
    if value is None
]


if missing:
    raise SystemExit(
        "Missing expected columns: "
        + ",".join(missing)
    )


ids = [
    (row.get(id_col) or "").strip()
    for row in rows
]

patients = [
    (row.get(patient_col) or "").strip()
    for row in rows
]


print(
    "UNIQUE_ENCOUNTER_IDS="
    + str(
        len(
            {
                x
                for x in ids
                if x
            }
        )
    )
)

print(
    "UNIQUE_PATIENT_IDS="
    + str(
        len(
            {
                x
                for x in patients
                if x
            }
        )
    )
)


id_counts = Counter(ids)

duplicate_ids = sum(
    1
    for key, count
    in id_counts.items()
    if key and count > 1
)


print(
    "DUPLICATE_ENCOUNTER_IDS="
    + str(duplicate_ids)
)


for col, label in [
    (
        id_col,
        "NULL_ENCOUNTER_ID"
    ),
    (
        patient_col,
        "NULL_PATIENT_ID"
    ),
    (
        start_col,
        "NULL_START"
    ),
    (
        stop_col,
        "NULL_STOP"
    ),
    (
        class_col,
        "NULL_ENCOUNTER_CLASS"
    ),
]:

    count = sum(
        1
        for row in rows
        if not (
            row.get(col)
            or ""
        ).strip()
    )

    print(
        f"{label}={count}"
    )


classes = Counter(
    (
        row.get(class_col)
        or ""
    ).strip()
    for row in rows
)


print(
    "ENCOUNTER_CLASS_DISTINCT="
    + str(
        len(
            [
                x
                for x in classes
                if x
            ]
        )
    )
)


print(
    "ENCOUNTER_CLASS_COUNTS_BEGIN"
)

for key in sorted(classes):

    if not key:
        continue

    print(
        f"{key}={classes[key]}"
    )

print(
    "ENCOUNTER_CLASS_COUNTS_END"
)
PY


echo "PASS"
echo


# ============================================================
# 2. PostgreSQL OMOP Visit table
# ============================================================

echo "[2/6] Inspect cdm.visit_occurrence..."


VISIT_EXISTS="$(
    scalar "
    SELECT CASE
        WHEN to_regclass(
            'cdm.visit_occurrence'
        ) IS NULL
        THEN 0
        ELSE 1
    END;
    "
)"


echo \
  "VISIT_OCCURRENCE_EXISTS=${VISIT_EXISTS}"


if [[ "${VISIT_EXISTS}" != "1" ]]; then
    echo "ERROR:"
    echo "cdm.visit_occurrence does not exist."
    exit 1
fi


VISIT_COLUMNS="$(
    scalar "
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = 'cdm'
      AND table_name = 'visit_occurrence';
    "
)"


VISIT_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.visit_occurrence;
    "
)"


echo \
  "VISIT_OCCURRENCE_COLUMNS=${VISIT_COLUMNS}"

echo \
  "VISIT_OCCURRENCE_ROWS=${VISIT_ROWS}"


echo
echo "VISIT_SCHEMA_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        ordinal_position,
        column_name,
        data_type,
        is_nullable

    FROM information_schema.columns

    WHERE table_schema = 'cdm'
      AND table_name = 'visit_occurrence'

    ORDER BY ordinal_position;
    "

echo "VISIT_SCHEMA_END"

echo "PASS"
echo


# ============================================================
# 3. Constraints
# ============================================================

echo "[3/6] Inspect Visit constraints..."


echo "VISIT_CONSTRAINTS_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        tc.constraint_name,
        tc.constraint_type,
        kcu.column_name,
        ccu.table_schema
            AS foreign_table_schema,
        ccu.table_name
            AS foreign_table_name,
        ccu.column_name
            AS foreign_column_name

    FROM information_schema.table_constraints tc

    LEFT JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.constraint_schema = kcu.constraint_schema

    LEFT JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
     AND tc.constraint_schema = ccu.constraint_schema

    WHERE tc.table_schema = 'cdm'
      AND tc.table_name = 'visit_occurrence'

    ORDER BY
        tc.constraint_type,
        tc.constraint_name,
        kcu.ordinal_position;
    "

echo "VISIT_CONSTRAINTS_END"

echo "PASS"
echo


# ============================================================
# 4. Check source Patient -> stable person_id coverage
# ============================================================

echo "[4/6] Check Encounter Patient -> stable Person coverage..."


TMP_PATIENTS="$(
    mktemp
)"


trap \
  'rm -f "${TMP_PATIENTS}"' \
  EXIT


python3 - \
    "${SOURCE_CSV}" \
    "${TMP_PATIENTS}" <<'PY'

import csv
import sys
from pathlib import Path


source = Path(sys.argv[1])
output = Path(sys.argv[2])


with source.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:

    reader = csv.DictReader(f)

    patient_col = next(
        (
            c
            for c in reader.fieldnames or []
            if c.lower() == "patient"
        ),
        None,
    )

    if patient_col is None:
        raise SystemExit(
            "Patient column not found."
        )

    values = sorted(
        {
            (
                row.get(patient_col)
                or ""
            ).strip()

            for row in reader
            if (
                row.get(patient_col)
                or ""
            ).strip()
        }
    )


output.write_text(
    "\n".join(values)
    + "\n",
    encoding="utf-8",
)


print(
    "SOURCE_UNIQUE_VISIT_PATIENTS="
    + str(len(values))
)
PY


SOURCE_PATIENT_COUNT="$(
    wc -l \
      < "${TMP_PATIENTS}" \
    | tr -d '[:space:]'
)"


MAP_SOURCE_IDS="$(
    mktemp
)"


trap \
  'rm -f "${TMP_PATIENTS}" "${MAP_SOURCE_IDS}"' \
  EXIT


psql_omop \
    -qAt \
    -c "
    SELECT source_person_id
    FROM etl.person_id_map
    WHERE source_system = 'synthea'
    ORDER BY source_person_id;
    " \
    > "${MAP_SOURCE_IDS}"


MISSING_PATIENTS="$(
    comm \
      -23 \
      "${TMP_PATIENTS}" \
      "${MAP_SOURCE_IDS}" \
    | wc -l \
    | tr -d '[:space:]'
)"


echo \
  "SOURCE_UNIQUE_VISIT_PATIENTS=${SOURCE_PATIENT_COUNT}"

echo \
  "VISIT_PATIENTS_MISSING_PERSON_MAP=${MISSING_PATIENTS}"


if [[ "${MISSING_PATIENTS}" != "0" ]]; then

    echo
    echo "MISSING_PATIENT_IDS_BEGIN"

    comm \
      -23 \
      "${TMP_PATIENTS}" \
      "${MAP_SOURCE_IDS}"

    echo "MISSING_PATIENT_IDS_END"

fi


echo "PASS"
echo


# ============================================================
# 5. Existing Visit source values / concepts
# ============================================================

echo "[5/6] Inspect existing Visit data..."


echo "EXISTING_VISIT_CONCEPTS_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        visit_concept_id,
        COUNT(*) AS rows

    FROM cdm.visit_occurrence

    GROUP BY visit_concept_id

    ORDER BY
        rows DESC,
        visit_concept_id;
    "

echo "EXISTING_VISIT_CONCEPTS_END"


echo
echo "EXISTING_VISIT_SOURCE_VALUES_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        visit_source_value,
        COUNT(*) AS rows

    FROM cdm.visit_occurrence

    GROUP BY visit_source_value

    ORDER BY
        rows DESC,
        visit_source_value

    LIMIT 30;
    "

echo "EXISTING_VISIT_SOURCE_VALUES_END"

echo "PASS"
echo


# ============================================================
# 6. Discovery summary
# ============================================================

echo "[6/6] Discovery summary..."

echo
echo "============================================================"
echo "TASK-003 STEP 01 RESULT"
echo "============================================================"
echo
echo "STEP01=PASS"
echo "ENTITY=visit_occurrence"
echo "SOURCE_FILE=encounters.csv"
echo "VISIT_OCCURRENCE_EXISTS=YES"
echo "VISIT_OCCURRENCE_COLUMNS=${VISIT_COLUMNS}"
echo "VISIT_OCCURRENCE_ROWS=${VISIT_ROWS}"
echo "SOURCE_UNIQUE_VISIT_PATIENTS=${SOURCE_PATIENT_COUNT}"
echo "VISIT_PATIENTS_MISSING_PERSON_MAP=${MISSING_PATIENTS}"
echo "DATABASE_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo "============================================================"
