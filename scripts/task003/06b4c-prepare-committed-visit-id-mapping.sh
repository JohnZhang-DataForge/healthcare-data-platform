#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06b4c-generator.XXXXXX)"

echo '#### TASK003 STEP06B4C PREPARE COMMITTED VISIT ID MAPPING OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06B4C_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4C PREPARE COMMITTED VISIT ID MAPPING OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4b-r2-corrected-visit-id-allocation.sh" <<'R2_RUNNER_EOF_TASK003_06B4C'
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

EXPECTED_HEAD=d2bddab5ffee00df0f42db8273379b89364be115

RUN_ID=visit-proc-20261009t192437z-2081886

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e
EXPECTED_RECOVERY_SHA=c34f6682f5a4482f1ef33f8a085463c4714fe858cd72c14bc03d75be3608dcc2
EXPECTED_FAILED_SQL_SHA=46ba2f9f1ffad0fbbe1415f27122c04c23b2422c34e93ab836dcdf87e00570f6

ADVISORY_LOCK_KEY=5947676943154735385

SEQUENCE=etl.visit_occurrence_id_map_visit_occurrence_id_seq

FAILED_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation.20261010t141014z.2485209"
FAILED_SQL="$FAILED_REPORT/allocation.sql"

RECOVERY_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-recovery.20261010t141250z.2486206"
RECOVERY_STATE="$RECOVERY_REPORT/run-state.json"

AMENDMENT="$ROOT/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json"

SNAPSHOT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID/business-keys.tsv"

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-corrected.${STAMP}.$$"

SQL_FILE="$REPORT/allocation-corrected.sql"
MUTATION_INTENT="$REPORT/mutation-intent.json"
PRECHECK="$REPORT/pre-execution-database-state.txt"
PSQL_OUT="$REPORT/psql-output.txt"
TX_SUMMARY="$REPORT/transaction-summary.json"

POST_DB="$REPORT/post-commit-database-state.txt"
POST_MAP="$REPORT/post-commit-map.tsv"
POST_VERIFY="$REPORT/post-commit-verification.json"
RUN_STATE="$REPORT/run-state.json"

RECOVERY_DB="$REPORT/recovery-database-state.txt"
RECOVERY_MAP="$REPORT/recovery-map.tsv"

MUTATION_PHASE=PRE_EXECUTION

echo '#### TASK003 STEP06B4B-R2 CORRECTED VISIT ID ALLOCATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4B_R2_PHASE=$MUTATION_PHASE"

  if [[ "$rc" -ne 0 ]]; then
    case "$MUTATION_PHASE" in
      EXECUTING_TRANSACTION)
        echo 'CORRECTED_MUTATION_STATUS=UNCERTAIN'
        echo 'SEQUENCE_MAY_HAVE_ADVANCED=YES'
        echo 'BLIND_RETRY_ALLOWED=NO'
        echo 'SETVAL_BACKWARD_ALLOWED=NO'
        ;;
      COMMIT_CONFIRMED|POST_COMMIT_VERIFY)
        echo 'CORRECTED_MUTATION_COMMITTED_OR_LIKELY_COMMITTED=YES'
        echo 'BLIND_RETRY_ALLOWED=NO'
        echo 'DO_NOT_RERUN_R2=YES'
        ;;
    esac
  fi

  echo "STEP06B4B_R2_REPORT=$REPORT"
  echo "STEP06B4B_R2_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06B4B-R2 CORRECTED VISIT ID ALLOCATION OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

reconcile_after_uncertain_execution() {
  echo '=== RECOVERY: independent READ ONLY reconciliation ==='

  set +e

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
    > "$RECOVERY_DB" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    count(*),
    count(DISTINCT visit_occurrence_id),
    COALESCE(min(visit_occurrence_id), 0),
    COALESCE(max(visit_occurrence_id), 0)
FROM etl.visit_occurrence_id_map;

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

SELECT count(*)
FROM cdm.visit_occurrence c
JOIN etl.visit_occurrence_id_map m
  ON m.visit_occurrence_id = c.visit_occurrence_id;

ROLLBACK;
SQL

  RECOVERY_DB_RC=$?

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
    > "$RECOVERY_MAP" <<'SQL'
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

  RECOVERY_MAP_RC=$?

  set -e

  if [[ "$RECOVERY_DB_RC" -eq 0 ]]; then
    cat "$RECOVERY_DB"
  else
    echo "RECOVERY_DATABASE_QUERY_EXIT_CODE=$RECOVERY_DB_RC"
  fi

  echo "RECOVERY_MAP_QUERY_EXIT_CODE=$RECOVERY_MAP_RC"
  echo 'RECOVERY_READBACK_ATTEMPTED=YES'
  echo 'BLIND_RETRY_ALLOWED=NO'
}

echo '=== 1. Verify recovery Git checkpoint ==='

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
  echo 'ERROR: local HEAD is not frozen recovery checkpoint'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main is not frozen recovery checkpoint'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: working tree is not clean'
  git status --short
  exit 1
}

echo 'RECOVERY_GIT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Re-run canonical recovery gate ==='

bash \
  scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh

echo 'CANONICAL_RECOVERY_GATE=PASS'

echo '=== 3. Verify immutable recovery inputs ==='

for file in \
  "$FAILED_SQL" \
  "$RECOVERY_STATE" \
  "$AMENDMENT" \
  "$SNAPSHOT"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe R2 input: $file"
    exit 1
  }
done

FAILED_SQL_SHA="$(
  sha256sum "$FAILED_SQL" |
  awk '{print $1}'
)"

RECOVERY_SHA="$(
  sha256sum "$RECOVERY_STATE" |
  awk '{print $1}'
)"

SNAPSHOT_SHA="$(
  sha256sum "$SNAPSHOT" |
  awk '{print $1}'
)"

AMENDMENT_SHA="$(
  sha256sum "$AMENDMENT" |
  awk '{print $1}'
)"

echo "FAILED_ALLOCATION_SQL_SHA256=$FAILED_SQL_SHA"
echo "RECOVERY_STATE_SHA256=$RECOVERY_SHA"
echo "RECOVERY_AMENDMENT_SHA256=$AMENDMENT_SHA"
echo "BUSINESS_KEY_SNAPSHOT_SHA256=$SNAPSHOT_SHA"

[[ "$FAILED_SQL_SHA" == "$EXPECTED_FAILED_SQL_SHA" ]] || {
  echo 'ERROR: failed SQL lineage mismatch'
  exit 1
}

[[ "$RECOVERY_SHA" == "$EXPECTED_RECOVERY_SHA" ]] || {
  echo 'ERROR: recovery-state lineage mismatch'
  exit 1
}

