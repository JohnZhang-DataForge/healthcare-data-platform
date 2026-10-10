#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06a5-stage.XXXXXX)"

echo '#### TASK003 STEP06A5 PREPARE READONLY RUNNER SNAPSHOTS OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06A5_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06A5 PREPARE READONLY RUNNER SNAPSHOTS OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/scripts/task003"

cat > "$STAGE/scripts/task003/06a1-visit-id-allocation-baseline-discovery.sh" <<'A1_EOF_TASK003_06A5'
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
A1_EOF_TASK003_06A5

cat > "$STAGE/scripts/task003/06a2-plan-visit-id-allocation.sh" <<'A2_EOF_TASK003_06A5'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute this script with bash; do not source it'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-postgre
POD=dw-postgre-database-0
DB=omop
DB_USER=omop_admin

EXPECTED_HEAD=4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4

BASELINE_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-baseline.20261009T234622Z.2178592"
BASELINE_STATE="$BASELINE_REPORT/run-state.json"

PROCESSED_READBACK="$ROOT/runtime/reports/task003/step05/persisted-readback.vDQg1J9w/run-state.json"

RUN_ID=visit-proc-20261009t192437z-2081886

SEQ=etl.visit_occurrence_id_map_visit_occurrence_id_seq

EXPECTED_CANDIDATE_ROWS=5799
EXPECTED_UNIQUE_KEYS=5799
EXPECTED_PERSONS=113

PLAN_DIR="$ROOT/runtime/reports/task003/step06/visit-id-allocation-plans/$RUN_ID"
PLAN_FILE="$PLAN_DIR/plan.json"

echo '#### TASK003 STEP06A2 VISIT ID ALLOCATION PLAN OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "VISIT_ID_ALLOCATION_PLAN=$PLAN_FILE"
  echo "PLAN_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06A2 VISIT ID ALLOCATION PLAN OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$PLAN_DIR"

cd "$ROOT"

echo '=== 1. Verify STEP05 final Git checkpoint ==='

HEAD=$(git rev-parse HEAD)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: Git HEAD drifted'
  exit 1
}

echo 'STEP05_FINAL_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify STEP06A1 baseline evidence ==='

[[ -s "$BASELINE_STATE" && ! -L "$BASELINE_STATE" ]] || {
  echo 'ERROR: STEP06A1 state missing'
  exit 1
}

python3 - \
  "$BASELINE_STATE" \
  "$EXPECTED_HEAD" \
  <<'PY_BASELINE'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert state['task'] == 'TASK-003'
assert state['step'] == 'STEP-06A1'

assert (
    state['status']
    == 'VISIT_ID_ALLOCATION_BASELINE_DISCOVERED'
)

assert state['git_checkpoint'] == sys.argv[2]

assert state['processed_publication_complete'] is True
assert state['processed_prefix_frozen'] is True
assert state['processed_reservation_present'] is False

assert state['transaction_read_only'] is True

assert state['visit_id_allocation_started'] is False
assert state['visit_id_map_mutated'] is False
assert state['sequence_advanced'] is False
assert state['cdm_visit_occurrence_write'] is False
assert state['s3_mutation'] is False

print('STEP06A1_BASELINE_EVIDENCE=PASS')
PY_BASELINE

echo '=== 3. Verify frozen Candidate evidence ==='

[[ -s "$PROCESSED_READBACK" && ! -L "$PROCESSED_READBACK" ]] || {
  echo 'ERROR: persisted Candidate readback missing'
  exit 1
}

python3 - \
  "$PROCESSED_READBACK" \
  <<'PY_CAND'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert state['status'] == \
    'INDEPENDENT_S3_READBACK_PASS'

assert state['run_id'] == \
    'visit-proc-20261009t192437z-2081886'

assert state['rows'] == 5799
assert state['unique_business_keys'] == 5799
assert state['referenced_persons'] == 113
assert state['contract_field_count'] == 36

assert state['candidate_published_verified'] is True
assert state['s3_write_verified'] is True

assert state['postgresql_write'] is False

print('FROZEN_CANDIDATE_EVIDENCE=PASS')
print('CANDIDATE_ROWS=5799')
print('CANDIDATE_UNIQUE_BUSINESS_KEYS=5799')
print('CANDIDATE_REFERENCED_PERSONS=113')
PY_CAND

echo '=== 4. Fresh READ ONLY allocation-state discovery ==='

SQL_OUT="$PLAN_DIR/database-allocation-state.txt"

kubectl -n "$NS" \
  exec -i "$POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -P pager=off \
    -A \
    -t \
    -F '|' \
  > "$SQL_OUT" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

\echo 'IDENTITY'
SELECT
    current_database(),
    current_user,
    current_setting('transaction_read_only');

\echo 'COUNTS'
SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

\echo 'SEQUENCE_DIRECT_STATE'
SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

\echo 'SEQUENCE_CATALOG'
SELECT
    start_value,
    min_value,
    max_value,
    increment_by,
    cycle,
    cache_size,
    COALESCE(last_value::text, 'NULL')
FROM pg_sequences
WHERE schemaname = 'etl'
  AND sequencename =
      'visit_occurrence_id_map_visit_occurrence_id_seq';

\echo 'SERIAL_SEQUENCE_BINDING'
SELECT
    COALESCE(
        pg_get_serial_sequence(
            'etl.visit_occurrence_id_map',
            'visit_occurrence_id'
        ),
        'NONE'
    );

\echo 'COLUMN_DEFAULT'
SELECT
    COALESCE(column_default, 'NONE')
FROM information_schema.columns
WHERE table_schema = 'etl'
  AND table_name = 'visit_occurrence_id_map'
  AND column_name = 'visit_occurrence_id';

\echo 'SEQUENCE_PRIVILEGES'
SELECT
    has_sequence_privilege(
        current_user,
        'etl.visit_occurrence_id_map_visit_occurrence_id_seq',
        'USAGE'
    ),
    has_sequence_privilege(
        current_user,
        'etl.visit_occurrence_id_map_visit_occurrence_id_seq',
        'SELECT'
    ),
    has_sequence_privilege(
        current_user,
        'etl.visit_occurrence_id_map_visit_occurrence_id_seq',
        'UPDATE'
    );

\echo 'MAP_COLLISIONS'
SELECT
    (
        SELECT count(*)
        FROM (
            SELECT
                source_system,
                source_encounter_id
            FROM etl.visit_occurrence_id_map
            GROUP BY
                source_system,
                source_encounter_id
            HAVING count(*) > 1
        ) x
    ),
    (
        SELECT count(*)
        FROM (
            SELECT visit_occurrence_id
            FROM etl.visit_occurrence_id_map
            GROUP BY visit_occurrence_id
            HAVING count(*) > 1
        ) y
    );

\echo 'CDM_MAP_OVERLAP'
SELECT count(*)
FROM etl.visit_occurrence_id_map m
JOIN cdm.visit_occurrence v
  ON v.visit_occurrence_id =
     m.visit_occurrence_id;

