import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, countDistinct, trim


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only TASK004 reconciliation between "
            "Canonical Patient and Encounter Processing outputs."
        )
    )
    parser.add_argument("--patient-uri", required=True)
    parser.add_argument("--encounter-uri", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument(
        "--expected-patient-rows",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--expected-encounter-rows",
        type=int,
        required=True,
    )
    return parser.parse_args()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def one_nonblank_value(dataframe, name):
    values = [
        row[name]
        for row in dataframe.select(name).distinct().collect()
    ]

    require(
        len(values) == 1,
        f"{name} must contain exactly one value: {values}",
    )

    value = values[0]

    require(
        value is not None,
        f"{name} must not be null",
    )

    if isinstance(value, str):
        require(
            value.strip() != "",
            f"{name} must not be blank",
        )

    return value


def main():
    args = parse_args()

    require(
        args.batch_id.strip() != "",
        "batch_id must not be blank",
    )
    require(
        args.expected_patient_rows > 0,
        "expected_patient_rows must be positive",
    )
    require(
        args.expected_encounter_rows > 0,
        "expected_encounter_rows must be positive",
    )

    spark = (
        SparkSession.builder
        .appName(
            "task004-person-visit-batch-reconciliation"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        patient = (
            spark.read
            .parquet(args.patient_uri)
            .cache()
        )

        encounter = (
            spark.read
            .parquet(args.encounter_uri)
            .cache()
        )

        patient_required = {
            "source_record_id",
            "source_system",
            "source_version",
            "source_batch_id",
            "source_ingest_date",
        }

        encounter_required = {
            "source_encounter_id",
            "source_person_id",
            "source_system",
            "source_version",
            "source_batch_id",
            "source_ingest_date",
        }

        require(
            patient_required.issubset(patient.columns),
            "Patient processing schema missing "
            "reconciliation fields",
        )

        require(
            encounter_required.issubset(encounter.columns),
            "Encounter processing schema missing "
            "reconciliation fields",
        )

        patient_rows = patient.count()
        encounter_rows = encounter.count()

        patient_unique = (
            patient
            .agg(
                countDistinct("source_record_id")
                .alias("n")
            )
            .first()["n"]
        )

        encounter_unique = (
            encounter
            .agg(
                countDistinct("source_encounter_id")
                .alias("n")
            )
            .first()["n"]
        )

        patient_blank = (
            patient
            .filter(
                col("source_record_id").isNull()
                | (trim(col("source_record_id")) == "")
            )
            .count()
        )

        encounter_blank = (
            encounter
            .filter(
                col("source_encounter_id").isNull()
                | (
                    trim(col("source_encounter_id"))
                    == ""
                )
                | col("source_person_id").isNull()
                | (
                    trim(col("source_person_id"))
                    == ""
                )
            )
            .count()
        )

        require(
            patient_rows == args.expected_patient_rows,
            "Patient row count mismatch",
        )
        require(
            encounter_rows == args.expected_encounter_rows,
            "Encounter row count mismatch",
        )
        require(
            patient_unique == patient_rows,
            "Patient source_record_id not unique",
        )
        require(
            encounter_unique == encounter_rows,
            "Encounter source_encounter_id not unique",
        )
        require(
            patient_blank == 0,
            "Blank/null Patient key",
        )
        require(
            encounter_blank == 0,
            "Blank/null Encounter key/reference",
        )

        patient_source = one_nonblank_value(
            patient,
            "source_system",
        )
        encounter_source = one_nonblank_value(
            encounter,
            "source_system",
        )

        patient_version = one_nonblank_value(
            patient,
            "source_version",
        )
        encounter_version = one_nonblank_value(
            encounter,
            "source_version",
        )

        patient_batch = one_nonblank_value(
            patient,
            "source_batch_id",
        )
        encounter_batch = one_nonblank_value(
            encounter,
            "source_batch_id",
        )

        patient_date = one_nonblank_value(
            patient,
            "source_ingest_date",
        )
        encounter_date = one_nonblank_value(
            encounter,
            "source_ingest_date",
        )

        require(
            patient_source == encounter_source,
            "source_system mismatch",
        )
        require(
            patient_version == encounter_version,
            "source_version mismatch",
        )
        require(
            patient_batch == args.batch_id,
            "Patient batch_id mismatch",
        )
        require(
            encounter_batch == args.batch_id,
            "Encounter batch_id mismatch",
        )
        require(
            patient_date == encounter_date,
            "source_ingest_date mismatch",
        )

        patient_keys = (
            patient
            .select(
                col("source_record_id")
                .alias("patient_id")
            )
            .distinct()
        )

        orphan_encounters = (
            encounter
            .select(
                "source_encounter_id",
                "source_person_id",
            )
            .join(
                patient_keys,
                col("source_person_id")
                == col("patient_id"),
                "left_anti",
            )
            .count()
        )

        referenced_people = (
            encounter
            .select("source_person_id")
            .distinct()
            .count()
        )

        require(
            orphan_encounters == 0,
            "Encounter references Patient not present "
            "in same batch",
        )
        require(
            referenced_people > 0,
            "Encounter references no patients",
        )
        require(
            referenced_people <= patient_rows,
            "Referenced Patient cardinality exceeds "
            "Patient row count",
        )

        print(f"PATIENT_ROWS={patient_rows}")
        print(f"PATIENT_UNIQUE_IDS={patient_unique}")
        print(f"ENCOUNTER_ROWS={encounter_rows}")
        print(
            "ENCOUNTER_UNIQUE_IDS="
            f"{encounter_unique}"
        )
        print(
            "REFERENCED_PATIENTS="
            f"{referenced_people}"
        )
        print(
            "ORPHAN_ENCOUNTERS="
            f"{orphan_encounters}"
        )
        print(
            "SOURCE_SYSTEM="
            f"{patient_source}"
        )
        print(
            "SOURCE_VERSION="
            f"{patient_version}"
        )
        print(
            "SOURCE_BATCH_ID="
            f"{patient_batch}"
        )
        print(
            "SOURCE_INGEST_DATE="
            f"{patient_date}"
        )
        print("PROCESSING_MUTATION=NO")
        print("POSTGRESQL_MUTATION=NO")
        print("BATCH_RECONCILIATION=PASS")
        print("RESULT=PASS")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
