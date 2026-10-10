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

EXPECTED_HEAD=6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a

RUN_ID=visit-proc-20261009t192437z-2081886

FREEZE_STATE="$ROOT/runtime/reports/task003/step06/readonly-preflight-freeze/run-state.json"

A2_PLAN="$ROOT/runtime/reports/task003/step06/visit-id-allocation-plans/$RUN_ID/plan.json"

A3_DIR="$ROOT/runtime/reports/task003/step06/visit-id-reconciliation.20261010t004249z-2195105"
A3_STATE="$A3_DIR/run-state.json"
A3_RESULT="$A3_DIR/reconciliation-result.json"

CONTRACT_DIR="$ROOT/runtime/reports/task003/step06/visit-id-mutation-contracts/$RUN_ID"
CONTRACT="$CONTRACT_DIR/contract.json"
DISCOVERY="$CONTRACT_DIR/fresh-readonly-database-state.txt"

EXPECTED_PLAN_SHA=28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93
EXPECTED_RECON_SHA=fb2905064173c564a8074b7f946c976b8d2ea1e0165ce7f2f3f2b3feb258eb31
EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e

SEQUENCE=etl.visit_occurrence_id_map_visit_occurrence_id_seq

# Deterministically derived from:
# TASK003:etl.visit_occurrence_id_map:visit_occurrence_id_allocation:v1
ADVISORY_LOCK_KEY=5947676943154735385

echo '#### TASK003 STEP06B1 VISIT ID MUTATION CONTRACT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B1_CONTRACT=$CONTRACT"
  echo "STEP06B1_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B1 VISIT ID MUTATION CONTRACT OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

cd "$ROOT"

mkdir -p "$CONTRACT_DIR"

echo '=== 1. Verify STEP06A final Git checkpoint ==='

HEAD="$(git rev-parse HEAD)"
BRANCH="$(git branch --show-current)"
REMOTE_MAIN="$(
  git ls-remote origin refs/heads/main |
  awk '{print $1}'
)"

echo "CURRENT_HEAD=$HEAD"
echo "CURRENT_LOCAL_BRANCH=${BRANCH:-DETACHED}"
echo "REMOTE_MAIN_HEAD=$REMOTE_MAIN"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: local HEAD is not frozen STEP06A checkpoint'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main is not frozen STEP06A checkpoint'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: repository working tree is not clean'
  git status --short
  exit 1
}

echo 'STEP06A_GIT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Verify frozen STEP06A evidence ==='

for file in \
  "$FREEZE_STATE" \
  "$A2_PLAN" \
  "$A3_STATE" \
  "$A3_RESULT"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe STEP06A evidence: $file"
    exit 1
  }
done

python3 - \
  "$FREEZE_STATE" \
  "$A2_PLAN" \
  "$A3_STATE" \
  "$A3_RESULT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_PLAN_SHA" \
  "$EXPECTED_RECON_SHA" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_FREEZE'
import hashlib
import json
import sys
from pathlib import Path


freeze_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
a3_state_path = Path(sys.argv[3])
a3_result_path = Path(sys.argv[4])

expected_head = sys.argv[5]
expected_plan_sha = sys.argv[6]
expected_recon_sha = sys.argv[7]
expected_key_sha = sys.argv[8]


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


freeze = load(freeze_path)
plan = load(plan_path)
a3_state = load(a3_state_path)
a3_result = load(a3_result_path)

assert freeze["status"] == "VISIT_ID_READONLY_PREFLIGHT_FROZEN"
assert freeze["git_checkpoint"] == "4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4"

assert freeze["candidate_rows"] == 5799
assert freeze["candidate_unique_business_keys"] == 5799
assert freeze["existing_candidate_mappings"] == 0
assert freeze["new_candidate_mappings"] == 5799

assert freeze["candidate_business_key_sha256"] == expected_key_sha

assert freeze["visit_id_allocation_started"] is False
assert freeze["visit_id_map_mutated"] is False
assert freeze["sequence_advanced"] is False
assert freeze["cdm_visit_occurrence_write"] is False
assert freeze["s3_mutation"] is False

assert sha(plan_path) == expected_plan_sha
assert sha(a3_result_path) == expected_recon_sha

assert plan["status"] == "VISIT_ID_ALLOCATION_PLAN_READY"

