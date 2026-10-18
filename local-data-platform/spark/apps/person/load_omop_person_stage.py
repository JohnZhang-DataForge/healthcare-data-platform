import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, countDistinct


EXPECTED_COLUMNS = [
    "person_id",
    "gender_concept_id",
    "year_of_birth",
    "month_of_birth",
    "day_of_birth",
    "birth_datetime",
    "race_concept_id",
    "ethnicity_concept_id",
    "location_id",
    "provider_id",
    "care_site_id",
    "person_source_value",
    "gender_source_value",
    "gender_source_concept_id",
    "race_source_value",
    "race_source_concept_id",
    "ethnicity_source_value",
    "ethnicity_source_concept_id",
]

REQUIRED_COLUMNS = [
    "person_id",
    "gender_concept_id",
    "year_of_birth",
    "race_concept_id",
    "ethnicity_concept_id",
    "person_source_value",
]


parser = argparse.ArgumentParser()

parser.add_argument(
    "--processed-data-uri",
    required=True,
)

parser.add_argument(
    "--stage-table",
    required=True,
)

parser.add_argument(
    "--expected-rows",
    type=int,
    required=True,
)

args = parser.parse_args()


spark = (
    SparkSession.builder
    .appName("task002-omop-person-stage-load")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


try:
    print("=" * 72)
    print("TASK-002 - OMOP PERSON -> POSTGRESQL STAGE")
    print("=" * 72)

    print(
        "PROCESSED_INPUT="
        + args.processed_data_uri
    )

    print(
        "STAGE_TABLE="
        + args.stage_table
    )

    print(
        "EXPECTED_ROWS="
        + str(args.expected_rows)
    )


    # ========================================================
    # Read Processed OMOP Person
    # ========================================================

    person = (
        spark.read
        .parquet(
            args.processed_data_uri
        )
        .cache()
    )


    if person.columns != EXPECTED_COLUMNS:
        raise RuntimeError(
            "OMOP Person stage schema mismatch.\n"
            f"Expected={EXPECTED_COLUMNS}\n"
            f"Actual={person.columns}"
        )


    rows = person.count()

    unique_ids = (
        person
        .agg(
            countDistinct("person_id")
            .alias("cnt")
        )
        .first()["cnt"]
    )


    invalid_required = (
        person
        .filter(
            col("person_id").isNull()
            | col("gender_concept_id").isNull()
            | col("year_of_birth").isNull()
            | col("race_concept_id").isNull()
            | col("ethnicity_concept_id").isNull()
            | col("person_source_value").isNull()
        )
        .count()
    )


    print(
        "PROCESSED_PERSON_ROWS="
        + str(rows)
    )

    print(
        "PROCESSED_PERSON_UNIQUE_IDS="
        + str(unique_ids)
    )

    print(
        "PROCESSED_PERSON_INVALID_REQUIRED="
        + str(invalid_required)
    )


    if rows != args.expected_rows:
        raise RuntimeError(
            "Processed row count mismatch."
        )

    if unique_ids != args.expected_rows:
        raise RuntimeError(
            "Processed person_id uniqueness failed."
        )

    if invalid_required != 0:
        raise RuntimeError(
            "Processed required field DQ failed."
        )


    print(
        "PROCESSED_PERSON_DQ=PASS"
    )


    # ========================================================
    # PostgreSQL connection
    # ========================================================

    pg_host = os.environ["PGHOST"]
    pg_port = os.environ["PGPORT"]
    pg_database = os.environ["PGDATABASE"]
    pg_user = os.environ["PGUSER"]
    pg_password = os.environ["PGPASSWORD"]


    jdbc_url = (
        f"jdbc:postgresql://"
        f"{pg_host}:{pg_port}/"
        f"{pg_database}"
    )


    # ========================================================
    # Write stage only
    # ========================================================

    (
        person
        .write
        .format("jdbc")
        .option(
            "url",
            jdbc_url,
        )
        .option(
            "dbtable",
            args.stage_table,
        )
        .option(
            "user",
            pg_user,
        )
        .option(
            "password",
            pg_password,
        )
        .option(
            "driver",
            "org.postgresql.Driver",
        )
        .option(
            "batchsize",
            "1000",
        )
        .mode("append")
        .save()
    )


    print(
        "POSTGRESQL_STAGE_WRITE=PASS"
    )


    # ========================================================
    # Read stage back through JDBC
    # ========================================================

    stage = (
        spark.read
        .format("jdbc")
        .option(
            "url",
            jdbc_url,
        )
        .option(
            "dbtable",
            args.stage_table,
        )
        .option(
            "user",
            pg_user,
        )
        .option(
            "password",
            pg_password,
        )
        .option(
            "driver",
            "org.postgresql.Driver",
        )
        .load()
        .cache()
    )


    stage_rows = stage.count()

    stage_unique = (
        stage
        .agg(
            countDistinct("person_id")
            .alias("cnt")
        )
        .first()["cnt"]
    )


    print(
        "STAGE_READBACK_ROWS="
        + str(stage_rows)
    )

    print(
        "STAGE_READBACK_UNIQUE_IDS="
        + str(stage_unique)
    )


    if stage_rows != args.expected_rows:
        raise RuntimeError(
            "Stage readback row count mismatch."
        )

    if stage_unique != args.expected_rows:
        raise RuntimeError(
            "Stage readback person_id uniqueness failed."
        )


    print(
        "STAGE_READBACK=PASS"
    )

    print(
        "CDM_PERSON_WRITE=NO"
    )

    print(
        "TASK002_PERSON_STAGE_LOAD=PASS"
    )

finally:
    spark.stop()
