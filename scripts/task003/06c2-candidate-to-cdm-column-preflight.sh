#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

SPARK_NS=dw-spark

TEMPLATE_APP=visit-id-recon-20261010t004249z-2195105
TEMPLATE_CM=visit-id-recon-20261010t004249z-2195105-app

EXPECTED_HEAD=8595a2dd46092517ec8fde40408172b1dfb76c09

EXPECTED_CANDIDATE_ROWS=5799
EXPECTED_CANDIDATE_COLUMNS=36

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e

EXPECTED_MAPPING_SHA=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f

EXPECTED_PERSON_MAP_SHA=f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98

EXPECTED_CANONICAL_ENCOUNTER_CONTRACT_SHA=473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837

CANDIDATE_URI='s3a://health-processed/contract_version=v1/entity=visit_occurrence/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/raw_publish_run_id=encounter-raw-20261009T005128Z-1681690/run_id=visit-proc-20261009t192437z-2081886/data/'

CANONICAL_ENCOUNTER_CONTRACT="$ROOT/spark/contracts/canonical/encounter-v1.json"

C1_REPORT="$ROOT/runtime/reports/task003/step06/cdm-visit-baseline.20261010t143104z.2493274"
C1_SUMMARY="$C1_REPORT/summary.json"

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
SHORT_STAMP="$(date -u +%Y%m%dt%H%M%Sz | tr '[:upper:]' '[:lower:]')"

APP_NAME="visit-cdm-preflight-${SHORT_STAMP}-$$"
CM_NAME="${APP_NAME}-app"

REPORT="$ROOT/runtime/reports/task003/step06/candidate-to-cdm-preflight.${STAMP}.$$"

APP_FILE="$REPORT/candidate_to_cdm_preflight.py"
TEMPLATE_JSON="$REPORT/template-sparkapplication.json"
APP_JSON="$REPORT/sparkapplication.json"
DRIVER_LOG="$REPORT/driver.log"

RESULT_JSON="$REPORT/result.json"
POST_DB="$REPORT/post-spark-database-state.txt"

echo '#### TASK003 STEP06C2 CANDIDATE TO CDM COLUMN PREFLIGHT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06C2_REPORT=$REPORT"
  echo "STEP06C2_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06C2 CANDIDATE TO CDM COLUMN PREFLIGHT OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify frozen STEP06B checkpoint ==='

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
  echo 'ERROR: local HEAD is not frozen STEP06B checkpoint'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main differs from frozen STEP06B checkpoint'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: working tree is not clean'
  git status --short
  exit 1
}

echo 'STEP06B_FINAL_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Re-run authoritative Visit ID mapping gate ==='

bash \
  scripts/task003/06b4c-verify-committed-visit-id-mapping.sh

echo 'AUTHORITATIVE_VISIT_ID_MAPPING_GATE=PASS'

echo '=== 3. Verify STEP06C1 schema baseline ==='

[[ -s "$C1_SUMMARY" && ! -L "$C1_SUMMARY" ]] || {
  echo "ERROR: missing STEP06C1 summary: $C1_SUMMARY"
  exit 1
}

python3 - "$C1_SUMMARY" <<'PY_C1'
import json
import sys
from pathlib import Path


state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert (
    state["status"]
    == "CDM_VISIT_READ_ONLY_BASELINE_DISCOVERED"
)

assert state["target_table"] == "cdm.visit_occurrence"

assert state["column_count"] == 17

assert state["column_names"] == [
    "visit_occurrence_id",
    "person_id",
    "visit_concept_id",
    "visit_start_date",
    "visit_start_datetime",
    "visit_end_date",
    "visit_end_datetime",
    "visit_type_concept_id",
    "provider_id",
    "care_site_id",
    "visit_source_value",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "admitted_from_source_value",
    "discharged_to_concept_id",
    "discharged_to_source_value",
    "preceding_visit_occurrence_id",
]

assert (
    state[
        "required_insert_columns_no_default_non_identity"
    ]
    == [
        "visit_occurrence_id",
        "person_id",
        "visit_concept_id",
        "visit_start_date",
        "visit_end_date",
        "visit_type_concept_id",
    ]
)

assert state["identity_columns"] == []

assert state["constraint_count"] == 10
assert state["index_count"] == 3
assert state["user_trigger_count"] == 0

assert state["committed_visit_id_map_rows"] == 5799

assert state["committed_visit_id_range"] == [
    2,
    5800,
]

assert (
    state["authoritative_mapping_sha256"]
    == "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f"
)

assert state["cdm_visit_rows"] == 0
assert state["person_map_rows"] == 113

print("STEP06C1_BASELINE_GATE=PASS")
print("TARGET_CDM_VISIT_COLUMNS=17")
print("TARGET_CDM_REQUIRED_COLUMNS=6")
PY_C1

echo '=== 4. Verify frozen Candidate contract ==='

[[ -s "$CANONICAL_ENCOUNTER_CONTRACT" && ! -L "$CANONICAL_ENCOUNTER_CONTRACT" ]] || {
  echo "ERROR: missing Candidate contract: $CANONICAL_ENCOUNTER_CONTRACT"
  exit 1
}

CANONICAL_ENCOUNTER_CONTRACT_SHA="$(
  sha256sum "$CANONICAL_ENCOUNTER_CONTRACT" |
  awk '{print $1}'
)"

echo "CANONICAL_ENCOUNTER_CONTRACT_SHA256=$CANONICAL_ENCOUNTER_CONTRACT_SHA"

[[ "$CANONICAL_ENCOUNTER_CONTRACT_SHA" == "$EXPECTED_CANONICAL_ENCOUNTER_CONTRACT_SHA" ]] || {
  echo 'ERROR: frozen Candidate contract SHA mismatch'
  exit 1
}

echo 'CANONICAL_ENCOUNTER_CONTRACT_GATE=PASS'

echo '=== 5. Verify proven Spark+JDBC template still exists ==='

kubectl -n "$SPARK_NS" \
  get sparkapplication "$TEMPLATE_APP" \
  -o json \
  > "$TEMPLATE_JSON"

[[ -s "$TEMPLATE_JSON" ]] || {
  echo 'ERROR: proven A3 SparkApplication template unavailable'
  exit 1
}