[[ "$SNAPSHOT_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: business-key snapshot mismatch'
  exit 1
}

python3 - \
  "$RECOVERY_STATE" \
  "$AMENDMENT" \
  <<'PY_INPUT'
import json
import sys
from pathlib import Path


recovery = json.loads(
    Path(sys.argv[1]).read_bytes()
)

amendment = json.loads(
    Path(sys.argv[2]).read_bytes()
)

assert recovery["status"] == "FAILED_ALLOCATION_RECONCILED"

assert recovery["committed_visit_map_rows"] == 0
assert recovery["sequence_last_value"] == 1
assert recovery["sequence_is_called"] is True
assert recovery["sequence_value_1_consumed"] is True

assert recovery["old_b4b_rerun_allowed"] is False
assert recovery["setval_backward_allowed"] is False

assert amendment["status"] == "VISIT_ID_ALLOCATION_RECOVERY_AMENDMENT_READY"

identity = amendment["identity"]

assert identity["is_identity"] is True
assert identity["identity_generation"] == "ALWAYS"

assert (
    identity["sequence"]
    == "etl.visit_occurrence_id_map_visit_occurrence_id_seq"
)

correction = amendment[
    "corrected_mutation_requirements"
]

assert (
    correction[
        "explicit_identity_insert"
    ][
        "required_clause"
    ]
    == "OVERRIDING SYSTEM VALUE"
)

assert (
    correction[
        "fresh_locked_revalidation_required"
    ]
    is True
)

print("RECOVERY_INPUT_GATE=PASS")
print("R2_REQUIRED_SEQUENCE_BASELINE=1|TRUE")
print("R2_REQUIRED_IDENTITY_GENERATION=ALWAYS")
print("R2_REQUIRED_OVERRIDE=OVERRIDING_SYSTEM_VALUE")
PY_INPUT

echo '=== 4. Fresh independent pre-execution DB reconciliation ==='

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
  > "$PRECHECK" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

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

SELECT COALESCE(
    pg_get_serial_sequence(
        'etl.visit_occurrence_id_map',
        'visit_occurrence_id'
    ),
    'NONE'
);

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$PRECHECK"

python3 - \
  "$PRECHECK" \
  "$SEQUENCE" \
  <<'PY_PRECHECK'
import sys
from pathlib import Path


rows = [
    line.strip()
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        "BEGIN",
        "SET",
        "ROLLBACK",
    }
]

sequence = sys.argv[2]

assert rows == [
    "0|0|113",
    "1|t",
    "YES|ALWAYS|1|1|NO|NONE",
    sequence,
    "on",
], rows

print("FRESH_R2_DATABASE_BASELINE=PASS")
print("VISIT_MAP_ROWS_BEFORE_R2=0")
print("SEQUENCE_STATE_BEFORE_R2=1|TRUE")
print("IDENTITY_GENERATION_BEFORE_R2=ALWAYS")
PY_PRECHECK

echo '=== 5. Derive corrected SQL from immutable failed SQL ==='

python3 - \
  "$FAILED_SQL" \
  "$SQL_FILE" \
  "$EXPECTED_FAILED_SQL_SHA" \
  <<'PY_PATCH'
import hashlib
import sys
from pathlib import Path


source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
expected_sha = sys.argv[3]

source_bytes = source_path.read_bytes()

assert hashlib.sha256(
    source_bytes
).hexdigest() == expected_sha

source = source_bytes.decode("utf-8")


# Recovery baseline changed from 1|false to 1|true.
old_seq_gate = (
    "IF v_seq_last <> 1 OR v_seq_called THEN"
)

new_seq_gate = (
    "IF v_seq_last <> 1 OR NOT v_seq_called THEN"
)

assert source.count(old_seq_gate) == 3

source = source.replace(
    old_seq_gate,
    new_seq_gate,
)


# Explicit identity values require PostgreSQL identity override.
old_insert = """        INSERT INTO etl.visit_occurrence_id_map (
            visit_occurrence_id,
            source_system,
            source_encounter_id
        )
        VALUES (
"""

new_insert = """        INSERT INTO etl.visit_occurrence_id_map (
            visit_occurrence_id,
            source_system,
            source_encounter_id
        )
        OVERRIDING SYSTEM VALUE
        VALUES (
"""

assert source.count(old_insert) == 1

source = source.replace(
    old_insert,
    new_insert,
    1,
)


# Add a locked identity-metadata gate before Candidate COPY.
marker = (
    "\\echo PRE_COPY_DATABASE_REVALIDATION_PASS\n"
)

assert source.count(marker) == 1

identity_gate = marker + r'''
\echo IDENTITY_METADATA_REVALIDATION

DO $do$
DECLARE
    v_is_identity text;
    v_identity_generation text;
    v_identity_start text;
    v_identity_increment text;
    v_identity_cycle text;
    v_column_default text;
    v_serial_sequence text;
BEGIN
    SELECT
        is_identity,
        identity_generation,
        identity_start,
        identity_increment,
        identity_cycle,
        column_default
    INTO
        v_is_identity,
        v_identity_generation,
        v_identity_start,
        v_identity_increment,
        v_identity_cycle,
        v_column_default
    FROM information_schema.columns
    WHERE table_schema = 'etl'
      AND table_name = 'visit_occurrence_id_map'
      AND column_name = 'visit_occurrence_id';

    SELECT pg_get_serial_sequence(
        'etl.visit_occurrence_id_map',
        'visit_occurrence_id'
    )
    INTO v_serial_sequence;

    IF v_is_identity <> 'YES' THEN
        RAISE EXCEPTION
            'visit_occurrence_id is no longer identity: %',
            v_is_identity;
    END IF;

    IF v_identity_generation <> 'ALWAYS' THEN
        RAISE EXCEPTION
            'identity generation changed: %',
            v_identity_generation;
    END IF;

    IF v_identity_start <> '1' THEN
        RAISE EXCEPTION
            'identity start changed: %',
            v_identity_start;
    END IF;

    IF v_identity_increment <> '1' THEN
        RAISE EXCEPTION
            'identity increment changed: %',
            v_identity_increment;
    END IF;

    IF v_identity_cycle <> 'NO' THEN
        RAISE EXCEPTION
            'identity cycle changed: %',
            v_identity_cycle;
    END IF;

    IF v_column_default IS NOT NULL THEN
        RAISE EXCEPTION
            'ordinary column default unexpectedly present: %',
            v_column_default;
    END IF;

    IF v_serial_sequence <> 'etl.visit_occurrence_id_map_visit_occurrence_id_seq' THEN
        RAISE EXCEPTION
            'identity sequence binding changed: %',
            v_serial_sequence;
    END IF;
END
$do$;

\echo IDENTITY_METADATA_REVALIDATION_PASS
'''