\echo 'READ_ONLY_FINAL'
SELECT current_setting('transaction_read_only');

ROLLBACK;

\echo 'DISCOVERY_COMPLETE'
SQL

cat "$SQL_OUT"

echo '=== 5. Build deterministic allocation plan ==='

python3 - \
  "$SQL_OUT" \
  "$PLAN_FILE" \
  "$BASELINE_STATE" \
  "$PROCESSED_READBACK" \
  "$EXPECTED_HEAD" \
  <<'PY_PLAN'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sql_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
baseline_state = Path(sys.argv[3])
readback_state = Path(sys.argv[4])
git_checkpoint = sys.argv[5]

lines = [
    line.strip()
    for line in sql_path.read_text(
        errors='replace'
    ).splitlines()
]

def value_after(marker):
    idx = lines.index(marker)

    for line in lines[idx + 1:]:
        if not line:
            continue
        if line.startswith('('):
            continue
        if line in {
            'IDENTITY',
            'COUNTS',
            'SEQUENCE_DIRECT_STATE',
            'SEQUENCE_CATALOG',
            'SERIAL_SEQUENCE_BINDING',
            'COLUMN_DEFAULT',
            'SEQUENCE_PRIVILEGES',
            'MAP_COLLISIONS',
            'CDM_MAP_OVERLAP',
            'READ_ONLY_FINAL',
            'DISCOVERY_COMPLETE',
            'BEGIN',
            'SET',
            'ROLLBACK',
        }:
            continue
        return line

    raise RuntimeError(
        'missing value after ' + marker
    )

identity = value_after('IDENTITY').split('|')
counts = value_after('COUNTS').split('|')
seq_state = value_after(
    'SEQUENCE_DIRECT_STATE'
).split('|')

seq_catalog = value_after(
    'SEQUENCE_CATALOG'
).split('|')

serial_binding = value_after(
    'SERIAL_SEQUENCE_BINDING'
)

column_default = value_after(
    'COLUMN_DEFAULT'
)

privileges = value_after(
    'SEQUENCE_PRIVILEGES'
).split('|')

collisions = value_after(
    'MAP_COLLISIONS'
).split('|')

overlap = int(
    value_after(
        'CDM_MAP_OVERLAP'
    )
)

read_only = value_after(
    'READ_ONLY_FINAL'
)

assert identity == [
    'omop',
    'omop_admin',
    'on',
]

map_rows = int(counts[0])
cdm_rows = int(counts[1])
person_rows = int(counts[2])

assert map_rows == 0
assert cdm_rows == 0
assert person_rows == 113

sequence_last_value = int(
    seq_state[0]
)

sequence_is_called = (
    seq_state[1].lower() == 't'
)

assert sequence_last_value == 1
assert sequence_is_called is False

start_value = int(seq_catalog[0])
min_value = int(seq_catalog[1])
max_value = int(seq_catalog[2])
increment_by = int(seq_catalog[3])
cycle = seq_catalog[4].lower() == 't'
cache_size = int(seq_catalog[5])
catalog_last_value = seq_catalog[6]

assert start_value == 1
assert min_value == 1
assert increment_by == 1
assert cycle is False
assert cache_size == 1
assert catalog_last_value == 'NULL'

assert serial_binding == 'etl.visit_occurrence_id_map_visit_occurrence_id_seq'
assert column_default == 'NONE'

assert privileges == [
    't',
    't',
    't',
]

assert collisions == [
    '0',
    '0',
]

assert overlap == 0
assert read_only == 'on'

candidate_rows = 5799
candidate_unique_keys = 5799

existing_mappings = map_rows
new_mappings = (
    candidate_unique_keys
    - existing_mappings
)

assert new_mappings == 5799

# This is only a prediction based on the current snapshot.
# No sequence value is consumed here.
if sequence_is_called:
    proposed_first_id = (
        sequence_last_value
        + increment_by
    )
else:
    proposed_first_id = (
        sequence_last_value
    )

proposed_last_id = (
    proposed_first_id
    + (
        new_mappings
        - 1
    )
    * increment_by
)

assert proposed_last_id <= max_value

def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()

