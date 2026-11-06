"""Local vs Shared Person/Visit contract/transform parity, synthetic and offline.

Both Local Person and Visit pure projections are invoked directly from the
actual Local production modules and compared with Shared output for every
column and row. Source validation/physical Writer remain separate runtime
responsibilities; these synthetic tests do not establish production migration.

No Warehouse/PG/Blob/Delta, no identity allocation and no clinical approval.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import unittest

from pyspark.sql import SparkSession, functions as F, types as T
from healthcare_data_engine.mapping.omop.candidates import build_omop_candidates

ROOT = Path(__file__).resolve().parents[5]
LOCAL = ROOT / "local-data-platform/spark"
CONTRACTS = LOCAL / "contracts"
SOURCE = "synthetic:hospital-a:fhir-r4"
BATCH = "local-shared-parity-synthetic"
MANIFEST_SHA = hashlib.sha256(b"synthetic-parity-only").hexdigest()
HOSPITAL = "hospital-a"


def _load_local_module(path, name):
    """Load the existing Local transform, never copy its business logic."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOCAL_PARITY_MODULE_NOT_FOUND")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_frame(spark, entity, records):
    contract = json.loads(
        (CONTRACTS / "canonical" / f"{entity}-v1.json").read_text(encoding="utf-8")
    )
    types = {
        "string": T.StringType(), "date": T.DateType(),
        "timestamp": T.TimestampType(), "bigint": T.LongType(),
        "decimal(18,2)": T.DecimalType(18, 2),
    }
    schema = T.StructType([
        T.StructField(f["name"], types[f["type"]], f["nullable"])
        for f in contract["fields"]
    ])
    rows = [tuple(record.get(field.name) for field in schema.fields)
            for record in records]
    return spark.createDataFrame(rows, schema)


def _base_record(entity):
    return {
        "source_system": SOURCE, "source_batch_id": BATCH,
        "source_version": "synthetic-only", "source_ingest_date": date(2026, 11, 6),
        "source_file": "synthetic-fixture.json", "source_file_sha256": "a" * 64,
        "source_file_size_bytes": 100, "adapter_name": "parity-test-only",
        "adapter_version": "test", "canonical_version": "v1",
        "processing_run_id": "offline-test", "processed_at":
            datetime(2026, 11, 6, 12, tzinfo=timezone.utc),
    }


class LocalSharedPersonVisitParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder.master("local[1]")
            .appName("local-shared-omop-synthetic-parity")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate()
        )
        common = str(LOCAL / "common")
        if common not in sys.path:
            sys.path.insert(0, common)
        cls.person_module = _load_local_module(
            LOCAL / "apps/person/map_canonical_patient_to_omop.py",
            "local_person_candidate_parity",
        )
        cls.visit_module = _load_local_module(
            LOCAL / "apps/visit/map_encounter_to_visit_candidate.py",
            "local_visit_candidate_parity",
        )
        cls.omop = _load_local_module(LOCAL / "common/omop.py", "local_omop_constants_parity")
        cls.visit_contract_bytes = (
            CONTRACTS / "omop/visit-class-v1.json"
        ).read_bytes()
        cls.local_visit_profile = json.loads(cls.visit_contract_bytes)

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def setUp(self):
        patient = {
            **_base_record("patient"), "source_record_id": "patient-one",
            "birth_date": date(1990, 5, 16), "gender_code": "M",
            "race_code": "white", "ethnicity_code": "nonhispanic",
        }
        self.patients = _canonical_frame(self.spark, "patient", [patient])
        encounters = []
        for name, klass in (("visit-one", "ambulatory"), ("visit-two", "inpatient")):
            encounters.append({
                **_base_record("encounter"), "source_encounter_id": name,
                "source_person_id": "patient-one",
                "start_datetime": datetime(2026, 11, 5, 10, tzinfo=timezone.utc),
                "end_datetime": datetime(2026, 11, 5, 11, tzinfo=timezone.utc),
                "encounter_class": klass, "source_code": "synthetic-code",
                "source_description": "synthetic-visit",
            })
        self.encounters = _canonical_frame(self.spark, "encounter", encounters)
        self.ids = self.spark.createDataFrame(
            [("PERSON", HOSPITAL, SOURCE, "patient-one", 12345)],
            "entity_type string, hospital_id string, source_system string, "
            "source_business_key string, omop_id int",
        )
        local_class = self.local_visit_profile["class_to_visit_concept"]
        self.profile = {
            "mapping_name": "synthetic-local-parity-NOT-CLINICALLY-APPROVED",
            "mapping_version": "test-only",
            "source_system": SOURCE,
            "gender_concepts": dict(self.omop.GENDER_CONCEPTS),
            "race_concepts": dict(self.omop.RACE_CONCEPTS),
            "ethnicity_concepts": dict(self.omop.ETHNICITY_CONCEPTS),
            "visit_class_concepts":
                {code: row["concept_id"] for code, row in local_class.items()},
            "visit_type_concept_id":
                self.local_visit_profile["visit_type_concept_id"],
        }
        self.raw_profile = json.dumps(
            self.profile, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.concepts = self.spark.createDataFrame(
            [(cid, "S", None) for cid in sorted(
                {self.profile["visit_type_concept_id"]} |
                set(self.profile["gender_concepts"].values()) |
                set(self.profile["race_concepts"].values()) |
                set(self.profile["ethnicity_concepts"].values()) |
                set(self.profile["visit_class_concepts"].values())
            )],
            "concept_id int, standard_concept string, invalid_reason string",
        )
        self.approval = {
            "status": "SILVER_APPROVED",
            "source_batch_id": BATCH,
            "manifest_sha256": MANIFEST_SHA,
            "processing_version": "synthetic-parity-only",
            "publication_id": "synthetic-approval-not-physical",
            "patient_count": 1, "encounter_count": 2, "quarantine_count": 0,
        }

    def shared(self, **updates):
        params = dict(
            patients=self.patients, encounters=self.encounters,
            identity_map=self.ids, concepts=self.concepts,
            approval=self.approval, hospital_id=HOSPITAL, source_system=SOURCE,
            source_batch_id=BATCH, manifest_sha256=MANIFEST_SHA,
            processing_version="synthetic-parity-only",
            mapping_profile_bytes=self.raw_profile,
            mapping_profile_sha256=hashlib.sha256(self.raw_profile).hexdigest(),
            raw_publish_run_id="synthetic-raw-only",
        )
        params.update(updates)
        return build_omop_candidates(**params)

    def local_person(self, patients=None, identity_map=None):
        # Execute the same pure projection that Local main() invokes.
        # No Local main(), JDBC, physical write, or identity allocation.
        local_ids = (self.ids if identity_map is None else identity_map).select(
            F.col("source_business_key").alias("source_person_id"),
            F.col("omop_id").alias("person_id"),
        )
        joined = (
            (self.patients if patients is None else patients).alias("p")
            .join(local_ids.alias("m"),
                  F.col("p.source_record_id") == F.col("m.source_person_id"),
                  "left")
        )
        return self.person_module.map_joined_patient_to_person(joined)

    def local_visit(self, encounters=None):
        # Only the legacy *pure* function is called; never Local main()/JDBC.
        persons = self.ids.select(
            "source_system",
            F.col("source_business_key").alias("source_person_id"),
            F.col("omop_id").alias("person_id"),
        )
        return self.visit_module.map_encounter_to_candidate(
            self.encounters if encounters is None else encounters,
            persons,
            self.local_visit_profile,
            {
                "mapping_contract_sha256":
                    hashlib.sha256(self.visit_contract_bytes).hexdigest(),
                "raw_publish_run_id": "synthetic-raw-only",
            },
        )

    def test_visit_all_columns_and_rows_equal_to_real_local_transform(self):
        shared = self.shared().visit
        local = self.local_visit()
        self.assertEqual(shared.columns, local.columns)
        self.assertEqual(shared.schema, local.schema)
        self.assertEqual(shared.count(), 2)
        self.assertEqual(local.exceptAll(shared).count(), 0)
        self.assertEqual(shared.exceptAll(local).count(), 0)

    def test_all_approved_legacy_visit_classes_have_matching_rows(self):
        # Real Local v1 profile drives this coverage, including home/virtual.
        classes = sorted(self.local_visit_profile["class_to_visit_concept"])
        cases = []
        for idx, klass in enumerate(classes):
            cases.append({
                **_base_record("encounter"),
                "source_encounter_id": f"all-class-{idx}",
                "source_person_id": "patient-one",
                "start_datetime": datetime(2026, 11, 5, 10, tzinfo=timezone.utc),
                "end_datetime": datetime(2026, 11, 5, 11, tzinfo=timezone.utc),
                "encounter_class": klass,
                "source_code": "synthetic-code",
                "source_description": "synthetic-only",
            })
        frame = _canonical_frame(self.spark, "encounter", cases)
        result = self.shared(
            encounters=frame,
            approval={**self.approval, "encounter_count": len(classes)},
        ).visit
        legacy = self.local_visit(frame)
        self.assertEqual(result.columns, legacy.columns)
        self.assertEqual(result.count(), len(classes))
        self.assertEqual(legacy.exceptAll(result).count(), 0)
        self.assertEqual(result.exceptAll(legacy).count(), 0)
        self.assertEqual(
            {r.encounter_class: r.visit_concept_id for r in result.collect()},
            {key: row["concept_id"] for key, row in
             self.local_visit_profile["class_to_visit_concept"].items()},
        )

    def test_replay_is_identical_without_storage_or_id_assignment(self):
        one, two = self.shared().visit, self.shared().visit
        self.assertEqual(one.exceptAll(two).count(), 0)
        self.assertEqual(two.exceptAll(one).count(), 0)
        local_one, local_two = self.local_visit(), self.local_visit()
        self.assertEqual(local_one.exceptAll(local_two).count(), 0)
        self.assertEqual(local_two.exceptAll(local_one).count(), 0)

    def test_person_full_schema_and_all_rows_equal_real_local_transform(self):
        shared = self.shared().person
        local = self.local_person()
        contract = json.loads(
            (CONTRACTS / "omop/person-v5.4.json").read_text(encoding="utf-8")
        )
        self.assertEqual(shared.columns, [f["name"] for f in contract["fields"]])
        self.assertEqual(shared.columns, local.columns)
        self.assertEqual(shared.schema, local.schema)
        self.assertEqual(shared.count(), 1)
        self.assertEqual(local.exceptAll(shared).count(), 0)
        self.assertEqual(shared.exceptAll(local).count(), 0)
        row = shared.first()
        self.assertEqual(row.person_id, 12345)
        self.assertEqual(row.gender_concept_id, self.omop.GENDER_CONCEPTS["M"])
        self.assertEqual(row.race_concept_id, self.omop.RACE_CONCEPTS["white"])
        self.assertEqual(row.ethnicity_concept_id,
                         self.omop.ETHNICITY_CONCEPTS["nonhispanic"])

    def test_person_all_legacy_demographic_combinations_and_replay(self):
        # Cross product covers 2 gender × 4 race × 2 ethnicity code paths.
        records, ids = [], []
        combinations = [
            (gender, race, ethnicity)
            for gender in sorted(self.omop.GENDER_CONCEPTS)
            for race in sorted(self.omop.RACE_CONCEPTS)
            for ethnicity in sorted(self.omop.ETHNICITY_CONCEPTS)
        ]
        self.assertEqual(len(combinations), 16)
        for idx, (gender, race, ethnicity) in enumerate(combinations):
            key = f"patient-combo-{idx:02d}"
            records.append({
                **_base_record("patient"), "source_record_id": key,
                "birth_date": date(1980 + idx, (idx % 12) + 1, (idx % 27) + 1),
                "gender_code": gender, "race_code": race,
                "ethnicity_code": ethnicity,
            })
            ids.append(("PERSON", HOSPITAL, SOURCE, key, 40001 + idx))
        patients = _canonical_frame(self.spark, "patient", records)
        identity = self.spark.createDataFrame(
            ids, self.ids.schema
        )
        shared = self.shared(
            patients=patients, identity_map=identity,
            approval={**self.approval, "patient_count": len(records)},
        ).person
        local = self.local_person(patients=patients, identity_map=identity)
        self.assertEqual(shared.schema, local.schema)
        self.assertEqual(shared.count(), len(records))
        self.assertEqual(local.count(), len(records))
        self.assertEqual(local.exceptAll(shared).count(), 0)
        self.assertEqual(shared.exceptAll(local).count(), 0)
        replay = self.shared(
            patients=patients, identity_map=identity,
            approval={**self.approval, "patient_count": len(records)},
        ).person
        self.assertEqual(shared.exceptAll(replay).count(), 0)
        self.assertEqual(replay.exceptAll(shared).count(), 0)

    def test_unknown_person_gender_fails_closed_before_shared_candidate(self):
        bad = self.patients.withColumn("gender_code", F.lit("UNKNOWN"))
        self.assertEqual(
            self.local_person(patients=bad)
            .filter(F.col("gender_concept_id").isNull()).count(), 1
        )
        with self.assertRaisesRegex(ValueError, "G5_UNKNOWN_MAPPING_CODE:gender_code"):
            self.shared(patients=bad)

    def test_unknown_visit_class_is_fail_closed_by_shared(self):
        unknown = self.encounters.withColumn("encounter_class", F.lit("unknown"))
        self.assertEqual(
            self.local_visit(unknown).filter(F.col("visit_concept_id").isNull()).count(), 2
        )
        with self.assertRaisesRegex(ValueError, "G5_UNKNOWN_MAPPING_CODE:encounter_class"):
            self.shared(encounters=unknown)

    def test_foreign_hospital_identity_is_rejected_by_shared(self):
        foreign = self.ids.withColumn("hospital_id", F.lit("hospital-b"))
        with self.assertRaisesRegex(ValueError, "G5_STABLE_PERSON_ID_NOT_FOUND"):
            self.shared(identity_map=foreign)

    def test_missing_standard_concept_fails_before_candidate(self):
        without_standard = self.concepts.withColumn("standard_concept", F.lit("C"))
        with self.assertRaisesRegex(ValueError, "G5_OMOP_STANDARD_CONCEPT"):
            self.shared(concepts=without_standard)


if __name__ == "__main__":
    unittest.main()
