#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

FROZEN_SOURCE_CHECKPOINT=46bf2f7348029d1a17ed3db178fc93ea3a6a97ca

REAL_MATERIALIZATION_SQL_SHA256=627056f9169fe0615c1649c8785623d240c8d6a562ba0ed993da537f2bafa214
CDM_ROW_SHAPE_SHA256=995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1
AUTHORITATIVE_MAPPING_SHA256=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f
PERSON_MAP_SHA256=f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98
CANDIDATE_BUSINESS_KEY_SHA256=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e

C4A_MUTATION_CONTRACT_SHA256=ab2d43d465b974aaf1d8c691dfd60fec97d807f6e09470a069fe50d043fc6859
REHEARSAL_SQL_SHA256=59b1843959ecaf686d1d1e16e5801fb83f5bc30db708f4f00257abc04deacb31
VERIFIED_PREINSERT_PREFIX_SHA256=fde40c3a4fd84bbbe1fd6b9b660833de1cee73ffc662acc2d697e25d6c0284d5

D1_METADATA_SHA256=5404f2fdca36cfdbc0f2094f1fc5a7b365a5a0408c2ac52a3bc38abc5b225ccc
D2_EXECUTION_OUTPUT_SHA256=4ba017643edd1873507ccf3e5b489773fcf33c28f807d93a113a6fb0e3237858
D2_POST_STATE_SHA256=e8ac76c6954b1e9a99293f6e90d7294e7d1bfae50ff1f5b053a358a48cbe6ce7
D2_SUMMARY_SHA256=f6ddda0d2c3c7c2c53dbcdcd4f11b5ab7d290f7b184d426c6d80c314ecc3ca2d
R2_STATE_SHA256=4ca1df21370eb6d6599e45ce51d62099983e3eab3eac0f95542f7f0243331c85
R2_SUMMARY_SHA256=0ac2ae071d48a3f54c97748616e8ab38d20a58d41461653b326cdc2ad262c3ce
PAYLOAD_METADATA_SHA256=df17f57c267e32eafb11bd47cc3aad1d0343fea852581683d1e962a8f8cdeef8
REHEARSAL_SUMMARY_SHA256=4ded2b3d08312b19542460ab38143b0561dc2ae5d3ad68127f4e082070509c5c


echo '#### TASK003 STEP06C4E PREPARE COMMITTED CDM VISIT MATERIALIZATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06C4E_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06C4E PREPARE COMMITTED CDM VISIT MATERIALIZATION OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

cd "$ROOT"

STAGE="$(mktemp -d /data/spark/temp_shell/task003-step06c4e-stage.XXXXXX)"

cleanup() {
  rm -rf "$STAGE"
}

trap 'rc=$?; cleanup; echo "STEP06C4E_PREPARE_EXIT_CODE=$rc"; echo "#### TASK003 STEP06C4E PREPARE COMMITTED CDM VISIT MATERIALIZATION OUTPUT END ####"; exit "$rc"' EXIT

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/docs/task003" \
  "$STAGE/scripts/task003" \
  "$STAGE/spark/contracts/processed" \
  "$STAGE/tests/task003"

APP="$STAGE/apps/task003/verify_committed_cdm_visit_materialization.py"
DOC="$STAGE/docs/task003/TASK003-STEP06C4E-Committed-CDM-Visit-Materialization.md"
RUNNER="$STAGE/scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh"
CONTRACT="$STAGE/spark/contracts/processed/visit-cdm-materialization-result-v1.json"
TEST="$STAGE/tests/task003/test_committed_cdm_visit_materialization.py"

cat > "$APP" <<'PY_APP'
#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