plan = {
    'task':
        'TASK-003',

    'step':
        'STEP-06A2',

    'status':
        'VISIT_ID_ALLOCATION_PLAN_READY',

    'run_id':
        'visit-proc-20261009t192437z-2081886',

    'git_checkpoint':
        git_checkpoint,

    'source_candidate': {
        'rows':
            candidate_rows,

        'unique_business_keys':
            candidate_unique_keys,

        'referenced_persons':
            113,

        'business_key': [
            'source_system',
            'source_encounter_id',
        ],

        'frozen':
            True,
    },

    'database_snapshot': {
        'visit_map_rows':
            map_rows,

        'cdm_visit_rows':
            cdm_rows,

        'person_map_rows':
            person_rows,

        'duplicate_business_key_groups':
            0,

        'duplicate_visit_id_groups':
            0,

        'mapped_ids_already_in_cdm':
            overlap,
    },

    'sequence': {
        'name':
            'etl.visit_occurrence_id_map_visit_occurrence_id_seq',

        'start_value':
            start_value,

        'min_value':
            min_value,

        'max_value':
            max_value,

        'increment_by':
            increment_by,

        'cycle':
            cycle,

        'cache_size':
            cache_size,

        'last_value_direct':
            sequence_last_value,

        'is_called':
            sequence_is_called,

        'pg_sequences_last_value':
            None,

        'column_default':
            None,

        'pg_get_serial_sequence_binding':
            serial_binding,

        'sequence_column_binding_present':
            True,

        'automatic_default_nextval':
            False,

        'explicit_allocation_required':
            True,
    },

    'allocation_preview': {
        'existing_candidate_mappings':
            existing_mappings,

        'new_candidate_mappings':
            new_mappings,

        'predicted_first_new_id':
            proposed_first_id,

        'predicted_last_new_id':
            proposed_last_id,

        'prediction_is_non_authoritative':
            True,
    },

    'mutation_time_requirements': [
        'revalidate map count and collisions',
        'revalidate cdm.visit_occurrence baseline',
        'revalidate sequence last_value and is_called',
        'reconcile frozen candidate business keys against map',
        'acquire database allocation serialization guard',
        'allocate IDs in controlled transaction',
        'same business key must retain same visit_occurrence_id',
    ],

    'safety': {
        'transaction_read_only':
            True,

        'nextval_called':
            False,

        'sequence_advanced':
            False,

        'visit_id_map_mutated':
            False,

        'cdm_visit_occurrence_write':
            False,

        's3_mutation':
            False,
    },

    'evidence': {
        'step06a1_state_sha256':
            sha(baseline_state),

        'processed_readback_state_sha256':
            sha(readback_state),

        'database_allocation_state_sha256':
            sha(sql_path),
    },

    'planned_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

plan_path.write_text(
    json.dumps(
        plan,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('VISIT_ID_ALLOCATION_PLAN_BUILD=PASS')
print('CURRENT_VISIT_MAP_ROWS=0')
print('CURRENT_CDM_VISIT_ROWS=0')
print('CURRENT_PERSON_MAP_ROWS=113')

print(
    'SEQUENCE_NAME='
    + plan['sequence']['name']
)

print(
    'SEQUENCE_DIRECT_LAST_VALUE='
    + str(sequence_last_value)
)

print(
    'SEQUENCE_IS_CALLED='
    + str(sequence_is_called).upper()
)

print(
    'PG_GET_SERIAL_SEQUENCE_BINDING='
    + serial_binding
)

print(
    'SEQUENCE_COLUMN_BINDING_PRESENT=YES'
)

print(
    'VISIT_ID_COLUMN_DEFAULT=NONE'
)

print(
    'AUTOMATIC_DEFAULT_NEXTVAL=NO'
)

print(
    'EXPLICIT_SEQUENCE_ALLOCATION_REQUIRED=YES'
)

print(
    'EXISTING_CANDIDATE_MAPPINGS='
    + str(existing_mappings)
)

print(
    'NEW_CANDIDATE_MAPPINGS='
    + str(new_mappings)
)

print(
    'PREDICTED_FIRST_NEW_VISIT_ID='
    + str(proposed_first_id)
)

print(
    'PREDICTED_LAST_NEW_VISIT_ID='
    + str(proposed_last_id)
)

print(
    'PREDICTED_RANGE_AUTHORITATIVE=NO'
)

print(
    'ALLOCATION_PLAN_SHA256='
    + sha(plan_path)
)
PY_PLAN

echo '=== 6. Static proof that no sequence allocation occurred ==='

if grep -Eqi \
  'nextval[[:space:]]*\(' \
  "$SQL_OUT"
then
  echo 'ERROR: unexpected nextval() in SQL evidence'
  exit 1
fi

echo 'NEXTVAL_CALLED=NO'
echo 'SEQUENCE_ADVANCED=NO'

echo '=== 7. Final STEP06A2 verdict ==='

echo 'STEP06A2_VISIT_ID_ALLOCATION_PLAN=PASS'

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'

echo 'EXISTING_VISIT_MAPPINGS=0'
echo 'NEW_VISIT_MAPPINGS_PLANNED=5799'

echo 'PREDICTED_VISIT_ID_RANGE=1..5799'
echo 'PREDICTED_RANGE_AUTHORITATIVE=NO'

echo 'MUTATION_TIME_REVALIDATION_REQUIRED=YES'

echo 'DATABASE_DISCOVERY=READ_ONLY'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'
A2_EOF_TASK003_06A5

cat > "$STAGE/scripts/task003/06a3-reconcile-visit-business-keys.sh" <<'A3_EOF_TASK003_06A5'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute this script with bash; do not source it'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-spark
DB_NS=dw-postgre
DB_POD=dw-postgre-database-0
DB=omop
DB_USER=omop_admin

EXPECTED_HEAD=4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4

RUN_ID=visit-proc-20261009t192437z-2081886

PLAN="$ROOT/runtime/reports/task003/step06/visit-id-allocation-plans/$RUN_ID/plan.json"
EXPECTED_PLAN_SHA=28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93

PROCESSED_DATA_URI='s3a://health-processed/contract_version=v1/entity=visit_occurrence/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/raw_publish_run_id=encounter-raw-20261009T005128Z-1681690/run_id=visit-proc-20261009t192437z-2081886/data/'

EXPECTED_ROWS=5799
EXPECTED_KEYS=5799
EXPECTED_PERSONS=113

DB_SECRET=dw-spark-omop-secret

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
SUFFIX="${STAMP}-$$"

APP="visit-id-recon-${SUFFIX}"
CM="${APP}-app"

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-reconciliation.${SUFFIX}"

DRIVER="$REPORT/reconcile_visit_id_keys.py"
SOURCE_APP_JSON="$REPORT/source-sparkapplication.json"
APP_JSON="$REPORT/sparkapplication.json"
APP_FINAL_JSON="$REPORT/sparkapplication-final.json"
DRIVER_LOG="$REPORT/driver.log"
RESULT_JSON="$REPORT/reconciliation-result.json"
DB_POSTCHECK="$REPORT/post-reconciliation-db-state.txt"
SECRET_MAP="$REPORT/db-secret-map.json"
RUN_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06A3 VISIT BUSINESS KEY RECONCILIATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06A3_REPORT=$REPORT"
  echo "STEP06A3_SPARKAPPLICATION=$APP"
  echo "STEP06A3_CONFIGMAP=$CM"
  echo "STEP06A3_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06A3 VISIT BUSINESS KEY RECONCILIATION OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify STEP05 final Git checkpoint ==='

HEAD="$(git rev-parse HEAD)"

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: Git HEAD drifted'
  exit 1
}

echo 'STEP05_FINAL_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify authoritative STEP06A2 plan ==='

[[ -s "$PLAN" && ! -L "$PLAN" ]] || {
  echo 'ERROR: STEP06A2 plan missing or unsafe'
  exit 1
}

PLAN_SHA="$(
  sha256sum "$PLAN" |
  awk '{print $1}'
)"

echo "ALLOCATION_PLAN_SHA256=$PLAN_SHA"
echo "EXPECTED_PLAN_SHA256=$EXPECTED_PLAN_SHA"

[[ "$PLAN_SHA" == "$EXPECTED_PLAN_SHA" ]] || {
  echo 'ERROR: STEP06A2 plan SHA mismatch'
  exit 1
}

python3 - \
  "$PLAN" \
  "$EXPECTED_HEAD" \
  <<'PY_PLAN'
import json
import sys
from pathlib import Path

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert plan['task'] == 'TASK-003'
assert plan['step'] == 'STEP-06A2'

assert (
    plan['status']
    == 'VISIT_ID_ALLOCATION_PLAN_READY'
)

assert plan['git_checkpoint'] == sys.argv[2]

candidate = plan['source_candidate']

assert candidate['rows'] == 5799
assert candidate['unique_business_keys'] == 5799
assert candidate['referenced_persons'] == 113
assert candidate['frozen'] is True

db = plan['database_snapshot']

assert db['visit_map_rows'] == 0
assert db['cdm_visit_rows'] == 0
assert db['person_map_rows'] == 113

seq = plan['sequence']

assert seq['last_value_direct'] == 1
assert seq['is_called'] is False

assert (
    seq['pg_get_serial_sequence_binding']
    == 'etl.visit_occurrence_id_map_visit_occurrence_id_seq'
)

assert (
    seq['sequence_column_binding_present']
    is True
)

assert seq['column_default'] is None
assert seq['automatic_default_nextval'] is False
assert seq['explicit_allocation_required'] is True

safety = plan['safety']

assert safety['transaction_read_only'] is True
assert safety['nextval_called'] is False
assert safety['sequence_advanced'] is False
assert safety['visit_id_map_mutated'] is False
assert safety['cdm_visit_occurrence_write'] is False
assert safety['s3_mutation'] is False

print('STEP06A2_PLAN_GATE=PASS')
PY_PLAN

echo '=== 3. Verify current PostgreSQL state before Spark reconciliation ==='

kubectl -n "$DB_NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -A \
    -t \
    -F '|' \
    -P pager=off \
  > "$REPORT/pre-reconciliation-db-state.txt" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*)
       FROM etl.visit_occurrence_id_map),
    (SELECT count(*)
       FROM cdm.visit_occurrence),
    (SELECT count(*)
       FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$REPORT/pre-reconciliation-db-state.txt"

python3 - \
  "$REPORT/pre-reconciliation-db-state.txt" \
  <<'PY_PRE'
import sys
from pathlib import Path

rows = [
    line.strip()
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        'BEGIN',
        'SET',
        'ROLLBACK',
    }
]

