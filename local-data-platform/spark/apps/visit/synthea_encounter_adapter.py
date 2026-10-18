import argparse
import json

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    countDistinct,
    current_timestamp,
    lit,
    lower,
    to_date,
    to_timestamp,
    trim,
)
from pyspark.sql.types import DecimalType


EXPECTED_SOURCE_COLUMNS = [
    "Id",
    "START",
    "STOP",
    "PATIENT",
    "ORGANIZATION",
    "PROVIDER",
    "PAYER",
    "ENCOUNTERCLASS",
    "CODE",
    "DESCRIPTION",
    "BASE_ENCOUNTER_COST",
    "TOTAL_CLAIM_COST",
    "PAYER_COVERAGE",
    "REASONCODE",
    "REASONDESCRIPTION",
]


ALLOWED_CLASSES = {
    "ambulatory",
    "emergency",
    "home",
    "hospice",
    "inpatient",
    "outpatient",
    "snf",
    "urgentcare",
    "virtual",
    "wellness",
}


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-uri",
        required=True,
    )

    parser.add_argument(
        "--output-data-uri",
        required=True,
    )

    parser.add_argument(
        "--contract-path",
        required=True,
    )

    parser.add_argument(
        "--expected-rows",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--source-system",
        required=True,
    )

    parser.add_argument(
        "--source-version",
        required=True,
    )

    parser.add_argument(
        "--source-batch-id",
        required=True,
    )

    parser.add_argument(
        "--source-ingest-date",
        required=True,
    )

    parser.add_argument(
        "--source-file",
        required=True,
    )

    parser.add_argument(
        "--source-file-sha256",
        required=True,
    )

    parser.add_argument(
        "--source-file-size-bytes",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--processing-run-id",
        required=True,
    )

    return parser.parse_args()


