#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-postgre
POD=dw-postgre-database-0
DB=omop
DB_USER=omop_admin

EXPECTED_HEAD=4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-baseline.$(date -u +%Y%m%dT%H%M%SZ).$$"

LOCK=visit-proc-lock-42dac37c79553e40c0affc4039acee27

echo '#### TASK003 STEP06A1 VISIT ID ALLOCATION BASELINE DISCOVERY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "VISIT_ID_BASELINE_REPORT=$REPORT"
  echo "DISCOVERY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06A1 VISIT ID ALLOCATION BASELINE DISCOVERY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify STEP05 final Git checkpoint ==='

HEAD=$(git rev-parse HEAD)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: Git HEAD drifted after STEP05 final checkpoint'
  exit 1
}

echo 'STEP05_FINAL_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify Processed publication Reservation remains absent ==='

if kubectl -n dw-spark \
    get configmap "$LOCK" \
    >/dev/null 2>&1
then
  echo 'ERROR: released Processed publication Reservation unexpectedly exists'
  exit 1
fi

echo 'PROCESSED_RESERVATION_ABSENT=PASS'
echo 'PROCESSED_PREFIX_FROZEN=YES'

echo '=== 3. Verify PostgreSQL target Pod ==='

kubectl -n "$NS" \
  get pod "$POD" \
  -o json \
  > "$REPORT/postgres-pod.json"

python3 - \
  "$REPORT/postgres-pod.json" \
  <<'PY_POD'
import json
import sys
from pathlib import Path

pod = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert pod['status']['phase'] == 'Running'

ready = {
    item['type']: item['status']
    for item in pod['status'].get(
        'conditions',
        []
    )
}

assert ready.get('Ready') == 'True'

print('POSTGRES_TARGET_POD=PASS')
PY_POD

echo '=== 4. Run transaction-level READ ONLY database discovery ==='

kubectl -n "$NS" \
  exec -i "$POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -P pager=off \
  > "$REPORT/database-baseline.txt" <<'SQL'
\echo '--- DATABASE IDENTITY BEGIN ---'

BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    current_database() AS database_name,
    current_user AS database_user,
    current_setting('transaction_read_only') AS transaction_read_only;

\echo '--- REQUIRED OBJECTS BEGIN ---'

SELECT
    to_regclass('etl.visit_occurrence_id_map')::text
        AS visit_occurrence_id_map,
    to_regclass('etl.person_id_map')::text
        AS person_id_map,
    to_regclass('cdm.visit_occurrence')::text
        AS cdm_visit_occurrence;

\echo '--- VISIT MAP COLUMNS BEGIN ---'

SELECT
    ordinal_position,
    column_name,
    data_type,
    udt_name,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'etl'
  AND table_name = 'visit_occurrence_id_map'
ORDER BY ordinal_position;

\echo '--- VISIT MAP CONSTRAINTS BEGIN ---'

SELECT
    c.conname AS constraint_name,
    c.contype AS constraint_type,
    pg_get_constraintdef(
        c.oid,
        true
    ) AS definition
FROM pg_constraint c
JOIN pg_class t
  ON t.oid = c.conrelid
JOIN pg_namespace n
  ON n.oid = t.relnamespace
WHERE n.nspname = 'etl'
  AND t.relname = 'visit_occurrence_id_map'
ORDER BY
    c.contype,
    c.conname;

\echo '--- VISIT MAP INDEXES BEGIN ---'

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'etl'
  AND tablename = 'visit_occurrence_id_map'
ORDER BY indexname;

\echo '--- VISIT-RELATED ETL SEQUENCES BEGIN ---'

SELECT
    schemaname,
    sequencename,
    data_type,
    start_value,
    min_value,
    max_value,
    increment_by,
    cycle,
    cache_size,
    last_value
FROM pg_sequences
WHERE schemaname = 'etl'
  AND sequencename ILIKE '%visit%'
ORDER BY sequencename;

\echo '--- VISIT MAP BASELINE BEGIN ---'

SELECT
    count(*) AS map_rows,
    count(
        DISTINCT (
            source_system,
            source_encounter_id
        )
    ) AS unique_business_keys,
    count(
        DISTINCT visit_occurrence_id
    ) AS unique_visit_occurrence_ids,
    min(
        visit_occurrence_id
    ) AS min_visit_occurrence_id,
    max(
        visit_occurrence_id
    ) AS max_visit_occurrence_id
FROM etl.visit_occurrence_id_map;

\echo '--- VISIT MAP NULL / DUPLICATE SAFETY BEGIN ---'

SELECT
    count(*) FILTER (
        WHERE source_system IS NULL
    ) AS null_source_system,

    count(*) FILTER (
        WHERE source_encounter_id IS NULL
    ) AS null_source_encounter_id,

    count(*) FILTER (
        WHERE visit_occurrence_id IS NULL
    ) AS null_visit_occurrence_id
FROM etl.visit_occurrence_id_map;

SELECT
    count(*) AS duplicate_business_key_groups