assert rows == [
    '0|0|113',
    '1|f',
    'on',
], rows

print('PRE_RECONCILIATION_DB_STATE=PASS')
print('VISIT_MAP_ROWS_BEFORE_A3=0')
print('CDM_VISIT_ROWS_BEFORE_A3=0')
print('SEQUENCE_LAST_VALUE_BEFORE_A3=1')
print('SEQUENCE_IS_CALLED_BEFORE_A3=FALSE')
PY_PRE

echo '=== 4. Resolve PostgreSQL Secret key mapping without exposing values ==='

kubectl -n "$NS" \
  get secret "$DB_SECRET" \
  -o json \
  > "$REPORT/db-secret.json"

python3 - \
  "$REPORT/db-secret.json" \
  "$SECRET_MAP" \
  <<'PY_SECRET'
import json
import re
import sys
from pathlib import Path

secret = json.loads(
    Path(sys.argv[1]).read_bytes()
)

keys = sorted(
    secret.get('data', {}).keys()
)

assert keys, 'database Secret has no keys'

def norm(value):
    return re.sub(
        r'[^a-z0-9]',
        '',
        value.lower(),
    )

by_norm = {
    norm(key): key
    for key in keys
}

def choose(*candidates):
    for candidate in candidates:
        found = by_norm.get(
            norm(candidate)
        )
        if found:
            return found
    return None

mapping = {
    'jdbc_url': choose(
        'jdbc-url',
        'jdbc_url',
        'jdbcurl',
        'omop-jdbc-url',
        'database-jdbc-url',
    ),

    'username': choose(
        'username',
        'user',
        'db-user',
        'db_user',
        'postgres-user',
        'postgres_user',
        'PGUSER',
    ),

    'password': choose(
        'password',
        'pass',
        'db-password',
        'db_password',
        'postgres-password',
        'postgres_password',
        'PGPASSWORD',
    ),

    'host': choose(
        'host',
        'db-host',
        'db_host',
        'postgres-host',
        'postgres_host',
        'PGHOST',
    ),

    'port': choose(
        'port',
        'db-port',
        'db_port',
        'postgres-port',
        'postgres_port',
        'PGPORT',
    ),

    'database': choose(
        'database',
        'dbname',
        'db-name',
        'db_name',
        'postgres-db',
        'postgres_db',
        'PGDATABASE',
    ),
}

assert mapping['username'], (
    'unable to identify DB username Secret key: '
    + repr(keys)
)

assert mapping['password'], (
    'unable to identify DB password Secret key: '
    + repr(keys)
)

assert (
    mapping['jdbc_url']
    or mapping['host']
), (
    'unable to identify JDBC URL or DB host Secret key: '
    + repr(keys)
)

