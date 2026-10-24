#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-postgre
DB_POD=dw-postgre-database-0
DB=omop
DB_USER=omop_admin

EXPECTED_HEAD=a4d4381dfa6541b10f8e22dd01cb3b8f50ab0a62

FAILED_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation.20261010t141014z.2485209"

ALLOCATION_SQL="$FAILED_REPORT/allocation.sql"
MUTATION_INTENT="$FAILED_REPORT/mutation-intent.json"
PSQL_OUTPUT="$FAILED_REPORT/psql-output.txt"

RECOVERY_DB_ORIGINAL="$FAILED_REPORT/recovery-database-state.txt"
RECOVERY_MAP_ORIGINAL="$FAILED_REPORT/recovery-map.tsv"

EXPECTED_ALLOCATION_SQL_SHA=46ba2f9f1ffad0fbbe1415f27122c04c23b2422c34e93ab836dcdf87e00570f6

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e

SEQUENCE=etl.visit_occurrence_id_map_visit_occurrence_id_seq

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-recovery.${STAMP}.$$"

DB_STATE="$REPORT/database-state.txt"
IDENTITY_STATE="$REPORT/identity-state.txt"
MAP_READBACK="$REPORT/map-readback.tsv"
RECOVERY_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06B4B-R1 FAILED ALLOCATION RECOVERY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4B_R1_REPORT=$REPORT"
  echo "STEP06B4B_R1_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06B4B-R1 FAILED ALLOCATION RECOVERY OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify Git checkpoint remains frozen ==='

HEAD="$(git rev-parse HEAD)"

REMOTE_MAIN="$(
  git ls-remote \
    origin \
    refs/heads/main \
  | awk '{print $1}'
)"

echo "CURRENT_HEAD=$HEAD"
echo "REMOTE_MAIN_HEAD=$REMOTE_MAIN"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: local Git HEAD drifted after failed mutation'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main drifted after failed mutation'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: working tree is not clean'
  git status --short
  exit 1
}

echo 'FAILED_MUTATION_PARENT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Verify failed mutation evidence is preserved ==='

for file in \
  "$ALLOCATION_SQL" \
  "$MUTATION_INTENT" \
  "$PSQL_OUTPUT" \
  "$RECOVERY_DB_ORIGINAL" \
  "$RECOVERY_MAP_ORIGINAL"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing failed-mutation evidence: $file"
    exit 1
  }
done

SQL_SHA="$(
  sha256sum "$ALLOCATION_SQL" |
  awk '{print $1}'
)"

INTENT_SHA="$(
  sha256sum "$MUTATION_INTENT" |
  awk '{print $1}'
)"

OUTPUT_SHA="$(
  sha256sum "$PSQL_OUTPUT" |
  awk '{print $1}'
)"

echo "FAILED_ALLOCATION_SQL_SHA256=$SQL_SHA"
echo "FAILED_MUTATION_INTENT_SHA256=$INTENT_SHA"
echo "FAILED_PSQL_OUTPUT_SHA256=$OUTPUT_SHA"

[[ "$SQL_SHA" == "$EXPECTED_ALLOCATION_SQL_SHA" ]] || {
  echo 'ERROR: failed allocation SQL SHA mismatch'
  exit 1
}

echo 'FAILED_MUTATION_EVIDENCE_PRESERVED=PASS'

echo '=== 3. Classify exact failure ==='

python3 - \
  "$ALLOCATION_SQL" \
  "$MUTATION_INTENT" \
  "$PSQL_OUTPUT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_FAILURE'
import json
import re
import sys
from pathlib import Path


sql = Path(sys.argv[1]).read_text()
intent = json.loads(
    Path(sys.argv[2]).read_bytes()
)
output = Path(sys.argv[3]).read_text()

expected_head = sys.argv[4]
expected_key_sha = sys.argv[5]


assert intent["task"] == "TASK-003"
assert intent["step"] == "STEP-06B4B"

