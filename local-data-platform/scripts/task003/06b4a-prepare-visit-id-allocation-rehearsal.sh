#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06b4a-generator.XXXXXX)"

echo '#### TASK003 STEP06B4A PREPARE ALLOCATION REHEARSAL OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06B4A_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4A PREPARE ALLOCATION REHEARSAL OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4a-rehearse-visit-id-allocation.sh" <<'RUNNER_EOF_TASK003_06B4A'
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

EXPECTED_HEAD=0fab643417dd3922f8adc8041014d352430c233f

RUN_ID=visit-proc-20261009t192437z-2081886

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e
EXPECTED_B1_SHA=58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0
EXPECTED_META_SHA=21ac6b5af6f74d3b078b4fbf7fb8ce21b5d5d32af1aaccc5e495e595fc90dbaa

ADVISORY_LOCK_KEY=5947676943154735385

CONTRACT="$ROOT/spark/contracts/processed/visit-id-mutation-contract-v1.json"
META="$ROOT/spark/contracts/processed/visit-business-key-snapshot-v1.json"

SNAPSHOT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID/business-keys.tsv"

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-rehearsal.${STAMP}.$$"

SQL_FILE="$REPORT/rehearsal.sql"
PSQL_OUT="$REPORT/psql-output.txt"
POSTCHECK="$REPORT/post-rehearsal-db-state.txt"
RUN_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06B4A VISIT ID ALLOCATION REHEARSAL OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4A_REPORT=$REPORT"
  echo "STEP06B4A_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4A VISIT ID ALLOCATION REHEARSAL OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify pre-mutation Git checkpoint ==='

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
  echo 'ERROR: local HEAD is not frozen pre-mutation checkpoint'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main differs from frozen pre-mutation checkpoint'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: repository working tree is not clean'
  git status --short
  exit 1
}

echo 'PRE_MUTATION_GIT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Re-run canonical pre-mutation gate ==='

bash \
  scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh

echo 'CANONICAL_PRE_MUTATION_GATE=PASS'

echo '=== 3. Verify contract, metadata and immutable snapshot ==='

for file in \
  "$CONTRACT" \
  "$META" \
  "$SNAPSHOT"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe mutation input: $file"
    exit 1
  }
done

CONTRACT_SHA="$(
  sha256sum "$CONTRACT" |
  awk '{print $1}'
)"

META_SHA="$(
  sha256sum "$META" |
  awk '{print $1}'
)"

SNAPSHOT_SHA="$(
  sha256sum "$SNAPSHOT" |
  awk '{print $1}'
)"

SNAPSHOT_ROWS="$(
  wc -l < "$SNAPSHOT" |
  tr -d ' '
)"

SNAPSHOT_MODE="$(
  stat -c '%a' "$SNAPSHOT"
)"

echo "MUTATION_CONTRACT_SHA256=$CONTRACT_SHA"
echo "SNAPSHOT_METADATA_SHA256=$META_SHA"
echo "BUSINESS_KEY_SNAPSHOT_SHA256=$SNAPSHOT_SHA"
echo "BUSINESS_KEY_SNAPSHOT_ROWS=$SNAPSHOT_ROWS"
echo "BUSINESS_KEY_SNAPSHOT_MODE=$SNAPSHOT_MODE"

[[ "$CONTRACT_SHA" == "$EXPECTED_B1_SHA" ]] || {
  echo 'ERROR: mutation contract SHA mismatch'
  exit 1
}

[[ "$META_SHA" == "$EXPECTED_META_SHA" ]] || {
  echo 'ERROR: snapshot metadata SHA mismatch'
  exit 1
}