Path(sys.argv[2]).write_text(
    json.dumps(
        mapping,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print(
    'DB_SECRET_AVAILABLE_KEYS='
    + ','.join(keys)
)

for name in (
    'jdbc_url',
    'username',
    'password',
    'host',
    'port',
    'database',
):
    value = mapping[name]

    print(
        'DB_SECRET_MAPPING_'
        + name.upper()
        + '='
        + (
            value
            if value
            else 'NONE'
        )
    )

print('DB_SECRET_KEY_MAPPING=PASS')
print('DB_SECRET_VALUES_EXPOSED=NO')
PY_SECRET

rm -f "$REPORT/db-secret.json"

echo '=== 5. Select a proven TASK003 SparkApplication runtime template ==='

if kubectl -n "$NS" \
    get sparkapplication \
    visit-cand-check-20261009t192437z-2081886 \
    -o json \
    > "$SOURCE_APP_JSON" \
    2>/dev/null
then
  SOURCE_APP=visit-cand-check-20261009t192437z-2081886

else
  kubectl -n "$NS" \
    get sparkapplication \
    -o json \
    > "$REPORT/all-sparkapplications.json"

  SOURCE_APP="$(
    python3 - \
      "$REPORT/all-sparkapplications.json" \
      <<'PY_SELECT'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

items = doc.get(
    'items',
    []
)

prefixes = (
    'visit-cand-check-',
    'visit-proc-write-',
    'visit-raw-check-',
)

for prefix in prefixes:
    matches = sorted(
        (
            item
            for item in items
            if item.get(
                'metadata',
                {},
            ).get(
                'name',
                '',
            ).startswith(prefix)
        ),
        key=lambda item: item.get(
            'metadata',
            {},
        ).get(
            'creationTimestamp',
            '',
        ),
        reverse=True,
    )

    if matches:
        print(
            matches[0][
                'metadata'
            ][
                'name'
            ]
        )
        raise SystemExit(0)

raise SystemExit(
    'ERROR: no proven TASK003 SparkApplication runtime found'
)
PY_SELECT
  )"

  kubectl -n "$NS" \
    get sparkapplication "$SOURCE_APP" \
    -o json \
    > "$SOURCE_APP_JSON"
fi

echo "SOURCE_SPARKAPPLICATION=$SOURCE_APP"

python3 - \
  "$SOURCE_APP_JSON" \
  <<'PY_RUNTIME'
import json
import sys
from pathlib import Path

app = json.loads(
    Path(sys.argv[1]).read_bytes()
)

spec = app['spec']

blob = json.dumps(
    spec,
    sort_keys=True,
).lower()

assert (
    'spark:3.5.7-python3'
    in blob
), 'unexpected Spark image'

assert (
    's3a'
    in blob
    or 'hadoop-aws'
    in blob
), 'proven runtime does not contain S3A/Hadoop AWS configuration'

assert (
    'postgres'
    in blob
), 'proven runtime does not contain PostgreSQL/JDBC support'

print('PROVEN_SPARK_RUNTIME=PASS')
print(
    'SOURCE_SPARK_IMAGE='
    + str(spec.get('image'))
)
PY_RUNTIME

echo '=== 6. Build standalone READ ONLY reconciliation driver ==='

cat > "$DRIVER" <<'PY_DRIVER'
#!/usr/bin/env python3

import hashlib
import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


EXPECTED_ROWS = 5799
EXPECTED_KEYS = 5799
EXPECTED_PERSONS = 113

EXPECTED_SOURCE_SYSTEM = "synthea"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def normalize_jdbc_url(value):
    value = value.strip()

    if value.startswith(
        "jdbc:postgresql://"
    ):
        return value

    if value.startswith(
        "postgresql://"
    ):
        return (
            "jdbc:"
            + value
        )

    raise RuntimeError(
        "Unsupported JDBC URL format"
    )


def resolve_jdbc_url():
    direct = os.environ.get(
        "A3_DB_JDBC_URL",
        "",
    ).strip()

    if direct:
        return normalize_jdbc_url(
            direct
        )

    host = os.environ.get(
        "A3_DB_HOST",
        "",
    ).strip()

    port = os.environ.get(
        "A3_DB_PORT",
        "5432",
    ).strip() or "5432"

    database = os.environ.get(
        "A3_DB_NAME",
        "omop",
    ).strip() or "omop"

    require(
        bool(host),
        "Missing JDBC URL and DB host",
    )

    return (
        "jdbc:postgresql://"
        + host
        + ":"
        + port
        + "/"
        + database
    )


def business_key_fingerprint(rows):
    canonical = [
        (
            str(row["source_system"])
            + "\t"
            + str(
                row[
                    "source_encounter_id"
                ]
            )
        )
        for row in rows
    ]

    canonical.sort()

    payload = (
        "\n".join(
            canonical
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def mapping_fingerprint(rows):
    canonical = [
        (
            str(row["source_system"])
            + "\t"
            + str(
                row[
                    "source_encounter_id"
                ]
            )
            + "\t"
            + str(
                row[
                    "visit_occurrence_id"
                ]
            )
        )
        for row in rows
    ]

    canonical.sort()

    payload = (
        "\n".join(
            canonical
        )
        + (
            "\n"
            if canonical
            else ""
        )
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def main():
    require(
        len(sys.argv) == 2,
        "Expected frozen Candidate data URI",
    )

    candidate_uri = sys.argv[1]

    jdbc_url = resolve_jdbc_url()

    jdbc_user = os.environ.get(
        "A3_DB_USER",
        "",
    )

    jdbc_password = os.environ.get(
        "A3_DB_PASSWORD",
        "",
    )

    require(
        bool(jdbc_user),
        "Missing DB user",
    )

    require(
        bool(jdbc_password),
        "Missing DB password",
    )

    spark = (
        SparkSession.builder
        .appName(
            "TASK003-STEP06A3-Visit-ID-Reconciliation"
        )
        .getOrCreate()
    )

    try:
        candidate = spark.read.parquet(
            candidate_uri
        )

        required_columns = {
            "source_system",
            "source_encounter_id",
            "person_id",
        }

        missing = (
            required_columns
            - set(
                candidate.columns
            )
        )

        require(
            not missing,
            "Candidate missing columns: "
            + repr(
                sorted(missing)
            ),
        )

        candidate_rows = (
            candidate.count()
        )

        require(
            candidate_rows
            == EXPECTED_ROWS,
            "Candidate row count mismatch",
        )

        invalid_keys = (
            candidate.filter(
                F.col(
                    "source_system"
                ).isNull()
                | (
                    F.length(
                        F.trim(
                            F.col(
                                "source_system"
                            )
                        )
                    )
                    == 0
                )
                | F.col(
                    "source_encounter_id"
                ).isNull()
                | (
                    F.length(
                        F.trim(
                            F.col(
                                "source_encounter_id"
                            )
                        )
                    )
                    == 0
                )
            )
            .count()
        )

        require(
            invalid_keys == 0,
            "Candidate contains null/blank business keys",
        )

        source_systems = [
            row["source_system"]
            for row in (
                candidate
                .select(
                    "source_system"
                )
                .distinct()
                .collect()
            )
        ]

        require(
            source_systems
            == [
                EXPECTED_SOURCE_SYSTEM
            ],
            "Unexpected source systems: "
            + repr(
                source_systems
            ),
        )

        candidate_keys_df = (
            candidate
            .select(
                "source_system",
                "source_encounter_id",
            )
            .distinct()
        )

        candidate_unique_keys = (
            candidate_keys_df.count()
        )

        require(
            candidate_unique_keys
            == EXPECTED_KEYS,
            "Candidate business-key count mismatch",
        )

        duplicate_candidate_groups = (
            candidate
            .groupBy(
                "source_system",
                "source_encounter_id",
            )
            .count()
            .filter(
                F.col("count") > 1
            )
            .count()
        )

        require(
            duplicate_candidate_groups == 0,
            "Duplicate Candidate business keys",
        )

        referenced_persons = (
            candidate
            .select(
                "person_id"
            )
            .distinct()
            .count()
        )

        require(
            referenced_persons
            == EXPECTED_PERSONS,
            "Referenced Person count mismatch",
        )

        jdbc_reader = (
            spark.read
            .format(
                "jdbc"
            )
            .option(
                "url",
                jdbc_url,
            )
            .option(
                "driver",
                "org.postgresql.Driver",
            )
            .option(
                "user",
                jdbc_user,
            )
            .option(
                "password",
                jdbc_password,
            )
            .option(
                "sessionInitStatement",
                "SET default_transaction_read_only = on",
            )
        )

        visit_map = (
            jdbc_reader
            .option(
                "dbtable",
                """(
                    SELECT
                        visit_occurrence_id,
                        source_system,
                        source_encounter_id
                    FROM etl.visit_occurrence_id_map
                ) AS visit_map"""
            )
            .load()
        )

        map_rows = (
            visit_map.count()
        )

        map_duplicate_business_keys = (
            visit_map
            .groupBy(
                "source_system",
                "source_encounter_id",
            )
            .count()
            .filter(
                F.col("count") > 1
            )
            .count()
        )

        map_duplicate_visit_ids = (
            visit_map
            .groupBy(
                "visit_occurrence_id"
            )
            .count()
            .filter(
                F.col("count") > 1
            )
            .count()
        )

        require(
            map_duplicate_business_keys == 0,
            "DB map contains duplicate business keys",
        )

        require(
            map_duplicate_visit_ids == 0,
            "DB map contains duplicate Visit IDs",
        )

        synthetic_map = (
            visit_map
            .filter(
                F.col(
                    "source_system"
                )
                == EXPECTED_SOURCE_SYSTEM
            )
        )

        synthetic_map_rows = (
            synthetic_map.count()
        )

        joined = (
            candidate_keys_df
            .alias(
                "c"
            )
            .join(
                synthetic_map.alias(
                    "m"
                ),
                on=(
                    (
                        F.col(
                            "c.source_system"
                        )
                        == F.col(
                            "m.source_system"
                        )
                    )
                    & (
                        F.col(
                            "c.source_encounter_id"
                        )
                        == F.col(
                            "m.source_encounter_id"
                        )
                    )
                ),
                how="left",
            )
            .select(
                F.col(
                    "c.source_system"
                ).alias(
                    "source_system"
                ),
                F.col(
                    "c.source_encounter_id"
                ).alias(
                    "source_encounter_id"
                ),
                F.col(
                    "m.visit_occurrence_id"
                ).alias(
                    "visit_occurrence_id"
                ),
            )
        )

        reconciled_rows = (
            joined.count()
        )

        require(
            reconciled_rows
            == EXPECTED_KEYS,
            "Reconciliation row count mismatch",
        )

        existing_mappings = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNotNull()
            )
            .count()
        )

        new_mappings = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNull()
            )
            .count()
        )

        require(
            (
                existing_mappings
                + new_mappings
            )
            == EXPECTED_KEYS,
            "Existing/new reconciliation total mismatch",
        )

        candidate_only_keys = (
            new_mappings
        )

        map_only_keys = (
            synthetic_map
            .alias(
                "m"
            )
            .join(
                candidate_keys_df.alias(
                    "c"
                ),
                on=(
                    (
                        F.col(
                            "m.source_system"
                        )
                        == F.col(
                            "c.source_system"
                        )
                    )
                    & (
                        F.col(
                            "m.source_encounter_id"
                        )
                        == F.col(
                            "c.source_encounter_id"
                        )
                    )
                ),
                how="left_anti",
            )
            .count()
        )

        candidate_key_rows = (
            candidate_keys_df
            .orderBy(
                "source_system",
                "source_encounter_id",
            )
            .collect()
        )

        candidate_key_sha = (
            business_key_fingerprint(
                candidate_key_rows
            )
        )

        existing_mapping_rows = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNotNull()
            )
            .orderBy(
                "source_system",
                "source_encounter_id",
            )
            .collect()
        )

        existing_mapping_sha = (
            mapping_fingerprint(
                existing_mapping_rows
            )
        )

        sample_new_keys = [
            {
                "source_system":
                    row[
                        "source_system"
                    ],

                "source_encounter_id":
                    row[
                        "source_encounter_id"
                    ],
            }
            for row in (
                joined
                .filter(
                    F.col(
                        "visit_occurrence_id"
                    ).isNull()
                )
                .orderBy(
                    "source_system",
                    "source_encounter_id",
                )
                .limit(
                    10
                )
                .collect()
            )
        ]

        result = {
            "task":
                "TASK-003",

            "step":
                "STEP-06A3",

            "status":
                "VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS",

            "run_id":
                "visit-proc-20261009t192437z-2081886",

            "candidate": {
                "rows":
                    candidate_rows,

                "unique_business_keys":
                    candidate_unique_keys,

                "referenced_persons":
                    referenced_persons,

                "duplicate_business_key_groups":
                    duplicate_candidate_groups,

                "business_key_sha256":
                    candidate_key_sha,
            },

            "database_map": {
                "total_rows":
                    map_rows,

                "synthea_rows":
                    synthetic_map_rows,

                "duplicate_business_key_groups":
                    map_duplicate_business_keys,

                "duplicate_visit_id_groups":
                    map_duplicate_visit_ids,
            },

            "reconciliation": {
                "rows":
                    reconciled_rows,

                "existing_mappings":
                    existing_mappings,

                "new_mappings":
                    new_mappings,

                "candidate_only_keys":
                    candidate_only_keys,

                "map_only_synthea_keys":
                    map_only_keys,

                "existing_mapping_sha256":
                    existing_mapping_sha,

                "sample_new_keys":
                    sample_new_keys,
            },

            "safety": {
                "s3_read_only":
                    True,

                "jdbc_read_only":
                    True,

                "nextval_called":
                    False,

                "setval_called":
                    False,

                "sequence_advanced":
                    False,

                "visit_id_map_write":
                    False,

                "cdm_visit_occurrence_write":
                    False,
            },
        }

        print(
            "VISIT_ID_RECONCILIATION_RESULT="
            + json.dumps(
                result,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            )
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
PY_DRIVER

chmod 0755 "$DRIVER"

python3 - \
  "$DRIVER" \
  <<'PY_STATIC'
import ast
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text()

ast.parse(source)

forbidden = (
    r'\bnextval\s*\(',
    r'\bsetval\s*\(',
    r'\bINSERT\s+INTO\b',
    r'\bUPDATE\s+',
    r'\bDELETE\s+FROM\b',
    r'\bTRUNCATE\b',
    r'\.write\b',
    r'\.save\s*\(',
    r'\.insertInto\s*\(',
    r'\.saveAsTable\s*\(',
)

for pattern in forbidden:
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

required = (
    'VISIT_ID_RECONCILIATION_RESULT=',
    'sessionInitStatement',
    'SET default_transaction_read_only = on',
    'source_encounter_id',
    'business_key_sha256',
    'existing_mappings',
    'new_mappings',
    'left_anti',
)

for token in required:
    assert token in source, token

print('A3_DRIVER_SYNTAX=PASS')
print('A3_DRIVER_STATIC_READ_ONLY=PASS')
print('A3_DRIVER_DB_WRITE_PATH=ABSENT')
print('A3_DRIVER_S3_WRITE_PATH=ABSENT')
PY_STATIC

echo '=== 7. Create reconciliation ConfigMap ==='

kubectl -n "$NS" \
  create configmap "$CM" \
  --from-file=reconcile_visit_id_keys.py="$DRIVER"

echo "A3_CONFIGMAP_CREATED=$CM"

echo '=== 8. Build SparkApplication from proven runtime ==='

python3 - \
  "$SOURCE_APP_JSON" \
  "$APP_JSON" \
  "$SECRET_MAP" \
  "$APP" \
  "$CM" \
  "$DB_SECRET" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP'
import copy
import json
import sys
from pathlib import Path

source_path = Path(
    sys.argv[1]
)

target_path = Path(
    sys.argv[2]
)

secret_map_path = Path(
    sys.argv[3]
)

app_name = sys.argv[4]
configmap_name = sys.argv[5]
db_secret = sys.argv[6]
candidate_uri = sys.argv[7]

source = json.loads(
    source_path.read_bytes()
)

mapping = json.loads(
    secret_map_path.read_bytes()
)

spec = copy.deepcopy(
    source[
        'spec'
    ]
)

spec[
    'mainApplicationFile'
] = (
    'local:///opt/spark/a3/'
    'reconcile_visit_id_keys.py'
)

spec[
    'arguments'
] = [
    candidate_uri,
]

spec[
    'restartPolicy'
] = {
    'type': 'Never',
}

# Remove old ConfigMap-backed runtime artifacts.
# Keep PVCs and Secrets because they may provide
# proven Spark/JAR/S3 runtime dependencies.
old_volumes = spec.get(
    'volumes',
    [],
)

removed_names = {
    volume.get(
        'name'
    )
    for volume in old_volumes
    if 'configMap' in volume
}

spec[
    'volumes'
] = [
    volume
    for volume in old_volumes
    if volume.get(
        'name'
    )
    not in removed_names
]

spec[
    'volumes'
].append(
    {
        'name':
            'a3-app',

        'configMap': {
            'name':
                configmap_name,
        },
    }
)

def remove_old_mounts(section):
    obj = spec.setdefault(
        section,
        {},
    )

    mounts = obj.get(
        'volumeMounts',
        [],
    )

    obj[
        'volumeMounts'
    ] = [
        mount
        for mount in mounts
        if mount.get(
            'name'
        )
        not in removed_names
        and mount.get(
            'name'
        )
        != 'a3-app'
    ]

    obj[
        'volumeMounts'
    ].append(
        {
            'name':
                'a3-app',

            'mountPath':
                '/opt/spark/a3',

            'readOnly':
                True,
        }
    )

    return obj


driver = remove_old_mounts(
    'driver'
)

executor = remove_old_mounts(
    'executor'
)

# The Python application only needs DB credentials
# in the driver. JDBC options are propagated by Spark.
driver_env = driver.setdefault(
    'env',
    [],
)

reserved_names = {
    'A3_DB_JDBC_URL',
    'A3_DB_USER',
    'A3_DB_PASSWORD',
    'A3_DB_HOST',
    'A3_DB_PORT',
    'A3_DB_NAME',
}

driver[
    'env'
] = [
    item
    for item in driver_env
    if item.get(
        'name'
    )
    not in reserved_names
]

def add_secret_env(
    env_name,
    secret_key,
):
    if not secret_key:
        return

    driver[
        'env'
    ].append(
        {
            'name':
                env_name,

            'valueFrom': {
                'secretKeyRef': {
                    'name':
                        db_secret,

                    'key':
                        secret_key,
                },
            },
        }
    )


add_secret_env(
    'A3_DB_JDBC_URL',
    mapping.get(
        'jdbc_url'
    ),
)

add_secret_env(
    'A3_DB_USER',
    mapping.get(
        'username'
    ),
)

add_secret_env(
    'A3_DB_PASSWORD',
    mapping.get(
        'password'
    ),
)

add_secret_env(
    'A3_DB_HOST',
    mapping.get(
        'host'
    ),
)

add_secret_env(
    'A3_DB_PORT',
    mapping.get(
        'port'
    ),
)

add_secret_env(
    'A3_DB_NAME',
    mapping.get(
        'database'
    ),
)

# Ensure Spark driver identity stays on the proven SA.
driver.setdefault(
    'serviceAccount',
    'spark-job',
)

# Remove old app-specific labels that can confuse
# evidence lookup, then add STEP06A3 identity.
for section in (
    driver,
    executor,
):
    labels = section.setdefault(
        'labels',
        {},
    )

    labels[
        'task'
    ] = 'task003'

    labels[
        'step'
    ] = 'step06a3'

doc = {
    'apiVersion':
        source[
            'apiVersion'
        ],

    'kind':
        source[
            'kind'
        ],

    'metadata': {
        'name':
            app_name,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task003',

            'step':
                'step06a3',

            'purpose':
                'visit-id-reconciliation',
        },
    },

    'spec':
        spec,
}

