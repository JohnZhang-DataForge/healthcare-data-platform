#!/usr/bin/env bash
set -Eeuo pipefail

PG_NS="dw-postgre"
PG_POD="dw-postgre-database-0"
PG_DATABASE="omop"
PG_USER="omop_admin"

SOURCE_CSV="/data/spark/phase3c/source/synthea/csv/encounters.csv"


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
echo "TASK-003 / STEP 02"
echo "Visit Mapping Foundation Discovery"
echo "============================================================"
echo


# ============================================================
# 1. Existing ETL Visit ID infrastructure
# ============================================================

echo "[1/6] Inspect existing Visit ID infrastructure..."


VISIT_MAP_EXISTS="$(
    scalar "
    SELECT CASE
        WHEN to_regclass(
            'etl.visit_occurrence_id_map'
        ) IS NULL
        THEN 0
        ELSE 1
    END;
    "
)"


echo \
  "VISIT_ID_MAP_EXISTS=${VISIT_MAP_EXISTS}"


echo
echo "ETL_VISIT_OBJECTS_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        table_schema,
        table_name

    FROM information_schema.tables

    WHERE table_schema = 'etl'
      AND (
           table_name ILIKE '%visit%'
        OR table_name ILIKE '%encounter%'
      )

    ORDER BY
        table_schema,
        table_name;
    "

echo "ETL_VISIT_OBJECTS_END"


echo
echo "VISIT_SEQUENCES_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        sequence_schema,
        sequence_name

    FROM information_schema.sequences

    WHERE sequence_name ILIKE '%visit%'
       OR sequence_name ILIKE '%encounter%'

    ORDER BY
        sequence_schema,
        sequence_name;
    "

echo "VISIT_SEQUENCES_END"

echo "PASS"
echo


# ============================================================
# 2. Existing visit_occurrence PK state
# ============================================================

echo "[2/6] Inspect Visit PK state..."


VISIT_ROWS="$(
    scalar "
    SELECT COUNT(*)
    FROM cdm.visit_occurrence;
    "
)"


MAX_VISIT_ID="$(
    scalar "
    SELECT COALESCE(
        MAX(visit_occurrence_id),
        0
    )
    FROM cdm.visit_occurrence;
    "
)"


echo \
  "VISIT_OCCURRENCE_ROWS=${VISIT_ROWS}"

echo \
  "MAX_VISIT_OCCURRENCE_ID=${MAX_VISIT_ID}"

echo "PASS"
echo


# ============================================================
# 3. Source encounter CODE / class relationship
# ============================================================

echo "[3/6] Inspect EncounterClass and source CODE distribution..."


python3 - "${SOURCE_CSV}" <<'PY'
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


path = Path(sys.argv[1])

with path.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:

    reader = csv.DictReader(f)

    rows = list(reader)


pairs = Counter()

codes_by_class = defaultdict(set)


for row in rows:

    encounter_class = (
        row.get("ENCOUNTERCLASS")
        or ""
    ).strip()

    code = (
        row.get("CODE")
        or ""
    ).strip()

    pairs[
        (
            encounter_class,
            code,
        )
    ] += 1

    if code:
        codes_by_class[
            encounter_class
        ].add(code)


print(
    "ENCOUNTER_CLASS_CODE_SUMMARY_BEGIN"
)

for encounter_class in sorted(codes_by_class):

    codes = sorted(
        codes_by_class[
            encounter_class
        ]
    )

    print(
        f"{encounter_class}:"
        f"distinct_codes={len(codes)}"
    )

print(
    "ENCOUNTER_CLASS_CODE_SUMMARY_END"
)


print(
    "TOP_CLASS_CODE_PAIRS_BEGIN"
)

for (
    encounter_class,
    code,
), count in pairs.most_common(40):

    print(
        f"{encounter_class}|{code}|{count}"
    )

print(
    "TOP_CLASS_CODE_PAIRS_END"
)
PY


echo "PASS"
echo


