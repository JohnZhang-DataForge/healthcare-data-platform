"""F2 pure planner + negative replay/namespace/allocator cases."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "writer"))
from identity_plan import (MAX_ID, IdentityKey, BatchFence, Receipt, PlanningHold, plan_ids, replay)

def person(h="hospital-A", key="patient-1"):
    return IdentityKey("PERSON", h, "fhir_r4", key)

def visit(h="hospital-A", key="encounter-1"):
    return IdentityKey("VISIT_OCCURRENCE", h, "fhir_r4", key)

def plan(keys, old=(), nextid=None, gold=None):
    if nextid is None: nextid={"PERSON":1, "VISIT_OCCURRENCE":1}
    if gold is None: gold={"PERSON":[], "VISIT_OCCURRENCE":[]}
    return plan_ids(keys, old, nextid, gold)

def batch(sha="a"*64):
    return BatchFence("hospital-A","fhir_r4","G4-request-100",sha,"b"*64,"f2-v1",100,5918)

class F2PlannerTest(unittest.TestCase):
    def test_cross_hospital_distinct_and_repeatable(self):
        keys=[person("hospital-B"), visit(), person()]
        a=plan(keys)
        self.assertEqual(a,plan(list(reversed(keys))))
        got=dict(a.assigned)
        self.assertEqual(got[person()],1)
        self.assertEqual(got[person("hospital-B")],2)
        self.assertEqual(got[visit()],1)
        self.assertEqual(dict(a.next_free),{"PERSON":3,"VISIT_OCCURRENCE":2})

    def test_existing_source_id_never_changes(self):
        k=person()
        result=plan([k,person("hospital-B")],[(k,123)],
                    nextid={"PERSON":124,"VISIT_OCCURRENCE":1},
                    gold={"PERSON":[123],"VISIT_OCCURRENCE":[]})
        self.assertEqual(dict(result.assigned)[k],123)
        self.assertEqual(dict(result.assigned)[person("hospital-B")],124)
        self.assertEqual(len(result.inserted),1)

    def test_duplicate_and_collation_key_hold(self):
        with self.assertRaisesRegex(PlanningHold,"DUPLICATE_SOURCE"):
            plan([person(),person()])
        with self.assertRaisesRegex(PlanningHold,"SOURCE_COLLATION_COLLISION"):
            plan([person(key="UPPER"),person(key="upper")])
        with self.assertRaises(PlanningHold):
            plan([person()],old=[(person(key="UPPER"),1),(person(key="upper"),2)],
                 nextid={"PERSON":3,"VISIT_OCCURRENCE":1},
                 gold={"PERSON":[1,2],"VISIT_OCCURRENCE":[]})

    def test_missing_keys_and_incorrect_entity(self):
        for value in ("", " key ", "bad\nkey", "x"*257):
            with self.assertRaises(PlanningHold):
                person(key=value)
        with self.assertRaises(PlanningHold):
            IdentityKey("UNKNOWN","h","fhir_r4","id")

    def test_identity_collision_partial_gold_or_allocator_rewind_hold(self):
        a=person()
        b=person("hospital-B")
        for old,physical,n in [
            ([(a,1),(b,1)],[1],3),
            ([(a,1)],[2],3),
            ([(a,1)],[],3),
            ([(a,1)],[1],1),
        ]:
            with self.assertRaises(PlanningHold):
                plan([b],old,nextid={"PERSON":n,"VISIT_OCCURRENCE":1},
                     gold={"PERSON":physical,"VISIT_OCCURRENCE":[]})

    def test_int_limit_and_invalid_counter(self):
        with self.assertRaisesRegex(PlanningHold,"INT_OVERFLOW"):
            plan([person(),person("hospital-B")],
                 nextid={"PERSON":MAX_ID,"VISIT_OCCURRENCE":1})
        self.assertEqual(dict(plan([person()],
            nextid={"PERSON":MAX_ID,"VISIT_OCCURRENCE":1}).next_free)["PERSON"],MAX_ID+1)
        for bad in (0,True,MAX_ID+2):
            with self.assertRaises(PlanningHold):
                plan([person()],nextid={"PERSON":bad,"VISIT_OCCURRENCE":1})

    def test_exact_ledger_replay(self):
        f=batch()
        self.assertEqual(replay(f,[],independently_verified=False),"NEW")
        receipt=Receipt(f,"COMMITTED",100,5918)
        self.assertEqual(replay(f,[receipt],independently_verified=True),"VERIFIED_SKIP")
        with self.assertRaisesRegex(PlanningHold,"GOLD_READBACK_REQUIRED"):
            replay(f,[receipt],independently_verified=False)
        with self.assertRaisesRegex(PlanningHold,"CONFLICTING_BATCH_HASH_OR_COUNTS"):
            replay(f,[Receipt(batch(sha="c"*64),"COMMITTED",100,5918)],
                   independently_verified=True)
        for rows in ([Receipt(f,"STARTED",None,None)],
                     [Receipt(f,"COMMITTED",100,5917)],
                     [receipt,receipt]):
            with self.assertRaises(PlanningHold):
                replay(f,rows,independently_verified=True)

    def test_unknown_hash_and_fake_count(self):
        with self.assertRaises(PlanningHold):
            batch(sha="not-a-sha")
        with self.assertRaises(PlanningHold):
            BatchFence("h","fhir_r4","b","a"*64,"b"*64,"v1",True,0)

if __name__=="__main__":
    unittest.main()