assert (
    intent["status"]
    == "VISIT_ID_ALLOCATION_READY_TO_EXECUTE"
)

assert intent["git_checkpoint"] == expected_head

assert (
    intent["candidate_business_key_sha256"]
    == expected_key_sha
)

assert intent["candidate_rows"] == 5799

assert (
    intent["sequence_gap_policy"]
    == "ACCEPT_GAPS_NEVER_REWIND"
)

assert (
    intent["blind_retry_after_uncertain_execution"]
    is False
)

assert intent["setval_backward"] == "FORBIDDEN"


assert "IRREVERSIBLE_BOUNDARY_BEGIN" in output

assert (
    'cannot insert a non-DEFAULT value into column "visit_occurrence_id"'
    in output
)

assert (
    "identity column defined as GENERATED ALWAYS"
    in output
)

assert (
    "Use OVERRIDING SYSTEM VALUE to override"
    in output
)


nextval = re.findall(
    r"\bnextval\s*\(",
    sql,
    re.IGNORECASE,
)

assert len(nextval) == 1


insert_match = re.search(
    r"INSERT\s+INTO\s+etl\.visit_occurrence_id_map\s*\("
    r".*?"
    r"\)\s*VALUES\s*\("
    r".*?"
    r"\)",
    sql,
    re.IGNORECASE | re.DOTALL,
)

assert insert_match

insert_sql = insert_match.group(0)

assert (
    "OVERRIDING SYSTEM VALUE"
    not in insert_sql.upper()
)


assert (
    "MUTATION_TRANSACTION_COMMIT_COMPLETE"
    not in output
)

assert (
    "IRREVERSIBLE_BOUNDARY_CROSSED"
    not in output
)


print("FAILED_MUTATION_CLASSIFICATION=PASS")

print(
    "FAILURE_CLASS="
    "GENERATED_ALWAYS_IDENTITY_OVERRIDE_REQUIRED"
)

print(
    "IRREVERSIBLE_BOUNDARY_BEGIN_OBSERVED=YES"
)

print(
    "TRANSACTION_COMMIT_COMPLETE_OBSERVED=NO"
)

print(
    "ORIGINAL_INSERT_OVERRIDE_SYSTEM_VALUE=NO"
)

print(
    "OLD_B4B_RERUN_ALLOWED=NO"
)
PY_FAILURE

echo '=== 4. Inspect identity-column definition READ ONLY ==='

kubectl -n "$NS" \
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
  > "$IDENTITY_STATE" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

\echo COLUMN_IDENTITY

SELECT
    is_identity,
    COALESCE(identity_generation, 'NONE'),
    COALESCE(identity_start, 'NONE'),
    COALESCE(identity_increment, 'NONE'),
    COALESCE(identity_cycle, 'NONE'),
    COALESCE(column_default, 'NONE')
FROM information_schema.columns
WHERE table_schema = 'etl'
  AND table_name = 'visit_occurrence_id_map'
  AND column_name = 'visit_occurrence_id';

\echo SERIAL_SEQUENCE

SELECT COALESCE(
    pg_get_serial_sequence(
        'etl.visit_occurrence_id_map',
        'visit_occurrence_id'
    ),
    'NONE'
);

\echo SEQUENCE_CONFIGURATION

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
  AND sequencename = 'visit_occurrence_id_map_visit_occurrence_id_seq';

\echo SEQUENCE_DIRECT

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

\echo SEQUENCE_DEPENDENCY

SELECT
    d.deptype,
    ns_seq.nspname || '.' || seq.relname,
    ns_tab.nspname || '.' || tab.relname,
    att.attname
FROM pg_depend d
JOIN pg_class seq
  ON seq.oid = d.objid
JOIN pg_namespace ns_seq
  ON ns_seq.oid = seq.relnamespace
JOIN pg_class tab
  ON tab.oid = d.refobjid
JOIN pg_namespace ns_tab
  ON ns_tab.oid = tab.relnamespace
