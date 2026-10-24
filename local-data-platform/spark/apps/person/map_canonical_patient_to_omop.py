import argparse
import json
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    countDistinct,
    dayofmonth,
    lit,
    month,
    to_timestamp,
    when,
    year,
)
from pyspark.sql.types import IntegerType

from batch_manifest import (
    read_json_document,
    s3_to_s3a,
)

from omop import (
    DEMOGRAPHIC_CONCEPT_IDS,
    ETHNICITY_CONCEPTS,
    GENDER_CONCEPTS,
    RACE_CONCEPTS,
    validate_omop_contract,
    validate_person_keys,
)


ENTITY = "person"
OMOP_VERSION = "v5.4"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Map approved Canonical Patient v1 "
            "to OMOP Person v5.4."
        )
    )

    parser.add_argument(
        "--raw-manifest-uri",
        required=True,
    )

    parser.add_argument(
        "--raw-data-uri",
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

    return parser.parse_args()


def load_contract(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def jdbc_options():
    host = os.environ["PGHOST"]
    port = os.environ["PGPORT"]
    database = os.environ["PGDATABASE"]
    user = os.environ["PGUSER"]
    password = os.environ["PGPASSWORD"]

    return {
        "url": (
            f"jdbc:postgresql://"
            f"{host}:{port}/{database}"
        ),
        "user": user,
        "password": password,
        "driver": "org.postgresql.Driver",
    }


def read_jdbc_query(
    spark,
    jdbc,
    query,
    alias,
):
    return (
        spark.read
        .format("jdbc")
        .option(
            "url",
            jdbc["url"],
        )
        .option(
            "dbtable",
            f"({query}) {alias}",
        )
        .option(
            "user",
            jdbc["user"],
        )
        .option(
            "password",
            jdbc["password"],
        )
        .option(
            "driver",
            jdbc["driver"],
        )
        .load()
    )


def validate_raw_manifest(
    manifest,
    raw_data_uri,
):
    required = [
        "manifest_version",
        "layer",
        "status",
        "entity",
        "canonical_version",
        "source",
        "source_version",
        "ingest_date",
        "batch_id",
        "processing_run_id",
        "raw_publish_run_id",
        "raw_data_uri",
        "output_rows",
        "dq_status",
    ]

    missing = [
        name
        for name in required
        if name not in manifest
    ]

    if missing:
        raise RuntimeError(
            "Raw manifest missing fields: "
            + ", ".join(missing)
        )

    if (
        manifest["layer"]
        != "canonical_raw"
    ):
        raise RuntimeError(
            "Input manifest is not "
            "canonical_raw."
        )

    if manifest["status"] != "APPROVED":
        raise RuntimeError(
            "Canonical Raw is not APPROVED."
        )

    if manifest["dq_status"] != "PASS":
        raise RuntimeError(
            "Canonical Raw DQ is not PASS."
        )

    if manifest["entity"] != "patient":
        raise RuntimeError(
            "Raw manifest entity "
            "is not patient."
        )

    if (
        manifest["canonical_version"]
        != "v1"
    ):
        raise RuntimeError(
            "Unsupported Canonical "
            "Patient version."
        )

    expected_uri = s3_to_s3a(
        manifest["raw_data_uri"]
    )

    actual_uri = s3_to_s3a(
        raw_data_uri
    )

    if (
        expected_uri.rstrip("/")
        != actual_uri.rstrip("/")
    ):
        raise RuntimeError(
            "Raw data URI does not match "
            "approved manifest."
        )

    return int(
        manifest["output_rows"]
    )


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName(
            "task002-canonical-patient-to-omop-person"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    print("=" * 72)
    print(
        "TASK-002 - CANONICAL PATIENT "
        "-> OMOP PERSON"
    )
    print("=" * 72)

    print(
        "RAW_MANIFEST="
        f"{args.raw_manifest_uri}"
    )

    print(
        "RAW_INPUT="
        f"{args.raw_data_uri}"
    )

    print(
        "PROCESSED_OUTPUT="
        f"{args.output_data_uri}"
    )


    # ========================================================
    # 1. Approved Raw commit boundary
    # ========================================================

    raw_manifest = read_json_document(
        spark,
        args.raw_manifest_uri,
    )

    expected_rows = validate_raw_manifest(
        raw_manifest,
        args.raw_data_uri,
    )

    source_system = raw_manifest[
        "source"
    ]

    if not source_system.replace(
        "_",
        "",
    ).isalnum():
        raise RuntimeError(
            "Invalid source system value."
        )

    print(
        "RAW_STATUS="
        f"{raw_manifest['status']}"
    )

    print(
        "RAW_DQ_STATUS="
        f"{raw_manifest['dq_status']}"
    )

    print(
        "RAW_PUBLISH_RUN_ID="
        f"{raw_manifest['raw_publish_run_id']}"
    )

    print(
        f"EXPECTED_ROWS={expected_rows}"
    )


    # ========================================================
    # 2. Read Canonical Patient
    # ========================================================

    patients = (
        spark.read
        .parquet(
            args.raw_data_uri
        )
        .cache()
    )

    patient_count = patients.count()

    unique_source_records = (
        patients
        .agg(
            countDistinct(
                "source_record_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    print(
        f"CANONICAL_ROWS={patient_count}"
    )

    print(
        "CANONICAL_UNIQUE_SOURCE_IDS="
        f"{unique_source_records}"
    )

    if patient_count != expected_rows:
        raise RuntimeError(
            "Canonical Raw row count "
            "does not match manifest."
        )

    if unique_source_records != expected_rows:
        raise RuntimeError(
            "Canonical source_record_id "
            "is not unique."
        )


    # ========================================================
    # 3. PostgreSQL read-only configuration
    # ========================================================

    jdbc = jdbc_options()


    # ========================================================
    # 4. Read stable person ID map
    #
    # Important V2 change:
    # Do NOT require the whole mapping table
    # to contain exactly this batch size.
    # ========================================================

    safe_source = source_system.replace(
        "'",
        "''",
    )

    person_map = (
        read_jdbc_query(
            spark,
            jdbc,
            f"""
            SELECT
                person_id,
                source_person_id
            FROM etl.person_id_map
            WHERE source_system = '{safe_source}'
            """,
            "person_map",
        )
        .cache()
    )

    total_map_rows = (
        person_map.count()
    )

    print(
        "SOURCE_PERSON_MAP_TOTAL_ROWS="
        f"{total_map_rows}"
    )


    # ========================================================
    # 5. Current batch stable-ID join
    # ========================================================

    joined = (
        patients.alias("p")
        .join(
            person_map.alias("m"),
            col("p.source_record_id")
            == col("m.source_person_id"),
            "left",
        )
        .cache()
    )

    joined_rows = joined.count()

    missing_person_ids = (
        joined
        .filter(
            col("m.person_id").isNull()
        )
        .count()
    )

    matched_unique_source_ids = (
        joined
        .filter(
            col("m.person_id").isNotNull()
        )
        .agg(
            countDistinct(
                "m.source_person_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    matched_unique_person_ids = (
        joined
        .filter(
            col("m.person_id").isNotNull()
        )
        .agg(
            countDistinct(
                "m.person_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    print(
        f"STABLE_ID_JOIN_ROWS={joined_rows}"
    )

    print(
        "STABLE_ID_MISSING="
        f"{missing_person_ids}"
    )

    print(
        "STABLE_ID_UNIQUE_SOURCE_IDS="
        f"{matched_unique_source_ids}"
    )

    print(
        "STABLE_ID_UNIQUE_PERSON_IDS="
        f"{matched_unique_person_ids}"
    )

    if joined_rows != expected_rows:
        raise RuntimeError(
            "Stable ID join changed row count. "
            "Possible duplicate mapping "
            "for a current-batch source ID."
        )

    if missing_person_ids != 0:
        raise RuntimeError(
            f"{missing_person_ids} current-batch "
            "patients have no stable person_id."
        )

    if (
        matched_unique_source_ids
        != expected_rows
    ):
        raise RuntimeError(
            "Current batch stable source IDs "
            "are incomplete or duplicated."
        )

    if (
        matched_unique_person_ids
        != expected_rows
    ):
        raise RuntimeError(
            "Current batch stable person IDs "
            "are not unique."
        )

    print(
        "STABLE_PERSON_ID_MAP=PASS"
    )


    # ========================================================
    # 6. Runtime OMOP concept validation
    # ========================================================

    concept_list = ",".join(
        str(value)
        for value
        in DEMOGRAPHIC_CONCEPT_IDS
    )

    concepts = (
        read_jdbc_query(
            spark,
            jdbc,
            f"""
            SELECT
                concept_id,
                concept_name,
                domain_id,
                standard_concept,
                invalid_reason
            FROM cdm.concept
            WHERE concept_id IN (
                {concept_list}
            )
            """,
            "demographic_concepts",
        )
        .cache()
    )

    concept_count = concepts.count()

    invalid_concepts = (
        concepts
        .filter(
            (
                col("standard_concept")
                != "S"
            )
            | (
                col("invalid_reason")
                .isNotNull()
            )
        )
        .count()
    )

    print(
        f"DEMOGRAPHIC_CONCEPT_ROWS="
        f"{concept_count}"
    )

    print(
        "DEMOGRAPHIC_INVALID_CONCEPTS="
        f"{invalid_concepts}"
    )

    if concept_count != len(
        DEMOGRAPHIC_CONCEPT_IDS
    ):
        raise RuntimeError(
            "Required demographic OMOP "
            "concepts are missing."
        )

    if invalid_concepts != 0:
        raise RuntimeError(
            "Invalid or non-standard "
            "demographic OMOP concepts found."
        )

    print(
        "DEMOGRAPHIC_CONCEPT_VALIDATION=PASS"
    )


    # ========================================================
    # 7. Canonical -> OMOP mapping
    # ========================================================

    gender_concept = (
        when(
            col("p.gender_code") == "M",
            lit(
                GENDER_CONCEPTS["M"]
            ),
        )
        .when(
            col("p.gender_code") == "F",
            lit(
                GENDER_CONCEPTS["F"]
            ),
        )
    )

    race_concept = (
        when(
            col("p.race_code") == "asian",
            lit(
                RACE_CONCEPTS["asian"]
            ),
        )
        .when(
            col("p.race_code") == "black",
            lit(
                RACE_CONCEPTS["black"]
            ),
        )
        .when(
            col("p.race_code") == "hawaiian",
            lit(
                RACE_CONCEPTS["hawaiian"]
            ),
        )
        .when(
            col("p.race_code") == "white",
            lit(
                RACE_CONCEPTS["white"]
            ),
        )
    )

    ethnicity_concept = (
        when(
            col("p.ethnicity_code")
            == "hispanic",
            lit(
                ETHNICITY_CONCEPTS[
                    "hispanic"
                ]
            ),
        )
        .when(
            col("p.ethnicity_code")
            == "nonhispanic",
            lit(
                ETHNICITY_CONCEPTS[
                    "nonhispanic"
                ]
            ),
        )
    )


    person = (
        joined
        .select(
            col("m.person_id")
            .cast("int")
            .alias(
                "person_id"
            ),

            gender_concept
            .cast("int")
            .alias(
                "gender_concept_id"
            ),

            year(
                col("p.birth_date")
            )
            .cast("int")
            .alias(
                "year_of_birth"
            ),

            month(
                col("p.birth_date")
            )
            .cast("int")
            .alias(
                "month_of_birth"
            ),

            dayofmonth(
                col("p.birth_date")
            )
            .cast("int")
            .alias(
                "day_of_birth"
            ),

            to_timestamp(
                col("p.birth_date")
            )
            .alias(
                "birth_datetime"
            ),

            race_concept
            .cast("int")
            .alias(
                "race_concept_id"
            ),

            ethnicity_concept
            .cast("int")
            .alias(
                "ethnicity_concept_id"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "location_id"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "provider_id"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "care_site_id"
            ),

            col(
                "p.source_record_id"
            )
            .alias(
                "person_source_value"
            ),

            col(
                "p.gender_code"
            )
            .alias(
                "gender_source_value"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "gender_source_concept_id"
            ),

            col(
                "p.race_code"
            )
            .alias(
                "race_source_value"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "race_source_concept_id"
            ),

            col(
                "p.ethnicity_code"
            )
            .alias(
                "ethnicity_source_value"
            ),

            lit(None)
            .cast(IntegerType())
            .alias(
                "ethnicity_source_concept_id"
            ),
        )
        .cache()
    )


    # ========================================================
    # 8. OMOP Person contract / DQ
    # ========================================================

    contract = load_contract(
        args.contract_path
    )

    contract_result = (
        validate_omop_contract(
            person,
            contract,
        )
    )

    key_result = (
        validate_person_keys(
            person,
            expected_rows,
        )
    )

    print(
        "OMOP_PERSON_SCHEMA="
        f"{contract_result['schema']}"
    )

    print(
        "OMOP_PERSON_REQUIRED_FIELDS="
        f"{contract_result['required_fields']}"
    )

    print(
        "OMOP_PERSON_ROWS="
        f"{key_result['rows']}"
    )

    print(
        "OMOP_PERSON_UNIQUE_IDS="
        f"{key_result['unique_person_ids']}"
    )

    print(
        "OMOP_PERSON_UNIQUE_SOURCE_IDS="
        f"{key_result['unique_source_ids']}"
    )


    # ========================================================
    # 9. Deferred FK contract
    # ========================================================

    for field in [
        "location_id",
        "provider_id",
        "care_site_id",
    ]:
        non_null = (
            person
            .filter(
                col(field).isNotNull()
            )
            .count()
        )

        print(
            f"DEFERRED_{field.upper()}_"
            f"NON_NULL={non_null}"
        )

        if non_null != 0:
            raise RuntimeError(
                f"{field} unexpectedly "
                "populated."
            )

    print(
        "OMOP_PERSON_DQ=PASS"
    )


    # ========================================================
    # 10. Write immutable health-processed run
    # ========================================================

    (
        person
        .write
        .mode(
            "errorifexists"
        )
        .parquet(
            args.output_data_uri
        )
    )

    print(
        "PROCESSED_WRITE=PASS"
    )


    # ========================================================
    # 11. Independent read-back
    # ========================================================

    verify = (
        spark.read
        .parquet(
            args.output_data_uri
        )
        .cache()
    )

    validate_omop_contract(
        verify,
        contract,
    )

    verify_result = (
        validate_person_keys(
            verify,
            expected_rows,
        )
    )

    print(
        "PROCESSED_READBACK=PASS"
    )

    print(
        "PROCESSED_READBACK_ROWS="
        f"{verify_result['rows']}"
    )

    print()
    print("=" * 72)
    print(
        "TASK-002 CANONICAL PATIENT "
        "-> OMOP PERSON PASSED"
    )
    print("=" * 72)

    print(
        "OMOP_PERSON_MAPPING=PASS"
    )

    print(
        "CDM_PERSON_WRITE=NO"
    )

    print(
        "POSTGRESQL_WRITE=NO"
    )

    spark.stop()


if __name__ == "__main__":
    main()