EXPECTED_STATE = {
    "TARGET_COLUMN_COUNT": "17",
    "TARGET_CONSTRAINT_COUNT": "10",
    "TARGET_INDEX_COUNT": "3",
    "TARGET_USER_TRIGGER_COUNT": "0",
    "CDM_STATE": "5799|5799|2|5800",
    "MAP_STATE": "5799|5799|2|5800",
    "PERSON_MAP_ROWS": "113",
    "SEQUENCE_STATE": "5800|true",
    "MAPPING_SHA256":
        "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b"
        "06b1d6349d7f21f6a0c03c9f",
    "PERSON_MAP_SHA256":
        "f52f95120b8a9bd80d33029d04d9abf4cb1c5920"
        "6d00b745b59e39b5a89c9a98",
    "CDM_ROW_SHAPE_SHA256":
        "995724ba282f443892074d9b189be134fde8819b2"
        "afda05f021729323b0ebce1",
    "TARGET_MAP_ID_MISMATCH": "0",
    "REQUIRED_NULL_ROWS": "0",
    "MISSING_PERSON_FK": "0",
    "MISSING_CONCEPT_FK": "0",
    "MISSING_PROVIDER_FK": "0",
    "MISSING_CARE_SITE_FK": "0",
    "MISSING_PRECEDING_VISIT_FK": "0",
    "TRANSACTION_READ_ONLY": "on",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def parse_state_text(text):
    values = {}

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            continue

        if line in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }:
            continue

        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        values[key] = value

    return values


def validate_state(values):
    for key, expected in EXPECTED_STATE.items():
        actual = values.get(key)

        require(
            actual == expected,
            (
                f"{key}: expected {expected!r}, "
                f"got {actual!r}"
            ),
        )


