#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

DB_NS=dw-postgre
DB_POD=dw-postgre-database-0
DB_NAME=omop
DB_USER=omop_admin

CONTRACT="$ROOT/spark/contracts/processed/visit-cdm-materialization-result-v1.json"
APP="$ROOT/apps/task003/verify_committed_cdm_visit_materialization.py"

RUN_ID="$(
  date -u '+%Y%m%dT%H%M%SZ'
).$$"

REPORT="$ROOT/runtime/reports/task003/step06/cdm-visit-post-commit-canonical-verification.$RUN_ID"

STATE="$REPORT/database-state.txt"
RESULT="$REPORT/run-state.json"

echo '#### TASK003 STEP06C4E COMMITTED CDM VISIT VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06C4E_VERIFY_REPORT=$REPORT"
  echo "STEP06C4E_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06C4E COMMITTED CDM VISIT VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

cd "$ROOT"

[[ -s "$CONTRACT" && ! -L "$CONTRACT" ]] || {
  echo 'ERROR: canonical result contract missing'
  exit 1
}

[[ -s "$APP" && ! -L "$APP" ]] || {
  echo 'ERROR: canonical verifier missing'
  exit 1
}

mkdir -p "$REPORT"

kubectl -n "$DB_NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -A \
    -t \
    -P pager=off \
  > "$STATE" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    'TARGET_COLUMN_COUNT='
    || count(*)
FROM information_schema.columns
WHERE table_schema = 'cdm'
  AND table_name = 'visit_occurrence';


SELECT
    'TARGET_CONSTRAINT_COUNT='
    || count(*)
FROM pg_constraint
WHERE conrelid = 'cdm.visit_occurrence'::regclass;


SELECT
    'TARGET_INDEX_COUNT='
    || count(*)
FROM pg_indexes
WHERE schemaname = 'cdm'
  AND tablename = 'visit_occurrence';


SELECT
    'TARGET_USER_TRIGGER_COUNT='
    || count(*)
FROM pg_trigger
WHERE tgrelid = 'cdm.visit_occurrence'::regclass
  AND NOT tgisinternal;


SELECT
    'CDM_STATE='
    || count(*)
    || '|'
    || count(DISTINCT visit_occurrence_id)
    || '|'
    || min(visit_occurrence_id)
    || '|'
    || max(visit_occurrence_id)
FROM cdm.visit_occurrence;


SELECT
    'MAP_STATE='
    || count(*)
    || '|'
    || count(DISTINCT visit_occurrence_id)
    || '|'
    || min(visit_occurrence_id)
    || '|'
    || max(visit_occurrence_id)
FROM etl.visit_occurrence_id_map;


SELECT
    'PERSON_MAP_ROWS='
    || count(*)
FROM etl.person_id_map;


SELECT
    'SEQUENCE_STATE='
    || last_value
    || '|'
    || CASE
           WHEN is_called THEN 'true'
           ELSE 'false'
       END
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;


