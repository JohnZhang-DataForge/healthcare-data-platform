"""Eight NEW synthetic FHIR R4 resources through Canonical to OMOP Candidate.

Exercises the same Shared Engine mappings as the business pipeline with a
synthetic, explicitly nonclinical concept fixture and externally supplied
synthetic identity map. No Delta writes, Fabric, Gold grants, ID allocation,
or assertion about real Vocabulary/clinical approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from healthcare_data_engine.canonical.validation import accepted_dataframe
from healthcare_data_engine.mapping.omop.candidates import build_omop_candidates
from test_semantic_migration_fhir_eight import canonicalize, source_context

ROOT = Path(__file__).resolve().parents[5]


class SyntheticFhirToOmopCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]")
                     .appName("semantic-fhir-omop-candidate")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.session.timeZone", "UTC")
                     .getOrCreate())

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def setUp(self):
        self.context = source_context("semantic-migration-20261115-business-candidate")
        _, reconciled = canonicalize(self.context)
        self.assertEqual(reconciled.metrics["patient_accepted"], 4)
        self.assertEqual(reconciled.metrics["encounter_accepted"], 4)
        self.patients = accepted_dataframe(
            self.spark, reconciled.patient.accepted,
            self._contract("patient-v1.json"))
        self.encounters = accepted_dataframe(
            self.spark, reconciled.encounter.accepted,
            self._contract("encounter-v1.json"))
        self.source_system = self.context.namespaced_source_system

        patient_rows = reconciled.patient.accepted
        encounter_rows = reconciled.encounter.accepted
        # Synthetic-only test concepts. Never substitute for a physical,
        # independently reviewed OMOP Standard Concept / Vocabulary lookup.
        concepts = {
            "gender_concepts": {
                value: (8507, 8532)[i] for i, value in enumerate(
                    sorted({p["gender_code"] for p in patient_rows}))},
            "race_concepts": {
                value: (8527, 8516, 8515, 8657)[i]
                for i, value in enumerate(
                    sorted({p["race_code"] for p in patient_rows}))},
            "ethnicity_concepts": {
                value: 38003564 for value in
                sorted({p["ethnicity_code"] for p in patient_rows})},
            "visit_class_concepts": {
                value: (9202, 9201)[i] for i, value in enumerate(
                    sorted({e["encounter_class"] for e in encounter_rows}))},
        }
        self.profile = {
            "mapping_name": "eight-synthetic-resources-not-for-clinical-use",
            "mapping_version": "semantic-api-regression",
            "source_system": self.source_system,
            **concepts,
            "visit_type_concept_id": 32827,
        }
        self.profile_bytes = json.dumps(
            self.profile, sort_keys=True, separators=(",", ":")).encode()
        self.profile_sha256 = hashlib.sha256(self.profile_bytes).hexdigest()
        self.identities = self.spark.createDataFrame(
            [("PERSON", self.context.hospital_id, self.source_system,
              row["source_record_id"], 300001+i)
             for i, row in enumerate(sorted(
                 patient_rows, key=lambda x: x["source_record_id"]))],
            "entity_type string, hospital_id string, source_system string, "
            "source_business_key string, omop_id int",
        )
        all_ids = {32827}
        for group in concepts.values():
            all_ids.update(group.values())
        self.concept_df = self.spark.createDataFrame(
            [(id_value, "S", None) for id_value in sorted(all_ids)],
            "concept_id int, standard_concept string, invalid_reason string",
        )
        self.approval = {
            "status": "SILVER_APPROVED",
            "source_batch_id": self.context.source_batch_id,
            "manifest_sha256": self.context.manifest_sha256,
            "processing_version": self.context.processing_version,
            "publication_id": "synthetic-approval-not-physically-published",
            "patient_count": 4, "encounter_count": 4, "quarantine_count": 0,
        }

    @staticmethod
    def _contract(name):
        from healthcare_data_engine import load_pinned_contract
        expected = "patient" if name.startswith("patient") else "encounter"
        return load_pinned_contract(
            (ROOT / "local-data-platform/spark/contracts/canonical" / name).read_bytes(),
            expected)

    def candidate(self, **updates):
        args = {
            "patients": self.patients,
            "encounters": self.encounters,
            "identity_map": self.identities,
            "concepts": self.concept_df,
            "approval": self.approval,
            "hospital_id": self.context.hospital_id,
            "source_system": self.source_system,
            "source_batch_id": self.context.source_batch_id,
            "manifest_sha256": self.context.manifest_sha256,
            "processing_version": self.context.processing_version,
            "mapping_profile_bytes": self.profile_bytes,
            "mapping_profile_sha256": self.profile_sha256,
            "raw_publish_run_id": "synthetic-readonly-run-20261115",
        }
        args.update(updates)
        return build_omop_candidates(**args)

    def test_eight_fhir_resources_produce_four_person_and_four_visit_candidates(self):
        a = self.candidate()
        self.assertEqual(a.status, "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED")
        self.assertEqual((a.person_count, a.visit_count), (4, 4))
        self.assertEqual(a.person.count(), 4)
        self.assertEqual(a.visit.count(), 4)
        person_ids = {p.person_id for p in a.person.select("person_id").collect()}
        self.assertEqual(person_ids, {300001, 300002, 300003, 300004})
        self.assertEqual(
            {v.person_id for v in a.visit.select("person_id").collect()},
            person_ids)
        self.assertEqual(a.person.filter(F.col("person_id").isNull()).count(), 0)
        self.assertEqual(a.visit.filter(F.col("person_id").isNull()).count(), 0)
        self.assertEqual(a.mapping_sha256, self.profile_sha256)

    def test_replay_is_deterministic_and_missing_identity_fails_closed(self):
        a, b = self.candidate(), self.candidate()
        self.assertEqual(a.person.exceptAll(b.person).count(), 0)
        self.assertEqual(a.visit.exceptAll(b.visit).count(), 0)
        missing = self.identities.filter(F.col("omop_id") != 300004)
        with self.assertRaisesRegex(
                ValueError, "CANDIDATE_STABLE_PERSON_ID_NOT_FOUND"):
            self.candidate(identity_map=missing)
        with self.assertRaisesRegex(ValueError, "OMOP_STANDARD_CONCEPT"):
            self.candidate(concepts=self.concept_df.filter(
                F.col("concept_id") != 32827))


if __name__ == "__main__":
    unittest.main()
