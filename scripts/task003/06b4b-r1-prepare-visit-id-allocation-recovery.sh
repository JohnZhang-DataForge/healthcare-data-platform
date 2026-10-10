#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06b4b-r1-generator.XXXXXX)"

echo '#### TASK003 STEP06B4B-R1 PREPARE RECOVERY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06B4B_R1_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4B-R1 PREPARE RECOVERY OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4b-r1-reconcile-failed-visit-id-allocation.sh" <<'RECOVERY_RUNNER_EOF_TASK003'
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
RECOVERY_RUNNER_EOF_TASK003

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/verify_visit_id_allocation_recovery.py" <<'RECOVERY_APP_EOF_TASK003'
#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_HEAD = (
    "a4d4381dfa6541b10f8e22dd01cb3b8f50ab0a62"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_FAILED_SQL_SHA = (
    "46ba2f9f1ffad0fbbe1415f27122c04c"
    "23b2422c34e93ab836dcdf87e00570f6"
)

EXPECTED_FAILED_INTENT_SHA = (
    "e089d6a7d4adb00f2af4095715f92614"
    "1611dd2315d9f4b8b3a99a9b5136b664"
)

EXPECTED_FAILED_OUTPUT_SHA = (
    "bea7b2bbaa61de00accbc6f181782f257"
    "c6fe846d618c747b6790514b600c997"
)

EXPECTED_RECOVERY_SHA = (
    "c34f6682f5a4482f1ef33f8a085463c4"
    "714fe858cd72c14bc03d75be3608dcc2"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_bytes()
    )