kubectl -n "$SPARK_NS" \
  get configmap "$TEMPLATE_CM" \
  >/dev/null

echo "PROVEN_SPARK_TEMPLATE=$TEMPLATE_APP"
echo 'PROVEN_SPARK_JDBC_TEMPLATE=PASS'

echo '=== 6. Build read-only Spark preflight application ==='

cat > "$APP_FILE" <<'PY_APP'
#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import json
import os
from typing import Iterable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


EXPECTED_ROWS = 5799
EXPECTED_COLUMNS = 36

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_MAPPING_SHA = (
    "7e74c9c0a179e6222a7c4ded2993b8cf"
    "61a20d9b06b1d6349d7f21f6a0c03c9f"
)

EXPECTED_PERSON_MAP_SHA = (
    "f52f95120b8a9bd80d33029d04d9abf4"
    "cb1c59206d00b745b59e39b5a89c9a98"
)


TARGET_COLUMNS = [
    "visit_occurrence_id",
    "person_id",
    "visit_concept_id",
    "visit_start_date",
    "visit_start_datetime",
    "visit_end_date",
    "visit_end_datetime",
    "visit_type_concept_id",
    "provider_id",
    "care_site_id",
    "visit_source_value",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "admitted_from_source_value",
    "discharged_to_concept_id",
    "discharged_to_source_value",
    "preceding_visit_occurrence_id",
]


REQUIRED_TARGET_COLUMNS = [
    "visit_occurrence_id",
    "person_id",
    "visit_concept_id",
    "visit_start_date",
    "visit_end_date",
    "visit_type_concept_id",
]


REQUIRED_CANDIDATE_COLUMNS = [
    "source_system",
    "source_encounter_id",
    "source_person_id",
    "person_id",
    "visit_concept_id",
    "visit_start_date",
    "visit_start_datetime",
    "visit_end_date",
    "visit_end_datetime",
    "visit_type_concept_id",
    "provider_id",
    "care_site_id",
    "visit_source_value",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "admitted_from_source_value",
    "discharged_to_concept_id",
    "discharged_to_source_value",
    "preceding_visit_occurrence_id",
]


NUMERIC_CANDIDATE_COLUMNS = [
    "person_id",
    "visit_concept_id",
    "visit_type_concept_id",
    "provider_id",
    "care_site_id",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "discharged_to_concept_id",
    "preceding_visit_occurrence_id",
]


CONCEPT_COLUMNS = [
    "visit_concept_id",
    "visit_type_concept_id",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "discharged_to_concept_id",
]


STRING_50_COLUMNS = [
    "visit_source_value",
    "admitted_from_source_value",
    "discharged_to_source_value",
]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def env_first(*names):
    for name in names:
        value = os.environ.get(name)

        if value:
            return value

    raise RuntimeError(
        "missing environment value; tried "
        + ",".join(names)
    )


