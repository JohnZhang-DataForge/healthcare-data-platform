"""Pure, synthetic multi-entity Registry and Person/Visit adapter regression.

No Fabric, Spark, clinical data, external services or Gold writes.
"""
from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from healthcare_data_engine.mapping.omop.candidates import OmopCandidates
from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, DerivedRowKey, EntityDefinition,
    EntityRegistry, EntityRegistryHold, OmopTarget, verify_unique_derived_rows,
)
from healthcare_data_engine.mapping.omop.entity_candidates import (
    adapt_person_visit_candidates, build_registered_person_visit_candidates,
    EntityCandidateSet, TargetCandidate,
)

P = DEFAULT_OMOP_REGISTRY.definition("person")
V = DEFAULT_OMOP_REGISTRY.definition("visit_occurrence")
SHA = "a" * 64


class MultiEntityRegistryTest(unittest.TestCase):
    def test_existing_definitions_and_dependency_order(self):
        self.assertEqual(tuple(d.entity_key for d in
                         DEFAULT_OMOP_REGISTRY.dependency_order(("visit_occurrence",))),
                         ("person", "visit_occurrence"))
        self.assertEqual(P.targets[0].table, "cdm.person")
        self.assertEqual(V.targets[0].primary_key, "visit_occurrence_id")

    def test_missing_and_duplicate_registry_entities_fail_closed(self):
        with self.assertRaisesRegex(EntityRegistryHold, "ENTITY_NOT_REGISTERED"):
            DEFAULT_OMOP_REGISTRY.definition("condition")
        with self.assertRaisesRegex(EntityRegistryHold, "ENTITY_REGISTRY_DUPLICATE_KEY"):
            EntityRegistry((P, P))
        with self.assertRaisesRegex(EntityRegistryHold, "ENTITY_SELECTION_EMPTY"):
            DEFAULT_OMOP_REGISTRY.dependency_order(())

    def test_unknown_dependency_cycle_and_target_collision(self):
        with self.assertRaisesRegex(EntityRegistryHold, "UNKNOWN_DEPENDENCY"):
            EntityRegistry((replace(P, dependencies=("absent",)),))
        with self.assertRaisesRegex(EntityRegistryHold, "DEPENDENCY_CYCLE"):
            EntityRegistry((replace(P, dependencies=("visit_occurrence",)), V))
        with self.assertRaisesRegex(EntityRegistryHold, "TARGET_CONFLICT"):
            EntityRegistry((P, replace(V, targets=(OmopTarget("cdm.person", "visit_occurrence_id"),))))

    def test_multi_target_future_definition_no_person_visit_rewrite(self):
        future = EntityDefinition(
            "clinical_event", "1", "observation", SHA, "clinical_event_mapper",
            (OmopTarget("cdm.measurement", "measurement_id"),
             OmopTarget("cdm.observation", "observation_id")),
            dependencies=("person", "visit_occurrence"),
            publication_group="clinical_facts",
        )
        registry = EntityRegistry((future, V, P))
        self.assertEqual([d.entity_key for d in registry.dependency_order(
            ("clinical_event",))], ["person", "visit_occurrence", "clinical_event"])
        self.assertEqual(P, registry.definition("person"))
        self.assertEqual(len(registry.definition("clinical_event").targets), 2)

    def test_invalid_contract_sha_and_unreviewed_strategy(self):
        with self.assertRaisesRegex(EntityRegistryHold, "SHA_INVALID"):
            replace(P, canonical_contract_sha256="")
        with self.assertRaisesRegex(EntityRegistryHold, "STRATEGY_UNREVIEWED"):
            replace(P, identity_strategy="row_number")
        with self.assertRaisesRegex(EntityRegistryHold, "TARGETS_INVALID"):
            replace(P, targets=(P.targets[0], P.targets[0]))

    def test_derived_row_fanout_deterministic_under_input_order(self):
        keys = [
            DerivedRowKey("cdm.measurement", "hospital-a", "fhir:hospital-a:fhir",
                          "resource-1", "observation", "analyte-a"),
            DerivedRowKey("cdm.measurement", "hospital-a", "fhir:hospital-a:fhir",
                          "resource-1", "observation", "analyte-b"),
            DerivedRowKey("cdm.observation", "hospital-a", "fhir:hospital-a:fhir",
                          "resource-1"),
        ]
        self.assertEqual(set(verify_unique_derived_rows(keys)),
                         set(verify_unique_derived_rows(reversed(keys))))

    def test_derived_row_collision_casefold_and_discriminator(self):
        a = DerivedRowKey("cdm.measurement", "hospital-a", "fhir", "Resource-1")
        b = DerivedRowKey("cdm.measurement", "Hospital-A", "fhir", "resource-1")
        with self.assertRaisesRegex(EntityRegistryHold, "DERIVED_KEY_COLLISION"):
            verify_unique_derived_rows((a, b))
        with self.assertRaisesRegex(EntityRegistryHold, "DISCRIMINATOR_REQUIRED"):
            DerivedRowKey("cdm.measurement", "hospital-a", "fhir", "resource-1", "analyte")
        different_hospital = replace(a, hospital_id="hospital-b")
        self.assertEqual(len(verify_unique_derived_rows((a, different_hospital))), 2)

    def test_persisted_int_is_not_assigned_by_derived_key(self):
        value = DerivedRowKey("cdm.person", "hospital-a", "fhir", "p-1")
        self.assertFalse(hasattr(value, "omop_id"))