target_path.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('A3_SPARKAPPLICATION_RENDER=PASS')
PY_APP

echo '=== 9. Validate rendered SparkApplication safety ==='

python3 - \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP_CHECK'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

app_name = sys.argv[2]
cm_name = sys.argv[3]
candidate_uri = sys.argv[4]

assert doc['metadata']['name'] == app_name

spec = doc['spec']

assert (
    spec['mainApplicationFile']
    == 'local:///opt/spark/a3/reconcile_visit_id_keys.py'
)

assert spec['arguments'] == [
    candidate_uri
]

assert spec['restartPolicy']['type'] == 'Never'

volumes = {
    item['name']:
        item
    for item in spec.get(
        'volumes',
        []
    )
}

assert (
    volumes[
        'a3-app'
    ][
        'configMap'
    ][
        'name'
    ]
    == cm_name
)

driver_env = {
    item['name']:
        item
    for item in spec[
        'driver'
    ].get(
        'env',
        []
    )
}

assert 'A3_DB_USER' in driver_env
assert 'A3_DB_PASSWORD' in driver_env

assert (
    'A3_DB_JDBC_URL'
    in driver_env
    or 'A3_DB_HOST'
    in driver_env
)

blob = json.dumps(
    doc,
    sort_keys=True,
).lower()