source = source.replace(
    marker,
    identity_gate,
    1,
)


# With locked baseline 1|true and exactly 5799 sequence allocations,
# this isolated transaction must produce IDs 2..5800.
post_verify_marker = """    IF v_cdm_rows <> 0 THEN
        RAISE EXCEPTION
            'CDM Visit was modified during ID allocation: %',
            v_cdm_rows;
    END IF;
"""

assert source.count(post_verify_marker) == 1

strong_range_check = """    IF v_min_id <> 2 OR v_max_id <> 5800 THEN
        RAISE EXCEPTION
            'corrected allocation range mismatch: min %, max %',
            v_min_id,
            v_max_id;
    END IF;

    IF v_seq_last <> 5800 THEN
        RAISE EXCEPTION
            'corrected allocation sequence mismatch: %',
            v_seq_last;
    END IF;

""" + post_verify_marker

source = source.replace(
    post_verify_marker,
    strong_range_check,
    1,
)


# Make R2 markers unique.
replacements = {
    "MUTATION_TRANSACTION_BEGIN":
        "CORRECTED_MUTATION_TRANSACTION_BEGIN",

    "IRREVERSIBLE_BOUNDARY_BEGIN":
        "CORRECTED_IRREVERSIBLE_BOUNDARY_BEGIN",

    "IRREVERSIBLE_BOUNDARY_CROSSED":
        "CORRECTED_IRREVERSIBLE_BOUNDARY_CROSSED",

    "MUTATION_TRANSACTION_SUMMARY":
        "CORRECTED_MUTATION_TRANSACTION_SUMMARY",

    "MUTATION_TRANSACTION_COMMIT_BEGIN":
        "CORRECTED_MUTATION_TRANSACTION_COMMIT_BEGIN",

    "MUTATION_TRANSACTION_COMMIT_COMPLETE":
        "CORRECTED_MUTATION_TRANSACTION_COMMIT_COMPLETE",
}

for old, new in replacements.items():
    assert old in source
    source = source.replace(
        old,
        new,
    )


target_path.write_text(
    source
)

print("CORRECTED_SQL_DERIVATION=PASS")
PY_PATCH

chmod 0444 "$SQL_FILE"

CORRECTED_SQL_SHA="$(
  sha256sum "$SQL_FILE" |
  awk '{print $1}'
)"

echo "CORRECTED_ALLOCATION_SQL_SHA256=$CORRECTED_SQL_SHA"

echo '=== 6. Static proof of corrected mutation SQL ==='

python3 - "$SQL_FILE" <<'PY_STATIC'
import re
import sys
from pathlib import Path


source = Path(sys.argv[1]).read_text()


assert len(
    re.findall(
        r"\bnextval\s*\(",
        source,
        re.IGNORECASE,
    )
) == 1


assert not re.search(
    r"\bsetval\s*\(",
    source,
    re.IGNORECASE,
)


assert source.count(
    "OVERRIDING SYSTEM VALUE"
) == 1


assert source.count(
    "IF v_seq_last <> 1 OR NOT v_seq_called THEN"
) == 3


assert (
    "IDENTITY_METADATA_REVALIDATION_PASS"
    in source
)

assert (
    "v_identity_generation <> 'ALWAYS'"
    in source
)

assert (
    "v_min_id <> 2 OR v_max_id <> 5800"
    in source
)

assert (
    "v_seq_last <> 5800"
    in source
)


assert len(
    re.findall(
        r"\bINSERT\s+INTO\s+etl\.visit_occurrence_id_map\b",
        source,
        re.IGNORECASE,
    )
) == 1


assert not re.search(
    r"\bINSERT\s+INTO\s+cdm\.",
    source,
    re.IGNORECASE,
)


assert not re.search(
    r"\bON\s+CONFLICT\b",
    source,
    re.IGNORECASE,
)


boundary = source.index(
    "CORRECTED_IRREVERSIBLE_BOUNDARY_BEGIN"
)

allocation = re.search(
    r"\bnextval\s*\(",
    source,
    re.IGNORECASE,
).start()

commit = re.search(
    r"^\s*COMMIT\s*;",
    source,
    re.IGNORECASE | re.MULTILINE,
).start()

assert boundary < allocation < commit


print("R2_STATIC_MUTATION_SQL=PASS")
print("SEQUENCE_ALLOCATION_EXPRESSION_COUNT=1")
print("SETVAL_CALL=NO")
print("OVERRIDING_SYSTEM_VALUE_COUNT=1")
print("RECOVERY_SEQUENCE_BASELINE_GATES=3")
print("IDENTITY_METADATA_GATE=YES")
print("EXPECTED_TRANSACTION_RANGE=2..5800")
print("CDM_DML=NO")
print("ON_CONFLICT=NO")
print("BOUNDARY_ORDERING=PASS")
PY_STATIC

echo '=== 7. Record immutable corrected mutation intent ==='

python3 - \
  "$MUTATION_INTENT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  "$EXPECTED_RECOVERY_SHA" \
  "$EXPECTED_FAILED_SQL_SHA" \
  "$CORRECTED_SQL_SHA" \
  "$AMENDMENT_SHA" \
  "$ADVISORY_LOCK_KEY" \
  <<'PY_INTENT'
import json
import sys
from pathlib import Path


state = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B4B-R2",

    "status":
        "CORRECTED_VISIT_ID_ALLOCATION_READY_TO_EXECUTE",

    "git_checkpoint":
        sys.argv[2],

    "candidate_business_key_sha256":
        sys.argv[3],

    "recovery_state_sha256":
        sys.argv[4],

    "failed_allocation_sql_sha256":
        sys.argv[5],

    "corrected_allocation_sql_sha256":
        sys.argv[6],

    "recovery_amendment_sha256":
        sys.argv[7],

    "advisory_lock_key":
        int(sys.argv[8]),

    "required_sequence_baseline": {
        "last_value":
            1,

        "is_called":
            True
    },

    "identity_generation":
        "ALWAYS",

    "explicit_identity_insert":
        "OVERRIDING SYSTEM VALUE",

    "candidate_rows":
        5799,

    "predicted_visit_id_range": [
        2,
        5800
    ],

    "predicted_range_authoritative":
        False,

    "sequence_gap_policy":
        "ACCEPT_GAPS_NEVER_REWIND",

    "sequence_value_1_consumed":
        True,

    "setval_backward_allowed":
        False,

    "blind_retry_allowed":
        False,

    "cdm_visit_occurrence_write":
        False,

    "execution_started":
        False,
}


Path(sys.argv[1]).write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print("CORRECTED_MUTATION_INTENT_RECORDED=PASS")
PY_INTENT

chmod 0444 "$MUTATION_INTENT"

