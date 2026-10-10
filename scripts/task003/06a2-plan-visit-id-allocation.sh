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