# ============================================================
# 4. Standard Visit concept candidates
# ============================================================

echo "[4/6] Inspect standard OMOP Visit concepts..."


echo "STANDARD_VISIT_CONCEPT_CANDIDATES_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        concept_id,
        concept_name,
        vocabulary_id,
        concept_class_id,
        standard_concept,
        concept_code,
        invalid_reason

    FROM cdm.concept

    WHERE domain_id = 'Visit'
      AND standard_concept = 'S'
      AND invalid_reason IS NULL
      AND
      (
           lower(concept_name) LIKE '%inpatient%'
        OR lower(concept_name) LIKE '%outpatient%'
        OR lower(concept_name) LIKE '%emergency%'
        OR lower(concept_name) LIKE '%ambulatory%'
        OR lower(concept_name) LIKE '%home%'
        OR lower(concept_name) LIKE '%hospice%'
        OR lower(concept_name) LIKE '%skilled nursing%'
        OR lower(concept_name) LIKE '%urgent%'
        OR lower(concept_name) LIKE '%tele%'
        OR lower(concept_name) LIKE '%virtual%'
        OR lower(concept_name) LIKE '%wellness%'
    )

    ORDER BY
        concept_name,
        concept_id;
    "

echo "STANDARD_VISIT_CONCEPT_CANDIDATES_END"

echo "PASS"
echo


# ============================================================
# 5. Visit Type concept candidates
# ============================================================

echo "[5/6] Inspect Visit Type concepts..."


echo "VISIT_TYPE_CONCEPT_CANDIDATES_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        concept_id,
        concept_name,
        domain_id,
        vocabulary_id,
        concept_class_id,
        standard_concept,
        concept_code,
        invalid_reason

    FROM cdm.concept

    WHERE invalid_reason IS NULL
      AND
      (
           lower(concept_name) LIKE '%ehr%'
        OR lower(concept_name) LIKE '%electronic health record%'
        OR lower(concept_name) LIKE '%claims%'
      )
      AND
      (
           domain_id = 'Type Concept'
        OR vocabulary_id = 'Visit Type'
        OR concept_class_id ILIKE '%type%'
      )

    ORDER BY
        concept_name,
        concept_id;
    "

echo "VISIT_TYPE_CONCEPT_CANDIDATES_END"


echo
echo "KNOWN_VISIT_TYPE_RANGE_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        concept_id,
        concept_name,
        domain_id,
        vocabulary_id,
        concept_class_id,
        standard_concept,
        invalid_reason

    FROM cdm.concept

    WHERE concept_id BETWEEN 32800 AND 32999
      AND invalid_reason IS NULL

    ORDER BY concept_id;
    "

echo "KNOWN_VISIT_TYPE_RANGE_END"

echo "PASS"
echo


# ============================================================
# 6. Exact commonly-used Visit concepts, if present
# ============================================================

echo "[6/6] Inspect exact common Visit concepts..."


echo "COMMON_VISIT_CONCEPTS_BEGIN"

psql_omop \
    -P pager=off \
    -c "
    SELECT
        concept_id,
        concept_name,
        domain_id,
        vocabulary_id,
        concept_class_id,
        standard_concept,
        invalid_reason

    FROM cdm.concept

    WHERE concept_id IN
    (
        9201,
        9202,
        9203,
        262,
        581476,
        581477,
        581478,
        581479
    )

    ORDER BY concept_id;
    "

echo "COMMON_VISIT_CONCEPTS_END"


echo
echo "============================================================"
echo "TASK-003 STEP 02 RESULT"
echo "============================================================"
echo
echo "STEP02=PASS"
echo "VISIT_ID_MAP_EXISTS=${VISIT_MAP_EXISTS}"
echo "VISIT_OCCURRENCE_ROWS=${VISIT_ROWS}"
echo "MAX_VISIT_OCCURRENCE_ID=${MAX_VISIT_ID}"
echo "DATABASE_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo "============================================================"
