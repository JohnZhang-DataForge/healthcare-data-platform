"""Pure approved-Silver to OMOP 5.4 Person / Visit candidate transformations.

No SparkSession, I/O, ID allocation or Gold publisher is owned by this module.
The caller must *independently* read the physical Silver Approval and Delta
before passing evidence and must separately verify any physical candidate write.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


@dataclass(frozen=True)
class OmopCandidates:
    person: Any
    visit: Any
    mapping_sha256: str
    person_count: int
    visit_count: int
    status: str = "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED"


def load_omop_mapping_profile(raw: bytes, expected_sha256: str,
                              source_system: str) -> dict[str, Any]:
    """Require exact versioned, namespace-scoped profile bytes (never guess FHIR codes)."""
    if (not isinstance(raw, bytes) or not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64 or
            any(ch not in "0123456789abcdef" for ch in expected_sha256)):
        raise ValueError("G5_MAPPING_PROFILE_PIN_MISSING")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("G5_MAPPING_PROFILE_SHA_CONFLICT")
    def no_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("G5_MAPPING_PROFILE_DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        profile = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("G5_MAPPING_PROFILE_INVALID_JSON") from exc
    keys = {"mapping_name", "mapping_version", "source_system",
            "gender_concepts", "race_concepts", "ethnicity_concepts",
            "visit_class_concepts", "visit_type_concept_id"}
    if not isinstance(profile, dict) or set(profile) != keys:
        raise ValueError("G5_MAPPING_PROFILE_UNREVIEWED_SCHEMA")
    if (profile["source_system"] != source_system or
            not isinstance(source_system, str) or not source_system or
            not all(isinstance(profile[k], str) and profile[k].strip()
                    for k in ("mapping_name", "mapping_version"))):
        raise ValueError("G5_MAPPING_PROFILE_SOURCE_NAMESPACE_MISMATCH")
    for key in ("gender_concepts", "race_concepts", "ethnicity_concepts",
                "visit_class_concepts"):
        mapping = profile[key]
        if (not isinstance(mapping, dict) or not mapping or
                not all(isinstance(code, str) and code and type(cid) is int
                        and cid > 0 for code, cid in mapping.items())):
            raise ValueError("G5_MAPPING_PROFILE_CONCEPTS_INVALID:" + key)
    if (type(profile["visit_type_concept_id"]) is not int or
            profile["visit_type_concept_id"] <= 0):
        raise ValueError("G5_MAPPING_PROFILE_VISIT_TYPE_INVALID")
    return profile


def _require_source(df, *, entity: str, required: tuple[str, ...],
                    source_system: str, source_batch_id: str) -> int:
    from pyspark.sql import functions as F

    if not set(required).issubset(df.columns):
        raise ValueError("G5_" + entity + "_CANONICAL_SCHEMA_MISMATCH")
    count = df.count()
    if count <= 0:
        raise ValueError("G5_" + entity + "_EMPTY")
    if df.filter(
        F.col("source_system").isNull() |
        (F.col("source_system") != source_system) |
        F.col("source_batch_id").isNull() |
        (F.col("source_batch_id") != source_batch_id)
    ).limit(1).count():
        raise ValueError("G5_" + entity + "_SOURCE_NAMESPACE_OR_BATCH_DRIFT")
    pk = "source_record_id" if entity == "PATIENT" else "source_encounter_id"
    if df.filter(F.col(pk).isNull() | (F.trim(F.col(pk)) == "")).limit(1).count():
        raise ValueError("G5_" + entity + "_NULL_PK")
    if df.groupBy("source_system", pk).count().filter("count != 1").limit(1).count():
        raise ValueError("G5_" + entity + "_DUPLICATE_PK")
    return count


def _verify_codes(df, column: str, lookup: Mapping[str, int]) -> None:
    from pyspark.sql import functions as F

    if df.filter(F.col(column).isNull() | ~F.col(column).isin(*tuple(lookup))).limit(1).count():
        raise ValueError("G5_UNKNOWN_MAPPING_CODE:" + column)


def _verify_concepts(concepts, profile: Mapping[str, Any]) -> None:
    from pyspark.sql import functions as F

    expected = {profile["visit_type_concept_id"]}
    for name in ("gender_concepts", "race_concepts", "ethnicity_concepts",
                 "visit_class_concepts"):
        expected.update(profile[name].values())
    if not {"concept_id", "standard_concept", "invalid_reason"}.issubset(concepts.columns):
        raise ValueError("G5_CONCEPT_LOOKUP_SCHEMA_INVALID")
    rows = concepts.filter(F.col("concept_id").isin(*sorted(expected))).select(
        "concept_id", "standard_concept", "invalid_reason").collect()
    if (len(rows) != len(expected) or
            {r.concept_id for r in rows} != expected or
            any(r.standard_concept != "S" or r.invalid_reason is not None for r in rows)):
        raise ValueError("G5_OMOP_STANDARD_CONCEPT_LOOKUP_NOT_VERIFIED")


def _concept_expr(F, column: str, lookup: Mapping[str, int]):
    items = []
    for code, cid in sorted(lookup.items()):
        items.extend((F.lit(code), F.lit(cid)))
    return F.element_at(F.create_map(*items), F.col(column)).cast("int")


def build_omop_candidates(
    patients, encounters, identity_map, concepts, *,
    approval: Mapping[str, Any],
    hospital_id: str, source_system: str, source_batch_id: str, manifest_sha256: str,
    processing_version: str, mapping_profile_bytes: bytes,
    mapping_profile_sha256: str, raw_publish_run_id: str,
) -> OmopCandidates:
    """Map only independently approved Silver with externally verified stable IDs.

    A caller-provided approval row is *not* physical evidence by itself.
    Notebook/Workflow must independently reopen persisted Silver + Approval
    and fail closed before invoking this mapping.
    """
    from pyspark.sql import functions as F

    # Canonical v1 Person/Encounter tables deliberately do not duplicate
    # hospital_id: they carry BatchContext.namespaced_source_system instead.
    # Verify the exact hospital from the *independently approved* batch context
    # and then join to the real Warehouse F1 map on all namespace dimensions.
    if (not isinstance(hospital_id, str) or not hospital_id
            or hospital_id != hospital_id.strip()):
        raise ValueError("G5_HOSPITAL_ID_REQUIRED")
    parts = source_system.split(":") if isinstance(source_system, str) else []
    if (len(parts) != 3 or not all(parts) or parts[1] != hospital_id):
        raise ValueError("G5_HOSPITAL_SOURCE_CONTEXT_MISMATCH")

    profile = load_omop_mapping_profile(
        mapping_profile_bytes, mapping_profile_sha256, source_system)
    if (not source_batch_id or not raw_publish_run_id or
            not isinstance(manifest_sha256, str) or len(manifest_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in manifest_sha256) or
            not processing_version):
        raise ValueError("G5_SOURCE_OR_PROVENANCE_PIN_MISSING")
    required = {"status", "source_batch_id", "manifest_sha256", "processing_version",
                "patient_count", "encounter_count", "quarantine_count", "publication_id"}
    if not isinstance(approval, Mapping) or not required.issubset(approval):
        raise ValueError("G5_SILVER_APPROVAL_MISSING")
    if (approval["status"] != "SILVER_APPROVED" or
            approval["source_batch_id"] != source_batch_id or
            approval["manifest_sha256"] != manifest_sha256 or
            approval["processing_version"] != processing_version or
            type(approval["quarantine_count"]) is not int or
            approval["quarantine_count"] != 0 or
            not isinstance(approval["publication_id"], str) or
            not approval["publication_id"]):
        raise ValueError("G5_SILVER_APPROVAL_DENIED_OR_CONFLICT")

    pc = _require_source(
        patients, entity="PATIENT", source_system=source_system,
        source_batch_id=source_batch_id,
        required=("source_system", "source_batch_id", "source_record_id",
                  "birth_date", "gender_code", "race_code", "ethnicity_code"))
    ec = _require_source(
        encounters, entity="ENCOUNTER", source_system=source_system,
        source_batch_id=source_batch_id,
        required=("source_system", "source_batch_id", "source_encounter_id",
                  "source_person_id", "start_datetime", "end_datetime",
                  "encounter_class", "source_code", "source_description",
                  "source_organization_id", "source_provider_id", "source_payer_id",
                  "reason_code", "reason_description", "source_version",
                  "source_ingest_date", "processing_run_id", "canonical_version",
                  "source_file", "source_file_sha256", "source_file_size_bytes"))
    if (type(approval["patient_count"]) is not int or
            type(approval["encounter_count"]) is not int or
            approval["patient_count"] != pc or approval["encounter_count"] != ec):
        raise ValueError("G5_SILVER_APPROVAL_COUNTS_MISMATCH")
    if patients.filter(F.col("birth_date").isNull()).limit(1).count():
        raise ValueError("G5_PATIENT_DATE_MISSING")
    if encounters.filter(
        F.col("start_datetime").isNull() | F.col("end_datetime").isNull() |
        (F.col("start_datetime") > F.col("end_datetime"))
    ).limit(1).count():
        raise ValueError("G5_ENCOUNTER_DATES_INVALID")
    for df, column, mapping in (
        (patients, "gender_code", profile["gender_concepts"]),
        (patients, "race_code", profile["race_concepts"]),
        (patients, "ethnicity_code", profile["ethnicity_concepts"]),
        (encounters, "encounter_class", profile["visit_class_concepts"]),
    ):
        _verify_codes(df, column, mapping)
    _verify_concepts(concepts, profile)

    required_map = {"entity_type", "hospital_id", "source_system",
                    "source_business_key", "omop_id"}
    if not required_map.issubset(identity_map.columns):
        raise ValueError("G5_STABLE_ID_MAP_SCHEMA_INVALID")
    if identity_map.filter(
        F.col("entity_type").isNull() |
        ~F.col("entity_type").isin("PERSON", "VISIT_OCCURRENCE") |
        F.col("hospital_id").isNull() |
        (F.trim(F.col("hospital_id")) == "") |
        F.col("source_system").isNull() |
        (F.trim(F.col("source_system")) == "") |
        F.col("source_business_key").isNull() |
        (F.trim(F.col("source_business_key")) == "")
    ).limit(1).count():
        raise ValueError("G5_STABLE_ID_MAP_INVALID_SOURCE")

    # Global Person ID uniqueness is not guaranteed by Fabric Warehouse's
    # NOT ENFORCED unique constraints. Check all hospitals, not just ours.
    persons_all = identity_map.filter(F.col("entity_type") == "PERSON")
    if persons_all.groupBy(
        "hospital_id", "source_system", "source_business_key"
    ).count().filter("count != 1").limit(1).count():
        raise ValueError("G5_STABLE_ID_MAP_DUPLICATE_SOURCE")
    if persons_all.groupBy(
        F.lower(F.col("hospital_id")), F.lower(F.col("source_system")),
        F.lower(F.col("source_business_key"))
    ).count().filter("count != 1").limit(1).count():
        raise ValueError("G5_STABLE_ID_MAP_COLLATION_COLLISION")
    if persons_all.filter(
        F.col("omop_id").isNull() |
        (F.col("omop_id") <= 0) | (F.col("omop_id") > 2147483647) |
        (F.col("omop_id") != F.col("omop_id").cast("int"))
    ).limit(1).count():
        raise ValueError("G5_STABLE_ID_MAP_INVALID_PERSON_ID")
    if persons_all.groupBy("omop_id").count().filter(
            "count != 1").limit(1).count():
        raise ValueError("G5_STABLE_ID_MAP_DUPLICATE_PERSON_ID")

    ids = persons_all.filter(
        (F.col("hospital_id") == hospital_id) &
        (F.col("source_system") == source_system)
    ).select(
        "hospital_id", "source_system",
        F.col("source_business_key").alias("source_person_id"),
        F.col("omop_id").cast("int").alias("person_id"),
    )
    joined_p = patients.alias("p").join(
        ids.alias("i"),
        (F.col("i.hospital_id") == F.lit(hospital_id)) &
        (F.col("p.source_system") == F.col("i.source_system")) &
        (F.col("p.source_record_id") == F.col("i.source_person_id")), "left")
    if joined_p.count() != pc or joined_p.filter(
            F.col("i.person_id").isNull()).limit(1).count():
        raise ValueError("G5_STABLE_PERSON_ID_NOT_FOUND")
    reference = ids.select(
        "hospital_id", "source_system", "source_person_id", "person_id")
    joined_e = encounters.alias("e").join(
        reference.alias("i"),
        (F.col("i.hospital_id") == F.lit(hospital_id)) &
        (F.col("e.source_system") == F.col("i.source_system")) &
        (F.col("e.source_person_id") == F.col("i.source_person_id")), "left")
    if joined_e.count() != ec or joined_e.filter(
            F.col("i.person_id").isNull()).limit(1).count():
        raise ValueError("G5_VISIT_PERSON_FK_NOT_FOUND")

    person = joined_p.select(
        F.col("i.person_id").cast("int").alias("person_id"),
        _concept_expr(F, "p.gender_code", profile["gender_concepts"]).alias("gender_concept_id"),
        F.year("p.birth_date").cast("int").alias("year_of_birth"),
        F.month("p.birth_date").cast("int").alias("month_of_birth"),
        F.dayofmonth("p.birth_date").cast("int").alias("day_of_birth"),
        F.to_timestamp("p.birth_date").alias("birth_datetime"),
        _concept_expr(F, "p.race_code", profile["race_concepts"]).alias("race_concept_id"),
        _concept_expr(F, "p.ethnicity_code", profile["ethnicity_concepts"]).alias("ethnicity_concept_id"),
        F.lit(None).cast("int").alias("location_id"),
        F.lit(None).cast("int").alias("provider_id"),
        F.lit(None).cast("int").alias("care_site_id"),
        F.col("p.source_record_id").alias("person_source_value"),
        F.col("p.gender_code").alias("gender_source_value"),
        F.lit(None).cast("int").alias("gender_source_concept_id"),
        F.col("p.race_code").alias("race_source_value"),
        F.lit(None).cast("int").alias("race_source_concept_id"),
        F.col("p.ethnicity_code").alias("ethnicity_source_value"),
        F.lit(None).cast("int").alias("ethnicity_source_concept_id"),
    )
    visit = joined_e.select(
        F.col("e.source_system"),
        F.col("e.source_encounter_id"),
        F.col("e.source_person_id"),
        F.col("i.person_id").cast("int").alias("person_id"),
        _concept_expr(F, "e.encounter_class", profile["visit_class_concepts"]).alias("visit_concept_id"),
        F.to_date("e.start_datetime").alias("visit_start_date"),
        F.col("e.start_datetime").alias("visit_start_datetime"),
        F.to_date("e.end_datetime").alias("visit_end_date"),
        F.col("e.end_datetime").alias("visit_end_datetime"),
        F.lit(profile["visit_type_concept_id"]).cast("int").alias("visit_type_concept_id"),
        F.lit(None).cast("int").alias("provider_id"),
        F.lit(None).cast("int").alias("care_site_id"),
        F.col("e.encounter_class").alias("visit_source_value"),
        F.lit(None).cast("int").alias("visit_source_concept_id"),
        F.lit(None).cast("int").alias("admitted_from_concept_id"),
        F.lit(None).cast("string").alias("admitted_from_source_value"),
        F.lit(None).cast("int").alias("discharged_to_concept_id"),
        F.lit(None).cast("string").alias("discharged_to_source_value"),
        F.lit(None).cast("int").alias("preceding_visit_occurrence_id"),
        F.col("e.encounter_class"),
        F.col("e.source_code"),
        F.col("e.source_description"),
        F.col("e.source_organization_id"),
        F.col("e.source_provider_id"),
        F.col("e.source_payer_id"),
        F.col("e.reason_code"),
        F.col("e.reason_description"),
        F.col("e.source_version"),
        F.col("e.source_batch_id"),
        F.col("e.source_ingest_date"),
        F.col("e.processing_run_id"),
        F.lit(raw_publish_run_id).alias("raw_publish_run_id"),
        F.col("e.canonical_version"),
        F.col("e.source_file"),
        F.col("e.source_file_sha256"),
        F.col("e.source_file_size_bytes"),
    )
    if person.count() != pc or visit.count() != ec:
        raise ValueError("G5_OMOP_CANDIDATE_ROW_COUNT_CHANGED")
    return OmopCandidates(person, visit, mapping_profile_sha256, pc, ec)