echo '=== 8. Execute corrected REAL allocation transaction ==='

echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
echo 'CORRECTED REAL VISIT ID MUTATION IS STARTING'
echo 'Expected locked baseline: map=0, sequence=1|true'
echo 'Expected transaction allocation range: 2..5800'
echo 'If execution fails, DO NOT rerun R2.'
echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'

MUTATION_PHASE=EXECUTING_TRANSACTION

set +e

kubectl -n "$NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -f - \
  < "$SQL_FILE" \
  > "$PSQL_OUT" \
  2>&1

PSQL_RC=$?

set -e

cat "$PSQL_OUT"

echo "CORRECTED_MUTATION_PSQL_EXIT_CODE=$PSQL_RC"

if [[ "$PSQL_RC" -ne 0 ]]; then
  echo 'ERROR: corrected allocation transaction returned non-zero'
  echo 'AUTOMATIC_RETRY=DISABLED'

  if grep -Fx \
    'CORRECTED_IRREVERSIBLE_BOUNDARY_BEGIN' \
    "$PSQL_OUT" \
    >/dev/null
  then
    echo 'CORRECTED_IRREVERSIBLE_BOUNDARY_MARKER_OBSERVED=YES'
  else
    echo 'CORRECTED_IRREVERSIBLE_BOUNDARY_MARKER_OBSERVED=NO'
  fi

  reconcile_after_uncertain_execution

  exit 1
fi

echo '=== 9. Confirm corrected commit markers ==='

for marker in \
  CORRECTED_IRREVERSIBLE_BOUNDARY_BEGIN \
  CORRECTED_IRREVERSIBLE_BOUNDARY_CROSSED \
  TRANSACTION_INTERNAL_POST_ALLOCATION_VERIFY_PASS \
  CORRECTED_MUTATION_TRANSACTION_COMMIT_BEGIN \
  CORRECTED_MUTATION_TRANSACTION_COMMIT_COMPLETE
do
  grep -Fx \
    "$marker" \
    "$PSQL_OUT" \
    >/dev/null
done

MUTATION_PHASE=COMMIT_CONFIRMED

echo 'CORRECTED_IRREVERSIBLE_BOUNDARY_CROSSED=YES'
echo 'TRANSACTION_INTERNAL_POST_ALLOCATION_VERIFY=PASS'
echo 'CORRECTED_COMMIT_CONFIRMED_BY_PSQL=YES'

echo '=== 10. Parse committed transaction summary ==='

set +e

python3 - \
  "$PSQL_OUT" \
  "$TX_SUMMARY" \
  <<'PY_TX'
import json
import re
import sys
from pathlib import Path


text = Path(sys.argv[1]).read_text()

matches = re.findall(
    r"^(\d+)\|(\d+)\|(\d+)\|([0-9a-f]{64})\|(\d+)\|([tf])\|(\d+)$",
    text,
    re.MULTILINE,
)

assert len(matches) == 1, matches

(
    map_rows,
    min_id,
    max_id,
    mapping_sha,
    seq_last,
    seq_called,
    cdm_rows,
) = matches[0]

state = {
    "map_rows":
        int(map_rows),

    "min_visit_occurrence_id":
        int(min_id),

    "max_visit_occurrence_id":
        int(max_id),

    "mapping_sha256":
        mapping_sha,

    "sequence_last_value":
        int(seq_last),

    "sequence_is_called":
        seq_called == "t",

    "cdm_visit_rows":
        int(cdm_rows),
}

assert state["map_rows"] == 5799

assert (
    state["min_visit_occurrence_id"]
    == 2
)

assert (
    state["max_visit_occurrence_id"]
    == 5800
)

assert (
    state["sequence_last_value"]
    == 5800
)

assert state["sequence_is_called"] is True
assert state["cdm_visit_rows"] == 0

Path(sys.argv[2]).write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print("CORRECTED_TRANSACTION_SUMMARY=PASS")
print("TRANSACTION_MAP_ROWS=5799")
print("TRANSACTION_VISIT_ID_RANGE=2..5800")
print(
    "TRANSACTION_MAPPING_SHA256="
    + state["mapping_sha256"]
)
print("TRANSACTION_SEQUENCE_LAST_VALUE=5800")
print("TRANSACTION_SEQUENCE_IS_CALLED=TRUE")
PY_TX

TX_PARSE_RC=$?

set -e

if [[ "$TX_PARSE_RC" -ne 0 ]]; then
  echo 'ERROR: transaction committed but summary verification failed'
  echo 'DO_NOT_RERUN_R2=YES'

  reconcile_after_uncertain_execution

  exit 1
fi

echo '=== 11. Independent post-commit database verification ==='

MUTATION_PHASE=POST_COMMIT_VERIFY

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
  > "$POST_DB" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    count(DISTINCT visit_occurrence_id),
    min(visit_occurrence_id),
    max(visit_occurrence_id),
    count(*) FILTER (
        WHERE visit_occurrence_id <= 0
    )
FROM etl.visit_occurrence_id_map;

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

SELECT count(*)
FROM cdm.visit_occurrence c
JOIN etl.visit_occurrence_id_map m
  ON m.visit_occurrence_id = c.visit_occurrence_id;

SELECT
    is_identity,
    COALESCE(identity_generation, 'NONE')
FROM information_schema.columns
WHERE table_schema = 'etl'
  AND table_name = 'visit_occurrence_id_map'
  AND column_name = 'visit_occurrence_id';

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$POST_DB"

echo '=== 12. Capture exact committed mapping independently ==='

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
  > "$POST_MAP" <<'SQL'
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

echo 'POST_COMMIT_MAPPING_READBACK_CAPTURED=YES'

echo '=== 13. Independently verify authoritative mapping ==='

python3 - \
  "$POST_DB" \
  "$POST_MAP" \
  "$SNAPSHOT" \
  "$TX_SUMMARY" \
  "$POST_VERIFY" \
  <<'PY_POST'
import hashlib
import json
import sys
from pathlib import Path


db_path = Path(sys.argv[1])
map_path = Path(sys.argv[2])
snapshot_path = Path(sys.argv[3])
tx_path = Path(sys.argv[4])
output_path = Path(sys.argv[5])


db_rows = [
    line.strip()
    for line in db_path.read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        "BEGIN",
        "SET",
        "ROLLBACK",
    }
]

assert len(db_rows) == 7, db_rows

counts = db_rows[0].split("|")
sequence = db_rows[1].split("|")
ids = db_rows[2].split("|")
collisions = db_rows[3].split("|")
cdm_overlap = db_rows[4]
identity = db_rows[5].split("|")
readonly = db_rows[6]

assert counts == [
    "5799",
    "0",
    "113",
]

