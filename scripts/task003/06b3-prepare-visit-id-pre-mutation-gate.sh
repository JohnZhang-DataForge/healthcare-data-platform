#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06b3-generator.XXXXXX)"

echo '#### TASK003 STEP06B3 PREPARE PRE-MUTATION GATE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06B3_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B3 PREPARE PRE-MUTATION GATE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b1-build-visit-id-mutation-contract.sh" <<'B1_RUNNER_EOF_TASK003_06B3'
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
B1_RUNNER_EOF_TASK003_06B3

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b2-freeze-visit-business-key-snapshot.sh" <<'B2_RUNNER_EOF_TASK003_06B3'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-spark

EXPECTED_HEAD=6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a

RUN_ID=visit-proc-20261009t192437z-2081886

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e
EXPECTED_B1_SHA=58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0

B1_CONTRACT="$ROOT/runtime/reports/task003/step06/visit-id-mutation-contracts/$RUN_ID/contract.json"

PROCESSED_DATA_URI='s3a://health-processed/contract_version=v1/entity=visit_occurrence/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/raw_publish_run_id=encounter-raw-20261009T005128Z-1681690/run_id=visit-proc-20261009t192437z-2081886/data/'

SOURCE_APP=visit-id-recon-20261010t004249z-2195105

SNAPSHOT_DIR="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID"

SNAPSHOT="$SNAPSHOT_DIR/business-keys.tsv"
SNAPSHOT_META="$SNAPSHOT_DIR/snapshot.json"

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
SUFFIX="${STAMP}-$$"

APP="visit-key-freeze-${SUFFIX}"
CM="${APP}-app"

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshot-build.${SUFFIX}"

DRIVER="$REPORT/extract_visit_business_keys.py"
SOURCE_APP_JSON="$REPORT/source-sparkapplication.json"
APP_JSON="$REPORT/sparkapplication.json"
APP_FINAL_JSON="$REPORT/sparkapplication-final.json"
DRIVER_LOG="$REPORT/driver.log"

RAW_TSV="$REPORT/business-keys.raw.tsv"
CANONICAL_TSV="$REPORT/business-keys.canonical.tsv"

RESULT="$REPORT/result.json"
RUN_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06B2 VISIT BUSINESS KEY SNAPSHOT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B2_REPORT=$REPORT"
  echo "STEP06B2_SNAPSHOT=$SNAPSHOT"
  echo "STEP06B2_SNAPSHOT_META=$SNAPSHOT_META"
  echo "STEP06B2_SPARKAPPLICATION=$APP"
  echo "STEP06B2_CONFIGMAP=$CM"
  echo "STEP06B2_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06B2 VISIT BUSINESS KEY SNAPSHOT OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"
mkdir -p "$SNAPSHOT_DIR"

cd "$ROOT"

echo '=== 1. Verify STEP06A Git checkpoint ==='

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
  echo 'ERROR: local HEAD drifted'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main drifted'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: working tree is not clean'
  git status --short
  exit 1
}

echo 'STEP06A_GIT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Verify STEP06B1 mutation contract ==='

[[ -s "$B1_CONTRACT" && ! -L "$B1_CONTRACT" ]] || {
  echo 'ERROR: STEP06B1 mutation contract missing'
  exit 1
}

B1_SHA="$(
  sha256sum "$B1_CONTRACT" |
  awk '{print $1}'
)"

echo "MUTATION_CONTRACT_SHA256=$B1_SHA"
echo "EXPECTED_MUTATION_CONTRACT_SHA256=$EXPECTED_B1_SHA"

[[ "$B1_SHA" == "$EXPECTED_B1_SHA" ]] || {
  echo 'ERROR: STEP06B1 mutation contract SHA mismatch'
  exit 1
}

python3 - \
  "$B1_CONTRACT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_B1'
import json
import sys
from pathlib import Path

contract = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_head = sys.argv[2]
expected_key_sha = sys.argv[3]

assert contract["task"] == "TASK-003"
assert contract["step"] == "STEP-06B1"

assert (
    contract["status"]
    == "VISIT_ID_MUTATION_CONTRACT_READY"
)

assert contract["git_checkpoint"] == expected_head

scope = contract["scope"]

assert scope["candidate_rows"] == 5799
assert scope["candidate_unique_business_keys"] == 5799
assert scope["candidate_business_key_sha256"] == expected_key_sha

transport = contract["candidate_key_transport"]

assert transport["required_before_mutation"] is True
assert transport["producer_step"] == "STEP-06B2"
assert transport["format"] == "UTF-8 TSV"

assert transport["columns"] == [
    "source_system",
    "source_encounter_id",
]

assert transport["ordering"] == [
    "source_system ASC",
    "source_encounter_id ASC",
]

assert transport["expected_rows"] == 5799
assert transport["expected_unique_rows"] == 5799

assert (
    transport["expected_business_key_sha256"]
    == expected_key_sha
)

assert (
    transport["database_ingest"]
    == "COPY temporary table FROM STDIN"
)

assert transport["persistent_staging_table"] is False

safety = contract["safety"]

assert safety["nextval_called"] is False
assert safety["setval_called"] is False
assert safety["visit_id_allocation_started"] is False
assert safety["visit_id_map_mutated"] is False
assert safety["sequence_advanced"] is False

print('STEP06B1_CONTRACT_GATE=PASS')
PY_B1

echo '=== 3. Check immutable snapshot destination ==='

if [[ -e "$SNAPSHOT" || -e "$SNAPSHOT_META" ]]; then
  echo 'EXISTING_SNAPSHOT_DETECTED=YES'
  echo 'Existing snapshot will only be accepted if byte-identical.'
else
  echo 'EXISTING_SNAPSHOT_DETECTED=NO'
fi

echo '=== 4. Load proven STEP06A3 Spark runtime ==='

kubectl -n "$NS" \
  get sparkapplication "$SOURCE_APP" \
  -o json \
  > "$SOURCE_APP_JSON"

python3 - \
  "$SOURCE_APP_JSON" \
  "$SOURCE_APP" \
  <<'PY_RUNTIME'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_name = sys.argv[2]

assert doc["metadata"]["name"] == expected_name

state = (
    doc.get("status", {})
    .get("applicationState", {})
    .get("state")
)

assert state == "COMPLETED", state

blob = json.dumps(
    doc["spec"],
    sort_keys=True,
).lower()

assert "spark:3.5.7-python3" in blob
assert "s3a" in blob or "hadoop-aws" in blob

print('PROVEN_STEP06A3_SPARK_RUNTIME=PASS')
print('SOURCE_SPARKAPPLICATION_STATE=COMPLETED')
PY_RUNTIME

echo '=== 5. Build READ ONLY business-key extractor ==='

cat > "$DRIVER" <<'PY_DRIVER'
#!/usr/bin/env python3

import hashlib
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


EXPECTED_ROWS = 5799
EXPECTED_KEYS = 5799

EXPECTED_SOURCE_SYSTEM = "synthea"

EXPECTED_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

BEGIN_MARKER = (
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN"
)

