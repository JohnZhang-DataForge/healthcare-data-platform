"""Source-only F2 Silver identity bridging (no Blob, SQL, Spark or Gold writes)."""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "azure-fabric/warehouse/omop-foundation/writer"))
from identity_plan import PlanningHold
from silver_identity import (
    plan_silver_identity, bridge_f2_sql_readback_rows,
    plan_silver_identity_with_f2_bridge,
)
import hashlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] /
                       "shared-data-engine/src"))


SHA = "a" * 64


def fixture(*, hospital="atlanta-hospital-a", people=100, visits=5918):
    source = "synthea-fhir:" + hospital + ":fhir-r4"
    batch = "g4-frozen-test-batch"
    patient = [
        {"source_system": source, "source_batch_id": batch,
         "source_record_id": "patient-%04d" % i} for i in range(people)
    ]
    encounter = [
        {"source_system": source, "source_batch_id": batch,
         "source_encounter_id": "encounter-%05d" % i,
         "source_person_id": "patient-%04d" % (i % people)}
        for i in range(visits)
    ]
    approval = {
        "status": "SILVER_APPROVED", "source_batch_id": batch,
        "manifest_sha256": SHA, "processing_version": "fhir-silver-canonical-v1:engine-0.1.1",
        "publication_id": "independently-verified-fixture-only",
        "patient_count": people, "encounter_count": visits,
    }
    return dict(
        patients=patient, encounters=encounter, hospital_id=hospital,
        source_system=source, source_batch_id=batch, approval=approval,
        physical_readback_verified=True, quarantine_zero_verified=True,
        existing=(), next_free={"PERSON": 1, "VISIT_OCCURRENCE": 1},
        gold_ids={"PERSON": [], "VISIT_OCCURRENCE": []},
    )