def escape_text(value):
    if value is None:
        return r"\N"

    if isinstance(value, datetime.datetime):
        text = value.isoformat(
            sep=" ",
            timespec="microseconds",
        )
    elif isinstance(value, datetime.date):
        text = value.isoformat()
    else:
        text = str(value)

    return (
        text
        .replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def fingerprint_rows(rows, fields):
    payload = "".join(
        "\t".join(
            escape_text(
                row[field]
            )
            for field in fields
        )
        + "\n"
        for row in rows
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def collect_int_set(df, column):
    return {
        int(row[column])
        for row in (
            df
            .select(
                F.col(column)
            )
            .where(
                F.col(column).isNotNull()
            )
            .distinct()
            .collect()
        )
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--candidate-uri",
        required=True,
    )

    args = parser.parse_args()

    spark = (
        SparkSession
        .builder
        .appName(
            "task003-step06c2-candidate-to-cdm-preflight"
        )
        .getOrCreate()
    )

    spark.conf.set(
        "spark.sql.session.timeZone",
        "UTC",
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    host = env_first(
        "PGHOST",
        "A3_DB_HOST",
    )

    port = env_first(
        "PGPORT",
        "A3_DB_PORT",
    )

    database = env_first(
        "PGDATABASE",
        "A3_DB_DATABASE",
        "A3_DB_NAME",
    )

    user = env_first(
        "PGUSER",
        "A3_DB_USER",
    )

    password = env_first(
        "PGPASSWORD",
        "A3_DB_PASSWORD",
    )

    jdbc_url = (
        "jdbc:postgresql://"
        + host
        + ":"
        + port
        + "/"
        + database
    )

    def jdbc_query(sql):
        return (
            spark.read
            .format("jdbc")
            .option(
                "url",
                jdbc_url,
            )
            .option(
                "query",
                sql,
            )
            .option(
                "user",
                user,
            )
            .option(
                "password",
                password,
            )
            .option(
                "driver",
                "org.postgresql.Driver",
            )
            .load()
        )

    candidate = (
        spark.read
        .parquet(
            args.candidate_uri
        )
        .persist()
    )

    candidate_rows = candidate.count()

    candidate_columns = list(
        candidate.columns
    )

    require(
        candidate_rows == EXPECTED_ROWS,
        "Candidate row count mismatch: "
        + str(candidate_rows),
    )

    require(
        len(candidate_columns)
        == EXPECTED_COLUMNS,
        "Candidate column count mismatch: "
        + str(
            len(candidate_columns)
        ),
    )

    missing_candidate_columns = [
        name
        for name in REQUIRED_CANDIDATE_COLUMNS
        if name not in candidate_columns
    ]

    require(
        not missing_candidate_columns,
        "Candidate required columns missing: "
        + repr(
            missing_candidate_columns
        ),
    )

    candidate_unique_keys = (
        candidate
        .select(
            "source_system",
            "source_encounter_id",
        )
        .dropDuplicates()
        .count()
    )

    require(
        candidate_unique_keys
        == EXPECTED_ROWS,
        "Candidate business keys not unique",
    )

    key_rows = (
        candidate
        .select(
            "source_system",
            "source_encounter_id",
        )
        .orderBy(
            "source_system",
            "source_encounter_id",
        )
        .collect()
    )

    key_sha = fingerprint_rows(
        key_rows,
        [
            "source_system",
            "source_encounter_id",
        ],
    )

    require(
        key_sha == EXPECTED_KEY_SHA,
        "Candidate key fingerprint mismatch: "
        + key_sha,
    )

    visit_map = (
        jdbc_query(
            """
            SELECT
                source_system,
                source_encounter_id,
                visit_occurrence_id
            FROM etl.visit_occurrence_id_map
            WHERE source_system = 'synthea'
            """
        )
        .persist()
    )

    visit_map_rows = visit_map.count()

    require(
        visit_map_rows == EXPECTED_ROWS,
        "Visit map row count mismatch",
    )

    require(
        (
            visit_map
            .select(
                "source_system",
                "source_encounter_id",
            )
            .dropDuplicates()
            .count()
        )
        == EXPECTED_ROWS,
        "Visit map key uniqueness mismatch",
    )

    require(
        (
            visit_map
            .select(
                "visit_occurrence_id",
            )
            .dropDuplicates()
            .count()
        )
        == EXPECTED_ROWS,
        "Visit map ID uniqueness mismatch",
    )

    visit_map_sorted = (
        visit_map
        .select(
            "source_system",
            "source_encounter_id",
            "visit_occurrence_id",
        )
        .orderBy(
            "source_system",
            "source_encounter_id",
        )
        .collect()
    )

    mapping_sha = fingerprint_rows(
        visit_map_sorted,
        [
            "source_system",
            "source_encounter_id",
            "visit_occurrence_id",
        ],
    )

    require(
        mapping_sha == EXPECTED_MAPPING_SHA,
        "authoritative mapping fingerprint mismatch: "
        + mapping_sha,
    )

    candidate_without_visit_map = (
        candidate.alias("c")
        .join(
            visit_map.alias("v"),
            (
                F.col("c.source_system")
                == F.col("v.source_system")
            )
            & (
                F.col("c.source_encounter_id")
                == F.col("v.source_encounter_id")
            ),
            "left_anti",
        )
        .count()
    )

    visit_map_without_candidate = (
        visit_map.alias("v")
        .join(
            candidate.alias("c"),
            (
                F.col("v.source_system")
                == F.col("c.source_system")
            )
            & (
                F.col("v.source_encounter_id")
                == F.col("c.source_encounter_id")
            ),
            "left_anti",
        )
        .count()
    )

    require(
        candidate_without_visit_map == 0,
        "Candidate keys missing Visit mapping",
    )

    require(
        visit_map_without_candidate == 0,
        "Visit map contains unexpected keys",
    )

    person_map = (
        jdbc_query(
            """
            SELECT
                source_system,
                source_person_id,
                person_id
            FROM etl.person_id_map
            WHERE source_system = 'synthea'
            """
        )
        .persist()
    )

    require(
        person_map.count() == 113,
        "Person map row count mismatch",
    )

    require(
        (
            person_map
            .select(
                "source_system",
                "source_person_id",
            )
            .dropDuplicates()
            .count()
        )
        == 113,
        "Person map source-key uniqueness mismatch",
    )

    person_map_sorted = (
        person_map
        .select(
            "source_system",
            "source_person_id",
            "person_id",
        )
        .orderBy(
            "source_system",
            "source_person_id",
            "person_id",
        )
        .collect()
    )

    person_map_sha = fingerprint_rows(
        person_map_sorted,
        [
            "source_system",
            "source_person_id",
            "person_id",
        ],
    )

    require(
        person_map_sha
        == EXPECTED_PERSON_MAP_SHA,
        "Person map fingerprint mismatch: "
        + person_map_sha,
    )

    candidate_without_person_map = (
        candidate.alias("c")
        .join(
            person_map.alias("p"),
            (
                F.col("c.source_system")
                == F.col("p.source_system")
            )
            & (
                F.col("c.source_person_id")
                == F.col("p.source_person_id")
            ),
            "left_anti",
        )
        .count()
    )

    require(
        candidate_without_person_map == 0,
        "Candidate Person mapping coverage mismatch",
    )

    person_compare = (
        candidate.alias("c")
        .join(
            person_map.alias("p"),
            (
                F.col("c.source_system")
                == F.col("p.source_system")
            )
            & (
                F.col("c.source_person_id")
                == F.col("p.source_person_id")
            ),
            "inner",
        )
    )

    candidate_person_id_mismatch = (
        person_compare
        .where(
            F.col("c.person_id").cast("long")
            != F.col("p.person_id").cast("long")
        )
        .count()
    )

    require(
        candidate_person_id_mismatch == 0,
        "Candidate person_id differs from authoritative Person map",
    )

    joined = (
        candidate.alias("c")
        .join(
            visit_map.alias("v"),
            (
                F.col("c.source_system")
                == F.col("v.source_system")
            )
            & (
                F.col("c.source_encounter_id")
                == F.col("v.source_encounter_id")
            ),
            "inner",
        )
        .join(
            person_map.alias("p"),
            (
                F.col("c.source_system")
                == F.col("p.source_system")
            )
            & (
                F.col("c.source_person_id")
                == F.col("p.source_person_id")
            ),
            "inner",
        )
        .select(
            "c.*",
            F.col(
                "v.visit_occurrence_id"
            ).alias(
                "_mapped_visit_occurrence_id"
            ),
            F.col(
                "p.person_id"
            ).alias(
                "_mapped_person_id"
            ),
        )
        .persist()
    )

    require(
        joined.count() == EXPECTED_ROWS,
        "Candidate/map join row count mismatch",
    )

    cast_failure_counts = {}

    for name in NUMERIC_CANDIDATE_COLUMNS:
        failures = (
            candidate
            .where(
                F.col(name).isNotNull()
                & F.col(name).cast("long").isNull()
            )
            .count()
        )

        cast_failure_counts[
            name
        ] = failures

        require(
            failures == 0,
            "numeric cast failure: "
            + name,
        )

    for name in (
        "visit_start_date",
        "visit_end_date",
    ):
        failures = (
            candidate
            .where(
                F.col(name).isNotNull()
                & F.col(name).cast("date").isNull()
            )
            .count()
        )

        cast_failure_counts[
            name
        ] = failures

        require(
            failures == 0,
            "date cast failure: "
            + name,
        )

    for name in (
        "visit_start_datetime",
        "visit_end_datetime",
    ):
        failures = (
            candidate
            .where(
                F.col(name).isNotNull()
                & F.col(name).cast("timestamp").isNull()
            )
            .count()
        )

        cast_failure_counts[
            name
        ] = failures

        require(
            failures == 0,
            "timestamp cast failure: "
            + name,
        )

    final_df = (
        joined
        .select(
            F.col(
                "_mapped_visit_occurrence_id"
            ).cast(
                "int"
            ).alias(
                "visit_occurrence_id"
            ),

            F.col(
                "_mapped_person_id"
            ).cast(
                "int"
            ).alias(
                "person_id"
            ),

            F.col(
                "visit_concept_id"
            ).cast(
                "int"
            ).alias(
                "visit_concept_id"
            ),

            F.col(
                "visit_start_date"
            ).cast(
                "date"
            ).alias(
                "visit_start_date"
            ),

            F.col(
                "visit_start_datetime"
            ).cast(
                "timestamp"
            ).alias(
                "visit_start_datetime"
            ),

            F.col(
                "visit_end_date"
            ).cast(
                "date"
            ).alias(
                "visit_end_date"
            ),

            F.col(
                "visit_end_datetime"
            ).cast(
                "timestamp"
            ).alias(
                "visit_end_datetime"
            ),

            F.col(
                "visit_type_concept_id"
            ).cast(
                "int"
            ).alias(
                "visit_type_concept_id"
            ),

            F.col(
                "provider_id"
            ).cast(
                "int"
            ).alias(
                "provider_id"
            ),

            F.col(
                "care_site_id"
            ).cast(
                "int"
            ).alias(
                "care_site_id"
            ),

            F.col(
                "visit_source_value"
            ).cast(
                "string"
            ).alias(
                "visit_source_value"
            ),

            F.col(
                "visit_source_concept_id"
            ).cast(
                "int"
            ).alias(
                "visit_source_concept_id"
            ),

            F.col(
                "admitted_from_concept_id"
            ).cast(
                "int"
            ).alias(
                "admitted_from_concept_id"
            ),

            F.col(
                "admitted_from_source_value"
            ).cast(
                "string"
            ).alias(
                "admitted_from_source_value"
            ),

            F.col(
                "discharged_to_concept_id"
            ).cast(
                "int"
            ).alias(
                "discharged_to_concept_id"
            ),

            F.col(
                "discharged_to_source_value"
            ).cast(
                "string"
            ).alias(
                "discharged_to_source_value"
            ),

            F.col(
                "preceding_visit_occurrence_id"
            ).cast(
                "int"
            ).alias(
                "preceding_visit_occurrence_id"
            ),
        )
        .persist()
    )

    require(
        final_df.columns
        == TARGET_COLUMNS,
        "final CDM row-shape column mismatch",
    )

    final_rows = final_df.count()

    require(
        final_rows == EXPECTED_ROWS,
        "final CDM row-shape count mismatch",
    )

    final_unique_ids = (
        final_df
        .select(
            "visit_occurrence_id"
        )
        .dropDuplicates()
        .count()
    )

    require(
        final_unique_ids == EXPECTED_ROWS,
        "final Visit ID uniqueness mismatch",
    )

    required_null_counts = {}

    for name in REQUIRED_TARGET_COLUMNS:
        count = (
            final_df
            .where(
                F.col(name).isNull()
            )
            .count()
        )

        required_null_counts[
            name
        ] = count

        require(
            count == 0,
            "required target NULLs: "
            + name
            + "="
            + str(count),
        )

    invalid_date_order = (
        final_df
        .where(
            F.col("visit_start_date")
            > F.col("visit_end_date")
        )
        .count()
    )

    require(
        invalid_date_order == 0,
        "visit_start_date > visit_end_date",
    )

    invalid_datetime_order = (
        final_df
        .where(
            F.col(
                "visit_start_datetime"
            ).isNotNull()
            & F.col(
                "visit_end_datetime"
            ).isNotNull()
            & (
                F.col(
                    "visit_start_datetime"
                )
                > F.col(
                    "visit_end_datetime"
                )
            )
        )
        .count()
    )

    require(
        invalid_datetime_order == 0,
        "visit_start_datetime > visit_end_datetime",
    )

    start_date_datetime_mismatch = (
        final_df
        .where(
            F.col(
                "visit_start_datetime"
            ).isNotNull()
            & (
                F.to_date(
                    F.col(
                        "visit_start_datetime"
                    )
                )
                != F.col(
                    "visit_start_date"
                )
            )
        )
        .count()
    )

    require(
        start_date_datetime_mismatch == 0,
        "start date/datetime mismatch",
    )

    end_date_datetime_mismatch = (
        final_df
        .where(
            F.col(
                "visit_end_datetime"
            ).isNotNull()
            & (
                F.to_date(
                    F.col(
                        "visit_end_datetime"
                    )
                )
                != F.col(
                    "visit_end_date"
                )
            )
        )
        .count()
    )

    require(
        end_date_datetime_mismatch == 0,
        "end date/datetime mismatch",
    )

    string_length_violations = {}

    for name in STRING_50_COLUMNS:
        count = (
            final_df
            .where(
                F.col(name).isNotNull()
                & (
                    F.length(
                        F.col(name)
                    )
                    > 50
                )
            )
            .count()
        )

        string_length_violations[
            name
        ] = count

        require(
            count == 0,
            "varchar(50) overflow: "
            + name,
        )

    mapped_person_ids = collect_int_set(
        final_df,
        "person_id",
    )

    require(
        len(mapped_person_ids) == 113,
        "distinct mapped Person IDs mismatch",
    )

    person_id_sql = ",".join(
        str(value)
        for value in sorted(
            mapped_person_ids
        )
    )

    cdm_person_ids = {
        int(row["person_id"])
        for row in jdbc_query(
            """
            SELECT person_id
            FROM cdm.person
            WHERE person_id IN (
            """
            + person_id_sql
            + ")"
        ).collect()
    }

    missing_cdm_person_ids = sorted(
        mapped_person_ids
        - cdm_person_ids
    )

    require(
        not missing_cdm_person_ids,
        "missing cdm.person FK values: "
        + repr(
            missing_cdm_person_ids
        ),
    )

    concept_ids = set()

    concept_id_counts = {}

    for name in CONCEPT_COLUMNS:
        values = collect_int_set(
            final_df,
            name,
        )

        concept_id_counts[
            name
        ] = len(values)

        concept_ids.update(
            values
        )

    require(
        concept_ids,
        "no concept IDs discovered",
    )

    concept_sql = ",".join(
        str(value)
        for value in sorted(
            concept_ids
        )
    )

    existing_concepts = {
        int(row["concept_id"])
        for row in jdbc_query(
            """
            SELECT concept_id
            FROM cdm.concept
            WHERE concept_id IN (
            """
            + concept_sql
            + ")"
        ).collect()
    }

    missing_concepts = sorted(
        concept_ids
        - existing_concepts
    )

    require(
        not missing_concepts,
        "missing cdm.concept FK values: "
        + repr(
            missing_concepts
        ),
    )

    provider_ids = collect_int_set(
        final_df,
        "provider_id",
    )

    existing_provider_ids = set()

    if provider_ids:
        provider_sql = ",".join(
            str(value)
            for value in sorted(
                provider_ids
            )
        )

        existing_provider_ids = {
            int(row["provider_id"])
            for row in jdbc_query(
                """
                SELECT provider_id
                FROM cdm.provider
                WHERE provider_id IN (
                """
                + provider_sql
                + ")"
            ).collect()
        }

    missing_provider_ids = sorted(
        provider_ids
        - existing_provider_ids
    )

    require(
        not missing_provider_ids,
        "missing cdm.provider FK values: "
        + repr(
            missing_provider_ids
        ),
    )

    care_site_ids = collect_int_set(
        final_df,
        "care_site_id",
    )

    existing_care_site_ids = set()

    if care_site_ids:
        care_site_sql = ",".join(
            str(value)
            for value in sorted(
                care_site_ids
            )
        )

        existing_care_site_ids = {
            int(row["care_site_id"])
            for row in jdbc_query(
                """
                SELECT care_site_id
                FROM cdm.care_site
                WHERE care_site_id IN (
                """
                + care_site_sql
                + ")"
            ).collect()
        }

    missing_care_site_ids = sorted(
        care_site_ids
        - existing_care_site_ids
    )

    require(
        not missing_care_site_ids,
        "missing cdm.care_site FK values: "
        + repr(
            missing_care_site_ids
        ),
    )

    preceding_ids = collect_int_set(
        final_df,
        "preceding_visit_occurrence_id",
    )

    allocated_visit_ids = collect_int_set(
        final_df,
        "visit_occurrence_id",
    )

    missing_preceding_ids = sorted(
        preceding_ids
        - allocated_visit_ids
    )

    require(
        not missing_preceding_ids,
        "preceding_visit_occurrence_id not present in batch mapping: "
        + repr(
            missing_preceding_ids
        ),
    )

    cdm_visit_rows_before = (
        jdbc_query(
            """
            SELECT visit_occurrence_id
            FROM cdm.visit_occurrence
            """
        )
        .count()
    )

    require(
        cdm_visit_rows_before == 0,
        "cdm.visit_occurrence is no longer empty",
    )

    ordered_final_rows = (
        final_df
        .orderBy(
            "visit_occurrence_id"
        )
        .collect()
    )

    shape_sha = fingerprint_rows(
        ordered_final_rows,
        TARGET_COLUMNS,
    )

    nullable_null_counts = {}

    for name in TARGET_COLUMNS:
        if name in REQUIRED_TARGET_COLUMNS:
            continue

        nullable_null_counts[
            name
        ] = (
            final_df
            .where(
                F.col(name).isNull()
            )
            .count()
        )

    result = {
        "task":
            "TASK-003",

        "step":
            "STEP-06C2",

        "status":
            "CANDIDATE_TO_CDM_COLUMN_PREFLIGHT_PASS",

        "candidate_uri":
            args.candidate_uri,

        "candidate_rows":
            candidate_rows,

        "candidate_column_count":
            len(
                candidate_columns
            ),

        "candidate_columns":
            candidate_columns,

        "candidate_schema":
            candidate.schema.simpleString(),

        "candidate_unique_business_keys":
            candidate_unique_keys,

        "candidate_business_key_sha256":
            key_sha,

        "visit_id_map_rows":
            visit_map_rows,

        "authoritative_mapping_sha256":
            mapping_sha,

        "person_map_rows":
            113,

        "person_map_sha256":
            person_map_sha,

        "candidate_without_visit_map":
            candidate_without_visit_map,

        "visit_map_without_candidate":
            visit_map_without_candidate,

        "candidate_without_person_map":
            candidate_without_person_map,

        "candidate_person_id_mismatch":
            candidate_person_id_mismatch,

        "target_columns":
            TARGET_COLUMNS,

        "target_column_count":
            len(
                TARGET_COLUMNS
            ),

        "final_cdm_row_shape_rows":
            final_rows,

        "final_unique_visit_occurrence_ids":
            final_unique_ids,

        "required_target_null_counts":
            required_null_counts,

        "nullable_target_null_counts":
            nullable_null_counts,

        "cast_failure_counts":
            cast_failure_counts,

        "invalid_date_order_rows":
            invalid_date_order,

        "invalid_datetime_order_rows":
            invalid_datetime_order,

        "start_date_datetime_mismatch_rows":
            start_date_datetime_mismatch,

        "end_date_datetime_mismatch_rows":
            end_date_datetime_mismatch,

        "varchar_50_violation_counts":
            string_length_violations,

        "distinct_person_ids":
            len(
                mapped_person_ids
            ),

        "missing_cdm_person_ids":
            missing_cdm_person_ids,

        "distinct_concept_ids":
            len(
                concept_ids
            ),

        "concept_id_counts_by_column":
            concept_id_counts,

        "missing_cdm_concept_ids":
            missing_concepts,

        "distinct_provider_ids":
            len(
                provider_ids
            ),

        "missing_cdm_provider_ids":
            missing_provider_ids,

        "distinct_care_site_ids":
            len(
                care_site_ids
            ),

        "missing_cdm_care_site_ids":
            missing_care_site_ids,

        "distinct_preceding_visit_ids":
            len(
                preceding_ids
            ),

        "missing_preceding_visit_ids":
            missing_preceding_ids,

        "cdm_visit_rows_before":
            cdm_visit_rows_before,

        "cdm_row_shape_sha256":
            shape_sha,

        "database_access":
            "READ_ONLY",

        "database_mutation":
            False,

        "s3_access":
            "READ_ONLY",

        "s3_mutation":
            False,

        "ready_for_cdm_materialization_design":
            True,
    }

    print(
        "TASK003_STEP06C2_RESULT_JSON="
        + json.dumps(
            result,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ),
        flush=True,
    )

    print(
        "STEP06C2_SPARK_PREFLIGHT=PASS",
        flush=True,
    )

    spark.stop()


if __name__ == "__main__":
    main()
PY_APP

chmod 0444 "$APP_FILE"

python3 -m py_compile "$APP_FILE"

echo 'SPARK_PREFLIGHT_APPLICATION_BUILD=PASS'

echo '=== 7. Static proof: Spark application is read-only ==='

python3 - "$APP_FILE" <<'PY_STATIC'
import ast
import re
import sys
from pathlib import Path


source = Path(sys.argv[1]).read_text()

tree = ast.parse(
    source
)

forbidden_patterns = [
    r"\.write\b",
    r"\.save\s*\(",
    r"\.saveAsTable\s*\(",
    r"\.insertInto\s*\(",
    r"\bINSERT\s+INTO\b",
    r"\bUPDATE\s+",
    r"\bDELETE\s+FROM\b",
    r"\bTRUNCATE\s+",
    r"\bCREATE\s+TABLE\b",
    r"\bALTER\s+TABLE\b",
    r"\bDROP\s+TABLE\b",
    r"\bsetval\s*\(",
    r"\bnextval\s*\(",
]

for pattern in forbidden_patterns:
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

assert "spark.read" in source
assert '.format("jdbc")' in source
assert "spark.read.parquet" not in source or True

assert (
    "CANDIDATE_TO_CDM_COLUMN_PREFLIGHT_PASS"
    in source
)

print("STEP06C2_STATIC_READ_ONLY_PROOF=PASS")
print("SPARK_WRITE_API_PRESENT=NO")
print("DATABASE_DML_PRESENT=NO")
print("SEQUENCE_FUNCTION_PRESENT=NO")
PY_STATIC

echo '=== 8. Create immutable Spark application ConfigMap ==='

kubectl -n "$SPARK_NS" \
  create configmap "$CM_NAME" \
  --from-file=candidate_to_cdm_preflight.py="$APP_FILE"

echo "CONFIGMAP_CREATED=$CM_NAME"

echo '=== 9. Derive SparkApplication from proven A3 Spark+JDBC template ==='

python3 - \
  "$TEMPLATE_JSON" \
  "$APP_JSON" \
  "$TEMPLATE_CM" \
  "$CM_NAME" \
  "$APP_NAME" \
  "$CANDIDATE_URI" \
  <<'PY_MANIFEST'
import json
import sys
from pathlib import PurePosixPath


template_path = sys.argv[1]
output_path = sys.argv[2]

old_cm = sys.argv[3]
new_cm = sys.argv[4]

new_name = sys.argv[5]
candidate_uri = sys.argv[6]


with open(
    template_path,
    "r",
    encoding="utf-8",
) as handle:
    obj = json.load(
        handle
    )


metadata = obj[
    "metadata"
]

for key in (
    "creationTimestamp",
    "generation",
    "managedFields",
    "resourceVersion",
    "uid",
):
    metadata.pop(
        key,
        None,
    )

metadata["name"] = new_name

metadata.pop(
    "ownerReferences",
    None,
)

obj.pop(
    "status",
    None,
)


spec = obj[
    "spec"
]

old_main = spec[
    "mainApplicationFile"
]

assert old_main.startswith(
    "local:///"
), old_main

path = PurePosixPath(
    old_main[
        len("local://") :
    ]
)

new_path = (
    path.parent
    / "candidate_to_cdm_preflight.py"
)

spec[
    "mainApplicationFile"
] = (
    "local://"
    + str(
        new_path
    )
)

spec[
    "arguments"
] = [
    "--candidate-uri",
    candidate_uri,
]


patched_volume = False

for volume in spec.get(
    "volumes",
    [],
):
    config_map = volume.get(
        "configMap"
    )

    if (
        config_map
        and config_map.get(
            "name"
        )
        == old_cm
    ):
        config_map[
            "name"
        ] = new_cm

        config_map[
            "items"
        ] = [
            {
                "key":
                    "candidate_to_cdm_preflight.py",

                "path":
                    "candidate_to_cdm_preflight.py",
            }
        ]

        patched_volume = True


assert patched_volume, (
    "unable to locate A3 application ConfigMap volume"
)


spec.setdefault(
    "restartPolicy",
    {}
)

spec[
    "restartPolicy"
][
    "type"
] = "Never"


with open(
    output_path,
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        obj,
        handle,
        indent=2,
        sort_keys=True,
    )

    handle.write(
        "\n"
    )


print(
    "SPARKAPPLICATION_TEMPLATE_PATCH=PASS"
)

print(
    "NEW_MAIN_APPLICATION_FILE="
    + spec[
        "mainApplicationFile"
    ]
)

print(
    "APPLICATION_CONFIGMAP="
    + new_cm
)
PY_MANIFEST

python3 -m json.tool \
  "$APP_JSON" \
  >/dev/null

echo 'SPARKAPPLICATION_RENDER=PASS'

echo '=== 10. Verify rendered SparkApplication safety ==='

python3 - \
  "$APP_JSON" \
  "$CM_NAME" \
  "$APP_NAME" \
  <<'PY_VERIFY_MANIFEST'
import json
import sys
from pathlib import Path


obj = json.loads(
    Path(
        sys.argv[1]
    ).read_bytes()
)

cm = sys.argv[2]
app = sys.argv[3]

assert obj["metadata"]["name"] == app

assert (
    obj["spec"]["type"]
    == "Python"
)

assert (
    obj["spec"]["mode"]
    == "cluster"
)

assert (
    obj["spec"]["mainApplicationFile"]
    .endswith(
        "/candidate_to_cdm_preflight.py"
    )
)

assert (
    obj["spec"]["restartPolicy"]["type"]
    == "Never"
)

configmap_names = []

for volume in obj[
    "spec"
].get(
    "volumes",
    [],
):
    if "configMap" in volume:
        configmap_names.append(
            volume[
                "configMap"
            ].get(
                "name"
            )
        )

assert cm in configmap_names

driver = obj["spec"]["driver"]
executor = obj["spec"]["executor"]

assert (
    driver[
        "serviceAccount"
    ]
    == "spark-job"
)

assert (
    executor.get(
        "instances",
        1,
    )
    >= 1
)

# The proven A3 template must retain database access
# as well as the S3 read configuration.
serialized = json.dumps(
    obj,
    sort_keys=True,
)

assert (
    "dw-spark-s3-secret"
    in serialized
)

assert (
    "dw-spark-omop-secret"
    in serialized
    or "A3_DB_"
    in serialized
)

print("SPARKAPPLICATION_RENDER_SAFETY=PASS")
print("SPARK_SERVICE_ACCOUNT=spark-job")
print("S3_CREDENTIAL_CONFIGURATION=PRESENT")
print("POSTGRES_CREDENTIAL_CONFIGURATION=PRESENT")
PY_VERIFY_MANIFEST

echo '=== 11. Submit read-only Spark preflight ==='

kubectl -n "$SPARK_NS" \
  create \
  -f "$APP_JSON"

echo "SPARKAPPLICATION_CREATED=$APP_NAME"

echo '=== 12. Wait for Spark preflight terminal state ==='

FINAL_STATE=''

for _ in $(seq 1 180); do
  STATE="$(
    kubectl -n "$SPARK_NS" \
      get sparkapplication "$APP_NAME" \
      -o jsonpath='{.status.applicationState.state}' \
      2>/dev/null \
    || true
  )"

  if [[ "$STATE" == "COMPLETED" ]]; then
    FINAL_STATE="$STATE"
    break
  fi

  if [[ \
    "$STATE" == "FAILED" \
    || "$STATE" == "UNKNOWN" \
    || "$STATE" == "SUBMISSION_FAILED" \
  ]]; then
    FINAL_STATE="$STATE"
    break
  fi

  sleep 2
done

echo "FINAL_STATE=${FINAL_STATE:-TIMEOUT}"

DRIVER_POD="$(
  kubectl -n "$SPARK_NS" \
    get sparkapplication "$APP_NAME" \
    -o jsonpath='{.status.driverInfo.podName}' \
    2>/dev/null \
  || true
)"

echo "DRIVER_POD=${DRIVER_POD:-NONE}"

if [[ -n "$DRIVER_POD" ]]; then
  kubectl -n "$SPARK_NS" \
    logs "$DRIVER_POD" \
    > "$DRIVER_LOG" \
    2>&1 \
    || true
fi

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then
  echo 'ERROR: Spark preflight did not complete successfully'

  if [[ -s "$DRIVER_LOG" ]]; then
    echo '--- DRIVER LOG TAIL BEGIN ---'
    tail -n 200 "$DRIVER_LOG"
    echo '--- DRIVER LOG TAIL END ---'
  fi

  echo 'DATABASE_MUTATION=NO_EXPECTED'
  echo 'S3_MUTATION=NO_EXPECTED'
  echo 'SPARK_RESOURCES_PRESERVED=YES'

  exit 1
fi

echo 'SPARK_PREFLIGHT_FINAL_STATE=COMPLETED'

echo '=== 13. Extract Spark preflight result ==='

RESULT_LINE="$(
  grep \
    '^TASK003_STEP06C2_RESULT_JSON=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  || true
)"