assert sequence[1] == "t"

sequence_last = int(
    sequence[0]
)

assert sequence_last >= 5800

assert ids == [
    "5799",
    "2",
    "5800",
    "0",
], ids

assert collisions == [
    "0",
    "0",
]

assert cdm_overlap == "0"

assert identity == [
    "YES",
    "ALWAYS",
]

assert readonly == "on"


snapshot_lines = (
    snapshot_path
    .read_text()
    .splitlines()
)

assert len(snapshot_lines) == 5799


map_lines = [
    line
    for line in map_path.read_text().splitlines()
    if line
    and line not in {
        "BEGIN",
        "SET",
        "ROLLBACK",
    }
]

assert len(map_lines) == 5799


mapping = []

for line in map_lines:
    fields = line.split(
        "\t"
    )

    assert len(fields) == 3

    mapping.append(
        (
            fields[0],
            fields[1],
            int(fields[2]),
        )
    )


candidate_lines = [
    source_system
    + "\t"
    + encounter_id
    for (
        source_system,
        encounter_id,
        visit_id
    )
    in mapping
]

assert candidate_lines == snapshot_lines


visit_ids = [
    visit_id
    for (
        source_system,
        encounter_id,
        visit_id
    )
    in mapping
]

assert visit_ids == list(
    range(
        2,
        5801,
    )
)


payload = "".join(
    source_system
    + "\t"
    + encounter_id
    + "\t"
    + str(visit_id)
    + "\n"
    for (
        source_system,
        encounter_id,
        visit_id
    )
    in mapping
).encode(
    "utf-8"
)

mapping_sha = hashlib.sha256(
    payload
).hexdigest()


tx = json.loads(
    tx_path.read_bytes()
)

assert tx["map_rows"] == 5799

assert (
    tx["min_visit_occurrence_id"]
    == 2
)

assert (
    tx["max_visit_occurrence_id"]
    == 5800
)

assert (
    tx["sequence_last_value"]
    == 5800
)

assert (
    tx["mapping_sha256"]
    == mapping_sha
)


state = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B4B-R2",

    "status":
        "CORRECTED_VISIT_ID_ALLOCATION_POST_COMMIT_VERIFIED",

    "committed_map_rows":
        5799,

    "candidate_coverage":
        5799,

    "unique_business_keys":
        5799,

    "unique_visit_occurrence_ids":
        5799,

    "min_visit_occurrence_id":
        2,

    "max_visit_occurrence_id":
        5800,

    "mapping_sha256":
        mapping_sha,

    "sequence_last_value":
        sequence_last,

    "sequence_is_called":
        True,

    "sequence_value_1_consumed_gap":
        True,

    "visit_ids_contiguous_2_through_5800":
        True,

    "identity_generation":
        "ALWAYS",

    "explicit_insert_used_overriding_system_value":
        True,

    "business_key_collisions":
        0,

    "visit_id_collisions":
        0,

    "cdm_visit_rows":
        0,

    "cdm_map_overlap":
        0,

    "readback_transaction_read_only":
        True,
}


output_path.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


print("INDEPENDENT_R2_POST_COMMIT_VERIFICATION=PASS")
print("COMMITTED_VISIT_MAP_ROWS=5799")
print("COMMITTED_CANDIDATE_COVERAGE=5799")
print("COMMITTED_UNIQUE_VISIT_IDS=5799")
print("COMMITTED_VISIT_ID_RANGE=2..5800")
print("VISIT_ID_1_GAP_PRESERVED=YES")
print("VISIT_IDS_CONTIGUOUS_2_THROUGH_5800=YES")
print("AUTHORITATIVE_MAPPING_SHA256=" + mapping_sha)
print(
    "POST_COMMIT_SEQUENCE_LAST_VALUE="
    + str(sequence_last)
)
print("POST_COMMIT_SEQUENCE_IS_CALLED=TRUE")
print("IDENTITY_GENERATION=ALWAYS")
print("CDM_VISIT_ROWS_AFTER_ALLOCATION=0")
PY_POST

echo '=== 14. Record authoritative corrected allocation state ==='

python3 - \
  "$RUN_STATE" \
  "$POST_VERIFY" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  "$EXPECTED_RECOVERY_SHA" \
  "$EXPECTED_FAILED_SQL_SHA" \
  "$CORRECTED_SQL_SHA" \
  "$AMENDMENT_SHA" \
  "$PSQL_OUT" \
  "$ADVISORY_LOCK_KEY" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path


post = json.loads(
    Path(sys.argv[2]).read_bytes()
)

psql_sha = hashlib.sha256(
    Path(sys.argv[9]).read_bytes()
).hexdigest()


state = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B4B-R2",

    "status":
        "CORRECTED_VISIT_ID_ALLOCATION_COMMITTED_AND_VERIFIED",

    "git_checkpoint":
        sys.argv[3],

    "candidate_business_key_sha256":
        sys.argv[4],

    "recovery_state_sha256":
        sys.argv[5],

    "failed_allocation_sql_sha256":
        sys.argv[6],

    "corrected_allocation_sql_sha256":
        sys.argv[7],

    "recovery_amendment_sha256":
        sys.argv[8],

    "psql_output_sha256":
        psql_sha,

    "advisory_lock_key":
        int(sys.argv[10]),

    "committed_map_rows":
        5799,

    "committed_unique_visit_occurrence_ids":
        5799,

    "min_visit_occurrence_id":
        2,

    "max_visit_occurrence_id":
        5800,

    "mapping_sha256":
        post["mapping_sha256"],

    "sequence_last_value":
        post["sequence_last_value"],

    "sequence_is_called":
        True,

    "sequence_value_1_consumed_gap":
        True,

    "identity_generation":
        "ALWAYS",

    "explicit_identity_insert":
        "OVERRIDING SYSTEM VALUE",

    "sequence_gap_policy":
        "ACCEPT_GAPS_NEVER_REWIND",

    "irreversible_boundary_crossed":
        True,

    "nextval_called":
        True,

    "setval_called":
        False,

    "visit_id_map_mutated":
        True,

    "transaction_committed":
        True,

    "independent_post_commit_verification":
        True,

    "cdm_visit_occurrence_write":
        False,

    "blind_retry_allowed":
        False,
}


Path(sys.argv[1]).write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


print("STEP06B4B_R2_RUN_STATE=PASS")
print("CORRECTED_PSQL_OUTPUT_SHA256=" + psql_sha)
print(
    "AUTHORITATIVE_MAPPING_SHA256="
    + state["mapping_sha256"]
)
PY_STATE

MUTATION_PHASE=VERIFIED

echo '=== 15. Final STEP06B4B-R2 verdict ==='

