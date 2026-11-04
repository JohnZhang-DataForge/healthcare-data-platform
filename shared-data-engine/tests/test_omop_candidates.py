"""Synthetic G5 OMOP candidate tests; no cloud/Gold writes or ID allocation."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from healthcare_data_engine import (
    BatchContext, SourceObject, parse_fhir_resources,
    normalize_fhir_patient, normalize_fhir_encounter, load_pinned_contract,
)
from healthcare_data_engine.canonical.validation import accepted_dataframe
from healthcare_data_engine.mapping.omop.candidates import (
    build_omop_candidates, load_omop_mapping_profile,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures/fhir_r4/patient_encounters_bundle.json"


class OmopCandidateSparkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]").appName("g5-pure-omop-candidate")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.session.timeZone", "UTC").getOrCreate())

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def setUp(self):
        self.ctx = BatchContext(
            hospital_id="hospital-a", feed_id="fhir-r4", source_system="synthetic",
            request_id="g5-synthetic-fixture",
            manifest_sha256=hashlib.sha256(b"synthetic-g5-manifest").hexdigest(),
            processing_version="g4-synthetic-test", processing_run_id="test-g5",
            source_version="FHIR_R4", source_ingest_date=date(2026, 11, 3),
            processed_at=datetime(2026, 11, 3, 12, tzinfo=timezone.utc))
        parsed = parse_fhir_resources((SourceObject.from_bytes(
            "fixture.json", FIXTURE.read_bytes()),), self.ctx)
        pc = load_pinned_contract(
            (ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes(),
            "patient")
        ec = load_pinned_contract(
            (ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes(),
            "encounter")
        patients = normalize_fhir_patient(parsed, pc, self.ctx)
        encounters = normalize_fhir_encounter(parsed, ec, self.ctx)
        self.assertEqual(len(patients.accepted), 1)
        self.assertEqual(len(encounters.accepted), 2)
        self.patients = accepted_dataframe(self.spark, patients.accepted, pc)
        self.encounters = accepted_dataframe(self.spark, encounters.accepted, ec)
        self.system = self.ctx.namespaced_source_system
        p = patients.accepted[0]
        classes = {r["encounter_class"] for r in encounters.accepted}
        # Deliberately synthetic test profile, NOT an approved FHIR vocabulary
        # publication; runtime must inject real reviewed profile + Concept lookup.
        self.profile = {
            "mapping_name": "synthetic-fixture-only-not-for-publication",
            "mapping_version": "test-1",
            "source_system": self.system,
            "gender_concepts": {p["gender_code"]: 8507},
            "race_concepts": {p["race_code"]: 8527},
            "ethnicity_concepts": {p["ethnicity_code"]: 38003564},
            "visit_class_concepts": {name: 9202 for name in classes},
            "visit_type_concept_id": 32827,
        }
        self.profile_raw = json.dumps(
            self.profile, sort_keys=True, separators=(",", ":")).encode()
        self.profile_sha = hashlib.sha256(self.profile_raw).hexdigest()
        self.identity = self.spark.createDataFrame(
            [("PERSON", self.ctx.hospital_id, self.system, p["source_record_id"], 123456)],
            "entity_type string, hospital_id string, source_system string, "
            "source_business_key string, omop_id int")
        concept_ids = set([8507, 8527, 38003564, 9202, 32827])
        self.concepts = self.spark.createDataFrame(
            [(cid, "S", None) for cid in sorted(concept_ids)],
            "concept_id int, standard_concept string, invalid_reason string")
        self.approval = {
            "status": "SILVER_APPROVED",
            "source_batch_id": self.ctx.source_batch_id,
            "manifest_sha256": self.ctx.manifest_sha256,
            "processing_version": self.ctx.processing_version,
            "publication_id": "silver-physical-approval-fixture",
            "patient_count": 1, "encounter_count": 2, "quarantine_count": 0,
        }

    def build(self, **changes):
        args = dict(
            patients=self.patients, encounters=self.encounters,
            identity_map=self.identity, concepts=self.concepts,
            approval=self.approval, hospital_id=self.ctx.hospital_id,
            source_system=self.system, source_batch_id=self.ctx.source_batch_id,
            manifest_sha256=self.ctx.manifest_sha256,
            processing_version=self.ctx.processing_version,
            mapping_profile_bytes=self.profile_raw,
            mapping_profile_sha256=self.profile_sha,
            raw_publish_run_id="raw-snapshot-fixture",
        )
        args.update(changes)
        return build_omop_candidates(**args)

    def test_approved_person_and_visit_exact_local_column_contract(self):
        result = self.build()
        self.assertEqual(result.status, "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED")
        self.assertEqual((result.person_count, result.visit_count), (1, 2))
        for name, df in (
            ("person-v5.4.json", result.person),
            ("visit-candidate-v1.json", result.visit),
        ):
            contract = json.loads(
                (ROOT / "local-data-platform/spark/contracts/omop" / name).read_text())
            self.assertEqual(df.columns, [field["name"] for field in contract["fields"]])
            self.assertFalse(df.filter(F.col("person_id").isNull()).limit(1).count())
        person_id = result.person.first().person_id
        self.assertEqual(person_id, 123456)
        self.assertEqual({r.person_id for r in result.visit.select("person_id").collect()},
                         {person_id})
        self.assertEqual(result.person.first().gender_concept_id, 8507)
        self.assertEqual({r.visit_concept_id for r in
                          result.visit.select("visit_concept_id").collect()}, {9202})

    def test_replay_deterministic_and_no_id_allocation(self):
        first, second = self.build(), self.build()
        self.assertEqual(first.person.exceptAll(second.person).count(), 0)
        self.assertEqual(second.person.exceptAll(first.person).count(), 0)
        self.assertEqual(first.visit.exceptAll(second.visit).count(), 0)
        self.assertEqual(first.mapping_sha256, second.mapping_sha256)

    def test_rejected_silver_approval_never_maps(self):
        for update in (
            {"status": "SILVER_DENIED"},
            {"quarantine_count": 26, "patient_count": 99, "encounter_count": 5893},
            {"manifest_sha256": "0" * 64},
            {"processing_version": "other"},
            {"source_batch_id": "foreign"},
            {"patient_count": 100},
            {"publication_id": ""},
        ):
            with self.subTest(update=update):
                approval = {**self.approval, **update}
                with self.assertRaisesRegex(ValueError, "G5_SILVER_APPROVAL"):
                    self.build(approval=approval)

    def test_fhir_profile_checksum_schema_and_namespace_fail_closed(self):
        for kwargs, expected in (
            ({"mapping_profile_sha256": "0" * 64}, "G5_MAPPING_PROFILE_SHA_CONFLICT"),
            ({"mapping_profile_sha256": ""}, "G5_MAPPING_PROFILE_PIN_MISSING"),
            ({"source_system": "synthetic:hospital-b:fhir-r4"},
             "G5_HOSPITAL_SOURCE_CONTEXT_MISMATCH"),
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, expected):
                    self.build(**kwargs)
        foreign_profile = deepcopy(self.profile)
        foreign_profile["source_system"] = "synthetic:hospital-b:fhir-r4"
        foreign_raw = json.dumps(foreign_profile, sort_keys=True).encode()
        with self.assertRaisesRegex(ValueError, "G5_MAPPING_PROFILE_SOURCE_NAMESPACE_MISMATCH"):
            self.build(mapping_profile_bytes=foreign_raw,
                       mapping_profile_sha256=hashlib.sha256(foreign_raw).hexdigest())
        duplicate = (b'{"mapping_name":"one","mapping_name":"two"}')
        with self.assertRaisesRegex(ValueError, "G5_MAPPING_PROFILE_SHA_CONFLICT"):
            load_omop_mapping_profile(
                duplicate, self.profile_sha, self.system)
        with self.assertRaisesRegex(ValueError, "G5_MAPPING_PROFILE_DUPLICATE_KEY"):
            load_omop_mapping_profile(
                duplicate, hashlib.sha256(duplicate).hexdigest(), self.system)

    def test_unmapped_fhir_code_is_never_assumed_local_synthea(self):
        profile = deepcopy(self.profile)
        profile["race_concepts"] = {"white": 8527}  # local code, NOT FHIR code
        raw = json.dumps(profile, sort_keys=True).encode()
        with self.assertRaisesRegex(ValueError, "G5_UNKNOWN_MAPPING_CODE:race_code"):
            self.build(mapping_profile_bytes=raw,
                       mapping_profile_sha256=hashlib.sha256(raw).hexdigest())

    def test_concept_standard_and_missing_lookup_holds(self):
        invalid = self.spark.createDataFrame(
            [(cid, "S" if cid != 9202 else "C", None)
             for cid in (8507, 8527, 38003564, 9202, 32827)],
            "concept_id int, standard_concept string, invalid_reason string")
        with self.assertRaisesRegex(ValueError, "G5_OMOP_STANDARD_CONCEPT"):
            self.build(concepts=invalid)
        missing = self.concepts.filter("concept_id != 32827")
        with self.assertRaisesRegex(ValueError, "G5_OMOP_STANDARD_CONCEPT"):
            self.build(concepts=missing)

    def test_missing_duplicate_or_cross_hospital_ids_hold(self):
        missing = self.identity.filter("1 = 0")
        duplicate = self.identity.unionByName(self.identity)
        cross = self.identity.withColumn(
            "hospital_id", F.lit("hospital-b"))
        for ids, diagnostic in (
            (missing, "G5_STABLE_PERSON_ID_NOT_FOUND"),
            (duplicate, "G5_STABLE_ID_MAP_DUPLICATE_SOURCE"),
            (cross, "G5_STABLE_PERSON_ID_NOT_FOUND"),
        ):
            with self.subTest(diagnostic=diagnostic):
                with self.assertRaisesRegex(ValueError, diagnostic):
                    self.build(identity_map=ids)

    def test_explicit_hospital_scope_is_required_and_consistent(self):
        for proposed in ("hospital-b", "", "hospital-a ", "hospital-a:fhir-r4"):
            with self.subTest(proposed=proposed):
                with self.assertRaisesRegex(
                        ValueError, "G5_HOSPITAL_(ID_REQUIRED|SOURCE_CONTEXT_MISMATCH)"):
                    self.build(hospital_id=proposed)
        with self.assertRaisesRegex(ValueError, "G5_HOSPITAL_SOURCE_CONTEXT_MISMATCH"):
            self.build(source_system="synthetic:hospital-b:fhir-r4")

    def test_real_f1_warehouse_schema_and_global_person_id_uniqueness(self):
        # A different hospital may reuse the SAME external patient key,
        # but must have a different global Warehouse Person ID.
        another = self.identity.withColumn(
            "hospital_id", F.lit("hospital-b")).withColumn(
            "omop_id", F.lit(987654))
        self.assertEqual(self.build(
            identity_map=self.identity.unionByName(another)).person.first().person_id,
            123456)
        same_id = another.withColumn("omop_id", F.lit(123456))
        with self.assertRaisesRegex(ValueError, "G5_STABLE_ID_MAP_DUPLICATE_PERSON_ID"):
            self.build(identity_map=self.identity.unionByName(same_id))
        collision = another.withColumn(
            "hospital_id", F.lit("HOSPITAL-A")).withColumn(
            "source_business_key",
            F.upper(F.col("source_business_key")))
        with self.assertRaisesRegex(ValueError, "G5_STABLE_ID_MAP_COLLATION_COLLISION"):
            self.build(identity_map=self.identity.unionByName(collision))

    def test_wrong_entity_or_missing_map_fields_cannot_publish(self):
        visit_only = self.identity.withColumn("entity_type", F.lit("VISIT_OCCURRENCE"))
        with self.assertRaisesRegex(ValueError, "G5_STABLE_PERSON_ID_NOT_FOUND"):
            self.build(identity_map=visit_only)
        with self.assertRaisesRegex(ValueError, "G5_STABLE_ID_MAP_SCHEMA_INVALID"):
            self.build(identity_map=self.identity.drop("hospital_id"))
        with self.assertRaisesRegex(ValueError, "G5_STABLE_ID_MAP_INVALID_SOURCE"):
            self.build(identity_map=self.identity.withColumn(
                "source_business_key", F.lit(None).cast("string")))

    def test_invalid_fk_and_duplicate_encounter_hold(self):
        foreign = self.encounters.withColumn(
            "source_person_id", F.lit("different-person"))
        with self.assertRaisesRegex(ValueError, "G5_VISIT_PERSON_FK_NOT_FOUND"):
            self.build(encounters=foreign)
        with self.assertRaisesRegex(ValueError, "G5_ENCOUNTER_DUPLICATE_PK"):
            self.build(encounters=self.encounters.unionByName(self.encounters))


if __name__ == "__main__":
    unittest.main()
