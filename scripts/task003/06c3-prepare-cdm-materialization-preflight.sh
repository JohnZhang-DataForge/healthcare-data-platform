#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
STAGE="$(mktemp -d /data/spark/temp_shell/task003-06c3-generator.XXXXXX)"

echo '#### TASK003 STEP06C3 PREPARE CDM MATERIALIZATION PREFLIGHT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  echo "STEP06C3_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06C3 PREPARE CDM MATERIALIZATION PREFLIGHT OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/candidate_to_cdm_preflight.py" <<'C2_APP_EOF_TASK003_06C3'
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
C2_APP_EOF_TASK003_06C3

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06c2-candidate-to-cdm-column-preflight.sh" <<'C2_RUNNER_EOF_TASK003_06C3'
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
C2_RUNNER_EOF_TASK003_06C3

mkdir -p "$STAGE/spark/contracts/processed"
cat > "$STAGE/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json" <<'CONTRACT_EOF_TASK003_06C3'
{
  "access_policy": {
    "preflight_database_access": "READ_ONLY",
    "preflight_database_mutation": false,
    "preflight_s3_access": "READ_ONLY",
    "preflight_s3_mutation": false
  },
  "authoritative_visit_id_mapping": {
    "mapping_sha256": "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f",
    "max_visit_occurrence_id": 5800,
    "min_visit_occurrence_id": 2,
    "rows": 5799
  },
  "database_baseline": {
    "cdm_visit_rows": 0,
    "person_map_rows": 113,
    "sequence_is_called": true,
    "sequence_last_value": 5800,
    "visit_id_map_rows": 5799
  },
  "foreign_key_feasibility": {
    "care_site": "PASS",
    "concept": "PASS",
    "distinct_care_site_ids": 0,
    "distinct_concept_ids": 6,
    "distinct_person_ids": 113,
    "distinct_preceding_visit_ids": 0,
    "distinct_provider_ids": 0,
    "person": "PASS",
    "preceding_visit": "PASS",
    "provider": "PASS"
  },
  "git_checkpoint_before_preflight": "8595a2dd46092517ec8fde40408172b1dfb76c09",
  "materialization_policy": {
    "blind_retry_after_uncertain_mutation": "FORBIDDEN",
    "cdm_visit_occurrence_mutated": false,
    "fresh_database_revalidation_before_mutation": "REQUIRED",
    "materialization_transaction_required": true,
    "row_shape_is_authoritative_pre_mutation_payload": true
  },
  "person_mapping": {
    "person_map_sha256": "f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98",
    "rows": 113
  },
  "prepared_cdm_row_shape": {
    "cast_violations": 0,
    "column_count": 17,
    "date_datetime_consistency_violations": 0,
    "date_order_violations": 0,
    "datetime_order_violations": 0,
    "required_null_violations": 0,
    "row_shape_sha256": "995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1",
    "rows": 5799,
    "unique_visit_occurrence_ids": 5799,
    "varchar_length_violations": 0
  },
  "runtime_evidence": {
    "c1_summary_sha256": "6a472fbeadaffbb477d0651cae9dc73dfb753c8be01ef78785067618d8195d6b",
    "c2_driver_log_sha256": "d316496f4c128e54e00ceb3728225e01d0088244ed97887b9d1fdc9d59a6f630",
    "c2_post_database_state_sha256": "d9f3839654751fd10aafa8446e09de811c361339bbcdddfb1c7891578c0d16b5",
    "c2_result_sha256": "7f3d3f5e8f4c6a8e331c4ed2a7942e6d3cacf85c3643f8db51708b24246671cd",
    "c2_sparkapplication_manifest_sha256": "c84e108207ba40c65ac70e5e4f48842b3d550f52c95de42029414358824bb53a",
    "c2_verified_spark_application_sha256": "ccb6f8b77c9c5d4f763f80d4bcfff8d9e79bbb50ce9e323085c7fc8d60e1d66d"
  },
  "source_lineage": {
    "candidate_business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e",
    "candidate_column_count": 36,
    "candidate_rows": 5799,
    "candidate_unique_business_keys": 5799,
    "canonical_encounter_contract": "spark/contracts/canonical/encounter-v1.json",
    "canonical_encounter_contract_sha256": "473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837"
  },
  "status": "CDM_VISIT_MATERIALIZATION_PREFLIGHT_FROZEN",
  "step": "STEP-06C3",
  "target_schema": {
    "column_count": 17,
    "columns": [
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
      "preceding_visit_occurrence_id"
    ],
    "constraint_count": 10,
    "identity_column_count": 0,
    "index_count": 3,
    "required_insert_column_count": 6,
    "required_insert_columns": [
      "visit_occurrence_id",
      "person_id",
      "visit_concept_id",
      "visit_start_date",
      "visit_end_date",
      "visit_type_concept_id"
    ],
    "user_trigger_count": 0
  },
  "target_table": "cdm.visit_occurrence",
  "task": "TASK-003",
  "version": "v1"
}
CONTRACT_EOF_TASK003_06C3