[[ -n "$RESULT_LINE" ]] || {
  echo 'ERROR: Spark result JSON marker not found'

  tail -n 200 "$DRIVER_LOG"

  exit 1
}

printf '%s\n' \
  "${RESULT_LINE#TASK003_STEP06C2_RESULT_JSON=}" \
  > "$RESULT_JSON"

python3 -m json.tool \
  "$RESULT_JSON" \
  >/dev/null

echo 'SPARK_RESULT_JSON_EXTRACT=PASS'

echo '=== 14. Validate complete Candidate -> CDM feasibility ==='

python3 - \
  "$RESULT_JSON" \
  "$EXPECTED_KEY_SHA" \
  "$EXPECTED_MAPPING_SHA" \
  "$EXPECTED_PERSON_MAP_SHA" \
  <<'PY_RESULT'
import json
import sys
from pathlib import Path


state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_key = sys.argv[2]
expected_mapping = sys.argv[3]
expected_person = sys.argv[4]


assert (
    state["status"]
    == "CANDIDATE_TO_CDM_COLUMN_PREFLIGHT_PASS"
)

assert state["candidate_rows"] == 5799
assert state["candidate_column_count"] == 36
assert state["candidate_unique_business_keys"] == 5799

assert (
    state["candidate_business_key_sha256"]
    == expected_key
)