FROM (
    SELECT
        source_system,
        source_encounter_id
    FROM etl.visit_occurrence_id_map
    GROUP BY
        source_system,
        source_encounter_id
    HAVING count(*) > 1
) d;

SELECT
    count(*) AS duplicate_visit_id_groups
FROM (
    SELECT
        visit_occurrence_id
    FROM etl.visit_occurrence_id_map
    GROUP BY
        visit_occurrence_id
    HAVING count(*) > 1
) d;

\echo '--- VISIT MAP SAMPLE BEGIN ---'

SELECT *
FROM etl.visit_occurrence_id_map
ORDER BY
    visit_occurrence_id,
    source_system,
    source_encounter_id
LIMIT 20;

\echo '--- PERSON MAP BASELINE BEGIN ---'

SELECT
    count(*) AS person_map_rows,
    count(
        DISTINCT (
            source_system,
            source_person_id
        )
    ) AS unique_source_person_keys,
    count(
        DISTINCT person_id
    ) AS unique_person_ids,
    min(
        person_id
    ) AS min_person_id,
    max(
        person_id
    ) AS max_person_id
FROM etl.person_id_map;

\echo '--- CDM VISIT_OCCURRENCE COLUMNS BEGIN ---'

SELECT
    ordinal_position,
    column_name,
    data_type,
    udt_name,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'cdm'
  AND table_name = 'visit_occurrence'
ORDER BY ordinal_position;

\echo '--- CDM VISIT_OCCURRENCE BASELINE BEGIN ---'

SELECT
    count(*) AS cdm_visit_rows,
    count(
        DISTINCT visit_occurrence_id
    ) AS unique_visit_ids,
    min(
        visit_occurrence_id
    ) AS min_visit_occurrence_id,
    max(
        visit_occurrence_id
    ) AS max_visit_occurrence_id,
    count(
        DISTINCT person_id
    ) AS referenced_persons
FROM cdm.visit_occurrence;

\echo '--- MAP/CDM ID OVERLAP BEGIN ---'

SELECT
    count(*) AS mapped_ids_already_in_cdm
FROM etl.visit_occurrence_id_map m
JOIN cdm.visit_occurrence v
  ON v.visit_occurrence_id =
     m.visit_occurrence_id;

\echo '--- DATABASE WRITE GUARD BEGIN ---'

SELECT
    current_setting(
        'transaction_read_only'
    ) AS transaction_read_only;

ROLLBACK;

\echo '--- DATABASE DISCOVERY COMPLETE ---'
SQL

cat "$REPORT/database-baseline.txt"

echo '=== 5. Parse mandatory baseline facts ==='

python3 - \
  "$REPORT/database-baseline.txt" \
  <<'PY_PARSE'
import re
import sys
from pathlib import Path

text = Path(
    sys.argv[1]
).read_text(
    errors='replace'
)

required = (
    'etl.visit_occurrence_id_map',
    'etl.person_id_map',
    'cdm.visit_occurrence',
    'transaction_read_only',
    '--- DATABASE DISCOVERY COMPLETE ---',
)

for token in required:
    assert token in text, token

assert re.search(
    r'transaction_read_only\s*\n[-+ ]+\n\s*on',
    text,
    re.IGNORECASE,
), 'READ ONLY transaction not proven'

print('DATABASE_DISCOVERY_OUTPUT=PASS')
print('TRANSACTION_READ_ONLY=PASS')
PY_PARSE

echo '=== 6. Record read-only discovery state ==='

python3 - \
  "$REPORT/database-baseline.txt" \
  "$REPORT/run-state.json" \
  "$HEAD" \
  <<'PY_STATE'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

baseline = Path(sys.argv[1])
target = Path(sys.argv[2])
head = sys.argv[3]

blob = baseline.read_bytes()

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-06A1',

    'status':
        'VISIT_ID_ALLOCATION_BASELINE_DISCOVERED',

    'git_checkpoint':
        head,

    'database':
        'omop',

    'database_user':
        'omop_admin',

    'database_discovery_sha256':
        hashlib.sha256(
            blob
        ).hexdigest(),

    'processed_publication_complete':
        True,

    'processed_prefix_frozen':
        True,

    'processed_reservation_present':
        False,

    'transaction_read_only':
        True,

    'visit_id_allocation_started':
        False,

    'visit_id_map_mutated':
        False,

    'sequence_advanced':
        False,

    'cdm_visit_occurrence_write':
        False,

    's3_mutation':
        False,

    'observed_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('VISIT_ID_BASELINE_STATE=PASS')
print(
    'DATABASE_DISCOVERY_SHA256='
    + state['database_discovery_sha256']
)
PY_STATE

echo '=== 7. Final STEP06A1 safety verdict ==='

echo 'STEP06A1_VISIT_ID_ALLOCATION_BASELINE_DISCOVERY=PASS'

echo 'PROCESSED_PUBLICATION_COMPLETE=YES'
echo 'PROCESSED_PREFIX_FROZEN=YES'
echo 'RESERVATION_PRESENT=NO'

echo 'DATABASE_DISCOVERY=READ_ONLY'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'