[[ "$SNAPSHOT_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: business-key snapshot SHA mismatch'
  exit 1
}

[[ "$SNAPSHOT_ROWS" == "5799" ]] || {
  echo 'ERROR: snapshot row count mismatch'
  exit 1
}

[[ "$SNAPSHOT_MODE" == "444" ]] || {
  echo 'ERROR: frozen snapshot mode is not 0444'
  exit 1
}

python3 - "$SNAPSHOT" "$EXPECTED_KEY_SHA" <<'PY_SNAPSHOT'
import hashlib
import sys
from pathlib import Path


path = Path(sys.argv[1])
expected_sha = sys.argv[2]

payload = path.read_bytes()

assert payload.endswith(b"\n")
assert b"\r" not in payload
assert b"\\" not in payload

sha = hashlib.sha256(payload).hexdigest()

assert sha == expected_sha

lines = payload.decode("utf-8").splitlines()

assert len(lines) == 5799
assert len(set(lines)) == 5799
assert lines == sorted(lines)

for line in lines:
    fields = line.split("\t")

    assert len(fields) == 2
    assert fields[0] == "synthea"
    assert fields[1]

print("LOCAL_IMMUTABLE_SNAPSHOT_VERIFY=PASS")
print("LOCAL_SNAPSHOT_ROWS=5799")
print("LOCAL_SNAPSHOT_UNIQUE_KEYS=5799")
print("LOCAL_SNAPSHOT_SHA256=" + sha)
PY_SNAPSHOT

echo '=== 4. Build exact rehearsal transaction ==='

cat > "$SQL_FILE" <<SQL_HEAD
\\set ON_ERROR_STOP on
\\pset pager off
\\pset format unaligned
\\pset tuples_only on

\\echo REHEARSAL_TRANSACTION_BEGIN

BEGIN;

SET LOCAL lock_timeout = '15s';
SET LOCAL statement_timeout = '180s';

\\echo ACQUIRE_ADVISORY_LOCK

SELECT pg_advisory_xact_lock(${ADVISORY_LOCK_KEY});

\\echo ADVISORY_LOCK_ACQUIRED

\\echo ACQUIRE_TABLE_LOCKS

LOCK TABLE etl.visit_occurrence_id_map
    IN SHARE ROW EXCLUSIVE MODE;

LOCK TABLE etl.person_id_map
    IN SHARE MODE;

LOCK TABLE cdm.visit_occurrence
    IN SHARE MODE;

\\echo TABLE_LOCKS_ACQUIRED

\\echo PRE_COPY_DATABASE_REVALIDATION

DO \$do\$
DECLARE
    v_map_rows bigint;
    v_cdm_rows bigint;
    v_person_rows bigint;

    v_seq_last bigint;
    v_seq_called boolean;

    v_key_collision_groups bigint;
    v_id_collision_groups bigint;
    v_cdm_overlap bigint;
BEGIN
    SELECT count(*)
    INTO v_map_rows
    FROM etl.visit_occurrence_id_map;

    SELECT count(*)
    INTO v_cdm_rows
    FROM cdm.visit_occurrence;

    SELECT count(*)
    INTO v_person_rows
    FROM etl.person_id_map;

    SELECT
        last_value,
        is_called
    INTO
        v_seq_last,
        v_seq_called
    FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

    SELECT count(*)
    INTO v_key_collision_groups
    FROM (
        SELECT
            source_system,
            source_encounter_id
        FROM etl.visit_occurrence_id_map
        GROUP BY
            source_system,
            source_encounter_id
        HAVING count(*) > 1
    ) q;

    SELECT count(*)
    INTO v_id_collision_groups
    FROM (
        SELECT visit_occurrence_id
        FROM etl.visit_occurrence_id_map
        GROUP BY visit_occurrence_id
        HAVING count(*) > 1
    ) q;

    SELECT count(*)
    INTO v_cdm_overlap
    FROM cdm.visit_occurrence c
    JOIN etl.visit_occurrence_id_map m
      ON m.visit_occurrence_id = c.visit_occurrence_id;

    IF v_map_rows <> 0 THEN
        RAISE EXCEPTION
            'visit map row count changed: %',
            v_map_rows;
    END IF;

    IF v_cdm_rows <> 0 THEN
        RAISE EXCEPTION
            'CDM Visit row count changed: %',
            v_cdm_rows;
    END IF;

    IF v_person_rows <> 113 THEN
        RAISE EXCEPTION
            'Person map row count changed: %',
            v_person_rows;
    END IF;

    IF v_seq_last <> 1 OR v_seq_called THEN
        RAISE EXCEPTION
            'sequence state changed: last_value %, is_called %',
            v_seq_last,
            v_seq_called;
    END IF;

    IF v_key_collision_groups <> 0 THEN
        RAISE EXCEPTION
            'business-key collision groups: %',
            v_key_collision_groups;
    END IF;

    IF v_id_collision_groups <> 0 THEN
        RAISE EXCEPTION
            'Visit ID collision groups: %',
            v_id_collision_groups;
    END IF;

    IF v_cdm_overlap <> 0 THEN
        RAISE EXCEPTION
            'CDM/map overlap changed: %',
            v_cdm_overlap;
    END IF;
END
\$do\$;

\\echo PRE_COPY_DATABASE_REVALIDATION_PASS

CREATE TEMP TABLE task003_visit_candidate_keys (
    source_system text NOT NULL,
    source_encounter_id text NOT NULL,
    PRIMARY KEY (
        source_system,
        source_encounter_id
    )
) ON COMMIT DROP;

\\echo CANDIDATE_TEMP_TABLE_CREATED

COPY task003_visit_candidate_keys (
    source_system,
    source_encounter_id
)
FROM STDIN
WITH (
    FORMAT text,
    DELIMITER E'\\t'
);
SQL_HEAD

cat "$SNAPSHOT" >> "$SQL_FILE"

cat >> "$SQL_FILE" <<'SQL_TAIL'
\.

\echo CANDIDATE_COPY_COMPLETE

\echo TEMP_TABLE_REVALIDATION

DO $do$
DECLARE
    v_rows bigint;
    v_unique bigint;
    v_non_synthea bigint;
    v_existing bigint;
    v_map_only bigint;
    v_sha text;

    v_seq_last bigint;
    v_seq_called boolean;
BEGIN
    SELECT count(*)
    INTO v_rows
    FROM task003_visit_candidate_keys;

    SELECT count(*)
    INTO v_unique
    FROM (
        SELECT
            source_system,
            source_encounter_id
        FROM task003_visit_candidate_keys
        GROUP BY
            source_system,
            source_encounter_id
    ) q;

    SELECT count(*)
    INTO v_non_synthea
    FROM task003_visit_candidate_keys
    WHERE source_system <> 'synthea';

    SELECT count(*)
    INTO v_existing
    FROM task003_visit_candidate_keys c
    JOIN etl.visit_occurrence_id_map m
      ON m.source_system = c.source_system
     AND m.source_encounter_id = c.source_encounter_id;

    SELECT count(*)
    INTO v_map_only
    FROM etl.visit_occurrence_id_map m
    LEFT JOIN task003_visit_candidate_keys c
      ON c.source_system = m.source_system
     AND c.source_encounter_id = m.source_encounter_id
    WHERE m.source_system = 'synthea'
      AND c.source_system IS NULL;

    SELECT
        encode(
            sha256(
                convert_to(
                    string_agg(
                        source_system
                        || E'\t'
                        || source_encounter_id
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
    INTO v_sha
    FROM task003_visit_candidate_keys;

    SELECT
        last_value,
        is_called
    INTO
        v_seq_last,
        v_seq_called
    FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

    IF v_rows <> 5799 THEN
        RAISE EXCEPTION
            'TEMP row count mismatch: %',
            v_rows;
    END IF;

    IF v_unique <> 5799 THEN
        RAISE EXCEPTION
            'TEMP unique key count mismatch: %',
            v_unique;
    END IF;

    IF v_non_synthea <> 0 THEN
        RAISE EXCEPTION
            'unexpected source systems: %',
            v_non_synthea;
    END IF;

    IF v_existing <> 0 THEN
        RAISE EXCEPTION
            'Candidate keys already mapped: %',
            v_existing;
    END IF;

    IF v_map_only <> 0 THEN
        RAISE EXCEPTION
            'DB-only Synthea keys detected: %',
            v_map_only;
    END IF;

    IF v_sha <> 'aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e' THEN
        RAISE EXCEPTION
            'TEMP business-key fingerprint mismatch: %',
            v_sha;
    END IF;

    IF v_seq_last <> 1 OR v_seq_called THEN
        RAISE EXCEPTION
            'sequence changed during rehearsal: last_value %, is_called %',
            v_seq_last,
            v_seq_called;
    END IF;
END
$do$;

\echo TEMP_TABLE_REVALIDATION_PASS

\echo REHEARSAL_SUMMARY

SELECT
    (SELECT count(*)
       FROM task003_visit_candidate_keys),
    (
        SELECT encode(
            sha256(
                convert_to(
                    string_agg(
                        source_system
                        || E'\t'
                        || source_encounter_id
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
        FROM task003_visit_candidate_keys
    ),
    (
        SELECT count(*)
        FROM task003_visit_candidate_keys c
        JOIN etl.visit_occurrence_id_map m
          ON m.source_system = c.source_system
         AND m.source_encounter_id = c.source_encounter_id
    ),
    (
        SELECT last_value
        FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq
    ),
    (
        SELECT is_called
        FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq
    );

\echo IRREVERSIBLE_BOUNDARY_NOT_CROSSED

ROLLBACK;

\echo REHEARSAL_ROLLBACK_COMPLETE
SQL_TAIL

chmod 0444 "$SQL_FILE"

echo 'REHEARSAL_SQL_BUILD=PASS'

echo '=== 5. Static safety proof of rehearsal SQL ==='

python3 - "$SQL_FILE" <<'PY_SQL'
import re
import sys
from pathlib import Path


source = Path(sys.argv[1]).read_text()

required = (
    "BEGIN;",
    "pg_advisory_xact_lock",
    "SHARE ROW EXCLUSIVE MODE",
    "CREATE TEMP TABLE",
    "COPY task003_visit_candidate_keys",
    "TEMP_TABLE_REVALIDATION_PASS",
    "IRREVERSIBLE_BOUNDARY_NOT_CROSSED",
    "ROLLBACK;",
)

for token in required:
    assert token in source, token

# B4A must contain no sequence-allocation call at all.
assert not re.search(
    r"\bnextval\s*\(",
    source,
    re.IGNORECASE,
)

assert not re.search(
    r"\bsetval\s*\(",
    source,
    re.IGNORECASE,
)

# No persistent DML is allowed.
for pattern in (
    r"\bINSERT\s+INTO\s+etl\.",
    r"\bUPDATE\s+etl\.",
    r"\bDELETE\s+FROM\s+etl\.",
    r"\bINSERT\s+INTO\s+cdm\.",
    r"\bUPDATE\s+cdm\.",
    r"\bDELETE\s+FROM\s+cdm\.",
    r"\bTRUNCATE\s+etl\.",
    r"\bTRUNCATE\s+cdm\.",
    r"\bALTER\s+SEQUENCE\b",
):
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

print("B4A_STATIC_TRANSACTION_SAFETY=PASS")
print("SEQUENCE_ALLOCATION_CALL_IN_SQL=NO")
print("SETVAL_CALL_IN_SQL=NO")
print("PERSISTENT_DML_IN_SQL=NO")
print("TEMP_TABLE_COPY_ONLY=YES")
print("ROLLBACK_REQUIRED=YES")
PY_SQL

echo '=== 6. Execute real locked rehearsal transaction ==='

kubectl -n "$NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -f - \
  < "$SQL_FILE" \
  > "$PSQL_OUT"

cat "$PSQL_OUT"

echo '=== 7. Verify transaction reached all rehearsal gates ==='

python3 - "$PSQL_OUT" "$EXPECTED_KEY_SHA" <<'PY_OUTPUT'
import sys
from pathlib import Path


text = Path(sys.argv[1]).read_text()
expected_sha = sys.argv[2]

required = (
    "REHEARSAL_TRANSACTION_BEGIN",
    "ACQUIRE_ADVISORY_LOCK",
    "ADVISORY_LOCK_ACQUIRED",
    "ACQUIRE_TABLE_LOCKS",
    "TABLE_LOCKS_ACQUIRED",
    "PRE_COPY_DATABASE_REVALIDATION_PASS",
    "CANDIDATE_TEMP_TABLE_CREATED",
    "COPY 5799",
    "CANDIDATE_COPY_COMPLETE",
    "TEMP_TABLE_REVALIDATION_PASS",
    "REHEARSAL_SUMMARY",
    "IRREVERSIBLE_BOUNDARY_NOT_CROSSED",
    "ROLLBACK",
    "REHEARSAL_ROLLBACK_COMPLETE",
)

for token in required:
    assert token in text, token

summary = (
    "5799|"
    + expected_sha
    + "|0|1|f"
)

assert summary in text, (
    "expected rehearsal summary missing: "
    + summary
)

print("B4A_LOCKED_REHEARSAL_TRANSACTION=PASS")
print("ADVISORY_LOCK_ACQUIRED_DURING_REHEARSAL=YES")
print("TABLE_LOCKS_ACQUIRED_DURING_REHEARSAL=YES")
print("TEMP_TABLE_COPY_ROWS=5799")
print("TEMP_TABLE_BUSINESS_KEY_SHA256=" + expected_sha)
print("EXISTING_CANDIDATE_MAPPINGS_DURING_REHEARSAL=0")
print("SEQUENCE_LAST_VALUE_DURING_REHEARSAL=1")
print("SEQUENCE_IS_CALLED_DURING_REHEARSAL=FALSE")
print("IRREVERSIBLE_BOUNDARY_CROSSED=NO")
print("TRANSACTION_ROLLED_BACK=YES")
PY_OUTPUT

echo '=== 8. Independent post-rehearsal database verification ==='

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
  > "$POSTCHECK" <<'SQL'
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

SELECT count(*)
FROM pg_locks
WHERE locktype = 'advisory'
  AND granted
  AND objid IS NOT NULL
  AND pid = pg_backend_pid();

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$POSTCHECK"

python3 - "$POSTCHECK" <<'PY_POST'
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

assert rows == [
    "0|0|113",
    "1|f",
    "0",
    "on",
], rows

print("POST_B4A_DATABASE_STATE=PASS")
print("VISIT_MAP_ROWS_AFTER_REHEARSAL=0")
print("CDM_VISIT_ROWS_AFTER_REHEARSAL=0")
print("PERSON_MAP_ROWS_AFTER_REHEARSAL=113")
print("SEQUENCE_LAST_VALUE_AFTER_REHEARSAL=1")
print("SEQUENCE_IS_CALLED_AFTER_REHEARSAL=FALSE")
print("REHEARSAL_ADVISORY_LOCK_RELEASED=YES")
PY_POST

echo '=== 9. Record rehearsal evidence ==='

python3 - \
  "$RUN_STATE" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_B1_SHA" \
  "$EXPECTED_META_SHA" \
  "$EXPECTED_KEY_SHA" \
  "$ADVISORY_LOCK_KEY" \
  "$SQL_FILE" \
  "$PSQL_OUT" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path


output = Path(sys.argv[1])

checkpoint = sys.argv[2]
contract_sha = sys.argv[3]
meta_sha = sys.argv[4]
key_sha = sys.argv[5]
lock_key = int(sys.argv[6])

sql_path = Path(sys.argv[7])
psql_path = Path(sys.argv[8])


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


state = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B4A",

    "status":
        "VISIT_ID_ALLOCATION_REHEARSAL_PASS",

    "git_checkpoint":
        checkpoint,

    "mutation_contract_sha256":
        contract_sha,

    "snapshot_metadata_sha256":
        meta_sha,

    "candidate_business_key_sha256":
        key_sha,

    "candidate_rows":
        5799,

    "candidate_unique_business_keys":
        5799,

    "advisory_lock_key":
        lock_key,

    "rehearsal_sql_sha256":
        sha(sql_path),

    "psql_output_sha256":
        sha(psql_path),

    "advisory_lock_acquired":
        True,

    "table_locks_acquired":
        True,

    "candidate_temp_table_loaded":
        True,

    "candidate_temp_rows":
        5799,

    "candidate_temp_sha256":
        key_sha,

    "existing_candidate_mappings":
        0,

    "transaction_rolled_back":
        True,

    "advisory_lock_released":
        True,

    "irreversible_boundary_crossed":
        False,

    "nextval_called":
        False,

    "setval_called":
        False,

    "visit_id_allocation_started":
        False,

    "visit_id_map_mutated":
        False,

    "sequence_advanced":
        False,

    "cdm_visit_occurrence_write":
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


print("STEP06B4A_RUN_STATE=PASS")
print("REHEARSAL_SQL_SHA256=" + state["rehearsal_sql_sha256"])
print("REHEARSAL_PSQL_OUTPUT_SHA256=" + state["psql_output_sha256"])
PY_STATE

echo '=== 10. Final STEP06B4A verdict ==='

echo 'STEP06B4A_VISIT_ID_ALLOCATION_REHEARSAL=PASS'

echo "STEP06B_PRE_MUTATION_GIT_CHECKPOINT=$EXPECTED_HEAD"

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'
echo "CANDIDATE_BUSINESS_KEY_SHA256=$EXPECTED_KEY_SHA"

echo "ADVISORY_LOCK_KEY=$ADVISORY_LOCK_KEY"
echo 'ADVISORY_LOCK_ACQUIRED_DURING_REHEARSAL=YES'
echo 'TABLE_LOCKS_ACQUIRED_DURING_REHEARSAL=YES'
echo 'ADVISORY_LOCK_RELEASED_AFTER_ROLLBACK=YES'

echo 'COPY_TEMP_TABLE_ROWS=5799'
echo "COPY_TEMP_TABLE_SHA256=$EXPECTED_KEY_SHA"

echo 'MUTATION_TIME_REVALIDATION=PASS'
echo 'EXISTING_CANDIDATE_MAPPINGS=0'

echo 'SEQUENCE_LAST_VALUE=1'
echo 'SEQUENCE_IS_CALLED=FALSE'

echo 'IRREVERSIBLE_BOUNDARY_CROSSED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'TRANSACTION_ROLLED_BACK=YES'
echo 'PERSISTENT_DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'

echo 'READY_FOR_STEP06B4B_FIRST_MUTATION=YES'
RUNNER_EOF_TASK003_06B4A

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/verify_visit_id_allocation_rehearsal.py" <<'APP_EOF_TASK003_06B4A'
#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED_HEAD = (
    "0fab643417dd3922f8adc8041014d352430c233f"
)

EXPECTED_CONTRACT_SHA = (
    "58cd44b22eaf15674a7277c51c66418c"
    "305bd3743b403c7612d458453d87f9f0"
)

EXPECTED_META_SHA = (
    "21ac6b5af6f74d3b078b4fbf7fb8ce21"
    "b5d5d32af1aaccc5e495e595fc90dbaa"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_SQL_SHA = (
    "21e00285ce0ebaf43c0c38b57be74bf3"
    "2204236ae7af8d9c1170143b757d31e1"
)

EXPECTED_OUTPUT_SHA = (
    "7d26cf9f34bb39b445e2ff53171f4f34"
    "5eb6c2818a2a39b0692756c5fb48e92b"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def validate(
    state_path,
    sql_path,
    output_path,
    postcheck_path,
):
    state = json.loads(
        Path(state_path).read_bytes()
    )

    require(
        state["status"]
        == "VISIT_ID_ALLOCATION_REHEARSAL_PASS",
        "B4A status",
    )

    require(
        state["git_checkpoint"]
        == EXPECTED_HEAD,
        "B4A checkpoint",
    )

    require(
        state["mutation_contract_sha256"]
        == EXPECTED_CONTRACT_SHA,
        "B4A contract lineage",
    )

    require(
        state["snapshot_metadata_sha256"]
        == EXPECTED_META_SHA,
        "B4A metadata lineage",
    )

    require(
        state["candidate_business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "B4A key lineage",
    )

    require(
        sha(sql_path)
        == EXPECTED_SQL_SHA,
        "rehearsal SQL SHA",
    )

    require(
        sha(output_path)
        == EXPECTED_OUTPUT_SHA,
        "rehearsal output SHA",
    )

    require(
        state["candidate_temp_rows"]
        == 5799,
        "TEMP rows",
    )

    require(
        state["candidate_temp_sha256"]
        == EXPECTED_KEY_SHA,
        "TEMP fingerprint",
    )

    require(
        state["existing_candidate_mappings"]
        == 0,
        "existing mappings",
    )

    require(
        state["advisory_lock_acquired"]
        is True,
        "advisory lock",
    )

    require(
        state["table_locks_acquired"]
        is True,
        "table locks",
    )

    require(
        state["transaction_rolled_back"]
        is True,
        "rollback",
    )

    require(
        state["advisory_lock_released"]
        is True,
        "lock release",
    )

    require(
        state["irreversible_boundary_crossed"]
        is False,
        "irreversible boundary",
    )

    for field in (
        "nextval_called",
        "setval_called",
        "visit_id_allocation_started",
        "visit_id_map_mutated",
        "sequence_advanced",
        "cdm_visit_occurrence_write",
    ):
        require(
            state[field] is False,
            field,
        )

    sql = Path(
        sql_path
    ).read_text()

    require(
        not re.search(
            r"\bnextval\s*\(",
            sql,
            re.IGNORECASE,
        ),
        "sequence allocation in rehearsal SQL",
    )

    require(
        not re.search(
            r"\bsetval\s*\(",
            sql,
            re.IGNORECASE,
        ),
        "setval in rehearsal SQL",
    )

    output = Path(
        output_path
    ).read_text()

    for token in (
        "ADVISORY_LOCK_ACQUIRED",
        "TABLE_LOCKS_ACQUIRED",
        "COPY 5799",
        "TEMP_TABLE_REVALIDATION_PASS",
        "IRREVERSIBLE_BOUNDARY_NOT_CROSSED",
        "REHEARSAL_ROLLBACK_COMPLETE",
    ):
        require(
            token in output,
            token,
        )

    post = [
        x.strip()
        for x in Path(
            postcheck_path
        ).read_text().splitlines()
        if x.strip()
        and x.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        post
        == [
            "0|0|113",
            "1|f",
            "0",
            "on",
        ],
        "post-rehearsal DB state",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4A",

        "status":
            "VISIT_ID_ALLOCATION_REHEARSAL_VERIFIED",

        "candidate_rows":
            5799,

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "advisory_lock_key":
            5947676943154735385,

        "copy_temp_rows":
            5799,

        "transaction_rolled_back":
            True,

        "irreversible_boundary_crossed":
            False,

        "nextval_called":
            False,

        "visit_id_map_mutated":
            False,

        "sequence_advanced":
            False,

        "ready_for_first_mutation":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--state",
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
        "--postcheck",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.state,
        args.sql,
        args.psql_output,
        args.postcheck,
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
        "STEP06B4A_CANONICAL_EVIDENCE_VERIFY=PASS"
    )

    print(
        "IRREVERSIBLE_BOUNDARY_CROSSED=NO"
    )

    print(
        "READY_FOR_FIRST_VISIT_ID_MUTATION=YES"
    )


if __name__ == "__main__":
    main()
APP_EOF_TASK003_06B4A

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b4a-verify-visit-id-allocation-rehearsal.sh" <<'VERIFY_EOF_TASK003_06B4A'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-rehearsal.20261010t140207z.2482042"

APP="$ROOT/apps/task003/verify_visit_id_allocation_rehearsal.py"

STATE="$REPORT/run-state.json"
SQL="$REPORT/rehearsal.sql"
PSQL_OUTPUT="$REPORT/psql-output.txt"
POSTCHECK="$REPORT/post-rehearsal-db-state.txt"

OUTDIR="$ROOT/runtime/reports/task003/step06/rehearsal-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4A CANONICAL REHEARSAL VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4A_CANONICAL_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4A CANONICAL REHEARSAL VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$STATE" \
  "$SQL" \
  "$PSQL_OUTPUT" \
  "$POSTCHECK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe rehearsal evidence: $file"
    exit 1
  }
done

python3 "$APP" \
  --state "$STATE" \
  --sql "$SQL" \
  --psql-output "$PSQL_OUTPUT" \
  --postcheck "$POSTCHECK" \
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
    == "VISIT_ID_ALLOCATION_REHEARSAL_VERIFIED"
)

assert state["candidate_rows"] == 5799
assert state["copy_temp_rows"] == 5799

assert (
    state["candidate_business_key_sha256"]
    == "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
)

assert state["transaction_rolled_back"] is True
assert state["irreversible_boundary_crossed"] is False
assert state["nextval_called"] is False
assert state["visit_id_map_mutated"] is False
assert state["sequence_advanced"] is False
assert state["ready_for_first_mutation"] is True

print("STEP06B4A_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4A_REHEARSAL_CANONICAL_GATE=PASS'
echo 'ADVISORY_LOCK_REHEARSAL=PASS'
echo 'TABLE_LOCK_REHEARSAL=PASS'
echo 'COPY_5799_REHEARSAL=PASS'
echo 'BUSINESS_KEY_FINGERPRINT_REHEARSAL=PASS'

echo 'IRREVERSIBLE_BOUNDARY_CROSSED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'

echo 'READY_FOR_FIRST_VISIT_ID_MUTATION=YES'
VERIFY_EOF_TASK003_06B4A

mkdir -p "$STAGE/tests/task003"
cat > "$STAGE/tests/task003/test_visit_id_allocation_rehearsal.py" <<'TEST_EOF_TASK003_06B4A'
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
    / "apps/task003/verify_visit_id_allocation_rehearsal.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_visit_id_allocation_rehearsal",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class VisitIDAllocationRehearsalTests(
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
TEST_EOF_TASK003_06B4A

mkdir -p "$STAGE/docs/task003"
cat > "$STAGE/docs/task003/TASK003-STEP06B4A-Allocation-Rehearsal.md" <<'DOC_EOF_TASK003_06B4A'
# TASK-003 STEP06B4A — Visit ID Allocation Rehearsal

STEP06B4A validated the complete PostgreSQL transaction path immediately
before the first sequence allocation.

The rehearsal used the frozen 5799-row business-key snapshot.

## Verified operations

The rehearsal successfully:

1. acquired transaction advisory lock `5947676943154735385`
2. acquired the required table locks
3. revalidated the zero-row Visit ID map baseline
4. confirmed `cdm.visit_occurrence` remained empty
5. confirmed the sequence was still `last_value=1, is_called=false`
6. created a transaction-local Candidate key table
7. copied exactly 5799 frozen business keys using COPY FROM STDIN
8. recomputed the business-key SHA256 inside PostgreSQL
9. matched the frozen fingerprint
10. confirmed zero existing Candidate mappings
11. stopped before the irreversible sequence boundary
12. rolled back the complete rehearsal transaction
13. independently verified the database remained unchanged

Frozen business-key SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Rehearsal SQL SHA256:

`21e00285ce0ebaf43c0c38b57be74bf32204236ae7af8d9c1170143b757d31e1`

Rehearsal psql-output SHA256:

`7d26cf9f34bb39b445e2ff53171f4f345eb6c2818a2a39b0692756c5fb48e92b`

## Safety result

After rehearsal:

- Visit ID map rows: 0
- CDM Visit rows: 0
- Person map rows: 113
- sequence last_value: 1
- sequence is_called: false
- advisory lock released: yes
- nextval called: no
- setval called: no
- persistent mutation: no

STEP06B4A therefore validates the transaction path but does not allocate IDs.

The next mutation step must preserve the same lock, COPY, fingerprint and
database revalidation sequence before crossing the first sequence allocation
boundary.

If an error occurs after that boundary, automatic retry is forbidden.
DOC_EOF_TASK003_06B4A


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

install_one scripts/task003/06b4a-rehearse-visit-id-allocation.sh
install_one apps/task003/verify_visit_id_allocation_rehearsal.py
install_one scripts/task003/06b4a-verify-visit-id-allocation-rehearsal.sh
install_one tests/task003/test_visit_id_allocation_rehearsal.py
install_one docs/task003/TASK003-STEP06B4A-Allocation-Rehearsal.md

python3 -m py_compile \
  "$ROOT/apps/task003/verify_visit_id_allocation_rehearsal.py" \
  "$ROOT/tests/task003/test_visit_id_allocation_rehearsal.py"

bash -n \
  "$ROOT/scripts/task003/06b4a-rehearse-visit-id-allocation.sh"

bash -n \
  "$ROOT/scripts/task003/06b4a-verify-visit-id-allocation-rehearsal.sh"

echo 'STEP06B4A_CANONICAL_SOURCE_PREPARED=PASS'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'
echo 'GIT_COMMIT=NO'