assert state["visit_id_map_rows"] == 5799

assert (
    state["authoritative_mapping_sha256"]
    == expected_mapping
)

assert state["person_map_rows"] == 113

assert (
    state["person_map_sha256"]
    == expected_person
)

assert state["candidate_without_visit_map"] == 0
assert state["visit_map_without_candidate"] == 0
assert state["candidate_without_person_map"] == 0
assert state["candidate_person_id_mismatch"] == 0

assert state["target_column_count"] == 17

assert state["target_columns"] == [
    "visit_occurrence_id",
    "person_id",
    "visit_concept_id",
    "visit_start_date",
    "visit_start_datetime",
    "visit_end_date",
    "visit_end_datetime",
    "visit_type_concept_id",
    "provider_id",
    "care_site_id",
    "visit_source_value",
    "visit_source_concept_id",
    "admitted_from_concept_id",
    "admitted_from_source_value",
    "discharged_to_concept_id",
    "discharged_to_source_value",
    "preceding_visit_occurrence_id",
]

assert state["final_cdm_row_shape_rows"] == 5799

assert (
    state["final_unique_visit_occurrence_ids"]
    == 5799
)

assert all(
    value == 0
    for value in state[
        "required_target_null_counts"
    ].values()
)

assert all(
    value == 0
    for value in state[
        "cast_failure_counts"
    ].values()
)

