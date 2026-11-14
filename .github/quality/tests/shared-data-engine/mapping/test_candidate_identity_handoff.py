"""G5/F2 pure Preview -> Candidate handoff (synthetic identities only).

This uses the existing Fabric F2 algorithm and the Shared 0.1.5 verified
AllocationPlan bridge. No cloud, SparkSession, Person/Visit Gold or PHI.
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
    IdentitySnapshot, PersistedIdentity, adapt_person_visit_allocation_preview,
)
from healthcare_data_engine.identity.candidate_handoff import (
    CandidateIdentityHold, plan_candidate_identity_handoff,
)
from healthcare_data_engine.mapping.omop.registry import DerivedRowKey

SHA_A = "a" * 64
SHA_B = "b" * 64
PERSON = "cdm.person"
VISIT = "cdm.visit_occurrence"


def fixture(*, hospital="hospital-a", people=2, visits=4):
    source = f"synthetic:{hospital}:fhir-r4"
    batch = "fhir-synthetic-test-batch"
    patient = [dict(source_system=source, source_batch_id=batch,
                    source_record_id=f"patient-{i:04d}") for i in range(people)]
    encounter = [dict(source_system=source, source_batch_id=batch,
                      source_encounter_id=f"encounter-{i:05d}",
                      source_person_id=f"patient-{i % people:04d}",
                      encounter_class="ambulatory") for i in range(visits)]
    approval = dict(status="SILVER_APPROVED", source_batch_id=batch,
                    manifest_sha256=SHA_A,
                    processing_version="synthetic-fhir-v1",
                    publication_id="synthetic-approved-not-physical-proof",
                    patient_count=people, encounter_count=visits,
                    quarantine_count=0)
    return dict(patients=patient, encounters=encounter, approval=approval,
                hospital_id=hospital, source_system=source,
                source_batch_id=batch, manifest_sha256=SHA_A,
                processing_version="synthetic-fhir-v1")


def legacy_key(table, hospital, system, business):
    return IdentityKey(
        "PERSON" if table == PERSON else "VISIT_OCCURRENCE",
        hospital, system, business)


def to_derived(key):
    return DerivedRowKey(
        PERSON if key.entity_type == "PERSON" else VISIT,
        key.hospital_id, key.source_system, key.source_business_key)


def state_with_preview(rows, existing=(), next_free=None):
    # existing = sequence of (legacy IdentityKey, stable persisted OMOP INT)
    next_free = next_free or {"PERSON": 1, "VISIT_OCCURRENCE": 1}
    gold = {
        kind: [value for key, value in existing if key.entity_type == kind]
        for kind in ("PERSON", "VISIT_OCCURRENCE")
    }
    current = IdentitySnapshot(
        tuple(PersistedIdentity(to_derived(key), value)
              for key, value in existing),
        tuple(sorted((PERSON if kind == "PERSON" else VISIT, next_free[kind])
                     for kind in next_free)),
        ((PERSON, tuple(gold["PERSON"])), (VISIT, tuple(gold["VISIT_OCCURRENCE"]))),
        SHA_A, SHA_B)
    incoming = [
        legacy_key(PERSON, rows["hospital_id"], rows["source_system"],
                   patient["source_record_id"])
        for patient in rows["patients"]
    ] + [
        legacy_key(VISIT, rows["hospital_id"], rows["source_system"],
                   encounter["source_encounter_id"])
        for encounter in rows["encounters"]
    ]
    plan = plan_ids(incoming, existing, next_free, gold)
    preview = adapt_person_visit_allocation_preview(plan, current)
    return current, preview


def prepare(rows, *, persisted=(), counters=None):
    snapshot, preview = state_with_preview(rows, persisted, counters)
    return plan_candidate_identity_handoff(**rows, snapshot=snapshot, preview=preview)


class F2CandidateIdentityHandoffTests(unittest.TestCase):
    def test_first_batch_uses_provisional_1_2_without_persisting(self):
        result = prepare(fixture())
        self.assertEqual(result.status,
                         "G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED")
        self.assertEqual(len(result.batch_persons), 2)
        self.assertEqual(len(result.batch_visits), 4)
        self.assertEqual({x.state for x in result.batch_persons},
                         {"PROVISIONAL"})
        self.assertEqual({x.state for x in result.batch_visits},
                         {"PROVISIONAL"})
        self.assertEqual([x.visit_occurrence_id for x in result.batch_visits],
                         [1, 2, 3, 4])
        self.assertEqual({x.person_id for x in result.batch_visits}, {1, 2})
        self.assertEqual({row[0] for row in result.person_lookup_rows()}, {"PERSON"})
        self.assertEqual({row[5] for row in result.person_lookup_rows()},
                         {"PROVISIONAL"})
        self.assertEqual({x[3] for x in result.visit_id_rows()}, {"PROVISIONAL"})
        self.assertFalse(hasattr(result, "commit"))

    def test_f2_exact_replay_uses_old_persisted_ids(self):
        rows = fixture(people=1, visits=1)
        old = (
            (legacy_key(PERSON, rows["hospital_id"], rows["source_system"],
                        "patient-0000"), 7),
            (legacy_key(VISIT, rows["hospital_id"], rows["source_system"],
                        "encounter-00000"), 19),
        )
        result = prepare(rows, persisted=old,
                         counters={"PERSON": 8, "VISIT_OCCURRENCE": 20})
        self.assertEqual(result.batch_persons[0].person_id, 7)
        self.assertEqual(result.batch_visits[0].visit_occurrence_id, 19)
        self.assertEqual(result.batch_visits[0].person_id, 7)
        self.assertEqual(result.batch_persons[0].state, "PERSISTED")
        self.assertEqual(result.batch_visits[0].state, "PERSISTED")

    def test_full_snapshot_includes_other_hospitals_and_does_not_reallocate(self):
        other = fixture(hospital="hospital-b", people=1, visits=1)
        prior = ((legacy_key(PERSON, other["hospital_id"],
                             other["source_system"], "patient-0000"), 1),)
        current = fixture(hospital="hospital-a", people=1, visits=1)
        result = prepare(current, persisted=prior,
                         counters={"PERSON": 2, "VISIT_OCCURRENCE": 1})
        self.assertEqual(result.batch_persons[0].person_id, 2)
        self.assertEqual({item.person_id for item in result.person_lookup}, {1, 2})
        self.assertEqual(
            len({row[1] for row in result.person_lookup_rows()}), 2)

    def test_100_5918_source_keys_are_linear_and_counted(self):
        result = prepare(fixture(people=100, visits=5918))
        self.assertEqual((len(result.batch_persons), len(result.batch_visits)),
                         (100, 5918))
        self.assertEqual(result.batch_visits[-1].visit_occurrence_id, 5918)
        self.assertEqual({x.parent_state for x in result.batch_visits},
                         {"PROVISIONAL"})
        self.assertEqual(len({x.visit_occurrence_id for x in result.batch_visits}),
                         5918)

    def test_input_order_changes_do_not_change_business_ids(self):
        args = fixture(people=3, visits=7)
        original = prepare(args)
        shuffled = prepare({**args, "patients": list(reversed(args["patients"])),
                            "encounters": list(reversed(args["encounters"]))})
        self.assertEqual(original, shuffled)

    def test_denied_approval_or_quarantine_holds(self):
        args = fixture()
        for changed in (
            {"status": "SILVER_DENIED"},
            {"quarantine_count": 1},
            {"patient_count": 1},
            {"encounter_count": 5},
            {"source_batch_id": "other"},
            {"manifest_sha256": SHA_B},
            {"processing_version": "another"},
            {"publication_id": ""},
        ):
            with self.subTest(change=changed):
                broken = {**args, "approval": {**args["approval"], **changed}}
                state, plan = state_with_preview(broken)
                with self.assertRaisesRegex(CandidateIdentityHold,
                                            "APPROVAL_NOT_MATCHED"):
                    plan_candidate_identity_handoff(
                        **broken, snapshot=state, preview=plan)

    def test_manifest_and_processing_namespace_inputs_must_match(self):
        args = fixture()
        state, plan = state_with_preview(args)
        for broken in ({"manifest_sha256": SHA_B},
                       {"processing_version": "another"},
                       {"source_batch_id": "another"}):
            with self.subTest(change=broken):
                with self.assertRaises(CandidateIdentityHold):
                    plan_candidate_identity_handoff(
                        **{**args, **broken}, snapshot=state, preview=plan)

    def test_wrong_hospital_in_namespace_holds(self):
        args = fixture()
        state, plan = state_with_preview(args)
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "SOURCE_NAMESPACE_MISMATCH"):
            plan_candidate_identity_handoff(
                **{**args, "hospital_id": "hospital-b"},
                snapshot=state, preview=plan)

    def test_source_batch_or_hospital_drift_in_individual_row_holds(self):
        args = fixture()
        state, plan = state_with_preview(args)
        wrong = [dict(x) for x in args["patients"]]
        wrong[0]["source_system"] = "synthetic:hospital-b:fhir-r4"
        with self.assertRaisesRegex(CandidateIdentityHold, "SOURCE_ROW_SCOPE_DRIFT"):
            plan_candidate_identity_handoff(
                **{**args, "patients": wrong}, snapshot=state, preview=plan)

    def test_foreign_visit_parent_does_not_resolve(self):
        args = fixture()
        state, plan = state_with_preview(args)
        wrong = [dict(x) for x in args["encounters"]]
        wrong[0]["source_person_id"] = "foreign-person"
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "PARENT_PERSON_NOT_IN_SILVER"):
            plan_candidate_identity_handoff(
                **{**args, "encounters": wrong}, snapshot=state, preview=plan)

    def test_duplicate_source_patient_and_visit_casefold_holds(self):
        for target, name in (("patients", "source_record_id"),
                             ("encounters", "source_encounter_id")):
            args = fixture()
            state, plan = state_with_preview(args)
            rows = [dict(x) for x in args[target]]
            rows[1][name] = rows[0][name].upper()
            diagnostic = ("DUPLICATE_PERSON_SOURCE" if target == "patients"
                          else "DUPLICATE_VISIT_SOURCE")
            with self.subTest(target=target):
                with self.assertRaisesRegex(CandidateIdentityHold, diagnostic):
                    plan_candidate_identity_handoff(
                        **{**args, target: rows}, snapshot=state, preview=plan)

    def test_omop_person_source_and_visit_class_never_silently_truncated(self):
        args = fixture()
        state, plan = state_with_preview(args)
        long_p = [dict(x) for x in args["patients"]]
        long_p[0]["source_record_id"] = "p" * 51
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "PERSON_SOURCE_VALUE_LENGTH"):
            plan_candidate_identity_handoff(
                **{**args, "patients": long_p}, snapshot=state, preview=plan)
        long_v = [dict(x) for x in args["encounters"]]
        long_v[0]["encounter_class"] = "v" * 51
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "VISIT_SOURCE_VALUE_LENGTH"):
            plan_candidate_identity_handoff(
                **{**args, "encounters": long_v}, snapshot=state, preview=plan)

    def test_changed_snapshot_digest_holds_even_when_ids_look_same(self):
        args = fixture()
        state, plan = state_with_preview(args)
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "SNAPSHOT_CHANGED_OR_INVALID"):
            plan_candidate_identity_handoff(
                **args, snapshot=replace(state, ledger_sha256=SHA_B),
                preview=plan)

    def test_missing_or_extra_plan_rows_hold(self):
        args = fixture()
        state, plan = state_with_preview(args)
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "VISIT_ID_NOT_FOUND"):
            plan_candidate_identity_handoff(
                **args, snapshot=state,
                preview=replace(plan, identities=plan.identities[:-1]))
        extra = replace(plan, identities=plan.identities + (plan.identities[0],))
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "DUPLICATE_OR_DRIFTED_ID"):
            plan_candidate_identity_handoff(
                **args, snapshot=state, preview=extra)

    def test_forged_duplicate_target_ints_hold_even_if_source_keys_differ(self):
        args = fixture(people=2, visits=4)
        state, plan = state_with_preview(args)
        visit_items = [i for i, x in enumerate(plan.identities)
                       if x.key.target_table == VISIT]
        self.assertGreaterEqual(len(visit_items), 2)
        bad = list(plan.identities)
        bad[visit_items[1]] = replace(
            bad[visit_items[1]], omop_id=bad[visit_items[0]].omop_id)
        with self.assertRaisesRegex(CandidateIdentityHold, "TARGET_ID_COLLISION"):
            plan_candidate_identity_handoff(
                **args, snapshot=state,
                preview=replace(plan, identities=tuple(bad)))

    def test_spoofed_persisted_without_snapshot_mapping_holds(self):
        args = fixture()
        state, plan = state_with_preview(args)
        false_persisted = replace(
            plan, identities=tuple(replace(item, state="PERSISTED")
                                   for item in plan.identities))
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "UNBACKED_PERSISTED_ID"):
            plan_candidate_identity_handoff(
                **args, snapshot=state, preview=false_persisted)

    def test_unexpected_target_or_planner_scope_holds(self):
        args = fixture()
        state, plan = state_with_preview(args)
        wrong = replace(
            plan.identities[0],
            key=replace(plan.identities[0].key,
                        target_table="cdm.condition_occurrence"))
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "UNEXPECTED_TARGET"):
            plan_candidate_identity_handoff(
                **args, snapshot=state,
                preview=replace(plan, identities=(wrong,) + plan.identities[1:]))

    def test_future_derived_role_not_silently_inferred(self):
        args = fixture()
        state, plan = state_with_preview(args)
        wrong = replace(
            plan.identities[0],
            key=replace(plan.identities[0].key,
                        derived_role="secondary",
                        derived_discriminator="role-1"))
        with self.assertRaisesRegex(CandidateIdentityHold,
                                    "DERIVED_KEY_UNSUPPORTED"):
            plan_candidate_identity_handoff(
                **args, snapshot=state,
                preview=replace(plan, identities=(wrong,) + plan.identities[1:]))


if __name__ == "__main__":
    unittest.main()