assert 'nextval(' not in blob
assert 'setval(' not in blob

print('A3_SPARKAPPLICATION_STATIC_VALIDATION=PASS')
print('A3_DATABASE_SECRET_VALUE_EMBEDDED=NO')
print('A3_NEXTVAL_PATH=ABSENT')
print('A3_SETVAL_PATH=ABSENT')
PY_APP_CHECK

echo '=== 10. Launch real READ ONLY Spark reconciliation ==='

kubectl apply \
  -f "$APP_JSON"

echo "SPARKAPPLICATION_CREATED=$APP"

echo '=== 11. Observe SparkApplication ==='

FINAL_STATE=''

for _ in $(seq 1 180); do
  FINAL_STATE="$(
    kubectl -n "$NS" \
      get sparkapplication "$APP" \
      -o jsonpath='{.status.applicationState.state}' \
      2>/dev/null \
      || true
  )"

  case "$FINAL_STATE" in
    COMPLETED|FAILED|SUBMISSION_FAILED)
      break
      ;;
  esac

  sleep 5
done

echo "FINAL_STATE=$FINAL_STATE"

kubectl -n "$NS" \
  get sparkapplication "$APP" \
  -o json \
  > "$APP_FINAL_JSON"

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then
  DRIVER_POD="$(
    kubectl -n "$NS" \
      get sparkapplication "$APP" \
      -o jsonpath='{.status.driverInfo.podName}' \
      2>/dev/null \
      || true
  )"

  echo "FAILED_DRIVER_POD=${DRIVER_POD:-UNKNOWN}"

  if [[ -n "${DRIVER_POD:-}" ]]; then
    kubectl -n "$NS" \
      logs "$DRIVER_POD" \
      > "$DRIVER_LOG" \
      2>&1 \
      || true

    tail -n 200 "$DRIVER_LOG" || true
  fi

  echo 'ERROR: STEP06A3 Spark reconciliation did not complete'
  echo 'FAILED_RUNTIME_RESOURCES_PRESERVED=YES'
  exit 1
fi

echo 'SPARK_RECONCILIATION_APPLICATION=COMPLETED'

echo '=== 12. Capture driver log and reconciliation result ==='

DRIVER_POD="$(
  kubectl -n "$NS" \
    get sparkapplication "$APP" \
    -o jsonpath='{.status.driverInfo.podName}'
)"

echo "DRIVER_POD=$DRIVER_POD"

kubectl -n "$NS" \
  logs "$DRIVER_POD" \
  > "$DRIVER_LOG"

grep \
  'VISIT_ID_RECONCILIATION_RESULT=' \
  "$DRIVER_LOG" \
  | tail -n 1 \
  > "$REPORT/result-marker.txt"

[[ -s "$REPORT/result-marker.txt" ]] || {
  echo 'ERROR: reconciliation result marker missing'
  exit 1
}

python3 - \
  "$REPORT/result-marker.txt" \
  "$RESULT_JSON" \
  <<'PY_RESULT'
import json
import sys
from pathlib import Path

line = Path(
    sys.argv[1]
).read_text().strip()

prefix = (
    'VISIT_ID_RECONCILIATION_RESULT='
)

assert line.startswith(
    prefix
)

result = json.loads(
    line[
        len(prefix):
    ]
)