def validate(
    amendment_path,
    recovery_path,
    failed_sql_path,
    failed_intent_path,
    failed_output_path,
    identity_state_path,
    db_state_path,
    map_readback_path,
):
    amendment = load(
        amendment_path
    )

    recovery = load(
        recovery_path
    )

    require(
        amendment["task"]
        == "TASK-003",
        "amendment task",
    )

    require(
        amendment["step"]
        == "STEP-06B4B-R1",
        "amendment step",
    )

    require(
        amendment["status"]
        == "VISIT_ID_ALLOCATION_RECOVERY_AMENDMENT_READY",
        "amendment status",
    )

    require(
        amendment["git_checkpoint"]
        == EXPECTED_HEAD,
        "amendment checkpoint",
    )

    require(
        amendment["recovery_state_sha256"]
        == EXPECTED_RECOVERY_SHA,
        "amendment recovery SHA",
    )

    require(
        sha(recovery_path)
        == EXPECTED_RECOVERY_SHA,
        "runtime recovery SHA",
    )

    require(
        sha(failed_sql_path)
        == EXPECTED_FAILED_SQL_SHA,
        "failed SQL SHA",
    )

    require(
        sha(failed_intent_path)
        == EXPECTED_FAILED_INTENT_SHA,
        "failed intent SHA",
    )

    require(
        sha(failed_output_path)
        == EXPECTED_FAILED_OUTPUT_SHA,
        "failed output SHA",
    )

    identity = amendment["identity"]

    require(
        identity["is_identity"]
        is True,
        "identity flag",
    )

    require(
        identity["identity_generation"]
        == "ALWAYS",
        "identity generation",
    )

    require(
        identity["ordinary_column_default"]
        is None,
        "ordinary default",
    )

    require(
        identity["dependency_type"]
        == "i",
        "identity dependency",
    )

    require(
        identity["sequence"]
        == "etl.visit_occurrence_id_map_visit_occurrence_id_seq",
        "identity sequence",
    )

    baseline = amendment[
        "recovery_baseline"
    ]

    require(
        baseline[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "candidate fingerprint",
    )

    require(
        baseline[
            "committed_visit_map_rows"
        ]
        == 0,
        "map baseline",
    )

    require(
        baseline[
            "cdm_visit_rows"
        ]
        == 0,
        "CDM baseline",
    )

    require(
        baseline[
            "person_map_rows"
        ]
        == 113,
        "Person baseline",
    )

    require(
        baseline[
            "sequence_last_value"
        ]
        == 1,
        "sequence last",
    )

    require(
        baseline[
            "sequence_is_called"
        ]
        is True,
        "sequence is_called",
    )

    require(
        baseline[
            "sequence_value_1_consumed"
        ]
        is True,
        "consumed ID 1",
    )

    require(
        baseline[
            "predicted_next_sequence_value"
        ]
        == 2,
        "predicted next",
    )

    require(
        baseline[
            "predicted_next_value_authoritative"
        ]
        is False,
        "prediction authority",
    )

    correction = amendment[
        "corrected_mutation_requirements"
    ]

    require(
        correction[
            "explicit_identity_insert"
        ][
            "required_clause"
        ]
        == "OVERRIDING SYSTEM VALUE",
        "override clause",
    )

    require(
        correction[
            "old_b4b_rerun_allowed"
        ]
        is False,
        "old retry",
    )

    require(
        correction[
            "setval_backward_allowed"
        ]
        is False,
        "setval policy",
    )

    require(
        correction[
            "sequence_gap_policy"
        ]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "gap policy",
    )

    require(
        correction[
            "fresh_locked_revalidation_required"
        ]
        is True,
        "fresh lock gate",
    )

    require(
        recovery["status"]
        == "FAILED_ALLOCATION_RECONCILED",
        "runtime recovery status",
    )

    require(
        recovery["sequence_last_value"]
        == 1,
        "runtime sequence last",
    )

    require(
        recovery["sequence_is_called"]
        is True,
        "runtime sequence called",
    )

    require(
        recovery["sequence_value_1_consumed"]
        is True,
        "runtime consumed value",
    )

    identity_text = Path(
        identity_state_path
    ).read_text()

    require(
        "YES|ALWAYS|1|1|NO|NONE"
        in identity_text,
        "identity metadata",
    )

    require(
        "1|t"
        in identity_text,
        "identity sequence state",
    )

    db_text = Path(
        db_state_path
    ).read_text()

    require(
        "0|0|113"
        in db_text,
        "recovery DB counts",
    )

    require(
        "0|0|0|0"
        in db_text,
        "recovery map state",
    )

    map_lines = [
        line
        for line in Path(
            map_readback_path
        ).read_text().splitlines()
        if line.strip()
        and line.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        map_lines == [],
        "recovery map readback",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4B-R1A",

        "status":
            "VISIT_ID_ALLOCATION_RECOVERY_CANONICAL_GATE_PASS",

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "committed_visit_map_rows":
            0,

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

        "identity_generation":
            "ALWAYS",

        "explicit_id_insert_requirement":
            "OVERRIDING SYSTEM VALUE",

        "old_b4b_rerun_allowed":
            False,

        "setval_backward_allowed":
            False,

        "ready_for_corrected_mutation_design":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--amendment",
        required=True,
    )

    parser.add_argument(
        "--recovery",
        required=True,
    )

    parser.add_argument(
        "--failed-sql",
        required=True,
    )

    parser.add_argument(
        "--failed-intent",
        required=True,
    )

    parser.add_argument(
        "--failed-output",
        required=True,
    )

    parser.add_argument(
        "--identity-state",
        required=True,
    )

    parser.add_argument(
        "--db-state",
        required=True,
    )

    parser.add_argument(
        "--map-readback",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.amendment,
        args.recovery,
        args.failed_sql,
        args.failed_intent,
        args.failed_output,
        args.identity_state,
        args.db_state,
        args.map_readback,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "STEP06B4B_R1_CANONICAL_RECOVERY_VERIFY=PASS"
    )

    print(
        "RECOVERY_SEQUENCE_STATE=1|TRUE"
    )

    print(
        "SEQUENCE_VALUE_1_CONSUMED=YES"
    )

    print(
        "EXPLICIT_ID_INSERT_REQUIRES="
        "OVERRIDING_SYSTEM_VALUE"
    )

    print(
        "READY_FOR_CORRECTED_MUTATION_DESIGN=YES"
    )


if __name__ == "__main__":
    main()
RECOVERY_APP_EOF_TASK003

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh" <<'RECOVERY_VERIFY_EOF_TASK003'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

FAILED_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation.20261010t141014z.2485209"
RECOVERY_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-recovery.20261010t141250z.2486206"

APP="$ROOT/apps/task003/verify_visit_id_allocation_recovery.py"

AMENDMENT="$ROOT/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json"

RECOVERY="$RECOVERY_REPORT/run-state.json"

FAILED_SQL="$FAILED_REPORT/allocation.sql"
FAILED_INTENT="$FAILED_REPORT/mutation-intent.json"
FAILED_OUTPUT="$FAILED_REPORT/psql-output.txt"

IDENTITY_STATE="$RECOVERY_REPORT/identity-state.txt"
DB_STATE="$RECOVERY_REPORT/database-state.txt"
MAP_READBACK="$RECOVERY_REPORT/map-readback.tsv"

OUTDIR="$ROOT/runtime/reports/task003/step06/allocation-recovery-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4B-R1 CANONICAL RECOVERY VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4B_R1_CANONICAL_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4B-R1 CANONICAL RECOVERY VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$AMENDMENT" \
  "$RECOVERY" \
  "$FAILED_SQL" \
  "$FAILED_INTENT" \
  "$FAILED_OUTPUT" \
  "$IDENTITY_STATE" \
  "$DB_STATE" \
  "$MAP_READBACK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing recovery gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --amendment "$AMENDMENT" \
  --recovery "$RECOVERY" \
  --failed-sql "$FAILED_SQL" \
  --failed-intent "$FAILED_INTENT" \
  --failed-output "$FAILED_OUTPUT" \
  --identity-state "$IDENTITY_STATE" \
  --db-state "$DB_STATE" \
  --map-readback "$MAP_READBACK" \
  --output "$OUTPUT"

python3 - "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path


state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert (
    state["status"]
    == "VISIT_ID_ALLOCATION_RECOVERY_CANONICAL_GATE_PASS"
)

assert state["committed_visit_map_rows"] == 0
assert state["sequence_last_value"] == 1
assert state["sequence_is_called"] is True
assert state["sequence_value_1_consumed"] is True

assert state["predicted_next_sequence_value"] == 2
assert state["predicted_next_value_authoritative"] is False

assert state["identity_generation"] == "ALWAYS"

assert (
    state["explicit_id_insert_requirement"]
    == "OVERRIDING SYSTEM VALUE"
)

assert state["old_b4b_rerun_allowed"] is False
assert state["setval_backward_allowed"] is False

assert (
    state["ready_for_corrected_mutation_design"]
    is True
)

print("STEP06B4B_R1_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4B_R1_RECOVERY_CANONICAL_GATE=PASS'

echo 'COMMITTED_VISIT_MAP_ROWS=0'

echo 'SEQUENCE_LAST_VALUE=1'
echo 'SEQUENCE_IS_CALLED=TRUE'
echo 'SEQUENCE_VALUE_1_CONSUMED=YES'

echo 'PREDICTED_NEXT_SEQUENCE_VALUE=2'
echo 'PREDICTED_NEXT_VALUE_AUTHORITATIVE=NO'

echo 'IDENTITY_GENERATION=ALWAYS'
echo 'CORRECTED_INSERT_REQUIRES_OVERRIDING_SYSTEM_VALUE=YES'

echo 'OLD_B4B_RERUN_ALLOWED=NO'
echo 'SETVAL_BACKWARD_ALLOWED=NO'

echo 'READY_FOR_CORRECTED_MUTATION_DESIGN=YES'
RECOVERY_VERIFY_EOF_TASK003

mkdir -p "$STAGE/spark/contracts/processed"
cat > "$STAGE/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json" <<'RECOVERY_AMENDMENT_EOF_TASK003'
{
  "amends": {
    "mutation_contract": "spark/contracts/processed/visit-id-mutation-contract-v1.json",
    "reason": "The original pre-mutation discovery checked column_default but did not inspect PostgreSQL identity metadata. visit_occurrence_id is GENERATED ALWAYS AS IDENTITY."
  },
  "corrected_mutation_requirements": {
    "explicit_identity_insert": {
      "required_clause": "OVERRIDING SYSTEM VALUE",
      "visit_occurrence_id_is_identity": true,
      "identity_generation": "ALWAYS"
    },
    "fresh_locked_revalidation_required": true,
    "old_b4b_rerun_allowed": false,
    "sequence_gap_policy": "ACCEPT_GAPS_NEVER_REWIND",
    "setval_backward_allowed": false
  },
  "failed_attempt": {
    "allocation_sql_sha256": "46ba2f9f1ffad0fbbe1415f27122c04c23b2422c34e93ab836dcdf87e00570f6",
    "failure_class": "GENERATED_ALWAYS_IDENTITY_OVERRIDE_REQUIRED",
    "mutation_intent_sha256": "e089d6a7d4adb00f2af4095715f926141611dd2315d9f4b8b3a99a9b5136b664",
    "psql_output_sha256": "bea7b2bbaa61de00accbc6f181782f257c6fe846d618c747b6790514b600c997"
  },
  "git_checkpoint": "a4d4381dfa6541b10f8e22dd01cb3b8f50ab0a62",
  "identity": {
    "column": "etl.visit_occurrence_id_map.visit_occurrence_id",
    "dependency_type": "i",
    "identity_cycle": false,
    "identity_generation": "ALWAYS",
    "identity_increment": 1,
    "identity_start": 1,
    "is_identity": true,
    "ordinary_column_default": null,
    "sequence": "etl.visit_occurrence_id_map_visit_occurrence_id_seq"
  },
  "recovery_baseline": {
    "candidate_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
    "cdm_visit_rows": 0,
    "committed_visit_map_rows": 0,
    "person_map_rows": 113,
    "predicted_next_sequence_value": 2,
    "predicted_next_value_authoritative": false,
    "sequence_is_called": true,
    "sequence_last_value": 1,
    "sequence_value_1_consumed": true
  },
  "recovery_state_sha256": "c34f6682f5a4482f1ef33f8a085463c4714fe858cd72c14bc03d75be3608dcc2",
  "status": "VISIT_ID_ALLOCATION_RECOVERY_AMENDMENT_READY",
  "step": "STEP-06B4B-R1",
  "task": "TASK-003",
  "version": "v1"
}
RECOVERY_AMENDMENT_EOF_TASK003

mkdir -p "$STAGE/tests/task003"
cat > "$STAGE/tests/task003/test_visit_id_allocation_recovery.py" <<'RECOVERY_TEST_EOF_TASK003'
#!/usr/bin/env python3

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]

MODULE = (
    ROOT
    / "apps/task003/verify_visit_id_allocation_recovery.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_visit_id_allocation_recovery",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class VisitIDAllocationRecoveryTests(
    unittest.TestCase
):

    def test_require(self):
        module.require(
            True,
            "ok",
        )

        with self.assertRaises(
            RuntimeError
        ):
            module.require(
                False,
                "expected",
            )

    def test_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"

            path.write_bytes(
                b"abc"
            )

            self.assertEqual(
                module.sha(path),
                hashlib.sha256(
                    b"abc"
                ).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
RECOVERY_TEST_EOF_TASK003

mkdir -p "$STAGE/docs/task003"
cat > "$STAGE/docs/task003/TASK003-STEP06B4B-R1-Allocation-Recovery.md" <<'RECOVERY_DOC_EOF_TASK003'
# TASK-003 STEP06B4B-R1 — Failed Visit ID Allocation Recovery

## Failure

The first Visit ID allocation transaction crossed the sequence boundary but
failed on the first persistent INSERT.

PostgreSQL rejected the explicit value because:

`etl.visit_occurrence_id_map.visit_occurrence_id`

is:

`GENERATED ALWAYS AS IDENTITY`

The explicit INSERT therefore requires:

`OVERRIDING SYSTEM VALUE`

## Important discovery correction

The earlier pre-mutation inspection observed:

`column_default = NONE`

That fact is not sufficient to conclude that the column has no automatic
generation semantics.

The recovery inspection proved:

- `is_identity = YES`
- `identity_generation = ALWAYS`
- identity start = 1
- identity increment = 1
- identity cycle = NO
- sequence dependency type = `i`
- identity sequence =
  `etl.visit_occurrence_id_map_visit_occurrence_id_seq`

Future database-contract discovery must inspect identity metadata in addition
to `column_default`.

## Failure result

The first sequence allocation returned ID 1.

The subsequent INSERT failed.

The transaction rolled back, therefore:

- committed Visit ID map rows = 0
- CDM Visit rows = 0
- Person map rows = 113

PostgreSQL sequence advancement is not rolled back.

Recovery baseline:

- sequence last_value = 1
- sequence is_called = true
- ID 1 is consumed
- ID 1 is an accepted sequence gap
- predicted next value = 2

The predicted next value is not authoritative until a fresh locked
revalidation immediately before corrected mutation.

## Retry policy

The original STEP06B4B command must never be rerun.

Backward `setval()` is forbidden.

The corrected allocation transaction must:

1. acquire the same advisory lock
2. acquire the same table locks
3. revalidate map/CDM/Person state
4. verify identity metadata remains GENERATED ALWAYS
5. verify sequence baseline is still `1|true`
6. COPY the same frozen 5799-key snapshot
7. revalidate the business-key fingerprint
8. perform final sequence-state verification
9. cross a new irreversible boundary
10. allocate sequence values
11. INSERT explicit identity values using
   `OVERRIDING SYSTEM VALUE`
12. verify transaction state
13. commit
14. independently read back the committed mapping

With no other sequence consumer, the predicted allocation range is `2..5800`.
That range remains non-authoritative until the corrected transaction commits.
RECOVERY_DOC_EOF_TASK003


install_one() {
  rel="$1"
  src="$STAGE/$rel"
  dst="$ROOT/$rel"

  mkdir -p "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "UNCHANGED=$rel"
      return
    fi

    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi

  mode=0644

  case "$rel" in
    *.sh|*.py)
      mode=0755
      ;;
  esac

  install -m "$mode" "$src" "$dst"

  echo "INSTALLED=$rel"
}

install_one scripts/task003/06b4b-r1-reconcile-failed-visit-id-allocation.sh
install_one apps/task003/verify_visit_id_allocation_recovery.py
install_one scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh
install_one spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json
install_one tests/task003/test_visit_id_allocation_recovery.py
install_one docs/task003/TASK003-STEP06B4B-R1-Allocation-Recovery.md

python3 -m py_compile \
  "$ROOT/apps/task003/verify_visit_id_allocation_recovery.py" \
  "$ROOT/tests/task003/test_visit_id_allocation_recovery.py"

python3 -m json.tool \
  "$ROOT/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json" \
  >/dev/null

bash -n \
  "$ROOT/scripts/task003/06b4b-r1-reconcile-failed-visit-id-allocation.sh"

bash -n \
  "$ROOT/scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh"

echo 'STEP06B4B_R1_CANONICAL_SOURCE_PREPARED=PASS'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'
echo 'GIT_COMMIT=NO'