END_MARKER = (
    "TASK003_STEP06B2_BUSINESS_KEYS_END"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    require(
        len(sys.argv) == 2,
        "Expected frozen Processed Candidate URI",
    )

    uri = sys.argv[1]

    spark = (
        SparkSession.builder
        .appName(
            "TASK003-STEP06B2-Visit-Business-Key-Snapshot"
        )
        .getOrCreate()
    )

    try:
        df = spark.read.parquet(
            uri
        )

        required = {
            "source_system",
            "source_encounter_id",
        }

        missing = (
            required
            - set(df.columns)
        )

        require(
            not missing,
            "Missing Candidate columns: "
            + repr(sorted(missing)),
        )

        candidate = (
            df.select(
                F.col(
                    "source_system"
                ).cast("string").alias(
                    "source_system"
                ),
                F.col(
                    "source_encounter_id"
                ).cast("string").alias(
                    "source_encounter_id"
                ),
            )
        )

        total_rows = candidate.count()

        require(
            total_rows == EXPECTED_ROWS,
            "Candidate row count mismatch",
        )

        invalid = (
            candidate
            .filter(
                F.col(
                    "source_system"
                ).isNull()
                | F.col(
                    "source_encounter_id"
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
                | F.col(
                    "source_system"
                ).contains("\t")
                | F.col(
                    "source_system"
                ).contains("\n")
                | F.col(
                    "source_system"
                ).contains("\r")
                | F.col(
                    "source_encounter_id"
                ).contains("\t")
                | F.col(
                    "source_encounter_id"
                ).contains("\n")
                | F.col(
                    "source_encounter_id"
                ).contains("\r")
            )
            .count()
        )

        require(
            invalid == 0,
            "Invalid business-key values",
        )

        systems = [
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
            systems == [
                EXPECTED_SOURCE_SYSTEM
            ],
            "Unexpected source systems: "
            + repr(systems),
        )

        unique = (
            candidate
            .distinct()
        )

        unique_rows = unique.count()

        require(
            unique_rows == EXPECTED_KEYS,
            "Unique business-key count mismatch",
        )

        duplicates = (
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
            duplicates == 0,
            "Duplicate Candidate business keys",
        )

        rows = (
            unique
            .orderBy(
                F.col(
                    "source_system"
                ).asc(),
                F.col(
                    "source_encounter_id"
                ).asc(),
            )
            .collect()
        )

        lines = [
            (
                str(
                    row[
                        "source_system"
                    ]
                )
                + "\t"
                + str(
                    row[
                        "source_encounter_id"
                    ]
                )
            )
            for row in rows
        ]

        require(
            len(lines) == EXPECTED_KEYS,
            "Collected key count mismatch",
        )

        require(
            lines == sorted(lines),
            "Business-key ordering mismatch",
        )

        require(
            len(set(lines))
            == EXPECTED_KEYS,
            "Business-key uniqueness mismatch",
        )

        payload = (
            "\n".join(lines)
            + "\n"
        ).encode(
            "utf-8"
        )

        sha = hashlib.sha256(
            payload
        ).hexdigest()

        require(
            sha == EXPECTED_SHA,
            "Business-key fingerprint mismatch: "
            + sha,
        )

        print(
            "TASK003_STEP06B2_ROWS="
            + str(total_rows)
        )

        print(
            "TASK003_STEP06B2_UNIQUE_KEYS="
            + str(unique_rows)
        )

        print(
            "TASK003_STEP06B2_BUSINESS_KEY_SHA256="
            + sha
        )

        print(BEGIN_MARKER)

        for line in lines:
            print(line)

        print(END_MARKER)

        print(
            "TASK003_STEP06B2_RESULT=PASS"
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

source = Path(
    sys.argv[1]
).read_text()

ast.parse(source)

for pattern in (
    r'\bnextval\s*\(',
    r'\bsetval\s*\(',
    r'\bINSERT\s+INTO\b',
    r'\bUPDATE\s+',
    r'\bDELETE\s+FROM\b',
    r'\bTRUNCATE\b',
    r'\.write\.',
    r'\.save\s*\(',
    r'\.saveAsTable\s*\(',
    r'\.insertInto\s*\(',
):
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

for token in (
    "EXPECTED_ROWS = 5799",
    "EXPECTED_KEYS = 5799",
    "EXPECTED_SOURCE_SYSTEM = \"synthea\"",
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN",
    "TASK003_STEP06B2_BUSINESS_KEYS_END",
    "TASK003_STEP06B2_RESULT=PASS",
):
    assert token in source, token

print('B2_EXTRACTOR_SYNTAX=PASS')
print('B2_EXTRACTOR_S3_READ_ONLY=PASS')
print('B2_DATABASE_ACCESS_PATH=ABSENT')
print('B2_S3_WRITE_PATH=ABSENT')
PY_STATIC

echo '=== 6. Create B2 runtime ConfigMap ==='

kubectl -n "$NS" \
  create configmap "$CM" \
  --from-file=extract_visit_business_keys.py="$DRIVER"

echo "B2_CONFIGMAP_CREATED=$CM"

echo '=== 7. Render B2 SparkApplication from proven runtime ==='

python3 - \
  "$SOURCE_APP_JSON" \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP'
import copy
import json
import sys
from pathlib import Path


source = json.loads(
    Path(sys.argv[1]).read_bytes()
)

target = Path(sys.argv[2])

app_name = sys.argv[3]
configmap_name = sys.argv[4]
candidate_uri = sys.argv[5]


spec = copy.deepcopy(
    source["spec"]
)

spec[
    "mainApplicationFile"
] = (
    "local:///opt/spark/b2/"
    "extract_visit_business_keys.py"
)

spec[
    "arguments"
] = [
    candidate_uri,
]

spec[
    "restartPolicy"
] = {
    "type": "Never",
}


# A3 had its application code in a ConfigMap.
# Strip every ConfigMap-backed application volume
# and add only the B2 source.
old_volumes = spec.get(
    "volumes",
    [],
)

removed_configmaps = {
    volume.get("name")
    for volume in old_volumes
    if "configMap" in volume
}

spec["volumes"] = [
    volume
    for volume in old_volumes
    if volume.get("name")
    not in removed_configmaps
]

spec["volumes"].append(
    {
        "name":
            "b2-app",

        "configMap": {
            "name":
                configmap_name,
        },
    }
)


def clean_section(name):
    section = spec.setdefault(
        name,
        {},
    )

    mounts = section.get(
        "volumeMounts",
        [],
    )

    section["volumeMounts"] = [
        mount
        for mount in mounts
        if mount.get("name")
        not in removed_configmaps
        and mount.get("name")
        != "b2-app"
    ]

    section["volumeMounts"].append(
        {
            "name":
                "b2-app",

            "mountPath":
                "/opt/spark/b2",

            "readOnly":
                True,
        }
    )

    # A3 used the OMOP Secret through envFrom on both
    # driver and executor. STEP06B2 must retain only
    # non-database envFrom sources such as the S3 Secret.
    section["envFrom"] = [
        item
        for item in section.get(
            "envFrom",
            [],
        )
        if item.get(
            "secretRef",
            {},
        ).get(
            "name"
        )
        != "dw-spark-omop-secret"
    ]

    labels = section.setdefault(
        "labels",
        {},
    )

    labels["task"] = "task003"
    labels["step"] = "step06b2"

    return section


driver = clean_section(
    "driver"
)

executor = clean_section(
    "executor"
)


# STEP06B2 does not use PostgreSQL.
# Remove all A3 DB credential references.
driver["env"] = [
    item
    for item in driver.get(
        "env",
        [],
    )
    if not item.get(
        "name",
        "",
    ).startswith(
        "A3_DB_"
    )
]


driver.setdefault(
    "serviceAccount",
    "spark-job",
)


doc = {
    "apiVersion":
        source["apiVersion"],

    "kind":
        source["kind"],

    "metadata": {
        "name":
            app_name,

        "namespace":
            "dw-spark",

        "labels": {
            "task":
                "task003",

            "step":
                "step06b2",

            "purpose":
                "visit-business-key-freeze",
        },
    },

    "spec":
        spec,
}


blob = json.dumps(
    doc,
    sort_keys=True,
)

assert "A3_DB_" not in blob
assert "dw-spark-omop-secret" not in blob


target.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print('B2_SPARKAPPLICATION_RENDER=PASS')
print('B2_DATABASE_SECRET_REFERENCE=ABSENT')
PY_APP

echo '=== 8. Validate rendered B2 SparkApplication ==='

python3 - \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_CHECK'
import json
import sys
from pathlib import Path


doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

app = sys.argv[2]
cm = sys.argv[3]
uri = sys.argv[4]

assert doc["metadata"]["name"] == app

spec = doc["spec"]

assert (
    spec["mainApplicationFile"]
    == "local:///opt/spark/b2/extract_visit_business_keys.py"
)

assert spec["arguments"] == [
    uri
]

assert spec["restartPolicy"]["type"] == "Never"

volumes = {
    item["name"]: item
    for item in spec.get(
        "volumes",
        []
    )
}

assert (
    volumes[
        "b2-app"
    ][
        "configMap"
    ][
        "name"
    ]
    == cm
)

blob = json.dumps(
    doc,
    sort_keys=True,
)

assert "A3_DB_" not in blob
assert "dw-spark-omop-secret" not in blob

low = blob.lower()

assert "nextval(" not in low
assert "setval(" not in low

print('B2_SPARKAPPLICATION_STATIC_VALIDATION=PASS')
print('B2_DATABASE_ACCESS_CONFIGURATION=ABSENT')
print('B2_NEXTVAL_PATH=ABSENT')
print('B2_SETVAL_PATH=ABSENT')
PY_CHECK

echo '=== 9. Launch real Spark READ ONLY key extraction ==='

kubectl apply \
  -f "$APP_JSON"

echo "SPARKAPPLICATION_CREATED=$APP"

echo '=== 10. Observe SparkApplication ==='

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

DRIVER_POD="$(
  kubectl -n "$NS" \
    get sparkapplication "$APP" \
    -o jsonpath='{.status.driverInfo.podName}' \
    2>/dev/null \
    || true
)"

echo "DRIVER_POD=${DRIVER_POD:-UNKNOWN}"

if [[ -n "${DRIVER_POD:-}" ]]; then
  kubectl -n "$NS" \
    logs "$DRIVER_POD" \
    > "$DRIVER_LOG" \
    2>&1 \
    || true
fi

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then

  tail -n 200 \
    "$DRIVER_LOG" \
    2>/dev/null \
    || true

  echo 'ERROR: STEP06B2 Spark extraction failed'
  echo 'FAILED_RUNTIME_RESOURCES_PRESERVED=YES'

  exit 1
fi

echo 'B2_SPARKAPPLICATION_COMPLETED=PASS'

echo '=== 11. Extract exact TSV bytes from driver log ==='

python3 - \
  "$DRIVER_LOG" \
  "$RAW_TSV" \
  <<'PY_EXTRACT'
import sys
from pathlib import Path


log_path = Path(sys.argv[1])
output = Path(sys.argv[2])

begin = (
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN"
)

end = (
    "TASK003_STEP06B2_BUSINESS_KEYS_END"
)


lines = log_path.read_text(
    errors="replace"
).splitlines()


begin_indexes = [
    index
    for index, line in enumerate(lines)
    if line.strip() == begin
]

end_indexes = [
    index
    for index, line in enumerate(lines)
    if line.strip() == end
]


assert len(begin_indexes) == 1, begin_indexes
assert len(end_indexes) == 1, end_indexes

start = begin_indexes[0]
finish = end_indexes[0]

assert finish > start

payload_lines = [
    line.strip("\r")
    for line in lines[
        start + 1:
        finish
    ]
]

assert len(payload_lines) == 5799, (
    len(payload_lines)
)

payload = (
    "\n".join(
        payload_lines
    )
    + "\n"
)

output.write_text(
    payload,
    encoding="utf-8",
    newline="\n",
)

print('B2_DRIVER_LOG_TSV_EXTRACTION=PASS')
print('EXTRACTED_BUSINESS_KEYS=5799')
PY_EXTRACT

echo '=== 12. Canonicalize and validate business-key snapshot ==='

python3 - \
  "$RAW_TSV" \
  "$CANONICAL_TSV" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_CANON'
import hashlib
import sys
from pathlib import Path


source = Path(sys.argv[1])
target = Path(sys.argv[2])
expected_sha = sys.argv[3]


raw = source.read_bytes()

assert b"\r" not in raw

text = raw.decode(
    "utf-8"
)

assert text.endswith(
    "\n"
)

lines = text.splitlines()

assert len(lines) == 5799


parsed = []

for index, line in enumerate(
    lines,
    start=1,
):

    fields = line.split(
        "\t"
    )

    assert len(fields) == 2, (
        index,
        fields,
    )

    source_system = fields[0]
    encounter_id = fields[1]

    assert source_system == "synthea"
    assert encounter_id

    assert "\t" not in encounter_id
    assert "\r" not in encounter_id
    assert "\n" not in encounter_id

    parsed.append(
        (
            source_system,
            encounter_id,
        )
    )


assert len(set(parsed)) == 5799

sorted_rows = sorted(
    parsed
)

assert parsed == sorted_rows


payload = "".join(
    source_system
    + "\t"
    + encounter_id
    + "\n"
    for (
        source_system,
        encounter_id
    )
    in sorted_rows
).encode(
    "utf-8"
)


sha = hashlib.sha256(
    payload
).hexdigest()


assert sha == expected_sha, (
    sha,
    expected_sha,
)


target.write_bytes(
    payload
)


print('B2_TSV_SCHEMA=PASS')
print('B2_TSV_ROWS=5799')
print('B2_TSV_UNIQUE_KEYS=5799')
print('B2_TSV_SORT_ORDER=PASS')
print('B2_TSV_UTF8=PASS')
print('B2_TSV_HEADER=NO')
print('B2_BUSINESS_KEY_SHA256=' + sha)
PY_CANON

echo '=== 13. Verify Spark-reported fingerprint ==='

SPARK_ROWS="$(
  grep '^TASK003_STEP06B2_ROWS=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_KEYS="$(
  grep '^TASK003_STEP06B2_UNIQUE_KEYS=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_SHA="$(
  grep '^TASK003_STEP06B2_BUSINESS_KEY_SHA256=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_RESULT="$(
  grep '^TASK003_STEP06B2_RESULT=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

echo "SPARK_REPORTED_ROWS=$SPARK_ROWS"
echo "SPARK_REPORTED_UNIQUE_KEYS=$SPARK_KEYS"
echo "SPARK_REPORTED_BUSINESS_KEY_SHA256=$SPARK_SHA"
echo "SPARK_REPORTED_RESULT=$SPARK_RESULT"

[[ "$SPARK_ROWS" == "5799" ]] || {
  echo 'ERROR: Spark row count mismatch'
  exit 1
}

[[ "$SPARK_KEYS" == "5799" ]] || {
  echo 'ERROR: Spark unique-key count mismatch'
  exit 1
}

[[ "$SPARK_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: Spark fingerprint mismatch'
  exit 1
}

[[ "$SPARK_RESULT" == "PASS" ]] || {
  echo 'ERROR: Spark extractor did not report PASS'
  exit 1
}

echo 'SPARK_REPORTED_SNAPSHOT_STATE=PASS'

echo '=== 14. Freeze immutable TSV snapshot ==='

if [[ -e "$SNAPSHOT" ]]; then

  if cmp -s \
    "$CANONICAL_TSV" \
    "$SNAPSHOT"
  then
    echo 'BUSINESS_KEY_SNAPSHOT_ALREADY_IDENTICAL=YES'
  else
    echo 'ERROR: existing immutable business-key snapshot differs'
    exit 1
  fi

else

  install \
    -m 0444 \
    "$CANONICAL_TSV" \
    "$SNAPSHOT"

  echo 'BUSINESS_KEY_SNAPSHOT_INSTALLED=YES'
fi

FINAL_SHA="$(
  sha256sum "$SNAPSHOT" |
  awk '{print $1}'
)"

FINAL_ROWS="$(
  wc -l < "$SNAPSHOT" |
  tr -d ' '
)"

echo "BUSINESS_KEY_SNAPSHOT_SHA256=$FINAL_SHA"
echo "BUSINESS_KEY_SNAPSHOT_ROWS=$FINAL_ROWS"

[[ "$FINAL_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: frozen snapshot SHA mismatch'
  exit 1
}

[[ "$FINAL_ROWS" == "5799" ]] || {
  echo 'ERROR: frozen snapshot row count mismatch'
  exit 1
}

echo 'IMMUTABLE_TSV_SNAPSHOT=PASS'

echo '=== 15. Build deterministic snapshot metadata ==='

TMP_META="$REPORT/snapshot.json"

python3 - \
  "$TMP_META" \
  "$EXPECTED_HEAD" \
  "$RUN_ID" \
  "$EXPECTED_B1_SHA" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_META'
import json
import sys
from pathlib import Path


output = Path(sys.argv[1])

checkpoint = sys.argv[2]
run_id = sys.argv[3]
b1_sha = sys.argv[4]
key_sha = sys.argv[5]


doc = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B2",

    "status":
        "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN",

    "snapshot_version":
        "v1",

    "git_checkpoint":
        checkpoint,

    "run_id":
        run_id,

    "source":
        "frozen Processed visit_occurrence Candidate",

    "format": {
        "encoding":
            "UTF-8",

        "delimiter":
            "TAB",

        "line_ending":
            "LF",

        "header":
            False,

        "columns": [
            "source_system",
            "source_encounter_id"
        ],

        "ordering": [
            "source_system ASC",
            "source_encounter_id ASC"
        ]
    },

    "rows":
        5799,

    "unique_business_keys":
        5799,

    "source_system":
        "synthea",

    "business_key_sha256":
        key_sha,

    "snapshot_file_sha256":
        key_sha,

    "lineage": {
        "step06b1_mutation_contract_sha256":
            b1_sha,

        "step06a_candidate_business_key_sha256":
            key_sha,
    },

    "intended_database_transport": {
        "method":
            "COPY temporary table FROM STDIN",

        "persistent_stage":
            False
    },

    "safety": {
        "s3_access":
            "READ_ONLY",

        "database_access":
            "NONE",

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
            False
    }
}


output.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print('B2_SNAPSHOT_METADATA_BUILD=PASS')
PY_META

python3 - \
  "$TMP_META" \
  "$SNAPSHOT" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_META_VERIFY'
import hashlib
import json
import sys
from pathlib import Path


meta = json.loads(
    Path(sys.argv[1]).read_bytes()
)

snapshot = Path(sys.argv[2])

expected_sha = sys.argv[3]


actual_sha = hashlib.sha256(
    snapshot.read_bytes()
).hexdigest()


assert actual_sha == expected_sha

assert meta["task"] == "TASK-003"
assert meta["step"] == "STEP-06B2"

assert (
    meta["status"]
    == "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN"
)

assert meta["rows"] == 5799
assert meta["unique_business_keys"] == 5799

assert meta["business_key_sha256"] == expected_sha
assert meta["snapshot_file_sha256"] == expected_sha

assert meta["format"]["header"] is False
assert meta["format"]["delimiter"] == "TAB"
assert meta["format"]["line_ending"] == "LF"

assert (
    meta["intended_database_transport"]["method"]
    == "COPY temporary table FROM STDIN"
)

safety = meta["safety"]

assert safety["s3_access"] == "READ_ONLY"
assert safety["database_access"] == "NONE"
assert safety["nextval_called"] is False
assert safety["setval_called"] is False
assert safety["visit_id_allocation_started"] is False
assert safety["visit_id_map_mutated"] is False
assert safety["sequence_advanced"] is False
assert safety["cdm_visit_occurrence_write"] is False

print('B2_SNAPSHOT_METADATA_VERIFY=PASS')
PY_META_VERIFY

if [[ -e "$SNAPSHOT_META" ]]; then

  if cmp -s \
    "$TMP_META" \
    "$SNAPSHOT_META"
  then
    echo 'SNAPSHOT_METADATA_ALREADY_IDENTICAL=YES'
  else
    echo 'ERROR: existing immutable snapshot metadata differs'
    exit 1
  fi

else

  install \
    -m 0444 \
    "$TMP_META" \
    "$SNAPSHOT_META"

  echo 'SNAPSHOT_METADATA_INSTALLED=YES'
fi

echo '=== 16. Independent snapshot byte verification ==='

python3 - \
  "$SNAPSHOT" \
  "$SNAPSHOT_META" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_FINAL'
import hashlib
import json
import sys
from pathlib import Path


snapshot = Path(sys.argv[1])
meta_path = Path(sys.argv[2])
expected_sha = sys.argv[3]


payload = snapshot.read_bytes()

sha = hashlib.sha256(
    payload
).hexdigest()

assert sha == expected_sha

assert payload.endswith(
    b"\n"
)

assert b"\r" not in payload


lines = payload.decode(
    "utf-8"
).splitlines()

assert len(lines) == 5799

assert lines == sorted(lines)

assert len(set(lines)) == 5799


for line in lines:

    fields = line.split(
        "\t"
    )

    assert len(fields) == 2

    assert fields[0] == "synthea"
    assert fields[1]


meta = json.loads(
    meta_path.read_bytes()
)

assert meta["snapshot_file_sha256"] == sha
assert meta["business_key_sha256"] == sha


print('INDEPENDENT_BUSINESS_KEY_SNAPSHOT_VERIFY=PASS')
print('BUSINESS_KEY_SNAPSHOT_ROWS=5799')
print('BUSINESS_KEY_SNAPSHOT_UNIQUE_KEYS=5799')
print('BUSINESS_KEY_SNAPSHOT_SHA256=' + sha)
PY_FINAL

echo '=== 17. Record unique B2 build evidence ==='

python3 - \
  "$RUN_STATE" \
  "$RESULT" \
  "$SNAPSHOT" \
  "$SNAPSHOT_META" \
  "$B1_CONTRACT" \
  "$APP" \
  "$CM" \
  "$SOURCE_APP" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path


state_path = Path(sys.argv[1])
result_path = Path(sys.argv[2])

snapshot = Path(sys.argv[3])
snapshot_meta = Path(sys.argv[4])
b1_contract = Path(sys.argv[5])

app = sys.argv[6]
cm = sys.argv[7]
source_app = sys.argv[8]


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


result = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B2",

    "status":
        "VISIT_BUSINESS_KEY_SNAPSHOT_BUILD_PASS",

    "rows":
        5799,

    "unique_business_keys":
        5799,

    "business_key_sha256":
        sha(snapshot),

    "snapshot_file_sha256":
        sha(snapshot),

    "snapshot_metadata_sha256":
        sha(snapshot_meta),

    "step06b1_mutation_contract_sha256":
        sha(b1_contract),
}