class CandidateAdapterTest(unittest.TestCase):
    def setUp(self):
        self.person = object()
        self.visit = object()
        self.legacy = OmopCandidates(self.person, self.visit, SHA, 100, 5918)

    def _wrap(self, **updates):
        kw = dict(source_batch_id="batch-a", manifest_sha256=SHA,
                  processing_version="engine-0.1.1")
        kw.update(updates)
        return adapt_person_visit_candidates(self.legacy, **kw)

    def test_legacy_frames_preserved_without_gold_claim(self):
        candidate = self._wrap()
        self.assertEqual(candidate.status, "ENTITY_CANDIDATE_ONLY_NOT_PUBLISHED")
        self.assertIs(candidate.for_table("cdm.person").rows, self.person)
        self.assertIs(candidate.for_table("cdm.visit_occurrence").rows, self.visit)
        self.assertEqual([t.row_count for t in candidate.targets], [100, 5918])
        self.assertEqual(candidate.for_table("cdm.visit_occurrence").id_state,
                         "VISIT_ID_NOT_ALLOCATED")
        self.assertEqual(candidate.mapping_sha256, SHA)

    def test_unknown_target_and_invalid_provenance(self):
        candidate = self._wrap()
        with self.assertRaisesRegex(EntityRegistryHold, "TARGET_NOT_REGISTERED"):
            candidate.for_table("cdm.condition_occurrence")
        with self.assertRaisesRegex(EntityRegistryHold, "PROVENANCE_INVALID"):
            self._wrap(manifest_sha256="bad")

    def test_legacy_invalid_state_cannot_be_published(self):
        with self.assertRaisesRegex(EntityRegistryHold, "LEGACY_CANDIDATE_NOT_APPROVED"):
            adapt_person_visit_candidates(
                replace(self.legacy, status="GOLD_COMMITTED"),
                source_batch_id="batch-a", manifest_sha256=SHA,
                processing_version="v1")
        with self.assertRaisesRegex(EntityRegistryHold, "CANDIDATE_CANNOT_PUBLISH"):
            replace(self._wrap(), status="GOLD_COMMITTED")

    def test_duplicate_target_and_invalid_row_count(self):
        c = self._wrap()
        with self.assertRaisesRegex(EntityRegistryHold, "DUPLICATE_OR_INVALID_TARGET"):
            replace(c, targets=(c.targets[0], c.targets[0]))
        with self.assertRaisesRegex(EntityRegistryHold, "INVALID_COUNT_OR_ROWS"):
            TargetCandidate("person", "cdm.person", self.person, -1,
                            "EXTERNAL_PERSON_MAP_NOT_GOLD")

    def test_registry_contract_rejection_before_return(self):
        wrong = EntityRegistry((replace(P, targets=(OmopTarget("cdm.death", "death_id"),)), V))
        with self.assertRaisesRegex(EntityRegistryHold, "TARGET_CONTRACT_CONFLICT"):
            self._wrap(registry=wrong)

    def test_registered_path_delegates_to_strict_legacy_mapper(self):
        with patch("healthcare_data_engine.mapping.omop.entity_candidates.build_omop_candidates",
                   return_value=self.legacy) as mapper:
            result = build_registered_person_visit_candidates(
                None, None, None, None,
                approval={"status": "SILVER_APPROVED"}, hospital_id="hospital-a",
                source_system="synthetic:hospital-a:fhir", source_batch_id="batch-a",
                manifest_sha256=SHA, processing_version="v1",
                mapping_profile_bytes=b"{}", mapping_profile_sha256=SHA,
                raw_publish_run_id="synthetic",
            )
        mapper.assert_called_once()
        self.assertIs(result.for_table("cdm.person").rows, self.person)
        self.assertEqual(result.for_table("cdm.visit_occurrence").row_count, 5918)

    def test_old_mapper_failure_propagates_without_approval(self):
        with patch("healthcare_data_engine.mapping.omop.entity_candidates.build_omop_candidates",
                   side_effect=ValueError("G5_UNKNOWN_MAPPING_CODE")):
            with self.assertRaisesRegex(ValueError, "G5_UNKNOWN_MAPPING_CODE"):
                build_registered_person_visit_candidates(
                    None, None, None, None,
                    approval={}, hospital_id="hospital-a",
                    source_system="synthetic:hospital-a:fhir", source_batch_id="batch-a",
                    manifest_sha256=SHA, processing_version="v1",
                    mapping_profile_bytes=b"{}", mapping_profile_sha256=SHA,
                    raw_publish_run_id="synthetic",
                )


if __name__ == "__main__":
    unittest.main()