JOIN pg_attribute att
  ON att.attrelid = tab.oid
 AND att.attnum = d.refobjsubid
WHERE seq.oid =
      'etl.visit_occurrence_id_map_visit_occurrence_id_seq'::regclass
  AND tab.oid =
      'etl.visit_occurrence_id_map'::regclass
  AND att.attname = 'visit_occurrence_id';

\echo TRANSACTION_READ_ONLY

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$IDENTITY_STATE"

echo '=== 5. Validate identity metadata ==='

python3 - \
  "$IDENTITY_STATE" \
  "$SEQUENCE" \
  <<'PY_IDENTITY'
import sys
from pathlib import Path


lines = [
    line.strip()
    for line in Path(
        sys.argv[1]
    ).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        "BEGIN",
        "SET",
        "ROLLBACK",
    }
]

expected_sequence = sys.argv[2]


def after(marker):
    index = lines.index(marker)
    return lines[index + 1]


column = after(
    "COLUMN_IDENTITY"
).split("|")

serial_sequence = after(
    "SERIAL_SEQUENCE"
)

config = after(
    "SEQUENCE_CONFIGURATION"
).split("|")

direct = after(
    "SEQUENCE_DIRECT"
).split("|")

dependency = after(
    "SEQUENCE_DEPENDENCY"
).split("|")

readonly = after(
    "TRANSACTION_READ_ONLY"
)


assert column[0] == "YES", column
assert column[1] == "ALWAYS", column
assert column[2] == "1", column
assert column[3] == "1", column
assert column[4] == "NO", column

# GENERATED ALWAYS identity may have no ordinary column_default.
assert column[5] == "NONE", column

assert serial_sequence == expected_sequence

assert config == [
    "1",
    "1",
    "2147483647",
    "1",
    "f",
    "1",
    "1",
], config

assert direct == [
    "1",
    "t",
], direct

assert len(dependency) == 4, dependency

assert dependency[1] == expected_sequence
assert dependency[2] == "etl.visit_occurrence_id_map"
assert dependency[3] == "visit_occurrence_id"

assert readonly == "on"


print("IDENTITY_METADATA_RECONCILIATION=PASS")

print("VISIT_ID_IS_IDENTITY=YES")
print("VISIT_ID_IDENTITY_GENERATION=ALWAYS")

print(
    "IDENTITY_SEQUENCE="
    + serial_sequence
)

print(
    "SEQUENCE_DEPENDENCY_TYPE="
    + dependency[0]
)

print("SEQUENCE_INCREMENT=1")
print("SEQUENCE_CACHE=1")

print("SEQUENCE_LAST_VALUE=1")
print("SEQUENCE_IS_CALLED=TRUE")

print("ORDINARY_COLUMN_DEFAULT=NONE")

print(
    "EXPLICIT_ID_INSERT_REQUIRES="
    "OVERRIDING_SYSTEM_VALUE"
)
PY_IDENTITY

echo '=== 6. Fresh full READ ONLY database reconciliation ==='

kubectl -n "$NS" \
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
  > "$DB_STATE" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

\echo COUNTS

SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

\echo SEQUENCE

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

\echo MAP_ID_STATE

SELECT
    count(*),
    count(DISTINCT visit_occurrence_id),
    COALESCE(min(visit_occurrence_id), 0),
    COALESCE(max(visit_occurrence_id), 0)
FROM etl.visit_occurrence_id_map;

\echo MAP_COLLISIONS

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

\echo CDM_MAP_OVERLAP

SELECT count(*)
FROM cdm.visit_occurrence c
JOIN etl.visit_occurrence_id_map m
  ON m.visit_occurrence_id = c.visit_occurrence_id;

\echo TRANSACTION_READ_ONLY

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$DB_STATE"

echo '=== 7. Capture exact map content READ ONLY ==='