class SilverToOmopIdentityPreview(unittest.TestCase):
    def test_100_patients_5918_encounters_approved_preview(self):
        preview = plan_silver_identity(**fixture())
        self.assertEqual(preview.status, "F2_ID_PREVIEW_ONLY_NOT_PERSISTED")
        self.assertEqual((len(preview.persons), len(preview.visits)), (100, 5918))
        self.assertEqual(preview.persons[0], ("patient-0000", 1))
        self.assertEqual(preview.visits[0], ("encounter-00000", 1, 1))
        self.assertEqual(preview.visits[-1], ("encounter-05917", 5918, 18))
        self.assertEqual(dict(preview.allocation.next_free),
                         {"PERSON": 101, "VISIT_OCCURRENCE": 5919})
        self.assertEqual(len(preview.allocation.inserted), 6018)

    def test_key_order_does_not_change_ids(self):
        args = fixture(people=4, visits=8)
        a = plan_silver_identity(**args)
        b = plan_silver_identity(**{
            **args,
            "patients": list(reversed(args["patients"])),
            "encounters": list(reversed(args["encounters"])),
        })
        self.assertEqual(a, b)

    def test_existing_committed_map_replay_does_not_reallocate(self):
        original = fixture(people=3, visits=7)
        a = plan_silver_identity(**original)
        existing = a.allocation.assigned
        gold = {
            kind: [omop_id for key, omop_id in existing if key.entity_type == kind]
            for kind in ("PERSON", "VISIT_OCCURRENCE")
        }
        replay = plan_silver_identity(**{
            **original, "existing": existing, "gold_ids": gold,
            "next_free": dict(a.allocation.next_free),
        })
        self.assertEqual((replay.persons, replay.visits), (a.persons, a.visits))
        self.assertEqual(replay.allocation.inserted, ())

    def test_same_business_keys_different_hospital_get_global_distinct_ids(self):
        first = plan_silver_identity(**fixture(hospital="hospital-a", people=1, visits=1))
        past = first.allocation.assigned
        gold = {
            kind: [omop_id for key, omop_id in past if key.entity_type == kind]
            for kind in ("PERSON", "VISIT_OCCURRENCE")
        }
        second = plan_silver_identity(**{
            **fixture(hospital="hospital-b", people=1, visits=1),
            "existing": past, "gold_ids": gold,
            "next_free": dict(first.allocation.next_free),
        })
        self.assertEqual(second.persons, (("patient-0000", 2),))
        self.assertEqual(second.visits, (("encounter-00000", 2, 2),))

    def test_unverified_silver_or_quarantine_never_grants_id_preview(self):
        for update in (
            {"physical_readback_verified": False},
            {"quarantine_zero_verified": False},
            {"physical_readback_verified": 1},
        ):
            with self.subTest(update=update):
                with self.assertRaisesRegex(
                    PlanningHold, "SILVER_PHYSICAL_APPROVAL_OR_DQ_NOT_VERIFIED"
                ):
                    plan_silver_identity(**{**fixture(people=1, visits=1), **update})

    def test_approval_drift_or_unsupported_status_holds(self):
        args = fixture(people=2, visits=3)
        for change in (
            {"status": "SILVER_DENIED"}, {"patient_count": 1},
            {"encounter_count": 2}, {"manifest_sha256": "broken"},
            {"source_batch_id": "other"}, {"publication_id": ""},
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(PlanningHold, "SILVER_APPROVAL_COUNTS_OR_HASH"):
                    plan_silver_identity(**{
                        **args, "approval": {**args["approval"], **change}
                    })

    def test_foreign_parent_and_source_namespace_holds(self):
        args = fixture(people=2, visits=3)
        wrong_parent = [dict(x) for x in args["encounters"]]
        wrong_parent[0]["source_person_id"] = "foreign-person"
        with self.assertRaisesRegex(PlanningHold, "SILVER_ENCOUNTER_PERSON_FK_MISSING"):
            plan_silver_identity(**{**args, "encounters": wrong_parent})
        wrong_scope = [dict(x) for x in args["patients"]]
        wrong_scope[0]["source_system"] = "synthea-fhir:hospital-b:fhir-r4"
        with self.assertRaisesRegex(PlanningHold, "SILVER_CANONICAL_NAMESPACE"):
            plan_silver_identity(**{**args, "patients": wrong_scope})
        with self.assertRaisesRegex(PlanningHold, "SILVER_HOSPITAL_NAMESPACE"):
            plan_silver_identity(**{**args, "hospital_id": "hospital-b"})

    def test_duplicate_and_casefold_identity_holds(self):
        args = fixture(people=2, visits=3)
        # Keep all Encounter FKs valid, so duplicate/collation is the first hold.
        args["encounters"] = [
            {**row, "source_person_id": "patient-0000"} for row in args["encounters"]
        ]
        with self.assertRaisesRegex(PlanningHold, "DUPLICATE_SOURCE"):
            plan_silver_identity(**{
                **args, "patients": [args["patients"][0]] * 2,
            })
        # Same source key under case-insensitive Warehouse collation.
        upper = [dict(row) for row in args["patients"]]
        upper[1]["source_record_id"] = upper[0]["source_record_id"].upper()
        with self.assertRaisesRegex(PlanningHold, "SOURCE_COLLATION_COLLISION"):
            plan_silver_identity(**{**args, "patients": upper})

    def test_mapping_gold_snapshot_drift_and_allocator_rewind_hold(self):
        args = fixture(people=2, visits=3)
        a = plan_silver_identity(**args)
        past = a.allocation.assigned
        with self.assertRaisesRegex(PlanningHold, "MAP_GOLD_PARTIAL_OR_DRIFT"):
            plan_silver_identity(**{
                **args, "existing": past, "next_free": dict(a.allocation.next_free),
            })
        gold = {
            kind: [omop_id for key, omop_id in past if key.entity_type == kind]
            for kind in ("PERSON", "VISIT_OCCURRENCE")
        }
        with self.assertRaisesRegex(PlanningHold, "ALLOCATOR_REWIND"):
            plan_silver_identity(**{
                **args, "existing": past, "gold_ids": gold,
                "next_free": {"PERSON": 1, "VISIT_OCCURRENCE": 1},
            })




# Real six-table SELECT-shaped rows but entirely SYNTHETIC fixtures. This
# validates the one existing F2 plan + Shared preview against a physical
# readback SHAPE; it is not an authenticated Silver/Warehouse cloud receipt.
def f2_bridge(rows=None):
    names = ("identity_map", "allocator", "person", "visit", "ledger", "audit")
    if rows is None:
        rows = {name: () for name in names}
    hashes = {}
    import json
    for name in names:
        digest = hashlib.sha256()
        for row in rows[name]:
            encoded = json.dumps(tuple(row), ensure_ascii=False,
                                 separators=(",", ":"), default=str).encode("utf-8")
            digest.update(len(encoded).to_bytes(4, "big") + encoded)
        hashes[name] = digest.hexdigest()
    return bridge_f2_sql_readback_rows(
        rows, first_table_sha256=hashes, second_table_sha256=hashes,
        warehouse_id="7a6d08da-278d-4603-8a3b-28640110984c")


def with_bridge(arguments=None, *, physical_bridge=None):
    d = fixture() if arguments is None else dict(arguments)
    d["physical_silver_readback_verified"] = d.pop("physical_readback_verified")
    for key in ("existing", "next_free", "gold_ids"):
        d.pop(key)
    d["physical_bridge"] = f2_bridge() if physical_bridge is None else physical_bridge
    return d


class F2PhysicalSharedG4SilverPreviewTests(unittest.TestCase):
    def test_100_5918_synthetic_silver_reuses_exact_single_planner(self):
        args = with_bridge()
        outcome = plan_silver_identity_with_f2_bridge(**args)
        old = plan_silver_identity(**fixture())
        self.assertEqual(outcome.silver, old)
        self.assertEqual(len(outcome.shared.identities), 6018)
        self.assertEqual((len(outcome.silver.persons), len(outcome.silver.visits)),
                         (100, 5918))
        self.assertEqual(outcome.shared.snapshot_fingerprint,
                         outcome.shared_snapshot_fingerprint)
        self.assertEqual({x.state for x in outcome.shared.identities},
                         {"PROVISIONAL"})
        self.assertFalse(outcome.candidate_write_authorized)
        self.assertFalse(outcome.gold_committed)
        self.assertEqual(outcome.status, "F2_G4_TO_SHARED_SOURCE_PREVIEW_NOT_RELEASED")

    def test_reverse_order_and_repeated_preview_are_stable(self):
        args = with_bridge(fixture(people=3, visits=9))
        original = plan_silver_identity_with_f2_bridge(**args)
        replay = plan_silver_identity_with_f2_bridge(
            **{**args, "patients": list(reversed(args["patients"])),
               "encounters": list(reversed(args["encounters"]))})
        self.assertEqual(original.silver, replay.silver)
        self.assertEqual(original.shared, replay.shared)
        self.assertEqual(original.physical_snapshot_sha256,
                         replay.physical_snapshot_sha256)

    def test_persisted_first_hospital_and_provisional_second_hospital(self):
        old = fixture(hospital="hospital-a", people=1, visits=1)
        rows = {
            "identity_map": (
                ("PERSON", "hospital-a", old["source_system"],
                 "patient-0000", 41, "frozen-b", "v1"),
                ("VISIT_OCCURRENCE", "hospital-a", old["source_system"],
                 "encounter-00000", 90, "frozen-b", "v1"),
            ),
            "allocator": (("PERSON", 42, "v1"), ("VISIT_OCCURRENCE", 91, "v1")),
            "person": ((41,),),
            "visit": ((90, 41),),
            "ledger": (),
            "audit": (),
        }
        bridge = f2_bridge(rows)
        same = plan_silver_identity_with_f2_bridge(
            **with_bridge(old, physical_bridge=bridge))
        self.assertEqual(same.silver.persons, (("patient-0000", 41),))
        self.assertEqual(same.silver.visits, (("encounter-00000", 90, 41),))
        self.assertEqual({x.state for x in same.shared.identities}, {"PERSISTED"})
        second = plan_silver_identity_with_f2_bridge(
            **with_bridge(fixture(hospital="hospital-b", people=1, visits=1),
                          physical_bridge=bridge))
        self.assertEqual(second.silver.persons, (("patient-0000", 42),))
        self.assertEqual(second.silver.visits, (("encounter-00000", 91, 42),))
        self.assertEqual({x.state for x in second.shared.identities},
                         {"PROVISIONAL"})

    def test_silver_physical_dq_and_approval_are_still_required(self):
        args = with_bridge(fixture(people=1, visits=1))
        for changed in (
            {"physical_silver_readback_verified": False},
            {"quarantine_zero_verified": False},
            {"approval": {**args["approval"], "status": "QUARANTINED"}},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(PlanningHold):
                    plan_silver_identity_with_f2_bridge(**{**args, **changed})

    def test_missing_or_fake_snapshot_bridge_fails_before_id_plan(self):
        args = with_bridge(fixture(people=1, visits=1))
        from dataclasses import replace
        for tampered in (None, "sha-only", replace(
                args["physical_bridge"], physical_snapshot_sha256="f" * 5)):
            with self.subTest(bridge=type(tampered).__name__):
                with self.assertRaisesRegex(PlanningHold,
                                            "F2_SHARED_SNAPSHOT_BRIDGE_INVALID"):
                    plan_silver_identity_with_f2_bridge(
                        **{**args, "physical_bridge": tampered})

    def test_unknown_f2_allocator_or_map_gold_mismatch_holds(self):
        rows = {name: () for name in
                ("identity_map", "allocator", "person", "visit", "ledger", "audit")}
        rows["person"] = ((41,),)
        with self.assertRaisesRegex(PlanningHold, "ALLOCATOR_MISSING_WITH_STATE"):
            f2_bridge(rows)

if __name__ == "__main__":
    unittest.main()
