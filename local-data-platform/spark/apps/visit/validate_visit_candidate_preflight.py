"""TASK003 STEP05F2: read-only Spark verification of Visit Candidate.

No JDBC write, S3 write, Visit ID allocation, or publication.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path

TYPE_NAMES = {
    "string": "string",
    "integer": "int",
    "long": "bigint",
    "timestamp": "timestamp",
    "date": "date",
}


def verify_projection(actual_fields, contract_fields):
    expected = [
        (field["name"], TYPE_NAMES[field["type"]])
        for field in contract_fields
    ]
    if actual_fields != expected:
        raise ValueError("Candidate schema/order mismatch")
    if "visit_occurrence_id" in [name for name, _ in actual_fields]:
        raise ValueError("Visit ID allocated before database transaction")


def require_empty(frame, label):
    if frame.limit(1).count():
        raise ValueError(label)


def file_sha(directory, name, expected):
    data = (directory / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Mounted source SHA mismatch: " + name)
    return data


def main():
    from pyspark.sql import SparkSession, functions as F
    from canonical_gate import (
        validate_contract,
        validate_metadata,
        validate_unique_key,
    )
    from verify_encounter_remote_metadata import verify_metadata
    from map_encounter_to_visit_candidate import map_encounter_to_candidate
    from visit_candidate_rules import validate_rules

    directory = Path(__file__).resolve().parent
    state = json.loads(
        (directory / "candidate-preflight-input.json").read_bytes()
    )
    ctx = state["raw_context"]

    candidate_bytes = file_sha(
        directory, "visit-candidate-v1.json",
        state["candidate_contract_sha256"],
    )
    file_sha(
        directory, "map_encounter_to_visit_candidate.py",
        state["mapper_sha256"],
    )
    raw_bytes = file_sha(
        directory, "encounter-v1.json",
        ctx["canonical_contract_sha256"],
    )
    mapping_bytes = file_sha(
        directory, "visit-class-v1.json",
        ctx["mapping_contract_sha256"],
    )

    raw_contract = json.loads(raw_bytes)
    mapping = json.loads(mapping_bytes)
    candidate_contract = json.loads(candidate_bytes)

    class_mapping = validate_rules(
        mapping, raw_contract, candidate_contract
    )

    if ctx.get("expected_rows", 0) <= 0 or ctx.get("status") != "PASS":
        raise ValueError("Unapproved or empty input context")
    if os.environ.get("PGDATABASE") != "omop":
        raise ValueError("Unexpected PostgreSQL database")

    spark = (
        SparkSession.builder
        .appName("visit-candidate-preflight")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        def remote_bytes(uri):
            rows = (
                spark.read.format("binaryFile")
                .load(uri.replace("s3://", "s3a://", 1))
                .select("content")
                .collect()
            )
            if len(rows) != 1:
                raise ValueError("Unexpected remote metadata count")
            return bytes(rows[0]["content"])

        verify_metadata(
            ctx,
            remote_bytes(ctx["raw_manifest_uri"]),
            remote_bytes(ctx["dq_uri"]),
        )
        manifest = json.loads(remote_bytes(ctx["raw_manifest_uri"]))

        raw = spark.read.parquet(
            ctx["raw_data_uri"].replace("s3://", "s3a://", 1)
        ).cache()

        validate_contract(raw, raw_contract)
        keys = validate_unique_key(raw, raw_contract["primary_key"])

        if (
            keys["rows"] != ctx["expected_rows"]
            or keys["unique_keys"] != keys["rows"]
        ):
            raise ValueError("Pinned Encounter row/key count mismatch")

        validate_metadata(raw, dict(
            source_system=ctx["source"],
            source_version=ctx["source_version"],
            source_batch_id=ctx["batch_id"],
            source_ingest_date=ctx["ingest_date"],
            processing_run_id=ctx["processing_run_id"],
            source_file=manifest["source_file"],
            source_file_sha256=manifest["source_file_sha256"],
            source_file_size_bytes=manifest["source_file_size_bytes"],
            adapter_name="synthea_encounter_adapter",
            adapter_version="v1",
            canonical_version="v1",
        ))

        require_empty(
            raw.filter(
                F.col("end_datetime") < F.col("start_datetime")
            ),
            "Raw Encounter end precedes start",
        )
        require_empty(
            raw.filter(
                F.length(F.trim("source_encounter_id")) == 0
            ),
            "Blank Encounter key",
        )
        require_empty(
            raw.filter(
                F.length(F.col("source_encounter_id")) > 255
            ),
            "Encounter key exceeds ID map length",
        )

        def jdbc_read(sql):
            return (
                spark.read.format("jdbc")
                .option(
                    "url",
                    "jdbc:postgresql://"
                    + os.environ["PGHOST"]
                    + ":"
                    + os.environ["PGPORT"]
                    + "/omop",
                )
                .option("user", os.environ["PGUSER"])
                .option("password", os.environ["PGPASSWORD"])
                .option("driver", "org.postgresql.Driver")
                .option(
                    "sessionInitStatement",
                    "SET default_transaction_read_only = on",
                )
                .option(
                    "dbtable", "(" + sql + ") AS visit_f2_readonly"
                )
                .load()
            )

        person_map = jdbc_read("""
            SELECT m.source_system,
                   m.source_person_id,
                   m.person_id,
                   p.person_id AS cdm_person_id
            FROM etl.person_id_map m
            LEFT JOIN cdm.person p ON p.person_id = m.person_id
            WHERE m.source_system = 'synthea'
        """).cache()

        require_empty(
            person_map.filter(
                F.col("person_id").isNull()
                | F.col("cdm_person_id").isNull()
                | (F.col("person_id") <= 0)
            ),
            "Invalid Person map or CDM reference",
        )

        require_empty(
            person_map
            .groupBy("source_system", "source_person_id")
            .count()
            .filter(F.col("count") != 1),
            "Duplicate Person source identity",
        )

        candidate = map_encounter_to_candidate(
            raw, person_map, mapping, ctx
        ).cache()

        verify_projection(
            [
                (field.name, field.dataType.simpleString())
                for field in candidate.schema.fields
            ],
            candidate_contract["fields"],
        )

        rows = candidate.count()
        if rows != keys["rows"]:
            raise ValueError("Person join changed Encounter row count")

        required = [
            field["name"]
            for field in candidate_contract["fields"]
            if not field["nullable"]
        ]

        null_condition = reduce(
            lambda left, right: left | right,
            [F.col(name).isNull() for name in required],
        )
        require_empty(
            candidate.filter(null_condition),
            "Null in required Candidate field",
        )

        require_empty(
            candidate.filter(
                (F.col("person_id") <= 0)
                | (F.col("visit_concept_id") <= 0)
                | (
                    F.col("visit_start_datetime")
                    > F.col("visit_end_datetime")
                )
                | (
                    F.col("visit_start_date")
                    != F.to_date("visit_start_datetime")
                )
                | (
                    F.col("visit_end_date")
                    != F.to_date("visit_end_datetime")
                )
                | (
                    F.col("visit_type_concept_id")
                    != mapping["visit_type_concept_id"]
                )
                | (
                    F.col("visit_source_value")
                    != F.col("encounter_class")
                )
            ),
            "Invalid Person/concept/date/type/source mapping",
        )

        deferred_names = {
            "provider_id", "care_site_id",
            "visit_source_concept_id",
            "admitted_from_concept_id",
            "admitted_from_source_value",
            "discharged_to_concept_id",
            "discharged_to_source_value",
            "preceding_visit_occurrence_id",
        }

        for name in deferred_names:
            require_empty(
                candidate.filter(F.col(name).isNotNull()),
                "Deferred field unexpectedly populated: " + name,
            )

        grouped = (
            candidate
            .groupBy("encounter_class", "visit_concept_id")
            .count()
            .collect()
        )

        class_counts = {}
        for record in grouped:
            klass = record["encounter_class"]
            concept = record["visit_concept_id"]
            count = record["count"]

            if (
                klass not in class_mapping
                or concept != class_mapping[klass]
            ):
                raise ValueError("Invalid Encounter class mapping")

            class_counts[klass] = class_counts.get(klass, 0) + count

        if sum(class_counts.values()) != rows:
            raise ValueError("Candidate class counts mismatch")

        if class_counts != state["expected_class_counts"]:
            raise ValueError("Class distribution differs from STEP05E")

        unique_rows = (
            candidate
            .select("source_system", "source_encounter_id")
            .distinct()
            .count()
        )
        if unique_rows != rows:
            raise ValueError("Duplicate Candidate source key")

        used_persons = candidate.select("person_id").distinct().count()
        if used_persons != state["expected_persons"]:
            raise ValueError("Referenced Person count changed")

        concept_ids = (
            set(class_mapping.values())
            | {mapping["visit_type_concept_id"]}
        )

        concepts = jdbc_read(
            "SELECT concept_id, domain_id, standard_concept, "
            "invalid_reason, valid_start_date, valid_end_date "
            "FROM cdm.concept WHERE concept_id IN ("
            + ",".join(map(str, sorted(concept_ids))) + ")"
        ).collect()

        if {r["concept_id"] for r in concepts} != concept_ids:
            raise ValueError("Missing Visit concepts")

        today = datetime.now(timezone.utc).date()
        for record in concepts:
            expected_domain = (
                "Type Concept"
                if record["concept_id"] == mapping["visit_type_concept_id"]
                else "Visit"
            )
            if (
                record["domain_id"] != expected_domain
                or record["standard_concept"] != "S"
                or record["invalid_reason"] is not None
                or not (
                    record["valid_start_date"]
                    <= today
                    <= record["valid_end_date"]
                )
            ):
                raise ValueError("Invalid Visit concept metadata")

        # Recheck approved remote metadata before PASS.
        verify_metadata(
            ctx,
            remote_bytes(ctx["raw_manifest_uri"]),
            remote_bytes(ctx["dq_uri"]),
        )

        result = dict(
            status="PASS",
            step="STEP-05F2",
            raw_publish_run_id=ctx["raw_publish_run_id"],
            expected_rows=ctx["expected_rows"],
            candidate_rows=rows,
            unique_source_keys=unique_rows,
            referenced_persons=used_persons,
            class_counts=class_counts,
            candidate_schema="PASS",
            person_mapping="PASS",
            visit_concepts="PASS",
            dates="PASS",
            nullability="PASS",
            deferred_fields="PASS",
            raw_manifest_sha256=ctx["raw_manifest_sha256"],
            dq_sha256=ctx["dq_sha256"],
            mapping_contract_sha256=ctx["mapping_contract_sha256"],
            candidate_contract_sha256=state[
                "candidate_contract_sha256"
            ],
            mapper_sha256=state["mapper_sha256"],
            ids_allocated=0,
            s3_write=False,
            postgresql_write=False,
            candidate_published=False,
        )

        print(
            "VISIT_CANDIDATE_PREFLIGHT_RESULT="
            + json.dumps(result, sort_keys=True),
            flush=True,
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