assert (
    plan["sequence"]["name"]
    == "etl.visit_occurrence_id_map_visit_occurrence_id_seq"
)

assert plan["sequence"]["last_value_direct"] == 1
assert plan["sequence"]["is_called"] is False
assert plan["sequence"]["automatic_default_nextval"] is False
assert plan["sequence"]["explicit_allocation_required"] is True

assert (
    a3_state["status"]
    == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_VERIFIED"
)

assert a3_state["candidate_business_key_sha256"] == expected_key_sha
assert a3_state["existing_candidate_mappings"] == 0
assert a3_state["new_candidate_mappings"] == 5799

assert (
    a3_result["status"]
    == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS"
)

assert a3_result["candidate"]["business_key_sha256"] == expected_key_sha
assert a3_result["reconciliation"]["existing_mappings"] == 0
assert a3_result["reconciliation"]["new_mappings"] == 5799
assert a3_result["reconciliation"]["map_only_synthea_keys"] == 0

print("STEP06A_FROZEN_EVIDENCE_GATE=PASS")
print("CANDIDATE_BUSINESS_KEY_SHA256=" + expected_key_sha)
print("ALLOCATION_PLAN_SHA256=" + expected_plan_sha)
print("RECONCILIATION_RESULT_SHA256=" + expected_recon_sha)
print("STEP06B_PARENT_CHECKPOINT=" + expected_head)
PY_FREEZE

echo '=== 3. Fresh READ ONLY database capability discovery ==='

TMP_DISCOVERY="$CONTRACT_DIR/.fresh-readonly-database-state.$$.tmp"

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
  > "$TMP_DISCOVERY" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

\echo IDENTITY
SELECT
    current_database(),
    current_user,
    current_setting('transaction_read_only');

\echo COUNTS
SELECT
    (SELECT count(*) FROM etl.visit_occurrence_id_map),
    (SELECT count(*) FROM cdm.visit_occurrence),
    (SELECT count(*) FROM etl.person_id_map);

\echo SEQUENCE_DIRECT_STATE
SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

\echo SEQUENCE_CATALOG
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

\echo SERIAL_SEQUENCE_BINDING
SELECT
    COALESCE(
        pg_get_serial_sequence(
            'etl.visit_occurrence_id_map',
            'visit_occurrence_id'
        ),
        'NONE'
    );

\echo COLUMN_DEFAULT
SELECT
    COALESCE(column_default, 'NONE')
FROM information_schema.columns
WHERE table_schema = 'etl'
  AND table_name = 'visit_occurrence_id_map'
  AND column_name = 'visit_occurrence_id';

\echo CAPABILITIES
SELECT
    has_sequence_privilege(
        current_user,
        'etl.visit_occurrence_id_map_visit_occurrence_id_seq',
        'USAGE'
    ),
    has_sequence_privilege(
        current_user,
        'etl.visit_occurrence_id_map_visit_occurrence_id_seq',
        'UPDATE'
    ),
    has_table_privilege(
        current_user,
        'etl.visit_occurrence_id_map',
        'SELECT'
    ),
    has_table_privilege(
        current_user,
        'etl.visit_occurrence_id_map',
        'INSERT'
    ),
    has_table_privilege(
        current_user,
        'etl.person_id_map',
        'SELECT'
    ),
    has_table_privilege(
        current_user,
        'cdm.visit_occurrence',
        'SELECT'
    ),
    has_database_privilege(
        current_user,
        current_database(),
        'TEMP'
    ),
    has_function_privilege(
        current_user,
        'pg_catalog.pg_advisory_xact_lock(bigint)',
        'EXECUTE'
    );

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

\echo READ_ONLY_FINAL
SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$TMP_DISCOVERY"

echo '=== 4. Validate fresh mutation prerequisites ==='

python3 - \
  "$TMP_DISCOVERY" \
  "$SEQUENCE" \
  <<'PY_DB'
import sys
from pathlib import Path


path = Path(sys.argv[1])
expected_sequence = sys.argv[2]

lines = [
    line.strip()
    for line in path.read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        "BEGIN",
        "SET",
        "ROLLBACK",
    }
]


def value_after(marker):
    try:
        index = lines.index(marker)
    except ValueError:
        raise AssertionError(
            "missing marker: " + marker
        )

    assert index + 1 < len(lines), marker
    return lines[index + 1]


