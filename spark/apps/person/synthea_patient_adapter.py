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
    trim,
    when,
)
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
)

from batch_manifest import (
    find_dataset_file,
    join_uri,
    read_json_document,
    s3_to_s3a,
    validate_intake_manifest,
)


ADAPTER_NAME = "synthea_patient"
ADAPTER_VERSION = "v1"
CANONICAL_VERSION = "v1"

SOURCE_COLUMNS = [
    "Id",
    "BIRTHDATE",
    "DEATHDATE",
    "SSN",
    "DRIVERS",
    "PASSPORT",
    "PREFIX",
    "FIRST",
    "MIDDLE",
    "LAST",
    "SUFFIX",
    "MAIDEN",
    "MARITAL",
    "RACE",
    "ETHNICITY",
    "GENDER",
    "BIRTHPLACE",
    "ADDRESS",
    "CITY",
    "STATE",
    "COUNTY",
    "FIPS",
    "ZIP",
    "LAT",
    "LON",
    "HEALTHCARE_EXPENSES",
    "HEALTHCARE_COVERAGE",
    "INCOME",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Convert Synthea patients.csv "
            "to Canonical Patient v1."
        )
    )

    parser.add_argument(
        "--manifest-uri",
        required=True,
    )

    parser.add_argument(
        "--batch-id",
        required=True,
    )

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--processing-data-uri",
        required=True,
    )

    parser.add_argument(
        "--contract-path",
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


def validate_contract(
    dataframe,
    contract,
):
    expected_columns = [
        field["name"]
        for field in contract["fields"]
    ]

    if dataframe.columns != expected_columns:
        raise RuntimeError(
            "Canonical columns do not "
            "match patient-v1 contract.\n"
            f"Expected: {expected_columns}\n"
            f"Actual  : {dataframe.columns}"
        )

    actual_types = {
        field.name:
            field.dataType.simpleString()
        for field
        in dataframe.schema.fields
    }

    for definition in contract["fields"]:
        name = definition["name"]

        expected_type = definition[
            "type"
        ]

        actual_type = actual_types[
            name
        ]

        if actual_type != expected_type:
            raise RuntimeError(
                f"Type mismatch for {name}: "
                f"expected={expected_type}, "
                f"actual={actual_type}"
            )

        if not definition["nullable"]:
            null_count = (
                dataframe
                .filter(
                    col(name).isNull()
                )
                .count()
            )

            if null_count != 0:
                raise RuntimeError(
                    f"Required field {name} "
                    f"contains {null_count} NULL rows."
                )


def validate_source(
    source,
    expected_rows,
):
    source_rows = source.count()

    unique_ids = (
        source
        .agg(
            countDistinct(
                "Id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    null_ids = (
        source
        .filter(
            col("Id").isNull()
            | (
                trim(col("Id"))
                == ""
            )
        )
        .count()
    )

    invalid_gender = (
        source
        .filter(
            col("GENDER").isNull()
            | (
                ~col("GENDER")
                .isin("M", "F")
            )
        )
        .count()
    )

    blank_birthdate = (
        source
        .filter(
            col("BIRTHDATE").isNull()
            | (
                trim(
                    col("BIRTHDATE")
                )
                == ""
            )
        )
        .count()
    )

    blank_race = (
        source
        .filter(
            col("RACE").isNull()
            | (
                trim(col("RACE"))
                == ""
            )
        )
        .count()
    )

    blank_ethnicity = (
        source
        .filter(
            col("ETHNICITY").isNull()
            | (
                trim(
                    col("ETHNICITY")
                )
                == ""
            )
        )
        .count()
    )

    print(
        f"SOURCE_ROWS={source_rows}"
    )

    print(
        f"SOURCE_UNIQUE_IDS={unique_ids}"
    )

    print(
        f"SOURCE_NULL_IDS={null_ids}"
    )

    print(
        f"SOURCE_INVALID_GENDER="
        f"{invalid_gender}"
    )

    print(
        f"SOURCE_BLANK_BIRTHDATE="
        f"{blank_birthdate}"
    )

    print(
        f"SOURCE_BLANK_RACE="
        f"{blank_race}"
    )

    print(
        f"SOURCE_BLANK_ETHNICITY="
        f"{blank_ethnicity}"
    )

    if source_rows != expected_rows:
        raise RuntimeError(
            "Source row count mismatch: "
            f"expected={expected_rows}, "
            f"actual={source_rows}"
        )

    if unique_ids != source_rows:
        raise RuntimeError(
            "Patient source IDs "
            "are not unique."
        )

    if null_ids != 0:
        raise RuntimeError(
            "Null/blank patient IDs found."
        )

    if invalid_gender != 0:
        raise RuntimeError(
            "Invalid gender values found."
        )

    if blank_birthdate != 0:
        raise RuntimeError(
            "Blank birthdate values found."
        )

    if blank_race != 0:
        raise RuntimeError(
            "Blank race values found."
        )

    if blank_ethnicity != 0:
        raise RuntimeError(
            "Blank ethnicity values found."
        )


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName(
            "task002-synthea-patient-adapter"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    print("=" * 72)
    print(
        "TASK-002 - SYNTHEA PATIENT "
        "-> CANONICAL PATIENT V1"
    )
    print("=" * 72)

    print(
        f"BATCH_ID={args.batch_id}"
    )

    print(
        f"RUN_ID={args.run_id}"
    )

    print(
        "INPUT_MANIFEST="
        f"{args.manifest_uri}"
    )

    print(
        "PROCESSING_OUTPUT="
        f"{args.processing_data_uri}"
    )


    # ========================================================
    # 1. Intake manifest
    # ========================================================

    manifest = read_json_document(
        spark,
        args.manifest_uri,
    )

    validate_intake_manifest(
        manifest,
        expected_batch_id=args.batch_id,
    )

    patient_file = find_dataset_file(
        manifest,
        "patients",
        "patients.csv",
    )

    if patient_file["header"] != SOURCE_COLUMNS:
        raise RuntimeError(
            "patients.csv header does not "
            "match registered Synthea schema.\n"
            f"Expected: {SOURCE_COLUMNS}\n"
            f"Manifest: {patient_file['header']}"
        )

    expected_rows = int(
        patient_file["row_count"]
    )

    input_uri = s3_to_s3a(
        join_uri(
            manifest["landing_uri"],
            patient_file["path"],
        )
    )

    print(
        "INTAKE_MANIFEST_STATUS="
        f"{manifest['status']}"
    )

    print(
        f"INPUT_URI={input_uri}"
    )

    print(
        "EXPECTED_ROWS="
        f"{expected_rows}"
    )

    print(
        "SOURCE_FILE_SHA256="
        f"{patient_file['sha256']}"
    )


    # ========================================================
    # 2. Read Synthea source
    # ========================================================

    schema = StructType([
        StructField(
            name,
            StringType(),
            True,
        )
        for name in SOURCE_COLUMNS
    ])

    source = (
        spark.read
        .schema(schema)
        .option(
            "header",
            "true",
        )
        .option(
            "mode",
            "FAILFAST",
        )
        .csv(input_uri)
        .cache()
    )

    validate_source(
        source,
        expected_rows,
    )


    # ========================================================
    # 3. Canonical transformation
    # ========================================================

    canonical = (
        source
        .select(
            trim(
                col("Id")
            ).alias(
                "source_record_id"
            ),

            to_date(
                trim(
                    col("BIRTHDATE")
                ),
                "yyyy-MM-dd",
            ).alias(
                "birth_date"
            ),

            when(
                col("DEATHDATE").isNull()
                | (
                    trim(
                        col("DEATHDATE")
                    )
                    == ""
                ),
                None,
            )
            .otherwise(
                to_date(
                    trim(
                        col("DEATHDATE")
                    ),
                    "yyyy-MM-dd",
                )
            )
            .alias(
                "death_date"
            ),

            trim(
                col("GENDER")
            ).alias(
                "gender_code"
            ),

            lower(
                trim(
                    col("RACE")
                )
            ).alias(
                "race_code"
            ),

            lower(
                trim(
                    col("ETHNICITY")
                )
            ).alias(
                "ethnicity_code"
            ),
        )

        .withColumn(
            "source_system",
            lit(
                manifest["source"]
            ),
        )

        .withColumn(
            "source_version",
            lit(
                manifest["source_version"]
            ),
        )

        .withColumn(
            "source_batch_id",
            lit(
                manifest["batch_id"]
            ),
        )

        .withColumn(
            "source_ingest_date",
            to_date(
                lit(
                    manifest["ingest_date"]
                ),
                "yyyy-MM-dd",
            ),
        )

        .withColumn(
            "source_file",
            lit(
                patient_file["path"]
            ),
        )

        .withColumn(
            "source_file_sha256",
            lit(
                patient_file["sha256"]
            ),
        )

        .withColumn(
            "source_file_size_bytes",
            lit(
                int(
                    patient_file[
                        "size_bytes"
                    ]
                )
            ).cast("bigint"),
        )

        .withColumn(
            "adapter_name",
            lit(ADAPTER_NAME),
        )

        .withColumn(
            "adapter_version",
            lit(ADAPTER_VERSION),
        )

        .withColumn(
            "canonical_version",
            lit(CANONICAL_VERSION),
        )

        .withColumn(
            "processing_run_id",
            lit(args.run_id),
        )

        .withColumn(
            "processed_at",
            current_timestamp(),
        )

        .cache()
    )


    # ========================================================
    # 4. Canonical validation
    # ========================================================

    canonical_rows = (
        canonical.count()
    )

    unique_records = (
        canonical
        .agg(
            countDistinct(
                "source_record_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    invalid_birth_dates = (
        canonical
        .filter(
            col(
                "birth_date"
            ).isNull()
        )
        .count()
    )

    print(
        "CANONICAL_ROWS="
        f"{canonical_rows}"
    )

    print(
        "CANONICAL_UNIQUE_IDS="
        f"{unique_records}"
    )

    print(
        "CANONICAL_INVALID_BIRTH_DATES="
        f"{invalid_birth_dates}"
    )

    if canonical_rows != expected_rows:
        raise RuntimeError(
            "Canonical row count changed."
        )

    if unique_records != expected_rows:
        raise RuntimeError(
            "Canonical source_record_id "
            "is not unique."
        )

    if invalid_birth_dates != 0:
        raise RuntimeError(
            "Birthdate conversion failed."
        )

    validate_contract(
        canonical,
        load_contract(
            args.contract_path
        ),
    )

    print(
        "CANONICAL_CONTRACT=PASS"
    )


    # ========================================================
    # 5. Write isolated Processing output
    # ========================================================

    (
        canonical
        .write
        .mode(
            "errorifexists"
        )
        .parquet(
            args.processing_data_uri
        )
    )

    print(
        "PROCESSING_WRITE=PASS"
    )


    # ========================================================
    # 6. Independent read-back
    # ========================================================

    verify = (
        spark.read
        .parquet(
            args.processing_data_uri
        )
        .cache()
    )

    verify_rows = (
        verify.count()
    )

    verify_unique = (
        verify
        .agg(
            countDistinct(
                "source_record_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    validate_contract(
        verify,
        load_contract(
            args.contract_path
        ),
    )

    if verify_rows != expected_rows:
        raise RuntimeError(
            "Processing read-back "
            "row count mismatch."
        )

    if verify_unique != expected_rows:
        raise RuntimeError(
            "Processing read-back "
            "patient IDs are not unique."
        )

    print(
        "PROCESSING_READBACK=PASS"
    )

    print(
        "PROCESSING_READBACK_ROWS="
        f"{verify_rows}"
    )

    print()
    print("=" * 72)
    print(
        "TASK-002 PERSON CANONICAL "
        "ADAPTER PASSED"
    )
    print("=" * 72)

    print(
        "PERSON_CANONICAL_ADAPTER=PASS"
    )

    print(
        "RAW_PUBLISHED=NO"
    )

    print(
        "POSTGRESQL_TOUCHED=NO"
    )

    spark.stop()


if __name__ == "__main__":
    main()