state = {
    **result,

    "source_sparkapplication":
        source_app,

    "sparkapplication":
        app,

    "runtime_configmap":
        cm,

    "s3_access":
        "READ_ONLY",

    "database_access":
        "NONE",

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


result_path.write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

state_path.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


print('STEP06B2_BUILD_EVIDENCE=PASS')

print(
    'STEP06B2_SNAPSHOT_METADATA_SHA256='
    + result[
        "snapshot_metadata_sha256"
    ]
)
PY_STATE

echo '=== 18. Final STEP06B2 verdict ==='

echo 'STEP06B2_VISIT_BUSINESS_KEY_SNAPSHOT=PASS'

echo 'SNAPSHOT_FORMAT=UTF-8_TSV'
echo 'SNAPSHOT_HEADER=NO'
echo 'SNAPSHOT_ORDER=source_system_ASC,source_encounter_id_ASC'

echo 'SNAPSHOT_ROWS=5799'
echo 'SNAPSHOT_UNIQUE_BUSINESS_KEYS=5799'

echo "BUSINESS_KEY_SNAPSHOT_SHA256=$FINAL_SHA"
echo "EXPECTED_BUSINESS_KEY_SHA256=$EXPECTED_KEY_SHA"

echo 'BUSINESS_KEY_FINGERPRINT_MATCH=YES'

echo "MUTATION_CONTRACT_SHA256=$EXPECTED_B1_SHA"

echo 'SNAPSHOT_IMMUTABLE=YES'
echo 'SNAPSHOT_READY_FOR_COPY_STDIN=YES'

echo 'S3_ACCESS=READ_ONLY'
echo 'DATABASE_ACCESS=NONE'

echo 'ADVISORY_LOCK_ACQUIRED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'GIT_COMMIT=NO'

echo 'NEXT_REQUIRED_STEP=STEP06B3_PRE_MUTATION_CANONICALIZATION'
B2_RUNNER_EOF_TASK003_06B3

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/verify_visit_id_pre_mutation_gate.py" <<'VERIFY_APP_EOF_TASK003_06B3'
#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_PARENT = (
    "6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a"
)

