import argparse

from pyspark.sql import SparkSession

from batch_manifest import (
    find_dataset_file,
    read_json_document,
    validate_intake_manifest,
)

from canonical_gate import (
    load_contract,
    validate_contract,
    validate_metadata,
    validate_unique_key,
)


CANONICAL_VERSION = "v1"
ENTITY = "patient"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Validate Processing Canonical Patient "
            "and publish approved Raw data."
        )
    )

    parser.add_argument(
        "--input-manifest-uri",
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
        "--raw-data-uri",
        required=True,
    )

    parser.add_argument(
        "--contract-path",
        required=True,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName(
            "task002-canonical-patient-gate"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    print("=" * 72)
    print(
        "TASK-002 - CANONICAL PATIENT "
        "GATE -> HEALTH-RAW"
    )
    print("=" * 72)

    print(
        f"BATCH_ID={args.batch_id}"
    )

    print(
        f"RUN_ID={args.run_id}"
    )

    print(
        "PROCESSING_INPUT="
        f"{args.processing_data_uri}"
    )

    print(
        "RAW_OUTPUT="
        f"{args.raw_data_uri}"
    )


    # ========================================================
    # 1. Re-read authoritative TASK-001 manifest
    # ========================================================

    manifest = read_json_document(
        spark,
        args.input_manifest_uri,
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

    expected_rows = int(
        patient_file["row_count"]
    )

    print(
        "INPUT_MANIFEST_STATUS="
        f"{manifest['status']}"
    )

    print(
        f"EXPECTED_ROWS={expected_rows}"
    )

    print(
        "SOURCE_FILE_SHA256="
        f"{patient_file['sha256']}"
    )


    # ========================================================
    # 2. Read isolated Processing run
    # ========================================================

    processing = (
        spark.read
        .parquet(
            args.processing_data_uri
        )
        .cache()
    )

    contract = load_contract(
        args.contract_path
    )


    # ========================================================
    # 3. Canonical Gate
    # ========================================================

    contract_result = (
        validate_contract(
            processing,
            contract,
        )
    )

    key_result = (
        validate_unique_key(
            processing,
            contract["primary_key"],
        )
    )

    expected_metadata = {
        "source_system":
            manifest["source"],

        "source_version":
            manifest["source_version"],

        "source_batch_id":
            manifest["batch_id"],

        "source_ingest_date":
            manifest["ingest_date"],

        "source_file":
            patient_file["path"],

        "source_file_sha256":
            patient_file["sha256"],

        "source_file_size_bytes":
            int(
                patient_file["size_bytes"]
            ),

        "adapter_name":
            "synthea_patient",

        "adapter_version":
            "v1",

        "canonical_version":
            CANONICAL_VERSION,

        "processing_run_id":
            args.run_id,
    }

    metadata_result = (
        validate_metadata(
            processing,
            expected_metadata,
        )
    )


    rows = key_result["rows"]

    unique_keys = key_result[
        "unique_keys"
    ]

    if rows != expected_rows:
        raise RuntimeError(
            "Canonical Gate row count mismatch: "
            f"expected={expected_rows}, "
            f"actual={rows}"
        )

    print(
        "CANONICAL_SCHEMA="
        f"{contract_result['schema']}"
    )

    print(
        "CANONICAL_REQUIRED_FIELDS="
        f"{contract_result['required_fields']}"
    )

    print(
        "CANONICAL_METADATA="
        f"{metadata_result['metadata']}"
    )

    print(
        f"CANONICAL_GATE_ROWS={rows}"
    )

    print(
        "CANONICAL_GATE_UNIQUE_KEYS="
        f"{unique_keys}"
    )

    print(
        "CANONICAL_GATE=PASS"
    )


    # ========================================================
    # 4. Publish immutable Raw data prefix
    # ========================================================

    (
        processing
        .write
        .mode(
            "errorifexists"
        )
        .parquet(
            args.raw_data_uri
        )
    )

    print(
        "RAW_WRITE=PASS"
    )


    # ========================================================
    # 5. Raw independent read-back
    # ========================================================

    raw = (
        spark.read
        .parquet(
            args.raw_data_uri
        )
        .cache()
    )

    validate_contract(
        raw,
        contract,
    )

    raw_key_result = (
        validate_unique_key(
            raw,
            contract["primary_key"],
        )
    )

    validate_metadata(
        raw,
        expected_metadata,
    )


    raw_rows = raw_key_result[
        "rows"
    ]

    raw_unique = raw_key_result[
        "unique_keys"
    ]


    if raw_rows != expected_rows:
        raise RuntimeError(
            "Raw read-back row count mismatch."
        )

    if raw_unique != expected_rows:
        raise RuntimeError(
            "Raw read-back unique key mismatch."
        )


    print(
        "RAW_READBACK=PASS"
    )

    print(
        f"RAW_ROWS={raw_rows}"
    )

    print(
        f"RAW_UNIQUE_KEYS={raw_unique}"
    )


    print()
    print("=" * 72)
    print(
        "TASK-002 CANONICAL PATIENT "
        "GATE PASSED"
    )
    print("=" * 72)

    print(
        "CANONICAL_GATE=PASS"
    )

    print(
        "RAW_DATA_PUBLISHED=PASS"
    )

    print(
        "RAW_MANIFEST_PUBLISHED=NO"
    )

    print(
        "POSTGRESQL_TOUCHED=NO"
    )

    spark.stop()


if __name__ == "__main__":
    main()