identity = value_after("IDENTITY")
counts = value_after("COUNTS")
sequence_direct = value_after("SEQUENCE_DIRECT_STATE")
sequence_catalog = value_after("SEQUENCE_CATALOG")
binding = value_after("SERIAL_SEQUENCE_BINDING")
column_default = value_after("COLUMN_DEFAULT")
capabilities = value_after("CAPABILITIES")
collisions = value_after("MAP_COLLISIONS")
overlap = value_after("CDM_MAP_OVERLAP")
readonly = value_after("READ_ONLY_FINAL")

assert identity == "omop|omop_admin|on", identity
assert counts == "0|0|113", counts
assert sequence_direct == "1|f", sequence_direct
assert sequence_catalog == "1|1|2147483647|1|f|1|NULL", sequence_catalog
assert binding == expected_sequence, binding
assert column_default == "NONE", column_default

caps = capabilities.split("|")

assert len(caps) == 8, caps
assert caps == ["t"] * 8, capabilities

assert collisions == "0|0", collisions
assert overlap == "0", overlap
assert readonly == "on", readonly

print("FRESH_MUTATION_PREREQUISITES=PASS")

print("VISIT_MAP_ROWS=0")
print("CDM_VISIT_ROWS=0")
print("PERSON_MAP_ROWS=113")

print("SEQUENCE_LAST_VALUE=1")
print("SEQUENCE_IS_CALLED=FALSE")

print("SEQUENCE_USAGE_PRIVILEGE=PASS")
print("SEQUENCE_UPDATE_PRIVILEGE=PASS")
print("MAP_SELECT_PRIVILEGE=PASS")
print("MAP_INSERT_PRIVILEGE=PASS")
print("TEMP_TABLE_PRIVILEGE=PASS")
print("ADVISORY_LOCK_EXECUTE_PRIVILEGE=PASS")

print("MAP_BUSINESS_KEY_COLLISIONS=0")
print("MAP_VISIT_ID_COLLISIONS=0")
print("CDM_MAP_OVERLAP=0")

print("DATABASE_DISCOVERY=READ_ONLY")
PY_DB

if [[ -e "$DISCOVERY" ]]; then
  if cmp -s "$TMP_DISCOVERY" "$DISCOVERY"; then
    echo 'FRESH_DISCOVERY_ALREADY_IDENTICAL=YES'
    rm -f "$TMP_DISCOVERY"
  else
    echo 'ERROR: existing STEP06B1 database discovery differs'
    echo "EXISTING=$DISCOVERY"
    echo "NEW=$TMP_DISCOVERY"
    exit 1
  fi
else
  mv "$TMP_DISCOVERY" "$DISCOVERY"
fi

echo '=== 5. Build deterministic mutation contract ==='

TMP_CONTRACT="$CONTRACT_DIR/.contract.$$.tmp"

python3 - \
  "$TMP_CONTRACT" \
  "$EXPECTED_HEAD" \
  "$RUN_ID" \
  "$EXPECTED_PLAN_SHA" \
  "$EXPECTED_RECON_SHA" \
  "$EXPECTED_KEY_SHA" \
  "$SEQUENCE" \
  "$ADVISORY_LOCK_KEY" \
  <<'PY_CONTRACT'
import json
import sys
from pathlib import Path


output = Path(sys.argv[1])

checkpoint = sys.argv[2]
run_id = sys.argv[3]
plan_sha = sys.argv[4]
recon_sha = sys.argv[5]
key_sha = sys.argv[6]
sequence = sys.argv[7]
lock_key = int(sys.argv[8])