MAPPING_SHA="$(
  python3 - "$POST_VERIFY" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    state["mapping_sha256"]
)
PY
)"

SEQ_LAST="$(
  python3 - "$POST_VERIFY" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    state["sequence_last_value"]
)
PY
)"

echo 'STEP06B4B_R2_CORRECTED_VISIT_ID_ALLOCATION=PASS'

echo "STEP06B4B_RECOVERY_GIT_CHECKPOINT=$EXPECTED_HEAD"

echo 'CORRECTED_IRREVERSIBLE_BOUNDARY_CROSSED=YES'
echo 'NEXTVAL_CALLED=YES'
echo 'SETVAL_CALLED=NO'

echo 'IDENTITY_GENERATION=ALWAYS'
echo 'OVERRIDING_SYSTEM_VALUE_USED=YES'

echo 'TRANSACTION_COMMITTED=YES'
echo 'INDEPENDENT_POST_COMMIT_VERIFICATION=PASS'

echo 'COMMITTED_VISIT_MAP_ROWS=5799'
echo 'COMMITTED_CANDIDATE_COVERAGE=5799'
echo 'COMMITTED_UNIQUE_BUSINESS_KEYS=5799'
echo 'COMMITTED_UNIQUE_VISIT_IDS=5799'

echo 'COMMITTED_VISIT_ID_RANGE=2..5800'
echo 'VISIT_ID_1_GAP_PRESERVED=YES'
echo 'VISIT_IDS_CONTIGUOUS_2_THROUGH_5800=YES'

echo "AUTHORITATIVE_MAPPING_SHA256=$MAPPING_SHA"

echo "SEQUENCE_LAST_VALUE_AFTER_R2=$SEQ_LAST"
echo 'SEQUENCE_IS_CALLED_AFTER_R2=TRUE'

echo 'CDM_VISIT_ROWS_AFTER_ALLOCATION=0'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'SEQUENCE_GAP_POLICY=ACCEPT_GAPS_NEVER_REWIND'
echo 'BLIND_RETRY_ALLOWED=NO'

echo 'VISIT_ID_MAP_MUTATED=YES'
echo 'SEQUENCE_ADVANCED=YES'

echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'

echo 'NEXT_REQUIRED_STEP=STEP06B4C_CANONICALIZE_COMMITTED_VISIT_ID_MAPPING'
R2_RUNNER_EOF_TASK003_06B4C

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/verify_committed_visit_id_mapping.py" <<'VERIFY_APP_EOF_TASK003_06B4C'
#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_MAPPING_SHA = (
    "7e74c9c0a179e6222a7c4ded2993b8cf"
    "61a20d9b06b1d6349d7f21f6a0c03c9f"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_SQL_SHA = (
    "4e0f7ba8c81639d601df832781515d1b"
    "2e6084706f9e96f1829ec12a2937bf7e"
)

EXPECTED_PSQL_SHA = (
    "db7add87ae7185dc2127b21230ce7756"
    "e2ec3c11bb80676c023fed0e066c59a3"
)

EXPECTED_RECOVERY_SHA = (
    "c34f6682f5a4482f1ef33f8a085463c4"
    "714fe858cd72c14bc03d75be3608dcc2"
)