SELECT
    'MAPPING_SHA256='
    || encode(
        sha256(
            convert_to(
                string_agg(
                    source_system
                    || E'\t'
                    || source_encounter_id
                    || E'\t'
                    || visit_occurrence_id::text
                    || E'\n',
                    ''
                    ORDER BY
                        source_system,
                        source_encounter_id
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM etl.visit_occurrence_id_map;


SELECT
    'PERSON_MAP_SHA256='
    || encode(
        sha256(
            convert_to(
                string_agg(
                    source_system
                    || E'\t'
                    || source_person_id
                    || E'\t'
                    || person_id::text
                    || E'\n',
                    ''
                    ORDER BY
                        source_system,
                        source_person_id
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM etl.person_id_map;


WITH serialized AS (
    SELECT
        visit_occurrence_id,

        visit_occurrence_id::text
        || E'\t'
        || person_id::text
        || E'\t'
        || visit_concept_id::text
        || E'\t'
        || to_char(
            visit_start_date,
            'YYYY-MM-DD'
        )
        || E'\t'
        || COALESCE(
            to_char(
                visit_start_datetime,
                'YYYY-MM-DD HH24:MI:SS.US'
            ),
            chr(92) || 'N'
        )
        || E'\t'
        || to_char(
            visit_end_date,
            'YYYY-MM-DD'
        )
        || E'\t'
        || COALESCE(
            to_char(
                visit_end_datetime,
                'YYYY-MM-DD HH24:MI:SS.US'
            ),
            chr(92) || 'N'
        )
        || E'\t'
        || visit_type_concept_id::text
        || E'\t'
        || COALESCE(provider_id::text, chr(92) || 'N')
        || E'\t'
        || COALESCE(care_site_id::text, chr(92) || 'N')
        || E'\t'
        || COALESCE(
            replace(
                replace(
                    replace(
                        replace(
                            visit_source_value,
                            chr(92),
                            chr(92) || chr(92)
                        ),
                        E'\t',
                        chr(92) || 't'
                    ),
                    E'\r',
                    chr(92) || 'r'
                ),
                E'\n',
                chr(92) || 'n'
            ),
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            visit_source_concept_id::text,
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            admitted_from_concept_id::text,
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            replace(
                replace(
                    replace(
                        replace(
                            admitted_from_source_value,
                            chr(92),
                            chr(92) || chr(92)
                        ),
                        E'\t',
                        chr(92) || 't'
                    ),
                    E'\r',
                    chr(92) || 'r'
                ),
                E'\n',
                chr(92) || 'n'
            ),
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            discharged_to_concept_id::text,
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            replace(
                replace(
                    replace(
                        replace(
                            discharged_to_source_value,
                            chr(92),
                            chr(92) || chr(92)
                        ),
                        E'\t',
                        chr(92) || 't'
                    ),
                    E'\r',
                    chr(92) || 'r'
                ),
                E'\n',
                chr(92) || 'n'
            ),
            chr(92) || 'N'
        )
        || E'\t'
        || COALESCE(
            preceding_visit_occurrence_id::text,
            chr(92) || 'N'
        )
        || E'\n'
        AS line

    FROM cdm.visit_occurrence
)

SELECT
    'CDM_ROW_SHAPE_SHA256='
    || encode(
        sha256(
            convert_to(
                string_agg(
                    line,
                    ''
                    ORDER BY visit_occurrence_id
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM serialized;


SELECT
    'TARGET_MAP_ID_MISMATCH='
    || count(*)
FROM (
    SELECT
        v.visit_occurrence_id AS target_id,
        m.visit_occurrence_id AS map_id

    FROM cdm.visit_occurrence v

    FULL JOIN etl.visit_occurrence_id_map m
      ON m.visit_occurrence_id = v.visit_occurrence_id

    WHERE v.visit_occurrence_id IS NULL
       OR m.visit_occurrence_id IS NULL
) mismatch;


SELECT
    'REQUIRED_NULL_ROWS='
    || count(*)
FROM cdm.visit_occurrence
WHERE visit_occurrence_id IS NULL
   OR person_id IS NULL
   OR visit_concept_id IS NULL
   OR visit_start_date IS NULL
   OR visit_end_date IS NULL
   OR visit_type_concept_id IS NULL;


SELECT
    'MISSING_PERSON_FK='
    || count(*)
FROM (
    SELECT DISTINCT v.person_id
    FROM cdm.visit_occurrence v

    LEFT JOIN cdm.person p
      ON p.person_id = v.person_id

    WHERE p.person_id IS NULL
) q;


SELECT
    'MISSING_CONCEPT_FK='
    || count(*)
FROM (
    SELECT DISTINCT concept_id
    FROM (
        SELECT visit_concept_id AS concept_id
        FROM cdm.visit_occurrence

        UNION ALL

        SELECT visit_type_concept_id
        FROM cdm.visit_occurrence

        UNION ALL

        SELECT visit_source_concept_id
        FROM cdm.visit_occurrence

        UNION ALL

        SELECT admitted_from_concept_id
        FROM cdm.visit_occurrence

        UNION ALL

        SELECT discharged_to_concept_id
        FROM cdm.visit_occurrence
    ) x
    WHERE concept_id IS NOT NULL
) ids

LEFT JOIN cdm.concept c
  ON c.concept_id = ids.concept_id

WHERE c.concept_id IS NULL;


SELECT
    'MISSING_PROVIDER_FK='
    || count(*)
FROM (
    SELECT DISTINCT provider_id
    FROM cdm.visit_occurrence
    WHERE provider_id IS NOT NULL
) ids

LEFT JOIN cdm.provider p
  ON p.provider_id = ids.provider_id

WHERE p.provider_id IS NULL;


SELECT
    'MISSING_CARE_SITE_FK='
    || count(*)
FROM (
    SELECT DISTINCT care_site_id
    FROM cdm.visit_occurrence
    WHERE care_site_id IS NOT NULL
) ids

LEFT JOIN cdm.care_site c
  ON c.care_site_id = ids.care_site_id

WHERE c.care_site_id IS NULL;


SELECT
    'MISSING_PRECEDING_VISIT_FK='
    || count(*)
FROM (
    SELECT DISTINCT preceding_visit_occurrence_id
    FROM cdm.visit_occurrence
    WHERE preceding_visit_occurrence_id IS NOT NULL
) ids

LEFT JOIN cdm.visit_occurrence v
  ON v.visit_occurrence_id = ids.preceding_visit_occurrence_id

WHERE v.visit_occurrence_id IS NULL;


SELECT
    'TRANSACTION_READ_ONLY='
    || current_setting('transaction_read_only');

ROLLBACK;
SQL

python3 "$APP" \
  --contract "$CONTRACT" \
  --state "$STATE" \
  --output-json "$RESULT"

chmod 0444 \
  "$STATE" \
  "$RESULT"

echo 'STEP06C4E_COMMITTED_CDM_VISIT_CANONICAL_GATE=PASS'
echo 'DATABASE_ACCESS=READ_ONLY'
echo 'DATABASE_MUTATION=NO'
echo 'S3_ACCESS=NONE'
echo 'S3_MUTATION=NO'
echo 'READY_FOR_GIT_CHECKPOINT=YES'