contract = {
    "task": "TASK-003",
    "step": "STEP-06B1",
    "status": "VISIT_ID_MUTATION_CONTRACT_READY",
    "contract_version": "v1",

    "git_checkpoint": checkpoint,

    "run_id": run_id,

    "scope": {
        "mutation_target":
            "etl.visit_occurrence_id_map",

        "cdm_visit_occurrence_write":
            False,

        "s3_write":
            False,

        "business_key": [
            "source_system",
            "source_encounter_id"
        ],

        "candidate_rows":
            5799,

        "candidate_unique_business_keys":
            5799,

        "candidate_business_key_sha256":
            key_sha,
    },

    "lineage": {
        "allocation_plan_sha256":
            plan_sha,

        "reconciliation_result_sha256":
            recon_sha,
    },

    "required_pre_mutation_state": {
        "visit_map_rows":
            0,

        "cdm_visit_rows":
            0,

        "person_map_rows":
            113,

        "sequence": {
            "name":
                sequence,

            "last_value":
                1,

            "is_called":
                False,

            "increment_by":
                1,

            "cycle":
                False,

            "column_default":
                None,

            "automatic_default_nextval":
                False,
        },

        "map_business_key_collision_groups":
            0,

        "map_visit_id_collision_groups":
            0,

        "cdm_map_overlap_rows":
            0,
    },

    "serialization": {
        "advisory_lock": {
            "function":
                "pg_advisory_xact_lock(bigint)",

            "key":
                lock_key,

            "scope":
                "transaction",

            "purpose":
                "TASK003 Visit ID allocation serialization",
        },

        "table_locks": [
            {
                "relation":
                    "etl.visit_occurrence_id_map",

                "mode":
                    "SHARE ROW EXCLUSIVE",

                "purpose":
                    "block concurrent map mutations"
            },
            {
                "relation":
                    "etl.person_id_map",

                "mode":
                    "SHARE",

                "purpose":
                    "freeze Person mapping during allocation validation"
            },
            {
                "relation":
                    "cdm.visit_occurrence",

                "mode":
                    "SHARE",

                "purpose":
                    "prevent concurrent Visit CDM mutation while map IDs are allocated"
            }
        ],

        "lock_order": [
            "pg_advisory_xact_lock",
            "etl.visit_occurrence_id_map",
            "etl.person_id_map",
            "cdm.visit_occurrence"
        ]
    },

    "candidate_key_transport": {
        "required_before_mutation":
            True,

        "producer_step":
            "STEP-06B2",

        "format":
            "UTF-8 TSV",

        "columns": [
            "source_system",
            "source_encounter_id"
        ],

        "ordering": [
            "source_system ASC",
            "source_encounter_id ASC"
        ],

        "expected_rows":
            5799,

        "expected_unique_rows":
            5799,

        "expected_business_key_sha256":
            key_sha,

        "database_ingest":
            "COPY temporary table FROM STDIN",

        "temporary_table_primary_key": [
            "source_system",
            "source_encounter_id"
        ],

        "persistent_staging_table":
            False,
    },

    "transaction_protocol": [
        "BEGIN",
        "SET LOCAL lock_timeout",
        "SET LOCAL statement_timeout",
        "pg_advisory_xact_lock",
        "LOCK etl.visit_occurrence_id_map",
        "LOCK etl.person_id_map",
        "LOCK cdm.visit_occurrence",
        "revalidate exact frozen database state",
        "create transaction-local candidate key temporary table",
        "COPY exact STEP06B2 candidate key snapshot through STDIN",
        "verify 5799 rows and 5799 unique business keys",
        "verify zero existing Candidate mappings",
        "verify zero DB-only conflicting Synthea keys for this frozen batch",
        "verify sequence state immediately before first nextval",
        "allocate only in deterministic business-key order",
        "call explicit nextval once per new business key",
        "insert explicit visit_occurrence_id and business key",
        "verify exact 5799-key map coverage",
        "verify no duplicate business keys or Visit IDs",
        "verify cdm.visit_occurrence remains unchanged",
        "COMMIT"
    ],

    "allocation_policy": {
        "method":
            "explicit nextval in deterministic business-key order",

        "predicted_first_id":
            1,

        "predicted_last_id":
            5799,

        "predicted_range_authoritative":
            False,

        "authoritative_state":
            "committed etl.visit_occurrence_id_map rows",

        "existing_mapping_reassignment":
            "FORBIDDEN",

        "sequence_gap_policy":
            "ACCEPT_GAPS_NEVER_REWIND",

        "setval_backward":
            "FORBIDDEN",
    },

    "failure_policy": {
        "before_first_nextval": {
            "sequence_may_have_advanced":
                False,

            "retry":
                "allowed only after fresh full revalidation"
        },

        "after_first_nextval_before_commit": {
            "sequence_may_have_advanced":
                True,

            "map_rows_may_rollback":
                True,

            "blind_retry":
                False,

            "required_action":
                "preserve evidence and enter explicit recovery reconciliation"
        },

        "after_commit": {
            "mapping_authoritative":
                True,

            "required_action":
                "independent verification before any CDM Visit write"
        },

        "never": [
            "blindly retry after uncertain nextval execution",
            "rewind sequence with setval",
            "reassign an existing business key to another Visit ID",
            "combine Visit ID allocation with cdm.visit_occurrence loading"
        ]
    },

    "post_commit_verification": {
        "independent_session":
            True,

        "required_candidate_coverage":
            5799,

        "required_unique_business_keys":
            5799,

        "required_unique_visit_ids":
            5799,

        "required_cdm_visit_rows":
            0,

        "verify_sequence_state":
            True,

        "verify_mapping_fingerprint":
            True,

        "cdm_write_allowed_during_verification":
            False,
    },

    "safety": {
        "contract_build_database_access":
            "READ_ONLY",

        "contract_build_s3_access":
            "NONE",

        "advisory_lock_acquired":
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
    },
}