kubectl -n "$NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -A \
    -t \
    -P pager=off \
  > "$MAP_READBACK" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    source_system
    || E'\t'
    || source_encounter_id
    || E'\t'
    || visit_occurrence_id::text
FROM etl.visit_occurrence_id_map
ORDER BY
    source_system,
    source_encounter_id;

ROLLBACK;
SQL

echo 'EXACT_MAP_READBACK_CAPTURED=YES'

echo '=== 8. Validate post-failure database state ==='

python3 - \
  "$DB_STATE" \
  "$MAP_READBACK" \
  "$RECOVERY_DB_ORIGINAL" \
  "$RECOVERY_MAP_ORIGINAL" \
  <<'PY_DB'
import sys
from pathlib import Path


db_path = Path(sys.argv[1])
map_path = Path(sys.argv[2])
original_db_path = Path(sys.argv[3])
original_map_path = Path(sys.argv[4])


def meaningful(path):
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip()
        and line.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]


lines = meaningful(
    db_path
)


def after(marker):
    index = lines.index(marker)
    return lines[index + 1]


assert after("COUNTS") == "0|0|113"

assert after("SEQUENCE") == "1|t"

assert after("MAP_ID_STATE") == "0|0|0|0"

assert after("MAP_COLLISIONS") == "0|0"

assert after("CDM_MAP_OVERLAP") == "0"

assert (
    after("TRANSACTION_READ_ONLY")
    == "on"
)


map_lines = [
    line
    for line in meaningful(
        map_path
    )
    if "\t" in line
]

assert map_lines == []


original_db = meaningful(
    original_db_path
)

assert original_db == [
    "0|0|113",
    "1|t",
    "0|0|0|0",
    "0|0",
    "0",
], original_db


original_map_rows = [
    line
    for line in meaningful(
        original_map_path
    )
    if "\t" in line
]

assert original_map_rows == []


print(
    "POST_FAILURE_DATABASE_RECONCILIATION=PASS"
)

print(
    "ORIGINAL_RECOVERY_EVIDENCE_MATCH=YES"
)

print(
    "VISIT_MAP_ROWS_AFTER_FAILED_TRANSACTION=0"
)

print(
    "CDM_VISIT_ROWS_AFTER_FAILED_TRANSACTION=0"
)

print(
    "PERSON_MAP_ROWS_AFTER_FAILED_TRANSACTION=113"
)

print(
    "SEQUENCE_LAST_VALUE_AFTER_FAILED_TRANSACTION=1"
)

print(
    "SEQUENCE_IS_CALLED_AFTER_FAILED_TRANSACTION=TRUE"
)

print(
    "FAILED_TRANSACTION_COMMITTED_MAP_ROWS=0"
)

print(
    "SEQUENCE_VALUE_1_CONSUMED=YES"
)
PY_DB

echo '=== 9. Derive safe recovery policy without calling sequence ==='

python3 - <<'PY_POLICY'
last_value = 1
is_called = True
increment = 1

assert is_called is True
assert increment == 1

predicted_next = (
    last_value
    + increment
)

assert predicted_next == 2

print(
    "RECOVERY_SEQUENCE_POLICY=PASS"
)

print(
    "SEQUENCE_GAP_AT_ID_1=EXPECTED_AND_ACCEPTED"
)

print(
    "PREDICTED_NEXT_SEQUENCE_VALUE=2"
)

print(
    "PREDICTED_NEXT_VALUE_AUTHORITATIVE=NO"
)

print(
    "MUTATION_TIME_LOCKED_REVALIDATION_REQUIRED=YES"
)

print(
    "SETVAL_BACKWARD_ALLOWED=NO"
)

print(
    "OLD_B4B_RERUN_ALLOWED=NO"
)

print(
    "CORRECTED_INSERT_REQUIRES_OVERRIDING_SYSTEM_VALUE=YES"
)
PY_POLICY

echo '=== 10. Record immutable recovery state ==='

