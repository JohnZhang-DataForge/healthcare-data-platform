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