output.write_text(
    json.dumps(
        contract,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print("VISIT_ID_MUTATION_CONTRACT_BUILD=PASS")
print("ADVISORY_LOCK_KEY=" + str(lock_key))
print("SEQUENCE_GAP_POLICY=ACCEPT_GAPS_NEVER_REWIND")
print("SETVAL_BACKWARD=FORBIDDEN")
print("CDM_VISIT_WRITE_IN_ALLOCATION_TRANSACTION=NO")
PY_CONTRACT

python3 -m json.tool \
  "$TMP_CONTRACT" \
  >/dev/null

echo '=== 6. Validate mutation contract semantics ==='

python3 - \
  "$TMP_CONTRACT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  "$ADVISORY_LOCK_KEY" \
  <<'PY_VALIDATE'
import json
import sys
from pathlib import Path


contract = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_head = sys.argv[2]
expected_key_sha = sys.argv[3]
expected_lock = int(sys.argv[4])

assert contract["task"] == "TASK-003"
assert contract["step"] == "STEP-06B1"
assert contract["status"] == "VISIT_ID_MUTATION_CONTRACT_READY"

assert contract["git_checkpoint"] == expected_head

scope = contract["scope"]

assert scope["mutation_target"] == "etl.visit_occurrence_id_map"
assert scope["cdm_visit_occurrence_write"] is False
assert scope["s3_write"] is False
assert scope["candidate_rows"] == 5799
assert scope["candidate_unique_business_keys"] == 5799
assert scope["candidate_business_key_sha256"] == expected_key_sha

pre = contract["required_pre_mutation_state"]

assert pre["visit_map_rows"] == 0
assert pre["cdm_visit_rows"] == 0
assert pre["person_map_rows"] == 113

seq = pre["sequence"]

assert seq["last_value"] == 1
assert seq["is_called"] is False
assert seq["increment_by"] == 1
assert seq["cycle"] is False
assert seq["column_default"] is None
assert seq["automatic_default_nextval"] is False

lock = contract["serialization"]["advisory_lock"]

assert lock["key"] == expected_lock
assert lock["scope"] == "transaction"

transport = contract["candidate_key_transport"]

assert transport["producer_step"] == "STEP-06B2"
assert transport["expected_rows"] == 5799
assert transport["expected_unique_rows"] == 5799
assert transport["expected_business_key_sha256"] == expected_key_sha
assert transport["persistent_staging_table"] is False

policy = contract["allocation_policy"]

assert (
    policy["method"]
    == "explicit nextval in deterministic business-key order"
)

assert policy["predicted_first_id"] == 1
assert policy["predicted_last_id"] == 5799
assert policy["predicted_range_authoritative"] is False
assert policy["existing_mapping_reassignment"] == "FORBIDDEN"
assert policy["sequence_gap_policy"] == "ACCEPT_GAPS_NEVER_REWIND"
assert policy["setval_backward"] == "FORBIDDEN"

failure = contract["failure_policy"]

assert (
    failure["after_first_nextval_before_commit"]
    ["sequence_may_have_advanced"]
    is True
)

assert (
    failure["after_first_nextval_before_commit"]
    ["blind_retry"]
    is False
)

assert (
    "rewind sequence with setval"
    in failure["never"]
)

post = contract["post_commit_verification"]

assert post["independent_session"] is True
assert post["required_candidate_coverage"] == 5799
assert post["required_unique_business_keys"] == 5799
assert post["required_unique_visit_ids"] == 5799
assert post["required_cdm_visit_rows"] == 0

safety = contract["safety"]

assert safety["contract_build_database_access"] == "READ_ONLY"
assert safety["contract_build_s3_access"] == "NONE"
assert safety["advisory_lock_acquired"] is False
assert safety["nextval_called"] is False
assert safety["setval_called"] is False
assert safety["visit_id_allocation_started"] is False
assert safety["visit_id_map_mutated"] is False
assert safety["sequence_advanced"] is False
assert safety["cdm_visit_occurrence_write"] is False

print("MUTATION_CONTRACT_SEMANTICS=PASS")
print("EXACT_PRE_MUTATION_STATE_REQUIRED=YES")
print("FULL_CANDIDATE_KEY_SNAPSHOT_REQUIRED=YES")
print("MUTATION_AND_CDM_LOAD_SEPARATED=YES")
print("BLIND_RETRY_AFTER_NEXTVAL=FORBIDDEN")
PY_VALIDATE

if [[ -e "$CONTRACT" ]]; then
  if cmp -s "$TMP_CONTRACT" "$CONTRACT"; then
    echo 'MUTATION_CONTRACT_ALREADY_IDENTICAL=YES'
    rm -f "$TMP_CONTRACT"
  else
    echo 'ERROR: existing mutation contract conflicts with newly derived contract'
    echo "EXISTING=$CONTRACT"
    echo "NEW=$TMP_CONTRACT"
    exit 1
  fi
else
  mv "$TMP_CONTRACT" "$CONTRACT"
fi

echo '=== 7. Compute and verify deterministic advisory-lock derivation ==='

python3 - "$ADVISORY_LOCK_KEY" <<'PY_LOCK'
import hashlib
import sys


namespace = (
    b"TASK003:"
    b"etl.visit_occurrence_id_map:"
    b"visit_occurrence_id_allocation:"
    b"v1"
)

derived = (
    int.from_bytes(
        hashlib.sha256(namespace).digest()[:8],
        "big",
    )
    & ((1 << 63) - 1)
)

expected = int(sys.argv[1])

assert derived == expected, (
    derived,
    expected,
)

print("ADVISORY_LOCK_DERIVATION=PASS")
print("ADVISORY_LOCK_KEY=" + str(derived))
PY_LOCK

echo '=== 8. Static proof STEP06B1 itself performed no allocation ==='

CONTRACT_SHA="$(
  sha256sum "$CONTRACT" |
  awk '{print $1}'
)"

DISCOVERY_SHA="$(
  sha256sum "$DISCOVERY" |
  awk '{print $1}'
)"