def load_contract(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def main():
    args = parse_args()

    contract = load_contract(
        args.contract_path
    )

    expected_fields = [
        item["name"]
        for item in contract["fields"]
    ]

    spark = (
        SparkSession.builder
        .appName(
            "task003-synthea-encounter-adapter"
        )
        .config(
            "spark.sql.session.timeZone",
            "UTC",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    try:
        print("=" * 72)
        print(
            "TASK-003 - SYNTHEA ENCOUNTER "
            "CANONICAL ADAPTER"
        )
        print("=" * 72)

        print(
            "INPUT_URI="
            + args.input_uri
        )

        print(
            "OUTPUT_DATA_URI="
            + args.output_data_uri
        )

        print(
            "SOURCE_BATCH_ID="
            + args.source_batch_id
        )

        print(
            "PROCESSING_RUN_ID="
            + args.processing_run_id
        )


        # ====================================================
        # Read source CSV
        # ====================================================

        source = (
            spark.read
            .option("header", "true")
            .option("inferSchema", "false")
            .csv(args.input_uri)
            .cache()
        )


        if source.columns != EXPECTED_SOURCE_COLUMNS:
            raise RuntimeError(
                "Synthea encounters.csv schema mismatch.\n"
                f"Expected={EXPECTED_SOURCE_COLUMNS}\n"
                f"Actual={source.columns}"
            )


        source_rows = source.count()

        unique_encounters = (
            source
            .agg(
                countDistinct("Id")
                .alias("cnt")
            )
            .first()["cnt"]
        )


        print(
            "SOURCE_ROWS="
            + str(source_rows)
        )

        print(
            "SOURCE_UNIQUE_ENCOUNTERS="
            + str(unique_encounters)
        )


        if source_rows != args.expected_rows:
            raise RuntimeError(
                "Unexpected encounter source row count."
            )

        if unique_encounters != args.expected_rows:
            raise RuntimeError(
                "Encounter source IDs are not unique."
            )


        # ====================================================
        # Canonical transformation
        # ====================================================

        canonical = (
            source
            .select(
                trim(col("Id"))
                .alias(
                    "source_encounter_id"
                ),

                trim(col("PATIENT"))
                .alias(
                    "source_person_id"
                ),

                to_timestamp(
                    col("START")
                )
                .alias(
                    "start_datetime"
                ),

                to_timestamp(
                    col("STOP")
                )
                .alias(
                    "end_datetime"
                ),

                lower(
                    trim(
                        col("ENCOUNTERCLASS")
                    )
                )
                .alias(
                    "encounter_class"
                ),

                trim(col("CODE"))
                .alias(
                    "source_code"
                ),

                trim(col("DESCRIPTION"))
                .alias(
                    "source_description"
                ),

                trim(col("ORGANIZATION"))
                .alias(
                    "source_organization_id"
                ),

                trim(col("PROVIDER"))
                .alias(
                    "source_provider_id"
                ),

                trim(col("PAYER"))
                .alias(
                    "source_payer_id"
                ),

                col("BASE_ENCOUNTER_COST")
                .cast(
                    DecimalType(18, 2)
                )
                .alias(
                    "base_encounter_cost"
                ),

                col("TOTAL_CLAIM_COST")
                .cast(
                    DecimalType(18, 2)
                )
                .alias(
                    "total_claim_cost"
                ),

                col("PAYER_COVERAGE")
                .cast(
                    DecimalType(18, 2)
                )
                .alias(
                    "payer_coverage"
                ),

                trim(col("REASONCODE"))
                .alias(
                    "reason_code"
                ),

                trim(col("REASONDESCRIPTION"))
                .alias(
                    "reason_description"
                ),

                lit(args.source_system)
                .alias(
                    "source_system"
                ),

                lit(args.source_version)
                .alias(
                    "source_version"
                ),

                lit(args.source_batch_id)
                .alias(
                    "source_batch_id"
                ),

                to_date(
                    lit(
                        args.source_ingest_date
                    )
                )
                .alias(
                    "source_ingest_date"
                ),

                lit(args.source_file)
                .alias(
                    "source_file"
                ),

                lit(
                    args.source_file_sha256
                )
                .alias(
                    "source_file_sha256"
                ),

                lit(
                    args.source_file_size_bytes
                )
                .cast("long")
                .alias(
                    "source_file_size_bytes"
                ),

                lit(
                    "synthea_encounter_adapter"
                )
                .alias(
                    "adapter_name"
                ),

                lit("v1")
                .alias(
                    "adapter_version"
                ),

                lit("v1")
                .alias(
                    "canonical_version"
                ),

                lit(
                    args.processing_run_id
                )
                .alias(
                    "processing_run_id"
                ),

                current_timestamp()
                .alias(
                    "processed_at"
                ),
            )
            .cache()
        )


        # ====================================================
        # Contract validation
        # ====================================================

        if canonical.columns != expected_fields:
            raise RuntimeError(
                "Canonical Encounter field order mismatch.\n"
                f"Expected={expected_fields}\n"
                f"Actual={canonical.columns}"
            )


        canonical_rows = canonical.count()

        canonical_unique = (
            canonical
            .agg(
                countDistinct(
                    "source_encounter_id"
                )
                .alias("cnt")
            )
            .first()["cnt"]
        )


        required_invalid = (
            canonical
            .filter(
                col(
                    "source_encounter_id"
                ).isNull()
                | (
                    trim(
                        col(
                            "source_encounter_id"
                        )
                    ) == ""
                )
                | col(
                    "source_person_id"
                ).isNull()
                | (
                    trim(
                        col(
                            "source_person_id"
                        )
                    ) == ""
                )
                | col(
                    "start_datetime"
                ).isNull()
                | col(
                    "end_datetime"
                ).isNull()
                | col(
                    "encounter_class"
                ).isNull()
                | col(
                    "source_code"
                ).isNull()
            )
            .count()
        )


        invalid_classes = (
            canonical
            .filter(
                ~col(
                    "encounter_class"
                ).isin(
                    sorted(
                        ALLOWED_CLASSES
                    )
                )
            )
            .count()
        )


        invalid_time_order = (
            canonical
            .filter(
                col("end_datetime")
                < col("start_datetime")
            )
            .count()
        )


        print(
            "CANONICAL_ROWS="
            + str(canonical_rows)
        )

        print(
            "CANONICAL_UNIQUE_ENCOUNTERS="
            + str(canonical_unique)
        )

        print(
            "CANONICAL_INVALID_REQUIRED="
            + str(required_invalid)
        )

        print(
            "CANONICAL_INVALID_CLASSES="
            + str(invalid_classes)
        )

        print(
            "CANONICAL_INVALID_TIME_ORDER="
            + str(invalid_time_order)
        )


        if canonical_rows != args.expected_rows:
            raise RuntimeError(
                "Canonical row count mismatch."
            )

        if canonical_unique != args.expected_rows:
            raise RuntimeError(
                "Canonical encounter uniqueness failed."
            )

        if required_invalid != 0:
            raise RuntimeError(
                "Canonical required field DQ failed."
            )

        if invalid_classes != 0:
            raise RuntimeError(
                "Unexpected encounter class found."
            )

        if invalid_time_order != 0:
            raise RuntimeError(
                "Encounter end precedes start."
            )


        print(
            "CANONICAL_ENCOUNTER_CONTRACT=PASS"
        )

        print(
            "CANONICAL_ENCOUNTER_DQ=PASS"
        )


        # ====================================================
        # Immutable processing write
        # ====================================================

        (
            canonical
            .write
            .mode("errorifexists")
            .parquet(
                args.output_data_uri
            )
        )


        print(
            "PROCESSING_WRITE=PASS"
        )


        readback = (
            spark.read
            .parquet(
                args.output_data_uri
            )
            .cache()
        )


        readback_rows = readback.count()

        readback_unique = (
            readback
            .agg(
                countDistinct(
                    "source_encounter_id"
                )
                .alias("cnt")
            )
            .first()["cnt"]
        )


        print(
            "PROCESSING_READBACK_ROWS="
            + str(readback_rows)
        )

        print(
            "PROCESSING_READBACK_UNIQUE_ENCOUNTERS="
            + str(readback_unique)
        )


        if readback_rows != args.expected_rows:
            raise RuntimeError(
                "Processing readback row count mismatch."
            )

        if readback_unique != args.expected_rows:
            raise RuntimeError(
                "Processing readback uniqueness failed."
            )


        print(
            "PROCESSING_READBACK=PASS"
        )

        print(
            "RAW_PUBLISH=NO"
        )

        print(
            "POSTGRESQL_WRITE=NO"
        )

        print(
            "TASK003_ENCOUNTER_ADAPTER=PASS"
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