EXPECTED_AMENDMENT_SHA = (
    "f3f81af4effadc65e73255837f5cf79f"
    "e74050f2bf3f4685385f360b20a76a03"
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
    contract_path,
    state_path,
    post_verify_path,
    tx_path,
    sql_path,
    psql_path,
    map_path,
):
    contract = load(
        contract_path
    )

    state = load(
        state_path
    )

    post = load(
        post_verify_path
    )

    tx = load(
        tx_path
    )

    require(
        contract["status"]
        == "VISIT_ID_ALLOCATION_COMMITTED_AND_FROZEN",
        "contract status",
    )

    require(
        contract[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "candidate key SHA",
    )

    committed = contract[
        "committed_mapping"
    ]

    require(
        committed["rows"]
        == 5799,
        "mapping rows",
    )

    require(
        committed[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "unique IDs",
    )

    require(
        committed[
            "min_visit_occurrence_id"
        ]
        == 2,
        "min ID",
    )

    require(
        committed[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "max ID",
    )

    require(
        committed[
            "mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "mapping SHA",
    )

    require(
        committed[
            "visit_ids_contiguous_2_through_5800"
        ]
        is True,
        "contiguous IDs",
    )

    require(
        contract[
            "cdm_visit_rows_after_allocation"
        ]
        == 0,
        "CDM rows",
    )

    require(
        contract[
            "cdm_visit_occurrence_write"
        ]
        is False,
        "CDM write",
    )

    recovery = contract[
        "recovery_lineage"
    ]

    require(
        recovery[
            "recovery_state_sha256"
        ]
        == EXPECTED_RECOVERY_SHA,
        "recovery SHA",
    )

    require(
        recovery[
            "recovery_amendment_sha256"
        ]
        == EXPECTED_AMENDMENT_SHA,
        "amendment SHA",
    )

    require(
        recovery[
            "sequence_value_1_consumed_gap"
        ]
        is True,
        "gap lineage",
    )

    correction = contract[
        "corrected_allocation"
    ]

    require(
        correction[
            "allocation_sql_sha256"
        ]
        == EXPECTED_SQL_SHA,
        "SQL SHA",
    )

    require(
        correction[
            "psql_output_sha256"
        ]
        == EXPECTED_PSQL_SHA,
        "psql SHA",
    )

    require(
        correction[
            "explicit_identity_insert"
        ]
        == "OVERRIDING SYSTEM VALUE",
        "identity override",
    )

    require(
        correction[
            "identity_generation"
        ]
        == "ALWAYS",
        "identity generation",
    )

    require(
        correction[
            "transaction_committed"
        ]
        is True,
        "transaction commit",
    )

    require(
        correction[
            "independent_post_commit_verification"
        ]
        is True,
        "independent verify",
    )

    sequence = contract[
        "sequence"
    ]

    require(
        sequence["last_value"]
        == 5800,
        "sequence last",
    )

    require(
        sequence["is_called"]
        is True,
        "sequence called",
    )

    require(
        sequence["gap_policy"]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "gap policy",
    )

    require(
        sequence[
            "setval_backward_used"
        ]
        is False,
        "setval policy",
    )

    require(
        sha(sql_path)
        == EXPECTED_SQL_SHA,
        "runtime SQL SHA",
    )

    require(
        sha(psql_path)
        == EXPECTED_PSQL_SHA,
        "runtime psql SHA",
    )

    require(
        state["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "state mapping SHA",
    )

    require(
        state["committed_map_rows"]
        == 5799,
        "state rows",
    )

    require(
        state[
            "min_visit_occurrence_id"
        ]
        == 2,
        "state min",
    )

    require(
        state[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "state max",
    )

    require(
        state["transaction_committed"]
        is True,
        "state commit",
    )

    require(
        state[
            "independent_post_commit_verification"
        ]
        is True,
        "state independent verify",
    )

    require(
        state[
            "cdm_visit_occurrence_write"
        ]
        is False,
        "state CDM write",
    )

    require(
        post["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "post mapping SHA",
    )

    require(
        post["committed_map_rows"]
        == 5799,
        "post rows",
    )

    require(
        post["candidate_coverage"]
        == 5799,
        "candidate coverage",
    )

    require(
        post[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "post unique IDs",
    )

    require(
        post["cdm_visit_rows"]
        == 0,
        "post CDM rows",
    )

    require(
        tx["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "tx mapping SHA",
    )

    require(
        tx["map_rows"]
        == 5799,
        "tx rows",
    )

    require(
        tx[
            "min_visit_occurrence_id"
        ]
        == 2,
        "tx min",
    )

    require(
        tx[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "tx max",
    )

    map_lines = [
        line
        for line in Path(
            map_path
        ).read_text().splitlines()
        if line
        and line not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        len(map_lines)
        == 5799,
        "map readback rows",
    )

    parsed = []

    for line in map_lines:
        fields = line.split("\t")

        require(
            len(fields)
            == 3,
            "map TSV schema",
        )

        parsed.append(
            (
                fields[0],
                fields[1],
                int(fields[2]),
            )
        )

    ids = [
        row[2]
        for row in parsed
    ]

    require(
        ids
        == list(
            range(
                2,
                5801,
            )
        ),
        "authoritative ID sequence",
    )

    payload = "".join(
        source_system
        + "\t"
        + encounter_id
        + "\t"
        + str(visit_id)
        + "\n"
        for (
            source_system,
            encounter_id,
            visit_id
        )
        in parsed
    ).encode(
        "utf-8"
    )

    require(
        hashlib.sha256(
            payload
        ).hexdigest()
        == EXPECTED_MAPPING_SHA,
        "readback mapping SHA",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4C",

        "status":
            "COMMITTED_VISIT_ID_MAPPING_CANONICAL_GATE_PASS",

        "committed_map_rows":
            5799,

        "candidate_coverage":
            5799,

        "unique_visit_occurrence_ids":
            5799,

        "min_visit_occurrence_id":
            2,

        "max_visit_occurrence_id":
            5800,

        "mapping_sha256":
            EXPECTED_MAPPING_SHA,

        "sequence_last_value":
            5800,

        "sequence_is_called":
            True,

        "sequence_value_1_consumed_gap":
            True,

        "cdm_visit_rows":
            0,

        "cdm_visit_occurrence_write":
            False,

        "ready_for_git_checkpoint":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--contract",
        required=True,
    )

    parser.add_argument(
        "--state",
        required=True,
    )

    parser.add_argument(
        "--post-verify",
        required=True,
    )

    parser.add_argument(
        "--transaction-summary",
        required=True,
    )

    parser.add_argument(
        "--sql",
        required=True,
    )

    parser.add_argument(
        "--psql-output",
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
        args.contract,
        args.state,
        args.post_verify,
        args.transaction_summary,
        args.sql,
        args.psql_output,
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
        "STEP06B4C_COMMITTED_MAPPING_VERIFY=PASS"
    )

    print(
        "COMMITTED_VISIT_MAP_ROWS=5799"
    )

    print(
        "COMMITTED_VISIT_ID_RANGE=2..5800"
    )

    print(
        "AUTHORITATIVE_MAPPING_SHA256="
        + EXPECTED_MAPPING_SHA
    )

    print(
        "CDM_VISIT_ROWS=0"
    )

    print(
        "READY_FOR_GIT_CHECKPOINT=YES"
    )


if __name__ == "__main__":
    main()
VERIFY_APP_EOF_TASK003_06B4C

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4c-verify-committed-visit-id-mapping.sh" <<'VERIFY_RUNNER_EOF_TASK003_06B4C'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-corrected.20261010t142456z.2490800"

APP="$ROOT/apps/task003/verify_committed_visit_id_mapping.py"

CONTRACT="$ROOT/spark/contracts/processed/visit-id-allocation-result-v1.json"

STATE="$REPORT/run-state.json"
POST_VERIFY="$REPORT/post-commit-verification.json"
TX="$REPORT/transaction-summary.json"
SQL="$REPORT/allocation-corrected.sql"
PSQL_OUTPUT="$REPORT/psql-output.txt"
MAP_READBACK="$REPORT/post-commit-map.tsv"

OUTDIR="$ROOT/runtime/reports/task003/step06/committed-visit-id-mapping-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4C COMMITTED MAPPING VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4C_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4C COMMITTED MAPPING VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$CONTRACT" \
  "$STATE" \
  "$POST_VERIFY" \
  "$TX" \
  "$SQL" \
  "$PSQL_OUTPUT" \
  "$MAP_READBACK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing committed-mapping gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --contract "$CONTRACT" \
  --state "$STATE" \
  --post-verify "$POST_VERIFY" \
  --transaction-summary "$TX" \
  --sql "$SQL" \
  --psql-output "$PSQL_OUTPUT" \
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
    == "COMMITTED_VISIT_ID_MAPPING_CANONICAL_GATE_PASS"
)

assert state["committed_map_rows"] == 5799
assert state["candidate_coverage"] == 5799

assert (
    state["unique_visit_occurrence_ids"]
    == 5799
)

assert state["min_visit_occurrence_id"] == 2
assert state["max_visit_occurrence_id"] == 5800

assert (
    state["mapping_sha256"]
    == "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f"
)

assert state["sequence_last_value"] == 5800
assert state["sequence_is_called"] is True

assert (
    state["sequence_value_1_consumed_gap"]
    is True
)

assert state["cdm_visit_rows"] == 0

assert (
    state["cdm_visit_occurrence_write"]
    is False
)

assert state["ready_for_git_checkpoint"] is True

print("STEP06B4C_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4C_COMMITTED_MAPPING_CANONICAL_GATE=PASS'

echo 'COMMITTED_VISIT_MAP_ROWS=5799'
echo 'COMMITTED_CANDIDATE_COVERAGE=5799'
echo 'COMMITTED_UNIQUE_VISIT_IDS=5799'

echo 'COMMITTED_VISIT_ID_RANGE=2..5800'

echo 'AUTHORITATIVE_MAPPING_SHA256=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f'

echo 'SEQUENCE_LAST_VALUE=5800'
echo 'SEQUENCE_IS_CALLED=TRUE'
echo 'VISIT_ID_1_GAP_PRESERVED=YES'

echo 'CDM_VISIT_ROWS=0'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'READY_FOR_GIT_CHECKPOINT=YES'
VERIFY_RUNNER_EOF_TASK003_06B4C

mkdir -p "$STAGE/spark/contracts/processed"
cat > "$STAGE/spark/contracts/processed/visit-id-allocation-result-v1.json" <<'RESULT_CONTRACT_EOF_TASK003_06B4C'
{
  "candidate_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
  "candidate_rows": 5799,
  "candidate_unique_business_keys": 5799,
  "cdm_visit_occurrence_write": false,
  "cdm_visit_rows_after_allocation": 0,
  "committed_mapping": {
    "business_key_order": [
      "source_system",
      "source_encounter_id"
    ],
    "mapping_sha256": "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f",
    "max_visit_occurrence_id": 5800,
    "min_visit_occurrence_id": 2,
    "rows": 5799,
    "unique_visit_occurrence_ids": 5799,
    "visit_ids_contiguous_2_through_5800": true
  },
  "corrected_allocation": {
    "allocation_sql_sha256": "4e0f7ba8c81639d601df832781515d1b2e6084706f9e96f1829ec12a2937bf7e",
    "explicit_identity_insert": "OVERRIDING SYSTEM VALUE",
    "identity_generation": "ALWAYS",
    "independent_post_commit_verification": true,
    "psql_output_sha256": "db7add87ae7185dc2127b21230ce7756e2ec3c11bb80676c023fed0e066c59a3",
    "transaction_committed": true
  },
  "git_checkpoint_before_corrected_mutation": "d2bddab5ffee00df0f42db8273379b89364be115",
  "recovery_lineage": {
    "recovery_amendment_sha256": "f3f81af4effadc65e73255837f5cf79fe74050f2bf3f4685385f360b20a76a03",
    "recovery_state_sha256": "c34f6682f5a4482f1ef33f8a085463c4714fe858cd72c14bc03d75be3608dcc2",
    "sequence_value_1_consumed_gap": true
  },
  "sequence": {
    "gap_policy": "ACCEPT_GAPS_NEVER_REWIND",
    "is_called": true,
    "last_value": 5800,
    "setval_backward_used": false
  },
  "status": "VISIT_ID_ALLOCATION_COMMITTED_AND_FROZEN",
  "step": "STEP-06B4C",
  "task": "TASK-003",
  "version": "v1"
}
RESULT_CONTRACT_EOF_TASK003_06B4C

mkdir -p "$STAGE/tests/task003"
cat > "$STAGE/tests/task003/test_committed_visit_id_mapping.py" <<'TEST_EOF_TASK003_06B4C'
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
    / "apps/task003/verify_committed_visit_id_mapping.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_committed_visit_id_mapping",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class CommittedVisitIDMappingTests(
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
TEST_EOF_TASK003_06B4C

mkdir -p "$STAGE/docs/task003"
cat > "$STAGE/docs/task003/TASK003-STEP06B4C-Committed-Visit-ID-Mapping.md" <<'DOC_EOF_TASK003_06B4C'
# TASK-003 STEP06B4C — Committed Visit ID Mapping

## Final allocation result

The corrected Visit ID allocation transaction completed successfully.

Frozen Candidate business keys:

- rows: 5799
- unique keys: 5799
- business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Committed Visit ID mapping:

- rows: 5799
- unique Visit IDs: 5799
- minimum Visit ID: 2
- maximum Visit ID: 5800
- IDs are contiguous from 2 through 5800
- authoritative mapping SHA256:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

The mapping fingerprint represents ordered rows:

`source_system<TAB>source_encounter_id<TAB>visit_occurrence_id<LF>`

ordered by:

`source_system, source_encounter_id`

## Sequence state

The first failed allocation attempt consumed sequence value 1.

That value is intentionally preserved as a legal sequence gap.

Final sequence state:

- last_value: 5800
- is_called: true
- gap policy: `ACCEPT_GAPS_NEVER_REWIND`
- backward `setval()` was never used

## Identity behavior

`etl.visit_occurrence_id_map.visit_occurrence_id`

is:

`GENERATED ALWAYS AS IDENTITY`

The corrected transaction therefore used:

`OVERRIDING SYSTEM VALUE`

for explicit IDs obtained from the owned identity sequence.

## Database scope

STEP06B4B-R2 mutated only:

`etl.visit_occurrence_id_map`

It did not write:

`cdm.visit_occurrence`

After allocation:

- Visit ID map rows: 5799
- CDM Visit rows: 0
- Person map rows: 113

## Audit lineage

Recovery checkpoint before corrected mutation:

`d2bddab5ffee00df0f42db8273379b89364be115`

Corrected allocation SQL SHA256:

`4e0f7ba8c81639d601df832781515d1b2e6084706f9e96f1829ec12a2937bf7e`

Corrected psql output SHA256:

`db7add87ae7185dc2127b21230ce7756e2ec3c11bb80676c023fed0e066c59a3`

Recovery state SHA256:

`c34f6682f5a4482f1ef33f8a085463c4714fe858cd72c14bc03d75be3608dcc2`

Recovery amendment SHA256:

`f3f81af4effadc65e73255837f5cf79fe74050f2bf3f4685385f360b20a76a03`

## Next boundary

The committed mapping is now authoritative.

No Visit IDs may be reassigned.

The next phase may use this mapping to prepare and validate
`cdm.visit_occurrence` rows, but CDM materialization must remain a separate
mutation boundary with its own preflight, reconciliation, canonical source,
and Git checkpoint.
DOC_EOF_TASK003_06B4C


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

install_one scripts/task003/06b4b-r2-corrected-visit-id-allocation.sh
install_one apps/task003/verify_committed_visit_id_mapping.py
install_one scripts/task003/06b4c-verify-committed-visit-id-mapping.sh
install_one spark/contracts/processed/visit-id-allocation-result-v1.json
install_one tests/task003/test_committed_visit_id_mapping.py
install_one docs/task003/TASK003-STEP06B4C-Committed-Visit-ID-Mapping.md

python3 -m py_compile \
  "$ROOT/apps/task003/verify_committed_visit_id_mapping.py" \
  "$ROOT/tests/task003/test_committed_visit_id_mapping.py"

python3 -m json.tool \
  "$ROOT/spark/contracts/processed/visit-id-allocation-result-v1.json" \
  >/dev/null

bash -n \
  "$ROOT/scripts/task003/06b4b-r2-corrected-visit-id-allocation.sh"

bash -n \
  "$ROOT/scripts/task003/06b4c-verify-committed-visit-id-mapping.sh"

echo 'STEP06B4C_CANONICAL_SOURCE_PREPARED=PASS'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'
echo 'GIT_COMMIT=NO'