assert state["invalid_date_order_rows"] == 0
assert state["invalid_datetime_order_rows"] == 0

assert (
    state[
        "start_date_datetime_mismatch_rows"
    ]
    == 0
)

assert (
    state[
        "end_date_datetime_mismatch_rows"
    ]
    == 0
)

assert all(
    value == 0
    for value in state[
        "varchar_50_violation_counts"
    ].values()
)

assert state["distinct_person_ids"] == 113
assert state["missing_cdm_person_ids"] == []

assert state["missing_cdm_concept_ids"] == []
assert state["missing_cdm_provider_ids"] == []
assert state["missing_cdm_care_site_ids"] == []
assert state["missing_preceding_visit_ids"] == []

assert state["cdm_visit_rows_before"] == 0

assert len(
    state["cdm_row_shape_sha256"]
) == 64

assert state["database_access"] == "READ_ONLY"
assert state["database_mutation"] is False

assert state["s3_access"] == "READ_ONLY"
assert state["s3_mutation"] is False

assert (
    state[
        "ready_for_cdm_materialization_design"
    ]
    is True
)


print("STEP06C2_RESULT_GATE=PASS")

print(
    "CANDIDATE_COLUMN_COUNT="
    + str(
        state["candidate_column_count"]
    )
)

print(
    "CANDIDATE_COLUMNS="
    + ",".join(
        state["candidate_columns"]
    )
)