echo "MUTATION_CONTRACT_SHA256=$CONTRACT_SHA"
echo "FRESH_DATABASE_DISCOVERY_SHA256=$DISCOVERY_SHA"

echo '=== 9. Final STEP06B1 verdict ==='

echo 'STEP06B1_VISIT_ID_MUTATION_CONTRACT=PASS'

echo "STEP06A_FINAL_GIT_CHECKPOINT=$EXPECTED_HEAD"

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'
echo "CANDIDATE_BUSINESS_KEY_SHA256=$EXPECTED_KEY_SHA"

echo 'CURRENT_VISIT_MAP_ROWS=0'
echo 'CURRENT_CDM_VISIT_ROWS=0'
echo 'CURRENT_PERSON_MAP_ROWS=113'

echo 'SEQUENCE_LAST_VALUE=1'
echo 'SEQUENCE_IS_CALLED=FALSE'

echo "ADVISORY_LOCK_KEY=$ADVISORY_LOCK_KEY"
echo 'ADVISORY_LOCK_ACQUIRED=NO'

echo 'CANDIDATE_KEY_SNAPSHOT_REQUIRED=YES'
echo 'NEXT_REQUIRED_STEP=STEP06B2'

echo 'PREDICTED_VISIT_ID_RANGE=1..5799'
echo 'PREDICTED_RANGE_AUTHORITATIVE=NO'

echo 'SEQUENCE_GAP_POLICY=ACCEPT_GAPS_NEVER_REWIND'
echo 'BLIND_RETRY_AFTER_NEXTVAL=FORBIDDEN'
echo 'CDM_VISIT_WRITE_IN_ALLOCATION_TRANSACTION=NO'

echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'
echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'DATABASE_DISCOVERY=READ_ONLY'
echo 'S3_MUTATION=NO'
echo 'KUBERNETES_MUTATION=NO'
echo 'GIT_COMMIT=NO'