EXPECTED_B1_SHA = (
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


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    return json.loads(
        Path(path).read_bytes()
    )


def sha256_file(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def validate(
    canonical_contract_path,
    canonical_meta_path,
    runtime_contract_path,
    snapshot_path,
    runtime_meta_path,
    b2_result_path,
    b2_state_path,
):
    canonical_contract = load_json(
        canonical_contract_path
    )

    canonical_meta = load_json(
        canonical_meta_path
    )

    runtime_contract = load_json(
        runtime_contract_path
    )

    runtime_meta = load_json(
        runtime_meta_path
    )

    b2_result = load_json(
        b2_result_path
    )

    b2_state = load_json(
        b2_state_path
    )

    require(
        sha256_file(
            canonical_contract_path
        )
        == EXPECTED_B1_SHA,
        "canonical B1 contract SHA",
    )

    require(
        sha256_file(
            runtime_contract_path
        )
        == EXPECTED_B1_SHA,
        "runtime B1 contract SHA",
    )

    require(
        canonical_contract
        == runtime_contract,
        "canonical/runtime B1 contract mismatch",
    )

    require(
        sha256_file(
            canonical_meta_path
        )
        == EXPECTED_META_SHA,
        "canonical B2 metadata SHA",
    )

    require(
        sha256_file(
            runtime_meta_path
        )
        == EXPECTED_META_SHA,
        "runtime B2 metadata SHA",
    )

    require(
        canonical_meta
        == runtime_meta,
        "canonical/runtime B2 metadata mismatch",
    )

    require(
        sha256_file(
            snapshot_path
        )
        == EXPECTED_KEY_SHA,
        "business-key snapshot SHA",
    )

    contract = canonical_contract

    require(
        contract["task"]
        == "TASK-003",
        "B1 task",
    )

    require(
        contract["step"]
        == "STEP-06B1",
        "B1 step",
    )

    require(
        contract["status"]
        == "VISIT_ID_MUTATION_CONTRACT_READY",
        "B1 status",
    )

    require(
        contract["git_checkpoint"]
        == EXPECTED_PARENT,
        "B1 parent checkpoint",
    )

    scope = contract["scope"]

    require(
        scope["mutation_target"]
        == "etl.visit_occurrence_id_map",
        "mutation target",
    )

    require(
        scope["cdm_visit_occurrence_write"]
        is False,
        "CDM write scope",
    )

    require(
        scope["s3_write"]
        is False,
        "S3 write scope",
    )

    require(
        scope["candidate_rows"]
        == 5799,
        "candidate rows",
    )

    require(
        scope["candidate_unique_business_keys"]
        == 5799,
        "candidate keys",
    )

    require(
        scope["candidate_business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "candidate fingerprint",
    )

    serialization = contract[
        "serialization"
    ]

    lock = serialization[
        "advisory_lock"
    ]

    require(
        lock["function"]
        == "pg_advisory_xact_lock(bigint)",
        "advisory function",
    )

    require(
        lock["key"]
        == 5947676943154735385,
        "advisory lock key",
    )

    require(
        lock["scope"]
        == "transaction",
        "advisory lock scope",
    )

    transport = contract[
        "candidate_key_transport"
    ]

    require(
        transport["producer_step"]
        == "STEP-06B2",
        "snapshot producer",
    )

    require(
        transport["expected_rows"]
        == 5799,
        "transport rows",
    )

    require(
        transport["expected_unique_rows"]
        == 5799,
        "transport unique rows",
    )

    require(
        transport[
            "expected_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "transport fingerprint",
    )

    require(
        transport[
            "database_ingest"
        ]
        == "COPY temporary table FROM STDIN",
        "database transport",
    )

    policy = contract[
        "allocation_policy"
    ]

    require(
        policy[
            "existing_mapping_reassignment"
        ]
        == "FORBIDDEN",
        "existing mapping policy",
    )

    require(
        policy[
            "sequence_gap_policy"
        ]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "sequence gap policy",
    )

    require(
        policy[
            "setval_backward"
        ]
        == "FORBIDDEN",
        "setval policy",
    )

    require(
        policy[
            "predicted_range_authoritative"
        ]
        is False,
        "predicted range authority",
    )

    failure = contract[
        "failure_policy"
    ]

    require(
        failure[
            "after_first_nextval_before_commit"
        ][
            "blind_retry"
        ]
        is False,
        "blind retry policy",
    )

    safety = contract[
        "safety"
    ]

    require(
        safety[
            "advisory_lock_acquired"
        ]
        is False,
        "B1 advisory state",
    )

    require(
        safety["nextval_called"]
        is False,
        "B1 nextval state",
    )

    require(
        safety["setval_called"]
        is False,
        "B1 setval state",
    )

    require(
        safety[
            "visit_id_allocation_started"
        ]
        is False,
        "B1 allocation state",
    )

    meta = canonical_meta

    require(
        meta["task"]
        == "TASK-003",
        "B2 metadata task",
    )

    require(
        meta["step"]
        == "STEP-06B2",
        "B2 metadata step",
    )

    require(
        meta["status"]
        == "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN",
        "B2 metadata status",
    )

    require(
        meta["git_checkpoint"]
        == EXPECTED_PARENT,
        "B2 parent checkpoint",
    )

    require(
        meta["rows"]
        == 5799,
        "B2 rows",
    )

    require(
        meta["unique_business_keys"]
        == 5799,
        "B2 unique rows",
    )

    require(
        meta["business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "B2 fingerprint",
    )

    require(
        meta["snapshot_file_sha256"]
        == EXPECTED_KEY_SHA,
        "B2 snapshot file fingerprint",
    )

    require(
        meta[
            "lineage"
        ][
            "step06b1_mutation_contract_sha256"
        ]
        == EXPECTED_B1_SHA,
        "B2 -> B1 lineage",
    )

    payload = Path(
        snapshot_path
    ).read_bytes()

    require(
        payload.endswith(b"\n"),
        "snapshot final LF",
    )

    require(
        b"\r" not in payload,
        "snapshot CR forbidden",
    )

    lines = payload.decode(
        "utf-8"
    ).splitlines()

    require(
        len(lines)
        == 5799,
        "snapshot line count",
    )

    require(
        len(set(lines))
        == 5799,
        "snapshot unique count",
    )

    require(
        lines
        == sorted(lines),
        "snapshot deterministic ordering",
    )

    for line in lines:
        fields = line.split(
            "\t"
        )

        require(
            len(fields)
            == 2,
            "snapshot TSV schema",
        )

        require(
            fields[0]
            == "synthea",
            "snapshot source_system",
        )

        require(
            bool(fields[1]),
            "snapshot encounter ID",
        )

    for doc in (
        b2_result,
        b2_state,
    ):
        require(
            doc["task"]
            == "TASK-003",
            "B2 evidence task",
        )

        require(
            doc["step"]
            == "STEP-06B2",
            "B2 evidence step",
        )

        require(
            doc["status"]
            == "VISIT_BUSINESS_KEY_SNAPSHOT_BUILD_PASS",
            "B2 evidence status",
        )

        require(
            doc["rows"]
            == 5799,
            "B2 evidence rows",
        )

        require(
            doc[
                "unique_business_keys"
            ]
            == 5799,
            "B2 evidence unique",
        )

        require(
            doc[
                "business_key_sha256"
            ]
            == EXPECTED_KEY_SHA,
            "B2 evidence fingerprint",
        )

        require(
            doc[
                "snapshot_metadata_sha256"
            ]
            == EXPECTED_META_SHA,
            "B2 metadata lineage",
        )

    require(
        b2_state[
            "database_access"
        ]
        == "NONE",
        "B2 database access",
    )

    require(
        b2_state[
            "s3_access"
        ]
        == "READ_ONLY",
        "B2 S3 access",
    )

    require(
        b2_state[
            "nextval_called"
        ]
        is False,
        "B2 nextval state",
    )

    require(
        b2_state[
            "setval_called"
        ]
        is False,
        "B2 setval state",
    )

    require(
        b2_state[
            "visit_id_map_mutated"
        ]
        is False,
        "B2 map mutation",
    )

    require(
        b2_state[
            "sequence_advanced"
        ]
        is False,
        "B2 sequence state",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B3",

        "status":
            "VISIT_ID_PRE_MUTATION_GATE_FROZEN",

        "parent_git_checkpoint":
            EXPECTED_PARENT,

        "mutation_contract_sha256":
            EXPECTED_B1_SHA,

        "snapshot_metadata_sha256":
            EXPECTED_META_SHA,

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "candidate_rows":
            5799,

        "candidate_unique_business_keys":
            5799,

        "advisory_lock_key":
            5947676943154735385,

        "database_transport":
            "COPY temporary table FROM STDIN",

        "sequence_gap_policy":
            "ACCEPT_GAPS_NEVER_REWIND",

        "predicted_visit_id_range": [
            1,
            5799
        ],

        "predicted_range_authoritative":
            False,

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
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--canonical-contract",
        required=True,
    )

    parser.add_argument(
        "--canonical-snapshot-meta",
        required=True,
    )

    parser.add_argument(
        "--runtime-contract",
        required=True,
    )

    parser.add_argument(
        "--snapshot",
        required=True,
    )

    parser.add_argument(
        "--runtime-snapshot-meta",
        required=True,
    )

    parser.add_argument(
        "--b2-result",
        required=True,
    )

    parser.add_argument(
        "--b2-state",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.canonical_contract,
        args.canonical_snapshot_meta,
        args.runtime_contract,
        args.snapshot,
        args.runtime_snapshot_meta,
        args.b2_result,
        args.b2_state,
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
        "STEP06B_PRE_MUTATION_GATE=PASS"
    )

    print(
        "MUTATION_CONTRACT_SHA256="
        + result[
            "mutation_contract_sha256"
        ]
    )

    print(
        "SNAPSHOT_METADATA_SHA256="
        + result[
            "snapshot_metadata_sha256"
        ]
    )

    print(
        "CANDIDATE_BUSINESS_KEY_SHA256="
        + result[
            "candidate_business_key_sha256"
        ]
    )


if __name__ == "__main__":
    main()
VERIFY_APP_EOF_TASK003_06B3

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh" <<'VERIFY_RUNNER_EOF_TASK003_06B3'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

PARENT=6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a

RUN_ID=visit-proc-20261009t192437z-2081886

APP="$ROOT/apps/task003/verify_visit_id_pre_mutation_gate.py"

CANONICAL_CONTRACT="$ROOT/spark/contracts/processed/visit-id-mutation-contract-v1.json"
CANONICAL_META="$ROOT/spark/contracts/processed/visit-business-key-snapshot-v1.json"

RUNTIME_CONTRACT="$ROOT/runtime/reports/task003/step06/visit-id-mutation-contracts/$RUN_ID/contract.json"

SNAPSHOT_DIR="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID"

SNAPSHOT="$SNAPSHOT_DIR/business-keys.tsv"
RUNTIME_META="$SNAPSHOT_DIR/snapshot.json"

B2_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshot-build.20261010t134824z-2476691"

B2_RESULT="$B2_REPORT/result.json"
B2_STATE="$B2_REPORT/run-state.json"

REPORT="$ROOT/runtime/reports/task003/step06/pre-mutation-gate"
OUTPUT="$REPORT/run-state.json"

echo '#### TASK003 STEP06B3 PRE-MUTATION GATE VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B3_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B3 PRE-MUTATION GATE VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

cd "$ROOT"

mkdir -p "$REPORT"

HEAD="$(git rev-parse HEAD)"

echo "CURRENT_HEAD=$HEAD"
echo "REQUIRED_PARENT=$PARENT"

git merge-base \
  --is-ancestor \
  "$PARENT" \
  "$HEAD" \
  || {
    echo 'ERROR: STEP06A checkpoint is not an ancestor of current HEAD'
    exit 1
  }

echo 'STEP06A_PARENT_ANCESTRY=PASS'

for file in \
  "$APP" \
  "$CANONICAL_CONTRACT" \
  "$CANONICAL_META" \
  "$RUNTIME_CONTRACT" \
  "$SNAPSHOT" \
  "$RUNTIME_META" \
  "$B2_RESULT" \
  "$B2_STATE"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --canonical-contract "$CANONICAL_CONTRACT" \
  --canonical-snapshot-meta "$CANONICAL_META" \
  --runtime-contract "$RUNTIME_CONTRACT" \
  --snapshot "$SNAPSHOT" \
  --runtime-snapshot-meta "$RUNTIME_META" \
  --b2-result "$B2_RESULT" \
  --b2-state "$B2_STATE" \
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
    == "VISIT_ID_PRE_MUTATION_GATE_FROZEN"
)

assert state["candidate_rows"] == 5799

assert (
    state[
        "candidate_unique_business_keys"
    ]
    == 5799
)

assert (
    state[
        "candidate_business_key_sha256"
    ]
    == "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
)

assert (
    state[
        "advisory_lock_key"
    ]
    == 5947676943154735385
)

assert (
    state[
        "sequence_gap_policy"
    ]
    == "ACCEPT_GAPS_NEVER_REWIND"
)

assert (
    state[
        "predicted_range_authoritative"
    ]
    is False
)

assert state["advisory_lock_acquired"] is False
assert state["nextval_called"] is False
assert state["setval_called"] is False

assert (
    state[
        "visit_id_allocation_started"
    ]
    is False
)

assert state["visit_id_map_mutated"] is False
assert state["sequence_advanced"] is False

assert (
    state[
        "cdm_visit_occurrence_write"
    ]
    is False
)

print(
    "STEP06B3_GATE_STATE=PASS"
)
PY

echo 'STEP06B3_PRE_MUTATION_GATE=PASS'

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'

echo 'CANDIDATE_BUSINESS_KEY_SHA256=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e'

echo 'MUTATION_CONTRACT_SHA256=58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0'

echo 'SNAPSHOT_METADATA_SHA256=21ac6b5af6f74d3b078b4fbf7fb8ce21b5d5d32af1aaccc5e495e595fc90dbaa'

echo 'ADVISORY_LOCK_KEY=5947676943154735385'

echo 'SEQUENCE_GAP_POLICY=ACCEPT_GAPS_NEVER_REWIND'

echo 'PREDICTED_VISIT_ID_RANGE=1..5799'
echo 'PREDICTED_RANGE_AUTHORITATIVE=NO'

echo 'ADVISORY_LOCK_ACQUIRED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'

echo 'READY_FOR_PRE_MUTATION_GIT_CHECKPOINT=YES'
VERIFY_RUNNER_EOF_TASK003_06B3

mkdir -p "$STAGE/spark/contracts/processed"
cat > "$STAGE/spark/contracts/processed/visit-id-mutation-contract-v1.json" <<'B1_CONTRACT_EOF_TASK003_06B3'
{
  "allocation_policy": {
    "authoritative_state": "committed etl.visit_occurrence_id_map rows",
    "existing_mapping_reassignment": "FORBIDDEN",
    "method": "explicit nextval in deterministic business-key order",
    "predicted_first_id": 1,
    "predicted_last_id": 5799,
    "predicted_range_authoritative": false,
    "sequence_gap_policy": "ACCEPT_GAPS_NEVER_REWIND",
    "setval_backward": "FORBIDDEN"
  },
  "candidate_key_transport": {
    "columns": [
      "source_system",
      "source_encounter_id"
    ],
    "database_ingest": "COPY temporary table FROM STDIN",
    "expected_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
    "expected_rows": 5799,
    "expected_unique_rows": 5799,
    "format": "UTF-8 TSV",
    "ordering": [
      "source_system ASC",
      "source_encounter_id ASC"
    ],
    "persistent_staging_table": false,
    "producer_step": "STEP-06B2",
    "required_before_mutation": true,
    "temporary_table_primary_key": [
      "source_system",
      "source_encounter_id"
    ]
  },
  "contract_version": "v1",
  "failure_policy": {
    "after_commit": {
      "mapping_authoritative": true,
      "required_action": "independent verification before any CDM Visit write"
    },
    "after_first_nextval_before_commit": {
      "blind_retry": false,
      "map_rows_may_rollback": true,
      "required_action": "preserve evidence and enter explicit recovery reconciliation",
      "sequence_may_have_advanced": true
    },
    "before_first_nextval": {
      "retry": "allowed only after fresh full revalidation",
      "sequence_may_have_advanced": false
    },
    "never": [
      "blindly retry after uncertain nextval execution",
      "rewind sequence with setval",
      "reassign an existing business key to another Visit ID",
      "combine Visit ID allocation with cdm.visit_occurrence loading"
    ]
  },
  "git_checkpoint": "6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a",
  "lineage": {
    "allocation_plan_sha256": "28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93",
    "reconciliation_result_sha256": "fb2905064173c564a8074b7f946c976b8d2ea1e0165ce7f2f3f2b3feb258eb31"
  },
  "post_commit_verification": {
    "cdm_write_allowed_during_verification": false,
    "independent_session": true,
    "required_candidate_coverage": 5799,
    "required_cdm_visit_rows": 0,
    "required_unique_business_keys": 5799,
    "required_unique_visit_ids": 5799,
    "verify_mapping_fingerprint": true,
    "verify_sequence_state": true
  },
  "required_pre_mutation_state": {
    "cdm_map_overlap_rows": 0,
    "cdm_visit_rows": 0,
    "map_business_key_collision_groups": 0,
    "map_visit_id_collision_groups": 0,
    "person_map_rows": 113,
    "sequence": {
      "automatic_default_nextval": false,
      "column_default": null,
      "cycle": false,
      "increment_by": 1,
      "is_called": false,
      "last_value": 1,
      "name": "etl.visit_occurrence_id_map_visit_occurrence_id_seq"
    },
    "visit_map_rows": 0
  },
  "run_id": "visit-proc-20261009t192437z-2081886",
  "safety": {
    "advisory_lock_acquired": false,
    "cdm_visit_occurrence_write": false,
    "contract_build_database_access": "READ_ONLY",
    "contract_build_s3_access": "NONE",
    "nextval_called": false,
    "sequence_advanced": false,
    "setval_called": false,
    "visit_id_allocation_started": false,
    "visit_id_map_mutated": false
  },
  "scope": {
    "business_key": [
      "source_system",
      "source_encounter_id"
    ],
    "candidate_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
    "candidate_rows": 5799,
    "candidate_unique_business_keys": 5799,
    "cdm_visit_occurrence_write": false,
    "mutation_target": "etl.visit_occurrence_id_map",
    "s3_write": false
  },
  "serialization": {
    "advisory_lock": {
      "function": "pg_advisory_xact_lock(bigint)",
      "key": 5947676943154735385,
      "purpose": "TASK003 Visit ID allocation serialization",
      "scope": "transaction"
    },
    "lock_order": [
      "pg_advisory_xact_lock",
      "etl.visit_occurrence_id_map",
      "etl.person_id_map",
      "cdm.visit_occurrence"
    ],
    "table_locks": [
      {
        "mode": "SHARE ROW EXCLUSIVE",
        "purpose": "block concurrent map mutations",
        "relation": "etl.visit_occurrence_id_map"
      },
      {
        "mode": "SHARE",
        "purpose": "freeze Person mapping during allocation validation",
        "relation": "etl.person_id_map"
      },
      {
        "mode": "SHARE",
        "purpose": "prevent concurrent Visit CDM mutation while map IDs are allocated",
        "relation": "cdm.visit_occurrence"
      }
    ]
  },
  "status": "VISIT_ID_MUTATION_CONTRACT_READY",
  "step": "STEP-06B1",
  "task": "TASK-003",
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
  ]
}
B1_CONTRACT_EOF_TASK003_06B3

mkdir -p "$STAGE/spark/contracts/processed"
cat > "$STAGE/spark/contracts/processed/visit-business-key-snapshot-v1.json" <<'B2_META_EOF_TASK003_06B3'
{
  "business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
  "format": {
    "columns": [
      "source_system",
      "source_encounter_id"
    ],
    "delimiter": "TAB",
    "encoding": "UTF-8",
    "header": false,
    "line_ending": "LF",
    "ordering": [
      "source_system ASC",
      "source_encounter_id ASC"
    ]
  },
  "git_checkpoint": "6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a",
  "intended_database_transport": {
    "method": "COPY temporary table FROM STDIN",
    "persistent_stage": false
  },
  "lineage": {
    "step06a_candidate_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
    "step06b1_mutation_contract_sha256": "58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0"
  },
  "rows": 5799,
  "run_id": "visit-proc-20261009t192437z-2081886",
  "safety": {
    "cdm_visit_occurrence_write": false,
    "database_access": "NONE",
    "nextval_called": false,
    "s3_access": "READ_ONLY",
    "sequence_advanced": false,
    "setval_called": false,
    "visit_id_allocation_started": false,
    "visit_id_map_mutated": false
  },
  "snapshot_file_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
  "snapshot_version": "v1",
  "source": "frozen Processed visit_occurrence Candidate",
  "source_system": "synthea",
  "status": "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN",
  "step": "STEP-06B2",
  "task": "TASK-003",
  "unique_business_keys": 5799
}
B2_META_EOF_TASK003_06B3

mkdir -p "$STAGE/tests/task003"
cat > "$STAGE/tests/task003/test_visit_id_pre_mutation_gate.py" <<'TEST_EOF_TASK003_06B3'
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
    / "apps/task003/verify_visit_id_pre_mutation_gate.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_visit_id_pre_mutation_gate",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class VisitIDPreMutationGateTests(
    unittest.TestCase
):

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(b"abc")

            self.assertEqual(
                module.sha256_file(
                    path
                ),
                hashlib.sha256(
                    b"abc"
                ).hexdigest(),
            )

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


if __name__ == "__main__":
    unittest.main()
TEST_EOF_TASK003_06B3

mkdir -p "$STAGE/docs/task003"
cat > "$STAGE/docs/task003/TASK003-STEP06B-PreMutation-Gate.md" <<'DOC_EOF_TASK003_06B3'
# TASK-003 STEP06B Pre-Mutation Gate

## Status

STEP06B1 and STEP06B2 are complete.

Visit ID allocation has **not** started.

## Frozen Input

Processed Candidate:

- rows: 5799
- unique business keys: 5799
- business key: `(source_system, source_encounter_id)`

Frozen business-key snapshot SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

The TSV file contains:

- UTF-8
- no header
- TAB delimiter
- LF line endings
- deterministic ascending business-key order
- exactly 5799 rows
- exactly 5799 unique keys

## Mutation Contract

Mutation Contract SHA256:

`58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0`

Allocation target:

`etl.visit_occurrence_id_map`

The allocation transaction must not write:

`cdm.visit_occurrence`

## Serialization

Transaction-scoped PostgreSQL advisory lock:

`5947676943154735385`

Lock order:

1. transaction advisory lock
2. `etl.visit_occurrence_id_map`
3. `etl.person_id_map`
4. `cdm.visit_occurrence`

## Candidate Transport

The frozen TSV is transported into PostgreSQL using:

`COPY temporary table FROM STDIN`

No persistent staging table is permitted.

## Allocation Policy

New business keys are allocated in deterministic ascending business-key order.

IDs use explicit:

`nextval('etl.visit_occurrence_id_map_visit_occurrence_id_seq')`

The current predicted range is:

`1..5799`

This prediction is not authoritative before mutation-time revalidation.

Only committed `(source_system, source_encounter_id) -> visit_occurrence_id`
mapping rows are authoritative.

## Sequence Failure Policy

PostgreSQL sequence advancement is not transactional.

If `nextval()` executes and the transaction later rolls back:

- sequence gaps are acceptable
- blind retry is forbidden
- backward `setval()` is forbidden
- recovery must reconcile both map state and sequence state first

Policy:

`ACCEPT_GAPS_NEVER_REWIND`

## Current Safety State

At STEP06B3:

- advisory lock acquired: NO
- nextval called: NO
- setval called: NO
- Visit ID allocation started: NO
- Visit ID map mutated: NO
- sequence advanced: NO
- CDM Visit write: NO

## Next Boundary

After the STEP06B3 source checkpoint, the first mutation step may:

1. acquire the advisory lock
2. acquire table locks
3. revalidate all database invariants
4. load the exact frozen key TSV into a temporary table
5. verify count, uniqueness, fingerprint-equivalent content, and zero prior mappings
6. revalidate sequence state immediately before allocation
7. execute explicit nextval allocation
8. insert only `etl.visit_occurrence_id_map`
9. commit
10. perform independent post-commit verification

CDM Visit row materialization remains a later separate step.
DOC_EOF_TASK003_06B3


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

install_one scripts/task003/06b1-build-visit-id-mutation-contract.sh
install_one scripts/task003/06b2-freeze-visit-business-key-snapshot.sh
install_one apps/task003/verify_visit_id_pre_mutation_gate.py
install_one scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh
install_one spark/contracts/processed/visit-id-mutation-contract-v1.json
install_one spark/contracts/processed/visit-business-key-snapshot-v1.json
install_one tests/task003/test_visit_id_pre_mutation_gate.py
install_one docs/task003/TASK003-STEP06B-PreMutation-Gate.md

python3 -m py_compile \
  "$ROOT/apps/task003/verify_visit_id_pre_mutation_gate.py" \
  "$ROOT/tests/task003/test_visit_id_pre_mutation_gate.py"

python3 -m json.tool \
  "$ROOT/spark/contracts/processed/visit-id-mutation-contract-v1.json" \
  >/dev/null

python3 -m json.tool \
  "$ROOT/spark/contracts/processed/visit-business-key-snapshot-v1.json" \
  >/dev/null

bash -n "$ROOT/scripts/task003/06b1-build-visit-id-mutation-contract.sh"
bash -n "$ROOT/scripts/task003/06b2-freeze-visit-business-key-snapshot.sh"
bash -n "$ROOT/scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh"

echo 'STEP06B3_CANONICAL_SOURCE_PREPARED=PASS'
echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'KUBERNETES_MUTATION=NO'
echo 'GIT_COMMIT=NO'