mkdir -p "$STAGE/apps/task003"
cat > "$STAGE/apps/task003/verify_cdm_materialization_preflight.py" <<'VERIFY_APP_EOF_TASK003_06C3'
#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_HEAD = (
    "8595a2dd46092517ec8fde40408172b1dfb76c09"
)

EXPECTED_ENCOUNTER_SHA = (
    "473ae45225c9063a7560b0092ed7914d71a43623"
    "f593d4959c66294e942a5837"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33ad9bb182"
    "cca61e6a19cdb69ff74f72e"
)

EXPECTED_MAPPING_SHA = (
    "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b"
    "06b1d6349d7f21f6a0c03c9f"
)

EXPECTED_PERSON_SHA = (
    "f52f95120b8a9bd80d33029d04d9abf4cb1c5920"
    "6d00b745b59e39b5a89c9a98"
)

EXPECTED_ROW_SHAPE_SHA = (
    "995724ba282f443892074d9b189be134fde8819b2"
    "afda05f021729323b0ebce1"
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
    c1_summary_path,
    c2_result_path,
    c2_app_path,
    c2_driver_path,
    c2_post_db_path,
    c2_sparkapp_path,
):
    contract = load(
        contract_path
    )

    c1 = load(
        c1_summary_path
    )

    c2 = load(
        c2_result_path
    )

    require(
        contract["task"] == "TASK-003",
        "task",
    )

    require(
        contract["step"] == "STEP-06C3",
        "step",
    )

    require(
        contract["status"]
        == "CDM_VISIT_MATERIALIZATION_PREFLIGHT_FROZEN",
        "status",
    )

    require(
        contract[
            "git_checkpoint_before_preflight"
        ]
        == EXPECTED_HEAD,
        "Git checkpoint",
    )

    target = contract[
        "target_schema"
    ]

    require(
        target["column_count"] == 17,
        "target columns",
    )

    require(
        target[
            "required_insert_column_count"
        ]
        == 6,
        "required columns",
    )

    require(
        target["identity_column_count"]
        == 0,
        "identity columns",
    )

    require(
        target["constraint_count"]
        == 10,
        "constraints",
    )

    source = contract[
        "source_lineage"
    ]

    require(
        source[
            "canonical_encounter_contract_sha256"
        ]
        == EXPECTED_ENCOUNTER_SHA,
        "Encounter contract SHA",
    )

    require(
        source[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "business key SHA",
    )

    require(
        source["candidate_rows"]
        == 5799,
        "candidate rows",
    )

    require(
        source["candidate_column_count"]
        == 36,
        "candidate columns",
    )

    mapping = contract[
        "authoritative_visit_id_mapping"
    ]

    require(
        mapping["rows"] == 5799,
        "mapping rows",
    )

    require(
        mapping["min_visit_occurrence_id"]
        == 2,
        "mapping min",
    )

    require(
        mapping["max_visit_occurrence_id"]
        == 5800,
        "mapping max",
    )

    require(
        mapping["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "mapping SHA",
    )

    person = contract[
        "person_mapping"
    ]

    require(
        person["rows"] == 113,
        "person rows",
    )

    require(
        person["person_map_sha256"]
        == EXPECTED_PERSON_SHA,
        "person SHA",
    )

    shape = contract[
        "prepared_cdm_row_shape"
    ]

    require(
        shape["rows"] == 5799,
        "shape rows",
    )

    require(
        shape["column_count"] == 17,
        "shape columns",
    )

    require(
        shape[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "shape unique IDs",
    )

    require(
        shape["row_shape_sha256"]
        == EXPECTED_ROW_SHAPE_SHA,
        "row shape SHA",
    )

    for key in (
        "required_null_violations",
        "cast_violations",
        "varchar_length_violations",
        "date_order_violations",
        "datetime_order_violations",
        "date_datetime_consistency_violations",
    ):
        require(
            shape[key] == 0,
            key,
        )

    fk = contract[
        "foreign_key_feasibility"
    ]

    for key in (
        "person",
        "concept",
        "provider",
        "care_site",
        "preceding_visit",
    ):
        require(
            fk[key] == "PASS",
            "FK " + key,
        )

    database = contract[
        "database_baseline"
    ]

    require(
        database["cdm_visit_rows"]
        == 0,
        "CDM rows",
    )

    require(
        database["visit_id_map_rows"]
        == 5799,
        "Visit map rows",
    )

    require(
        database["person_map_rows"]
        == 113,
        "Person map rows",
    )

    require(
        database["sequence_last_value"]
        == 5800,
        "sequence last",
    )

    require(
        database["sequence_is_called"]
        is True,
        "sequence called",
    )

    evidence = contract[
        "runtime_evidence"
    ]

    require(
        sha(c1_summary_path)
        == evidence[
            "c1_summary_sha256"
        ],
        "C1 summary SHA",
    )

    require(
        sha(c2_result_path)
        == evidence[
            "c2_result_sha256"
        ],
        "C2 result SHA",
    )

    require(
        sha(c2_app_path)
        == evidence[
            "c2_verified_spark_application_sha256"
        ],
        "C2 app SHA",
    )

    require(
        sha(c2_driver_path)
        == evidence[
            "c2_driver_log_sha256"
        ],
        "driver SHA",
    )

    require(
        sha(c2_post_db_path)
        == evidence[
            "c2_post_database_state_sha256"
        ],
        "post DB SHA",
    )

    require(
        sha(c2_sparkapp_path)
        == evidence[
            "c2_sparkapplication_manifest_sha256"
        ],
        "SparkApplication SHA",
    )

    require(
        c1["column_count"] == 17,
        "C1 column count",
    )

    require(
        c1["cdm_visit_rows"] == 0,
        "C1 CDM rows",
    )

    require(
        c1[
            "authoritative_mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "C1 mapping SHA",
    )

    require(
        c2["candidate_rows"] == 5799,
        "C2 candidate rows",
    )

    require(
        c2[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "C2 key SHA",
    )

    require(
        c2[
            "authoritative_mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "C2 mapping SHA",
    )

    require(
        c2["person_map_sha256"]
        == EXPECTED_PERSON_SHA,
        "C2 person SHA",
    )

    require(
        c2["cdm_row_shape_sha256"]
        == EXPECTED_ROW_SHAPE_SHA,
        "C2 shape SHA",
    )

    require(
        c2[
            "final_cdm_row_shape_rows"
        ]
        == 5799,
        "C2 shape rows",
    )

    require(
        c2["cdm_visit_rows_before"]
        == 0,
        "C2 CDM rows",
    )

    require(
        c2["database_mutation"]
        is False,
        "C2 database mutation",
    )

    require(
        c2["s3_mutation"]
        is False,
        "C2 S3 mutation",
    )

    post_rows = [
        line.strip()
        for line in Path(
            c2_post_db_path
        ).read_text().splitlines()
        if line.strip()
        and line.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        post_rows
        == [
            "5799|0|113",
            "5799|2|5800",
            "5800|t",
            EXPECTED_MAPPING_SHA,
            "on",
        ],
        "post-Spark DB state",
    )

    policy = contract[
        "materialization_policy"
    ]

    require(
        policy[
            "cdm_visit_occurrence_mutated"
        ]
        is False,
        "CDM mutation",
    )

    require(
        policy[
            "row_shape_is_authoritative_pre_mutation_payload"
        ]
        is True,
        "payload authority",
    )

    require(
        policy[
            "fresh_database_revalidation_before_mutation"
        ]
        == "REQUIRED",
        "fresh revalidation",
    )

    require(
        policy[
            "materialization_transaction_required"
        ]
        is True,
        "transaction policy",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06C3",

        "status":
            "CDM_MATERIALIZATION_PREFLIGHT_CANONICAL_GATE_PASS",

        "candidate_rows":
            5799,

        "target_columns":
            17,

        "cdm_row_shape_rows":
            5799,

        "cdm_row_shape_sha256":
            EXPECTED_ROW_SHAPE_SHA,

        "authoritative_mapping_sha256":
            EXPECTED_MAPPING_SHA,

        "person_map_sha256":
            EXPECTED_PERSON_SHA,

        "cdm_visit_rows":
            0,

        "database_mutation":
            False,

        "s3_mutation":
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
        "--c1-summary",
        required=True,
    )

    parser.add_argument(
        "--c2-result",
        required=True,
    )

    parser.add_argument(
        "--c2-app",
        required=True,
    )

    parser.add_argument(
        "--c2-driver",
        required=True,
    )

    parser.add_argument(
        "--c2-post-db",
        required=True,
    )

    parser.add_argument(
        "--c2-sparkapp",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.contract,
        args.c1_summary,
        args.c2_result,
        args.c2_app,
        args.c2_driver,
        args.c2_post_db,
        args.c2_sparkapp,
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
        "STEP06C3_PREFLIGHT_VERIFY=PASS"
    )

    print(
        "CDM_ROW_SHAPE_SHA256="
        + EXPECTED_ROW_SHAPE_SHA
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
VERIFY_APP_EOF_TASK003_06C3

mkdir -p "$STAGE/scripts/task003"
cat > "$STAGE/scripts/task003/06c3-verify-cdm-materialization-preflight.sh" <<'VERIFY_RUNNER_EOF_TASK003_06C3'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

C1="$ROOT/runtime/reports/task003/step06/cdm-visit-baseline.20261010t143104z.2493274"
C2="$ROOT/runtime/reports/task003/step06/candidate-to-cdm-preflight.20261010t144415z.2498243"

APP="$ROOT/apps/task003/verify_cdm_materialization_preflight.py"

CONTRACT="$ROOT/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json"

OUTDIR="$ROOT/runtime/reports/task003/step06/cdm-materialization-preflight-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06C3 CDM MATERIALIZATION PREFLIGHT VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06C3_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06C3 CDM MATERIALIZATION PREFLIGHT VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

python3 "$APP" \
  --contract "$CONTRACT" \
  --c1-summary "$C1/summary.json" \
  --c2-result "$C2/result.json" \
  --c2-app "$C2/candidate_to_cdm_preflight.py" \
  --c2-driver "$C2/driver.log" \
  --c2-post-db "$C2/post-spark-database-state.txt" \
  --c2-sparkapp "$C2/sparkapplication.json" \
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
    == "CDM_MATERIALIZATION_PREFLIGHT_CANONICAL_GATE_PASS"
)

assert state["candidate_rows"] == 5799
assert state["target_columns"] == 17
assert state["cdm_row_shape_rows"] == 5799

assert (
    state["cdm_row_shape_sha256"]
    == "995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1"
)

assert (
    state["authoritative_mapping_sha256"]
    == "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f"
)

assert state["cdm_visit_rows"] == 0
assert state["database_mutation"] is False
assert state["s3_mutation"] is False
assert state["ready_for_git_checkpoint"] is True

print("STEP06C3_CANONICAL_STATE=PASS")
PY

echo 'STEP06C3_CANONICAL_PREFLIGHT_GATE=PASS'

echo 'CANDIDATE_ROWS=5799'
echo 'TARGET_CDM_COLUMNS=17'
echo 'FINAL_CDM_ROW_SHAPE_ROWS=5799'

echo 'CDM_ROW_SHAPE_SHA256=995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1'

echo 'AUTHORITATIVE_MAPPING_SHA256=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f'

echo 'PERSON_MAP_SHA256=f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98'

echo 'ALL_DATABASE_FK_FEASIBILITY=PASS'

echo 'CDM_VISIT_ROWS=0'

echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'

echo 'READY_FOR_GIT_CHECKPOINT=YES'
VERIFY_RUNNER_EOF_TASK003_06C3

mkdir -p "$STAGE/tests/task003"
cat > "$STAGE/tests/task003/test_cdm_materialization_preflight.py" <<'TEST_EOF_TASK003_06C3'
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
    / "apps/task003/verify_cdm_materialization_preflight.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_cdm_materialization_preflight",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class CDMMaterializationPreflightTests(
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
TEST_EOF_TASK003_06C3

mkdir -p "$STAGE/docs/task003"
cat > "$STAGE/docs/task003/TASK003-STEP06C-CDM-Visit-Materialization-Preflight.md" <<'DOC_EOF_TASK003_06C3'
# TASK-003 STEP06C — CDM Visit Materialization Preflight

## Frozen upstream state

STEP06B finalized the authoritative Visit ID mapping:

- Candidate business keys: 5799
- Visit ID map rows: 5799
- Visit ID range: 2 through 5800
- Visit ID 1: intentionally consumed sequence gap
- mapping SHA256:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

## STEP06C1 target discovery

`cdm.visit_occurrence` contains 17 columns.

Six columns are NOT NULL with no default and therefore must be explicitly
materialized:

1. `visit_occurrence_id`
2. `person_id`
3. `visit_concept_id`
4. `visit_start_date`
5. `visit_end_date`
6. `visit_type_concept_id`

The target Visit ID column is not an identity column and has no default.

The table has:

- 10 constraints
- 3 indexes
- 0 user triggers

Before materialization:

- `cdm.visit_occurrence` rows = 0
- `etl.visit_occurrence_id_map` rows = 5799
- `etl.person_id_map` rows = 113

## STEP06C2 verified Spark preflight

The verified Spark preflight read:

- frozen Processed Visit Candidate from S3
- authoritative Visit ID map from PostgreSQL
- authoritative Person map from PostgreSQL
- referenced FK target tables from PostgreSQL

It performed no database write and no S3 write.

Candidate:

- rows: 5799
- columns: 36
- unique business keys: 5799
- business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Person map:

- rows: 113
- SHA256:
  `f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`

## Prepared CDM row shape

The preflight successfully constructed the complete 17-column
`cdm.visit_occurrence` row shape for all 5799 Candidate rows.

Frozen payload fingerprint:

`995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

This SHA is calculated from rows ordered by `visit_occurrence_id` and includes
all 17 target columns.

It is the authoritative pre-mutation payload fingerprint for the first Visit
materialization.

Validation results:

- final row shape rows: 5799
- unique Visit IDs: 5799
- required target NULL violations: 0
- cast failures: 0
- varchar(50) violations: 0
- invalid date order: 0
- invalid datetime order: 0
- date/datetime consistency violations: 0

## FK feasibility

All required database references were resolvable:

- Person FK: PASS
- Concept FK: PASS
- Provider FK: PASS
- Care Site FK: PASS
- preceding Visit FK feasibility: PASS

Observed distinct references:

- Person IDs: 113
- Concept IDs: 6
- Provider IDs: 0
- Care Site IDs: 0
- preceding Visit IDs: 0

The first batch therefore has no Provider, Care Site or preceding Visit
references to materialize.

## Canonical Encounter contract

The upstream frozen schema contract is:

`spark/contracts/canonical/encounter-v1.json`

SHA256:

`473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`

Earlier temporary C2 development called this a "Candidate contract". That name
was misleading. Canonical source now identifies it correctly as the Encounter
canonical contract.

## Mutation boundary

STEP06C1/C2/C3 do not write `cdm.visit_occurrence`.

Before the first CDM mutation, a new transaction contract must:

1. revalidate the frozen Git checkpoint
2. revalidate the authoritative Visit mapping
3. revalidate target schema and constraints
4. revalidate `cdm.visit_occurrence` is still empty
5. reproduce the exact 5799-row CDM payload
6. reproduce row-shape SHA256
   `995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`
7. acquire the required mutation locks
8. insert the complete Visit batch atomically
9. independently verify the committed CDM state

No `ON CONFLICT` or blind retry should hide unexpected database state.
DOC_EOF_TASK003_06C3


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

install_one apps/task003/candidate_to_cdm_preflight.py
install_one scripts/task003/06c2-candidate-to-cdm-column-preflight.sh
install_one spark/contracts/processed/visit-cdm-materialization-preflight-v1.json
install_one apps/task003/verify_cdm_materialization_preflight.py
install_one scripts/task003/06c3-verify-cdm-materialization-preflight.sh
install_one tests/task003/test_cdm_materialization_preflight.py
install_one docs/task003/TASK003-STEP06C-CDM-Visit-Materialization-Preflight.md

python3 -m py_compile \
  "$ROOT/apps/task003/candidate_to_cdm_preflight.py" \
  "$ROOT/apps/task003/verify_cdm_materialization_preflight.py" \
  "$ROOT/tests/task003/test_cdm_materialization_preflight.py"

python3 -m json.tool \
  "$ROOT/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json" \
  >/dev/null

bash -n \
  "$ROOT/scripts/task003/06c2-candidate-to-cdm-column-preflight.sh"

bash -n \
  "$ROOT/scripts/task003/06c3-verify-cdm-materialization-preflight.sh"

echo 'STEP06C3_CANONICAL_SOURCE_PREPARED=PASS'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'
echo 'GIT_COMMIT=NO'