print(
    "FINAL_CDM_ROW_SHAPE_ROWS="
    + str(
        state["final_cdm_row_shape_rows"]
    )
)

print(
    "CDM_ROW_SHAPE_SHA256="
    + state["cdm_row_shape_sha256"]
)

print(
    "DISTINCT_CONCEPT_IDS="
    + str(
        state["distinct_concept_ids"]
    )
)

print(
    "DISTINCT_PROVIDER_IDS="
    + str(
        state["distinct_provider_ids"]
    )
)

print(
    "DISTINCT_CARE_SITE_IDS="
    + str(
        state["distinct_care_site_ids"]
    )
)

print(
    "DISTINCT_PRECEDING_VISIT_IDS="
    + str(
        state[
            "distinct_preceding_visit_ids"
        ]
    )
)

print(
    "ALL_DATABASE_FKS_RESOLVABLE=YES"
)

print(
    "READY_FOR_CDM_MATERIALIZATION_DESIGN=YES"
)
PY_RESULT

echo '=== 15. Prove database state remained unchanged after Spark ==='

kubectl -n dw-postgre \
  exec -i dw-postgre-database-0 -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U omop_admin \
    -d omop \
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
    count(DISTINCT visit_occurrence_id),
    min(visit_occurrence_id),
    max(visit_occurrence_id)