def validate_contract(obj):
    require(
        obj["task"] == "TASK-003",
        "task",
    )

    require(
        obj["step"] == "STEP-06C4E",
        "step",
    )

    require(
        obj["status"]
        == "CDM_VISIT_MATERIALIZATION_COMMITTED_FROZEN",
        "status",
    )

    require(
        obj["target"]["table"]
        == "cdm.visit_occurrence",
        "target table",
    )

    require(
        obj["target"]["row_count"] == 5799,
        "target row count",
    )

    require(
        obj["target"]["unique_visit_occurrence_ids"]
        == 5799,
        "target unique IDs",
    )

    require(
        obj["target"]["visit_occurrence_id_min"] == 2,
        "target min ID",
    )

    require(
        obj["target"]["visit_occurrence_id_max"] == 5800,
        "target max ID",
    )

    require(
        obj["target"]["column_count"] == 17,
        "target columns",
    )

    require(
        obj["target"]["row_shape_sha256"]
        == EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"],
        "row shape SHA",
    )

    require(
        obj["lineage"]["authoritative_mapping_sha256"]
        == EXPECTED_STATE["MAPPING_SHA256"],
        "mapping SHA",
    )

    require(
        obj["lineage"]["person_map_sha256"]
        == EXPECTED_STATE["PERSON_MAP_SHA256"],
        "person map SHA",
    )

    require(
        obj["lineage"]["visit_id_map_rows"] == 5799,
        "Visit map rows",
    )

    require(
        obj["lineage"]["person_map_rows"] == 113,
        "Person map rows",
    )

    require(
        obj["sequence"]["last_value"] == 5800,
        "sequence value",
    )

    require(
        obj["sequence"]["is_called"] is True,
        "sequence called",
    )

    require(
        obj["sequence"]["mutated_by_materialization"]
        is False,
        "sequence mutation",
    )

    require(
        obj["execution"]["psql_exit_code"] == 0,
        "psql exit",
    )

    require(
        obj["execution"]["insert_rows"] == 5799,
        "insert rows",
    )

    require(
        obj["execution"]["commit_returned_successfully"]
        is True,
        "commit marker",
    )

    require(
        obj["execution"]["automatic_retry_performed"]
        is False,
        "retry",
    )

    require(
        obj["reconciliation"]["status"]
        == "PASS",
        "reconciliation",
    )

    for name, value in obj["foreign_key_gates"].items():
        require(
            value == "PASS",
            f"FK gate {name}",
        )

    require(
        obj["terminal_policy"]["materialization_rerun"]
        == "FORBIDDEN",
        "terminal rerun policy",
    )

    require(
        obj["terminal_policy"]["visit_id_reallocation"]
        == "FORBIDDEN",
        "Visit reallocation policy",
    )


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
        "--output-json",
        required=True,
    )

    args = parser.parse_args()

    contract = json.loads(
        Path(args.contract).read_bytes()
    )

    validate_contract(contract)

    state_text = Path(
        args.state
    ).read_text(
        encoding="utf-8",
    )

    values = parse_state_text(
        state_text
    )

    validate_state(
        values
    )

    result = {
        "task":
            "TASK-003",

        "step":
            "STEP-06C4E",

        "status":
            "COMMITTED_CDM_VISIT_CANONICAL_VERIFY_PASS",

        "cdm_visit_rows":
            5799,

        "cdm_visit_unique_ids":
            5799,

        "visit_occurrence_id_min":
            2,

        "visit_occurrence_id_max":
            5800,

        "cdm_row_shape_sha256":
            EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"],

        "authoritative_mapping_sha256":
            EXPECTED_STATE["MAPPING_SHA256"],

        "person_map_sha256":
            EXPECTED_STATE["PERSON_MAP_SHA256"],

        "sequence_last_value":
            5800,

        "sequence_is_called":
            True,

        "target_map_id_mismatch":
            0,

        "required_null_rows":
            0,

        "database_access":
            "READ_ONLY",

        "database_mutation":
            False,

        "ready_for_git_checkpoint":
            True,
    }

    Path(
        args.output_json
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "STEP06C4E_COMMITTED_CDM_VISIT_VERIFY=PASS"
    )

    print(
        "CDM_VISIT_ROWS=5799"
    )

    print(
        "CDM_VISIT_UNIQUE_IDS=5799"
    )

    print(
        "CDM_VISIT_ID_RANGE=2..5800"
    )

    print(
        "CDM_ROW_SHAPE_SHA256="
        + EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"]
    )

    print(
        "AUTHORITATIVE_MAPPING_SHA256="
        + EXPECTED_STATE["MAPPING_SHA256"]
    )

    print(
        "PERSON_MAP_SHA256="
        + EXPECTED_STATE["PERSON_MAP_SHA256"]
    )

    print(
        "SEQUENCE_STATE=5800|true"
    )

    print(
        "TARGET_MAP_ID_MISMATCH=0"
    )

    print(
        "ALL_DATABASE_FK_GATES=PASS"
    )

    print(
        "DATABASE_ACCESS=READ_ONLY"
    )

    print(
        "DATABASE_MUTATION=NO"
    )

    print(
        "READY_FOR_GIT_CHECKPOINT=YES"
    )


if __name__ == "__main__":
    main()
PY_APP

cat > "$RUNNER" <<'SH_RUNNER'
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
SH_RUNNER

cat > "$TEST" <<'PY_TEST'
import importlib.util
import unittest
from pathlib import Path


APP_PATH = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "task003"
    / "verify_committed_cdm_visit_materialization.py"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_committed_cdm_visit_materialization",
    APP_PATH,
)

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)


class CommittedCDMVisitMaterializationTests(
    unittest.TestCase
):
    def test_parse_state_text(self):
        text = """
BEGIN
SET
CDM_STATE=5799|5799|2|5800
SEQUENCE_STATE=5800|true
ROLLBACK
"""

        values = MODULE.parse_state_text(
            text
        )

        self.assertEqual(
            values["CDM_STATE"],
            "5799|5799|2|5800",
        )

        self.assertEqual(
            values["SEQUENCE_STATE"],
            "5800|true",
        )

    def test_validate_state_accepts_exact_state(self):
        MODULE.validate_state(
            dict(
                MODULE.EXPECTED_STATE
            )
        )

    def test_validate_state_rejects_drift(self):
        values = dict(
            MODULE.EXPECTED_STATE
        )

        values["CDM_STATE"] = (
            "5798|5798|2|5799"
        )

        with self.assertRaises(
            RuntimeError
        ):
            MODULE.validate_state(
                values
            )


