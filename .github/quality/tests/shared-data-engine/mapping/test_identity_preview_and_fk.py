"""Synthetic-only F2 identity proposal and multi-entity FK contract tests.

Uses the existing Fabric pure F2 allocator as the sole allocation algorithm.
No cloud service, real patients, IDs from real Warehouses or SQL writes.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))

from identity_plan import IdentityKey, plan_ids
from healthcare_data_engine.identity.preview import (
    IdentityPreview, IdentityPreviewHold, IdentitySnapshot, PersistedIdentity,
    PlannedIdentity, bridge_f2_person_visit_allocation, adapt_person_visit_allocation_preview,
    verify_allocation_proposal,
    require_preview_snapshot_unchanged,
)
from healthcare_data_engine.identity.references import (
    ReferenceHold, resolve_declared_dependencies, resolve_parent_reference,
)
from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, DerivedRowKey, EntityDefinition, EntityRegistry,
    OmopTarget,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
PERSON = "cdm.person"
VISIT = "cdm.visit_occurrence"


def legacy_key(kind="PERSON", hospital="hospital-a", key="p1"):
    return IdentityKey(kind, hospital, "synthetic:" + hospital + ":fhir", key)


def derived(kind="PERSON", hospital="hospital-a", key="p1"):
    source = "synthetic:" + hospital + ":fhir"
    return DerivedRowKey(PERSON if kind == "PERSON" else VISIT, hospital, source, key)


def snapshot(*, existing=(), next_person=1, next_visit=1, gold_person=(),
             gold_visit=(), ledger=SHA_A, readback=SHA_B,
             registry=DEFAULT_OMOP_REGISTRY):
    return IdentitySnapshot(
        tuple(PersistedIdentity(key, number) for key, number in existing),
        ((PERSON, next_person), (VISIT, next_visit)),
        ((PERSON, tuple(gold_person)), (VISIT, tuple(gold_visit))),
        ledger, readback, registry,
    )


def plan(snapshot_state, keys):
    legacy_existing = tuple(
        (IdentityKey("PERSON" if row.key.target_table == PERSON else "VISIT_OCCURRENCE",
                     row.key.hospital_id, row.key.source_system,
                     row.key.source_business_key), row.omop_id)
        for row in snapshot_state.existing
    )
    legacy_plan = plan_ids(
        tuple(keys), legacy_existing,
        {"PERSON": dict(snapshot_state.next_free)[PERSON],
         "VISIT_OCCURRENCE": dict(snapshot_state.next_free)[VISIT]},
        {"PERSON": dict(snapshot_state.gold_ids)[PERSON],
         "VISIT_OCCURRENCE": dict(snapshot_state.gold_ids)[VISIT]},
    )
    return adapt_person_visit_allocation_preview(legacy_plan, snapshot_state)


def condition_registry():
    p, v = DEFAULT_OMOP_REGISTRY.definitions
    child = EntityDefinition(
        "condition_occurrence", "1", "condition", SHA_A, "condition_mapper",
        (OmopTarget("cdm.condition_occurrence", "condition_occurrence_id"),),
        dependencies=("person", "visit_occurrence"),
        publication_group="clinical_facts",
    )
    return EntityRegistry((p, v, child))


class SnapshotAndIdentityPreviewTests(unittest.TestCase):
    def test_semantic_preview_adapter_is_exact_legacy_callable(self):
        import healthcare_data_engine as engine
        self.assertIs(
            adapt_person_visit_allocation_preview,
            bridge_f2_person_visit_allocation,
        )
        self.assertIs(
            engine.adapt_person_visit_allocation_preview,
            engine.bridge_f2_person_visit_allocation,
        )


    def test_first_person_visit_batch_id_preview_not_commit(self):
        state = snapshot()
        result = plan(state, [legacy_key(), legacy_key("VISIT_OCCURRENCE", key="v1")])
        self.assertEqual(result.status, "ID_PREVIEW_ONLY_NOT_PERSISTED")
        self.assertEqual(result.for_key(derived()).state, "PROVISIONAL")
        self.assertEqual(result.for_key(derived("VISIT_OCCURRENCE", key="v1")).omop_id, 1)
        self.assertEqual(dict(result.next_free), {PERSON: 2, VISIT: 2})
        self.assertEqual(result.snapshot_fingerprint, state.fingerprint)

    def test_persisted_plus_new_keeps_existing_int(self):
        state = snapshot(existing=((derived(), 44),), next_person=45, gold_person=(44,))
        result = plan(state, [legacy_key(), legacy_key(key="p2")])
        self.assertEqual((result.for_key(derived()).omop_id,
                          result.for_key(derived()).state), (44, "PERSISTED"))
        self.assertEqual((result.for_key(derived(key="p2")).omop_id,
                          result.for_key(derived(key="p2")).state), (45, "PROVISIONAL"))
        self.assertEqual(dict(result.next_free)[PERSON], 46)

    def test_full_snapshot_fingerprint_deterministic_and_sensitive_to_drift(self):
        a = snapshot(existing=((derived(), 1),
                               (derived("VISIT_OCCURRENCE", key="v1"), 3)),
                     next_person=2, next_visit=4, gold_person=(1,), gold_visit=(3,))
        b = snapshot(existing=tuple((entry.key, entry.omop_id) for entry in reversed(a.existing)), next_person=2, next_visit=4,
                     gold_person=(1,), gold_visit=(3,))
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertNotEqual(a.fingerprint, replace(a, ledger_sha256=SHA_B).fingerprint)
        self.assertNotEqual(a.fingerprint, replace(a, readback_sha256=SHA_A).fingerprint)

    def test_changed_ledger_or_readback_invalidates_preview(self):
        original = snapshot()
        planned = plan(original, [legacy_key()])
        self.assertIs(require_preview_snapshot_unchanged(planned, original), planned)
        with self.assertRaisesRegex(IdentityPreviewHold, "SNAPSHOT_CHANGED_BEFORE_COMMIT"):
            require_preview_snapshot_unchanged(
                planned, replace(original, ledger_sha256=SHA_B))
        with self.assertRaisesRegex(IdentityPreviewHold, "SNAPSHOT_CHANGED_BEFORE_COMMIT"):
            require_preview_snapshot_unchanged(
                planned, replace(original, readback_sha256=SHA_A))

    def test_replay_is_persisted_not_reallocated(self):
        initial = snapshot()
        result = plan(initial, [legacy_key()])
        persisted = snapshot(existing=((derived(), 1),), next_person=2, gold_person=(1,))
        replay = plan(persisted, [legacy_key()])
        self.assertEqual(result.for_key(derived()).omop_id,
                         replay.for_key(derived()).omop_id)
        self.assertEqual(replay.for_key(derived()).state, "PERSISTED")
        self.assertEqual(dict(replay.next_free)[PERSON], 2)

    def test_two_hospitals_same_source_key_get_distinct_ids(self):
        state = snapshot(existing=((derived(), 1),), next_person=2, gold_person=(1,))
        result = plan(state, [legacy_key(hospital="hospital-b")])
        self.assertEqual(result.for_key(derived(hospital="hospital-b")).omop_id, 2)

    def test_snapshot_rejects_map_gold_drift_duplicate_ids_and_counter_rewind(self):
        with self.assertRaisesRegex(IdentityPreviewHold, "MAP_GOLD_DRIFT"):
            snapshot(existing=((derived(), 1),), next_person=2)
        with self.assertRaisesRegex(IdentityPreviewHold, "PERSISTED_ID_COLLISION"):
            snapshot(existing=((derived(), 1), (derived(key="p2"), 1)),
                     gold_person=(1,))
        with self.assertRaisesRegex(IdentityPreviewHold, "ALLOCATOR_REWIND"):
            snapshot(existing=((derived(), 1),), gold_person=(1,))
        with self.assertRaisesRegex(IdentityPreviewHold, "SNAPSHOT_INCOMPLETE"):
            replace(snapshot(), next_free=((PERSON, 1),))
        with self.assertRaisesRegex(IdentityPreviewHold, "SNAPSHOT_SHA_NOT_PINNED"):
            replace(snapshot(), ledger_sha256="bad")

    def test_casefold_keys_fail_even_if_explicit_spellings_differ(self):
        with self.assertRaisesRegex(IdentityPreviewHold, "PERSISTED_KEY_COLLISION"):
            snapshot(existing=((derived(key="p1"), 1),
                               (derived(key="P1"), 2)),
                     next_person=3, gold_person=(1, 2))
        state = snapshot()
        assigned = ((derived(key="p1"), 1), (derived(key="P1"), 2))
        with self.assertRaisesRegex(IdentityPreviewHold, "PROPOSAL_KEY_COLLISION"):
            verify_allocation_proposal(state, assigned, assigned, {PERSON: 3, VISIT: 1})

    def test_proposal_rejects_reassigned_old_id_and_invalid_counter(self):
        state = snapshot(existing=((derived(), 3),), gold_person=(3,), next_person=4)
        with self.assertRaisesRegex(IdentityPreviewHold, "PERSISTED_ID_CHANGED"):
            verify_allocation_proposal(state, ((derived(), 4),), (),
                                       {PERSON: 4, VISIT: 1})
        with self.assertRaisesRegex(IdentityPreviewHold, "PROPOSED_COUNTER_DRIFT"):
            verify_allocation_proposal(snapshot(), ((derived(), 55),),
                                       ((derived(), 55),), {PERSON: 56, VISIT: 1})
        with self.assertRaisesRegex(IdentityPreviewHold, "PROPOSED_COUNTER_DRIFT"):
            verify_allocation_proposal(snapshot(), ((derived(), 1),),
                                       ((derived(), 1),), {PERSON: 999, VISIT: 1})

    def test_exceeded_int_or_bool_not_accepted(self):
        with self.assertRaisesRegex(IdentityPreviewHold, "INT_RANGE_INVALID"):
            PersistedIdentity(derived(), True)
        with self.assertRaisesRegex(IdentityPreviewHold, "INT_RANGE_INVALID"):
            snapshot(next_person=2_147_483_649)
        with self.assertRaisesRegex(IdentityPreviewHold, "INT_RANGE_INVALID"):
            verify_allocation_proposal(snapshot(next_person=2_147_483_648),
                ((derived(), 2_147_483_648),),
                ((derived(), 2_147_483_648),),
                {PERSON: 2_147_483_649, VISIT: 1})

    def test_bridge_rejects_unreviewed_target_or_broken_proposal(self):
        result = plan_ids([legacy_key()], (), {"PERSON": 1, "VISIT_OCCURRENCE": 1},
                          {"PERSON": [], "VISIT_OCCURRENCE": []})
        with self.assertRaisesRegex(IdentityPreviewHold, "F2_SCOPE_PERSON_VISIT_ONLY"):
            future = condition_registry()
            extra = IdentitySnapshot(
                (), ((PERSON, 1), (VISIT, 1), ("cdm.condition_occurrence", 1)),
                ((PERSON, ()), (VISIT, ()), ("cdm.condition_occurrence", ())),
                SHA_A, SHA_B, future)
            bridge_f2_person_visit_allocation(result, extra)
        with self.assertRaisesRegex(IdentityPreviewHold, "F2_COUNTERS_INVALID"):
            broken = replace(result, next_free=(("UNKNOWN", 2),))
            bridge_f2_person_visit_allocation(broken, snapshot())

    def test_arbitrary_third_target_plan_can_be_checked_not_allocated(self):
        reg = condition_registry()
        state = IdentitySnapshot((), ((PERSON, 1), (VISIT, 1),
                                     ("cdm.condition_occurrence", 1)),
                                 ((PERSON, ()), (VISIT, ()),
                                  ("cdm.condition_occurrence", ())),
                                 SHA_A, SHA_B, reg)
        derived_condition = DerivedRowKey("cdm.condition_occurrence",
                                          "hospital-a", "synthetic:hospital-a:fhir", "c1")
        preview = verify_allocation_proposal(
            state, ((derived_condition, 1),), ((derived_condition, 1),),
            {PERSON: 1, VISIT: 1, "cdm.condition_occurrence": 2})
        self.assertEqual(preview.for_key(derived_condition).state, "PROVISIONAL")
        self.assertNotIn("COMMITTED", preview.status)


class MultiEntityFkTests(unittest.TestCase):
    def test_person_provisional_within_same_group_is_reference_only(self):
        preview = plan(snapshot(), [legacy_key(), legacy_key("VISIT_OCCURRENCE", key="v1")])
        child = derived("VISIT_OCCURRENCE", key="v1")
        result = resolve_parent_reference(
            child_entity="visit_occurrence", child_key=child,
            parent_entity="person", parent_key=derived(),
            identity_preview=preview)
        self.assertEqual(result.omop_id, 1)
        self.assertEqual(result.state, "PROVISIONAL")
        self.assertEqual(result.status, "FK_PREFLIGHT_ONLY_NOT_COMMITTED")

    def test_future_condition_cannot_reference_provisional_base_group(self):
        preview = plan(snapshot(), [legacy_key()])
        reg = condition_registry()
        condition = DerivedRowKey("cdm.condition_occurrence", "hospital-a",
                                  "synthetic:hospital-a:fhir", "c1")
        with self.assertRaisesRegex(ReferenceHold, "PROVISIONAL_PARENT_CROSS_GROUP"):
            resolve_parent_reference(
                registry=reg, child_entity="condition_occurrence",
                child_key=condition, parent_entity="person", parent_key=derived(),
                identity_preview=preview)

    def test_committed_parent_requires_independent_readback_reference(self):
        persisted = snapshot(existing=((derived(), 1),), next_person=2,
                             gold_person=(1,))
        preview = plan(persisted, [legacy_key()])
        reg = condition_registry()
        condition = DerivedRowKey("cdm.condition_occurrence", "hospital-a",
                                  "synthetic:hospital-a:fhir", "c1")
        args = dict(registry=reg, child_entity="condition_occurrence",
                    child_key=condition, parent_entity="person",
                    parent_key=derived(), identity_preview=preview)
        with self.assertRaisesRegex(ReferenceHold, "COMMITTED_PARENT_READBACK_REQUIRED"):
            resolve_parent_reference(**args)
        resolved = resolve_parent_reference(**args, committed_readback_sha256=SHA_B)
        self.assertEqual((resolved.state, resolved.omop_id), ("PERSISTED", 1))

    def test_cross_hospital_or_source_reference_holds(self):
        preview = plan(snapshot(), [legacy_key()])
        with self.assertRaisesRegex(ReferenceHold, "CROSS_HOSPITAL_OR_SOURCE"):
            resolve_parent_reference(
                child_entity="visit_occurrence",
                child_key=derived("VISIT_OCCURRENCE", hospital="hospital-b", key="v1"),
                parent_entity="person", parent_key=derived(),
                identity_preview=preview)

    def test_missing_required_and_undeclared_parent_rejected(self):
        preview = plan(snapshot(), [legacy_key()])
        with self.assertRaisesRegex(ReferenceHold, "REQUIRED_PARENT_MISSING"):
            resolve_parent_reference(
                child_entity="visit_occurrence",
                child_key=derived("VISIT_OCCURRENCE", key="v1"),
                parent_entity="person", parent_key=None,
                identity_preview=preview)
        with self.assertRaisesRegex(ReferenceHold, "UNDECLARED_DEPENDENCY"):
            resolve_parent_reference(
                child_entity="person", child_key=derived(),
                parent_entity="visit_occurrence",
                parent_key=derived("VISIT_OCCURRENCE", key="v1"),
                identity_preview=preview)

    def test_all_declared_parents_must_be_present(self):
        preview = plan(snapshot(), [legacy_key()])
        reg = condition_registry()
        condition = DerivedRowKey("cdm.condition_occurrence", "hospital-a",
                                  "synthetic:hospital-a:fhir", "c1")
        with self.assertRaisesRegex(ReferenceHold, "DEPENDENCY_SET_INCOMPLETE"):
            resolve_declared_dependencies(
                registry=reg, child_entity="condition_occurrence",
                child_key=condition, references={"person": derived()},
                identity_preview=preview)

    def test_missing_parent_identity_and_spoofed_snapshot_holds(self):
        preview = plan(snapshot(), [legacy_key()])
        with self.assertRaisesRegex(ReferenceHold, "PARENT_ID_NOT_IN_PREVIEW"):
            resolve_parent_reference(
                child_entity="visit_occurrence",
                child_key=derived("VISIT_OCCURRENCE", key="v1"),
                parent_entity="person", parent_key=derived(key="unknown"),
                identity_preview=preview)
        modified = replace(preview, identities=(replace(
            preview.identities[0], snapshot_fingerprint=SHA_A),))
        with self.assertRaisesRegex(ReferenceHold, "IDENTITY_SNAPSHOT_CONFLICT"):
            resolve_parent_reference(
                child_entity="visit_occurrence",
                child_key=derived("VISIT_OCCURRENCE", key="v1"),
                parent_entity="person", parent_key=derived(),
                identity_preview=modified)


if __name__ == "__main__":
    unittest.main()