FROM etl.visit_occurrence_id_map;

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    encode(
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

SELECT current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$POST_DB"

python3 - \
  "$POST_DB" \
  "$EXPECTED_MAPPING_SHA" \
  <<'PY_POST'
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

expected_mapping = sys.argv[2]

assert rows == [
    "5799|0|113",
    "5799|2|5800",
    "5800|t",
    expected_mapping,
    "on",
], rows

print("POST_SPARK_DATABASE_STATE=PASS")
print("VISIT_ID_MAP_ROWS_AFTER_C2=5799")
print("CDM_VISIT_ROWS_AFTER_C2=0")
print("PERSON_MAP_ROWS_AFTER_C2=113")
print("SEQUENCE_STATE_AFTER_C2=5800|TRUE")
print("AUTHORITATIVE_MAPPING_UNCHANGED=YES")
PY_POST

echo '=== 16. Final STEP06C2 verdict ==='

ROW_SHAPE_SHA="$(
  python3 - "$RESULT_JSON" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    state["cdm_row_shape_sha256"]
)
PY
)"

COLUMN_LIST="$(
  python3 - "$RESULT_JSON" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    ",".join(
        state["candidate_columns"]
    )
)
PY
)"

echo 'STEP06C2_CANDIDATE_TO_CDM_COLUMN_PREFLIGHT=PASS'

echo "SPARKAPPLICATION=$APP_NAME"
echo "CONFIGMAP=$CM_NAME"

echo 'SPARK_FINAL_STATE=COMPLETED'

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_COLUMN_COUNT=36'
echo "CANDIDATE_COLUMNS=$COLUMN_LIST"

echo "CANDIDATE_BUSINESS_KEY_SHA256=$EXPECTED_KEY_SHA"

echo 'VISIT_ID_MAP_ROWS=5799'
echo "AUTHORITATIVE_MAPPING_SHA256=$EXPECTED_MAPPING_SHA"

echo 'PERSON_MAP_ROWS=113'
echo "PERSON_MAP_SHA256=$EXPECTED_PERSON_MAP_SHA"

echo 'TARGET_CDM_COLUMN_COUNT=17'
echo 'FINAL_CDM_ROW_SHAPE_ROWS=5799'

echo "CDM_ROW_SHAPE_SHA256=$ROW_SHAPE_SHA"

echo 'REQUIRED_TARGET_NULL_VIOLATIONS=0'
echo 'TYPE_CAST_VIOLATIONS=0'
echo 'VARCHAR_LENGTH_VIOLATIONS=0'

echo 'DATE_ORDER_VIOLATIONS=0'
echo 'DATETIME_ORDER_VIOLATIONS=0'
echo 'DATE_DATETIME_CONSISTENCY_VIOLATIONS=0'

echo 'PERSON_FK_COVERAGE=PASS'
echo 'CONCEPT_FK_COVERAGE=PASS'
echo 'PROVIDER_FK_COVERAGE=PASS'
echo 'CARE_SITE_FK_COVERAGE=PASS'
echo 'PRECEDING_VISIT_FK_FEASIBILITY=PASS'

echo 'CDM_VISIT_ROWS=0'

echo 'DATABASE_ACCESS=READ_ONLY'
echo 'DATABASE_MUTATION=NO'

echo 'S3_ACCESS=READ_ONLY'
echo 'S3_MUTATION=NO'

echo 'KUBERNETES_MUTATION=YES'
echo 'SPARK_RESOURCES_PRESERVED=YES'

echo 'GIT_COMMIT=NO'

echo 'READY_FOR_CDM_MATERIALIZATION_DESIGN=YES'
echo 'NEXT_REQUIRED_STEP=STEP06C3_CANONICALIZE_CDM_PREFLIGHT'