if __name__ == "__main__":
    unittest.main()
PY_TEST

cat > "$DOC" <<EOF_DOC
# TASK-003 STEP06C4E — Committed CDM Visit Materialization

## Status

**CDM Visit materialization is committed and independently reconciled.**

The authoritative target state is now:

- Target: \`cdm.visit_occurrence\`
- Rows: **5799**
- Unique \`visit_occurrence_id\`: **5799**
- ID range: **2..5800**
- ID 1 remains the accepted historical allocation gap.
- Target column count: **17**
- CDM row-shape SHA256:
  \`$CDM_ROW_SHAPE_SHA256\`

## Lineage

- Candidate rows: **5799**
- Candidate business-key SHA256:
  \`$CANDIDATE_BUSINESS_KEY_SHA256\`
- Visit ID map rows: **5799**
- Authoritative Visit mapping SHA256:
  \`$AUTHORITATIVE_MAPPING_SHA256\`
- Person map rows: **113**
- Person mapping SHA256:
  \`$PERSON_MAP_SHA256\`

## Visit ID sequence

The materialization did not allocate or modify Visit IDs.

- Before materialization: \`5800|true\`
- After materialization: \`5800|true\`
- \`nextval()\`: not used
- \`setval()\`: not used
- Visit ID reallocation: forbidden

## Real materialization

The frozen real materialization SQL SHA256 is:

\`$REAL_MATERIALIZATION_SQL_SHA256\`

The controlled execution performed exactly:

- one persistent INSERT into \`cdm.visit_occurrence\`
- explicit 17-column target list
- 5799 inserted rows
- one COMMIT
- no ON CONFLICT
- no UPDATE
- no DELETE
- no TRUNCATE
- no sequence mutation

The original PostgreSQL client returned exit code **0** and emitted the successful COMMIT marker.

## Independent reconciliation

The independently verified post-commit state is:

- \`cdm.visit_occurrence\`: 5799 rows
- unique IDs: 5799
- ID range: 2..5800
- target/map ID mismatch: 0
- required NULL violations: 0
- Person FK: PASS
- Concept FK: PASS
- Provider FK: PASS
- Care Site FK: PASS
- preceding Visit FK: PASS
- row-shape SHA exactly matches the frozen payload

## Recovered tooling errors

Two tooling errors occurred **after the real database state was already valid**:

1. D2 classified the committed state as ambiguous because it compared the normalized sequence string \`5800|true\` against \`5800|t\`.
2. The first recovery script used \`grep -F '^COMMIT$'\`; with fixed-string mode the anchors were treated literally.

Neither error caused an additional INSERT, rollback, Visit ID allocation, or retry.

The real materialization was **never rerun**.

## Terminal policy

The first-batch materialization is terminal.

- Re-running the empty-target materialization SQL is **FORBIDDEN**.
- Reallocating Visit IDs is **FORBIDDEN**.
- Rewriting the 5799 committed rows as a retry is **FORBIDDEN**.
- Future work must start from the committed state verified by STEP06C4E.

## Frozen source checkpoint

Pre-C4E Git checkpoint:

\`$FROZEN_SOURCE_CHECKPOINT\`

STEP06C4E itself performs only read-only database verification and canonical source generation. Git checkpointing is a separate subsequent step.
EOF_DOC

python3 - \
  "$CONTRACT" \
  "$FROZEN_SOURCE_CHECKPOINT" \
  "$REAL_MATERIALIZATION_SQL_SHA256" \
  "$CDM_ROW_SHAPE_SHA256" \
  "$AUTHORITATIVE_MAPPING_SHA256" \
  "$PERSON_MAP_SHA256" \
  "$CANDIDATE_BUSINESS_KEY_SHA256" \
  "$C4A_MUTATION_CONTRACT_SHA256" \
  "$REHEARSAL_SQL_SHA256" \
  "$VERIFIED_PREINSERT_PREFIX_SHA256" \
  "$D1_METADATA_SHA256" \
  "$D2_EXECUTION_OUTPUT_SHA256" \
  "$D2_POST_STATE_SHA256" \
  "$D2_SUMMARY_SHA256" \
  "$R2_STATE_SHA256" \
  "$R2_SUMMARY_SHA256" \
  "$PAYLOAD_METADATA_SHA256" \
  "$REHEARSAL_SUMMARY_SHA256" \
  <<'PY_CONTRACT'
import json
import sys
from pathlib import Path


obj = {
    "task":
        "TASK-003",

    "step":
        "STEP-06C4E",

    "contract_name":
        "visit-cdm-materialization-result",

    "contract_version":
        "v1",

    "status":
        "CDM_VISIT_MATERIALIZATION_COMMITTED_FROZEN",

    "frozen_source_checkpoint":
        sys.argv[2],

    "target": {
        "table":
            "cdm.visit_occurrence",

        "column_count":
            17,

        "row_count":
            5799,

        "unique_visit_occurrence_ids":
            5799,

        "visit_occurrence_id_min":
            2,

        "visit_occurrence_id_max":
            5800,

        "row_shape_sha256":
            sys.argv[4],

        "required_null_rows":
            0,

        "target_map_id_mismatch":
            0,
    },

    "lineage": {
        "candidate_rows":
            5799,

        "candidate_unique_business_keys":
            5799,

        "candidate_business_key_sha256":
            sys.argv[7],

        "visit_id_map_rows":
            5799,

        "authoritative_mapping_sha256":
            sys.argv[5],

        "person_map_rows":
            113,

        "person_map_sha256":
            sys.argv[6],

        "frozen_payload_rows":
            5799,

        "frozen_payload_columns":
            17,

        "frozen_payload_sha256":
            sys.argv[4],
    },

    "sequence": {
        "last_value":
            5800,

        "is_called":
            True,

        "id_1_gap_preserved":
            True,

        "mutated_by_materialization":
            False,
    },

    "execution": {
        "real_materialization_sql_sha256":
            sys.argv[3],

        "persistent_insert_statement_count":
            1,

        "explicit_target_column_count":
            17,

        "insert_rows":
            5799,

        "commit_statement_count":
            1,

        "psql_exit_code":
            0,

        "commit_returned_successfully":
            True,

        "automatic_retry_performed":
            False,

        "visit_id_reallocation":
            False,

        "sequence_mutation":
            False,
    },

    "reconciliation": {
        "status":
            "PASS",

        "fresh_read_only_reconciliation":
            True,

        "cdm_visit_rows":
            5799,

        "cdm_visit_unique_ids":
            5799,

        "visit_occurrence_id_min":
            2,

        "visit_occurrence_id_max":
            5800,

        "target_map_id_mismatch":
            0,

        "required_null_rows":
            0,

        "database_mutation":
            False,
    },

    "foreign_key_gates": {
        "person":
            "PASS",

        "concept":
            "PASS",

        "provider":
            "PASS",

        "care_site":
            "PASS",

        "preceding_visit":
            "PASS",
    },

    "mutation_boundaries": {
        "persistent_table_changed":
            "cdm.visit_occurrence",

        "visit_id_map_changed":
            False,

        "person_map_changed":
            False,

        "visit_id_sequence_changed":
            False,

        "s3_changed":
            False,

        "git_changed_by_materialization":
            False,
    },

    "recovered_tooling_errors": {
        "d2_false_ambiguous":
            "SEQUENCE_BOOLEAN_TEXT_FORMAT",

        "r1_failure":
            "GREP_FIXED_STRING_ANCHOR_MISUSE",

        "database_state_impacted":
            False,

        "real_mutation_retried":
            False,
    },

    "terminal_policy": {
        "materialization_rerun":
            "FORBIDDEN",

        "empty_target_contract_reuse":
            "FORBIDDEN",

        "visit_id_reallocation":
            "FORBIDDEN",

        "blind_retry":
            "FORBIDDEN",

        "future_work_baseline":
            "COMMITTED_CDM_VISIT_STATE",
    },

    "runtime_evidence": {
        "c4a_mutation_contract_sha256":
            sys.argv[8],

        "rehearsal_sql_sha256":
            sys.argv[9],

        "verified_preinsert_prefix_sha256":
            sys.argv[10],

        "d1_design_metadata_sha256":
            sys.argv[11],

        "d2_execution_output_sha256":
            sys.argv[12],

        "d2_post_state_sha256":
            sys.argv[13],

        "d2_summary_sha256":
            sys.argv[14],

        "r2_state_sha256":
            sys.argv[15],

        "r2_summary_sha256":
            sys.argv[16],

        "payload_metadata_sha256":
            sys.argv[17],

        "rehearsal_summary_sha256":
            sys.argv[18],
    },

    "canonical_verification": {
        "database_access":
            "READ_ONLY",

        "database_mutation":
            False,

        "s3_access":
            "NONE",

        "s3_mutation":
            False,

        "ready_for_git_checkpoint":
            True,
    },
}


Path(
    sys.argv[1]
).write_text(
    json.dumps(
        obj,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)
PY_CONTRACT

chmod 0755 \
  "$APP" \
  "$RUNNER"

chmod 0644 \
  "$DOC" \
  "$CONTRACT" \
  "$TEST"

python3 - "$APP" "$TEST" <<'PY_VALIDATE'
import sys
from pathlib import Path

for filename in sys.argv[1:]:
    source = Path(filename).read_text(
        encoding="utf-8"
    )

    compile(
        source,
        filename,
        "exec",
    )

print(
    "PYTHON_SOURCE_VALIDATION=PASS"
)
PY_VALIDATE

bash -n "$RUNNER"

python3 -m json.tool \
  "$CONTRACT" \
  >/dev/null

install_one() {
  src="$1"
  dst="$2"
  mode="$3"

  mkdir -p "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "UNCHANGED=${dst#$ROOT/}"
      return 0
    fi

    echo "ERROR: canonical target exists with conflicting content: ${dst#$ROOT/}"
    return 1
  fi

  install \
    -m "$mode" \
    "$src" \
    "$dst"

  echo "INSTALLED=${dst#$ROOT/}"
}

install_one \
  "$APP" \
  "$ROOT/apps/task003/verify_committed_cdm_visit_materialization.py" \
  0755

install_one \
  "$DOC" \
  "$ROOT/docs/task003/TASK003-STEP06C4E-Committed-CDM-Visit-Materialization.md" \
  0644

install_one \
  "$RUNNER" \
  "$ROOT/scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh" \
  0755

install_one \
  "$CONTRACT" \
  "$ROOT/spark/contracts/processed/visit-cdm-materialization-result-v1.json" \
  0644

install_one \
  "$TEST" \
  "$ROOT/tests/task003/test_committed_cdm_visit_materialization.py" \
  0644

echo 'STEP06C4E_CANONICAL_SOURCE_PREPARED=PASS'
echo 'DATABASE_ACCESS=NONE'
echo 'DATABASE_MUTATION=NO'
echo 'S3_ACCESS=NONE'
echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'

cleanup
trap - EXIT

echo 'STEP06C4E_PREPARE_EXIT_CODE=0'
echo '#### TASK003 STEP06C4E PREPARE COMMITTED CDM VISIT MATERIALIZATION OUTPUT END ####'