Path(
    sys.argv[2]
).write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

assert result['task'] == 'TASK-003'
assert result['step'] == 'STEP-06A3'

assert (
    result['status']
    == 'VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS'
)

candidate = result[
    'candidate'
]

assert candidate['rows'] == 5799
assert candidate['unique_business_keys'] == 5799
assert candidate['referenced_persons'] == 113

assert (
    candidate[
        'duplicate_business_key_groups'
    ]
    == 0
)

assert len(
    candidate[
        'business_key_sha256'
    ]
) == 64

db = result[
    'database_map'
]

assert db['total_rows'] == 0
assert db['synthea_rows'] == 0

assert (
    db[
        'duplicate_business_key_groups'
    ]
    == 0
)

assert (
    db[
        'duplicate_visit_id_groups'
    ]
    == 0
)

recon = result[
    'reconciliation'
]

assert recon['rows'] == 5799
assert recon['existing_mappings'] == 0
assert recon['new_mappings'] == 5799
assert recon['candidate_only_keys'] == 5799
assert recon['map_only_synthea_keys'] == 0

safety = result[
    'safety'
]

assert safety['s3_read_only'] is True
assert safety['jdbc_read_only'] is True
assert safety['nextval_called'] is False
assert safety['setval_called'] is False
assert safety['sequence_advanced'] is False
assert safety['visit_id_map_write'] is False
assert safety['cdm_visit_occurrence_write'] is False

print('A3_RECONCILIATION_RESULT=PASS')

print(
    'CANDIDATE_BUSINESS_KEY_SHA256='
    + candidate[
        'business_key_sha256'
    ]
)

print(
    'EXISTING_MAPPING_SHA256='
    + recon[
        'existing_mapping_sha256'
    ]
)

print('EXISTING_CANDIDATE_MAPPINGS=0')
print('NEW_CANDIDATE_MAPPINGS=5799')
print('CANDIDATE_ONLY_KEYS=5799')
print('MAP_ONLY_SYNTHEA_KEYS=0')
PY_RESULT

cat "$RESULT_JSON"

echo '=== 13. Independent post-Spark PostgreSQL immutability check ==='

kubectl -n "$DB_NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -A \
    -t \
    -F '|' \
    -P pager=off \
  > "$DB_POSTCHECK" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*)
       FROM etl.visit_occurrence_id_map),
    (SELECT count(*)
       FROM cdm.visit_occurrence),
    (SELECT count(*)
       FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$DB_POSTCHECK"

python3 - \
  "$DB_POSTCHECK" \
  <<'PY_POST'
import sys
from pathlib import Path

rows = [
    line.strip()
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        'BEGIN',
        'SET',
        'ROLLBACK',
    }
]

assert rows == [
    '0|0|113',
    '1|f',
    'on',
], rows

print('POST_A3_DATABASE_IMMUTABILITY=PASS')
print('VISIT_MAP_ROWS_AFTER_A3=0')
print('CDM_VISIT_ROWS_AFTER_A3=0')
print('PERSON_MAP_ROWS_AFTER_A3=113')
print('SEQUENCE_LAST_VALUE_AFTER_A3=1')
print('SEQUENCE_IS_CALLED_AFTER_A3=FALSE')
PY_POST

echo '=== 14. Record STEP06A3 evidence ==='

python3 - \
  "$RESULT_JSON" \
  "$RUN_STATE" \
  "$PLAN" \
  "$HEAD" \
  "$SOURCE_APP" \
  "$APP" \
  "$CM" \
  <<'PY_STATE'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

result_path = Path(
    sys.argv[1]
)

state_path = Path(
    sys.argv[2]
)

plan_path = Path(
    sys.argv[3]
)

head = sys.argv[4]
source_app = sys.argv[5]
app = sys.argv[6]
cm = sys.argv[7]

result = json.loads(
    result_path.read_bytes()
)

def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-06A3',

    'status':
        'VISIT_ID_BUSINESS_KEY_RECONCILIATION_VERIFIED',

    'run_id':
        'visit-proc-20261009t192437z-2081886',

    'git_checkpoint':
        head,

    'allocation_plan_sha256':
        sha(
            plan_path
        ),

    'reconciliation_result_sha256':
        sha(
            result_path
        ),

    'candidate_business_key_sha256':
        result[
            'candidate'
        ][
            'business_key_sha256'
        ],

    'candidate_rows':
        5799,

    'candidate_unique_business_keys':
        5799,

    'existing_candidate_mappings':
        0,

    'new_candidate_mappings':
        5799,

    'candidate_only_keys':
        5799,

    'map_only_synthea_keys':
        0,

    'source_sparkapplication':
        source_app,

    'sparkapplication':
        app,

    'runtime_configmap':
        cm,

    's3_read_only':
        True,

    'database_read_only':
        True,

    'visit_id_allocation_started':
        False,

    'visit_id_map_mutated':
        False,

    'sequence_advanced':
        False,

    'cdm_visit_occurrence_write':
        False,

    'observed_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

state_path.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('STEP06A3_RUN_STATE=PASS')

print(
    'STEP06A3_RESULT_SHA256='
    + state[
        'reconciliation_result_sha256'
    ]
)

print(
    'CANDIDATE_BUSINESS_KEY_SHA256='
    + state[
        'candidate_business_key_sha256'
    ]
)
PY_STATE

echo '=== 15. Final STEP06A3 verdict ==='

echo 'STEP06A3_VISIT_BUSINESS_KEY_RECONCILIATION=PASS'

echo 'FROZEN_CANDIDATE_ROWS=5799'
echo 'FROZEN_CANDIDATE_UNIQUE_KEYS=5799'
echo 'FROZEN_CANDIDATE_PERSONS=113'

echo 'EXISTING_CANDIDATE_MAPPINGS=0'
echo 'NEW_CANDIDATE_MAPPINGS=5799'
echo 'CANDIDATE_ONLY_KEYS=5799'
echo 'MAP_ONLY_SYNTHEA_KEYS=0'

echo 'BUSINESS_KEY_FINGERPRINT_CAPTURED=YES'

echo 'S3_ACCESS=READ_ONLY'
echo 'DATABASE_ACCESS=READ_ONLY'

echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'KUBERNETES_RUNTIME_RESOURCES_CREATED=YES'
echo 'RUNTIME_RESOURCES_AUTOMATIC_CLEANUP=NO'

echo 'GIT_COMMIT=NO'
A3_EOF_TASK003_06A5

for rel in   scripts/task003/06a1-visit-id-allocation-baseline-discovery.sh   scripts/task003/06a2-plan-visit-id-allocation.sh   scripts/task003/06a3-reconcile-visit-business-keys.sh
do
  src="$STAGE/$rel"
  dst="$ROOT/$rel"

  bash -n "$src"

  mkdir -p "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "UNCHANGED=$rel"
      continue
    fi

    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi

  install -m 0755 "$src" "$dst"
  echo "INSTALLED=$rel"
done

echo 'STEP06A_READONLY_RUNNER_SNAPSHOTS=PASS'
echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'