python3 - \
  "$RECOVERY_STATE" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_ALLOCATION_SQL_SHA" \
  "$INTENT_SHA" \
  "$OUTPUT_SHA" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_STATE'
import json
import sys
from pathlib import Path


output = Path(sys.argv[1])

state = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B4B-R1",

    "status":
        "FAILED_ALLOCATION_RECONCILED",

    "git_checkpoint":
        sys.argv[2],

    "failed_allocation_sql_sha256":
        sys.argv[3],

    "failed_mutation_intent_sha256":
        sys.argv[4],

    "failed_psql_output_sha256":
        sys.argv[5],

    "candidate_business_key_sha256":
        sys.argv[6],

    "failure_class":
        "GENERATED_ALWAYS_IDENTITY_OVERRIDE_REQUIRED",

    "visit_id_identity":
        True,

    "identity_generation":
        "ALWAYS",

    "explicit_id_insert_requirement":
        "OVERRIDING SYSTEM VALUE",

    "committed_visit_map_rows":
        0,

    "cdm_visit_rows":
        0,

    "person_map_rows":
        113,

    "sequence_last_value":
        1,

    "sequence_is_called":
        True,

    "sequence_value_1_consumed":
        True,

    "predicted_next_sequence_value":
        2,

    "predicted_next_value_authoritative":
        False,

    "sequence_gap_policy":
        "ACCEPT_GAPS_NEVER_REWIND",

    "setval_backward_allowed":
        False,

    "old_b4b_rerun_allowed":
        False,

    "corrected_mutation_requires_fresh_locked_revalidation":
        True,

    "database_access":
        "READ_ONLY",

    "database_mutation":
        False,

    "s3_mutation":
        False,

    "git_commit":
        False,
}


output.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


print(
    "STEP06B4B_R1_RECOVERY_STATE=PASS"
)
PY_STATE

chmod 0444 "$RECOVERY_STATE"

RECOVERY_SHA="$(
  sha256sum "$RECOVERY_STATE" |
  awk '{print $1}'
)"

echo "RECOVERY_STATE_SHA256=$RECOVERY_SHA"

echo '=== 11. Final STEP06B4B-R1 verdict ==='

echo 'STEP06B4B_R1_FAILED_ALLOCATION_RECONCILIATION=PASS'

echo 'FAILURE_CLASS=GENERATED_ALWAYS_IDENTITY_OVERRIDE_REQUIRED'

echo 'VISIT_ID_IS_IDENTITY=YES'
echo 'VISIT_ID_IDENTITY_GENERATION=ALWAYS'

echo 'ORIGINAL_COLUMN_DEFAULT=NONE'
echo "IDENTITY_SEQUENCE=$SEQUENCE"

echo 'COMMITTED_VISIT_MAP_ROWS=0'
echo 'CDM_VISIT_ROWS=0'
echo 'PERSON_MAP_ROWS=113'

echo 'SEQUENCE_LAST_VALUE=1'
echo 'SEQUENCE_IS_CALLED=TRUE'

echo 'SEQUENCE_VALUE_1_CONSUMED=YES'
echo 'SEQUENCE_GAP_AT_ID_1=ACCEPTED'

echo 'PREDICTED_NEXT_SEQUENCE_VALUE=2'
echo 'PREDICTED_NEXT_VALUE_AUTHORITATIVE=NO'

echo 'OLD_B4B_RERUN_ALLOWED=NO'
echo 'BLIND_RETRY_ALLOWED=NO'
echo 'SETVAL_BACKWARD_ALLOWED=NO'

echo 'CORRECTED_INSERT_REQUIRES_OVERRIDING_SYSTEM_VALUE=YES'
echo 'FRESH_LOCKED_REVALIDATION_BEFORE_RETRY=REQUIRED'

echo 'DATABASE_ACCESS=READ_ONLY'
echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'

echo 'NEXT_REQUIRED_STEP=STEP06B4B_R2_CORRECTED_MUTATION'
