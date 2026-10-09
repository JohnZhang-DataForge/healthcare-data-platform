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


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Validate one isolated Canonical entity "
            "and publish immutable approved Raw data."
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
        "--processing-run-id",
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

    parser.add_argument(
        "--entity",
        required=True,
    )

    parser.add_argument(
        "--dataset",
        required=True,
    )

    parser.add_argument(
        "--source-file-name",
        required=True,
    )

    parser.add_argument(
        "--expected-adapter-name",
        required=True,
    )

    parser.add_argument(
        "--adapter-version",
        default="v1",
    )

    parser.add_argument(
        "--canonical-version",
        default="v1",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName(
            f"canonical-{args.entity}-gate"
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
            "GENERIC CANONICAL GATE -> HEALTH-RAW"
        )

        print("=" * 72)

        print(
            f"ENTITY={args.entity}"
        )

        print(
            f"DATASET={args.dataset}"
        )

        print(
            f"BATCH_ID={args.batch_id}"
        )

        print(
            "PROCESSING_RUN_ID="
            f"{args.processing_run_id}"
        )

        print(
            "PROCESSING_INPUT="
            f"{args.processing_data_uri}"
        )

        print(
            "RAW_OUTPUT="
            f"{args.raw_data_uri}"
        )


        # ====================================================
        # 1. Authoritative TASK-001 manifest
        # ====================================================

        manifest = read_json_document(
            spark,
            args.input_manifest_uri,
        )

        validate_intake_manifest(
            manifest,
            expected_batch_id=args.batch_id,
        )

        source_file = find_dataset_file(
            manifest,
            args.dataset,
            args.source_file_name,
        )

        expected_rows = int(
            source_file["row_count"]
        )

        print(
            "INPUT_MANIFEST_STATUS="
            f"{manifest['status']}"
        )

        print(
            "EXPECTED_ROWS="
            f"{expected_rows}"
        )

        print(
            "SOURCE_FILE="
            f"{source_file['path']}"
        )

        print(
            "SOURCE_FILE_SHA256="
            f"{source_file['sha256']}"
        )


        # ====================================================
        # 2. Read isolated Processing run
        # ====================================================

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


        # ====================================================
        # 3. Canonical Gate
        # ====================================================

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
                source_file["path"],

            "source_file_sha256":
                source_file["sha256"],

            "source_file_size_bytes":
                int(
                    source_file["size_bytes"]
                ),

            "adapter_name":
                args.expected_adapter_name,

            "adapter_version":
                args.adapter_version,

            "canonical_version":
                args.canonical_version,

            "processing_run_id":
                args.processing_run_id,
        }

        metadata_result = (
            validate_metadata(
                processing,
                expected_metadata,
            )
        )

        rows = key_result[
            "rows"
        ]

        unique_keys = key_result[
            "unique_keys"
        ]

        if rows != expected_rows:
            raise RuntimeError(
                "Canonical Gate row count mismatch: "
                f"expected={expected_rows}, "
                f"actual={rows}"
            )

        if unique_keys != expected_rows:
            raise RuntimeError(
                "Canonical Gate unique key mismatch."
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


        # ====================================================
        # 4. Immutable Raw publication
        # ====================================================

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


        # ====================================================
        # 5. Independent Raw read-back
        # ====================================================

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
                "Raw readback row count mismatch."
            )

        if raw_unique != expected_rows:
            raise RuntimeError(
                "Raw readback unique key mismatch."
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
            "GENERIC CANONICAL GATE PASSED"
        )

        print("=" * 72)

        print(
            "CANONICAL_GATE=PASS"
        )

        print(
            "RAW_DATA_PUBLISHED=PASS"
        )

        # Final manifest remains an orchestration responsibility.
        print(
            "RAW_MANIFEST_PUBLISHED=NO"
        )

        print(
            "POSTGRESQL_WRITE=NO"
        )

        print(
            "GENERIC_CANONICAL_PUBLISHER=PASS"
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
