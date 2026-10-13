import unittest
from task004_step04b_replay_contract import Batch, Conflict, Retryable, Store, digest

BID = "task004-airflow-task004-step03e-38324111846"
ROOT = "s3a://health-processing/source=synthea/batch_id=" + BID
def batch(sha="a"*64, name=BID):
    root="s3a://health-processing/source=synthea/batch_id="+name
    return Batch(name,sha,"synthea",root+"/entity=patient/",root+"/entity=encounter/")
def row(k, entity="person", payload=None, parent="p1", bid=BID):
    value={"source_id":k,"source_batch_id":bid,"payload":payload or {"code":"valid"}}
    if entity=="visit":value["source_person_id"]=parent
    return value

class Contract(unittest.TestCase):
    def setUp(self):
        self.db=Store()
        self.b=batch()
        self.db.register(self.b)
    def person(self):
        self.db.prepare(self.b,"person",[row("p1")])
        return self.db.commit(self.b,"person")
    def test_A1_new_person_then_visit(self):
        self.assertEqual(self.person(),1)
        self.db.prepare(self.b,"visit",[row("v1","visit")])
        self.assertEqual(self.db.commit(self.b,"visit"),1)
        self.assertTrue(self.db.reconcile(self.b,"visit"))
    def test_A2_same_batch_noop_and_stable_ids(self):
        self.person()
        original=self.db.person[("synthea","p1")].copy()
        self.assertEqual(self.person(),0)
        self.assertEqual(self.db.person[("synthea","p1")],original)
    def test_A3_retry_before_commit(self):
        self.db.prepare(self.b,"person",[row("p1")])
        self.assertEqual(self.db.commit(self.b,"person"),1)
        self.assertEqual(self.db.commit(self.b,"person"),0)
    def test_A4_visit_failure_person_preserved(self):
        self.person()
        self.db.prepare(self.b,"visit",[row("v1","visit",parent="absent")])
        with self.assertRaises(Conflict):self.db.commit(self.b,"visit")
        self.assertEqual(len(self.db.person),1)
        self.assertEqual(len(self.db.visit),0)
        self.db.prepare(self.b,"visit",[row("v1","visit",parent="absent")])
    def test_A5_unknown_commit_requires_readback(self):
        self.db.prepare(self.b,"person",[row("p1")])
        with self.assertRaisesRegex(Retryable,"unknown"):
            self.db.commit(self.b,"person",simulate_unknown_commit=True)
        self.assertTrue(self.db.reconcile(self.b,"person"))
        self.assertEqual(self.db.commit(self.b,"person"),0)
    def test_A6_same_batch_manifest_conflict(self):
        with self.assertRaises(Conflict):self.db.register(batch("b"*64))
    def test_A7_cross_batch_same_business_key_same_content(self):
        self.person()
        other=batch("c"*64,"other-batch")
        self.db.register(other)
        self.db.prepare(other,"person",[row("p1",bid=other.batch_id)])
        self.assertEqual(self.db.commit(other,"person"),0)
    def test_A8_cross_batch_conflicting_content(self):
        self.person()
        other=batch("c"*64,"other-batch")
        self.db.register(other)
        self.db.prepare(other,"person",[row("p1",payload={"code":"different"},bid=other.batch_id)])
        with self.assertRaises(Conflict):self.db.commit(other,"person")
    def test_A9_simulated_concurrency_lock(self):
        self.db.prepare(self.b,"person",[row("p1")])
        self.db.acquire(BID)
        with self.assertRaises(Retryable):self.db.commit(self.b,"person")
        self.db.release(BID)
        self.assertEqual(self.db.commit(self.b,"person"),1)
    def test_A10_historic_protected_on_conflict(self):
        original={"id":113,"fingerprint":digest({"code":"historical"})}
        self.db.person[("synthea","historic")]=original.copy()
        self.db.prepare(self.b,"person",[row("new"),row("historic")])
        with self.assertRaises(Conflict):self.db.commit(self.b,"person")
        self.assertEqual(self.db.person[("synthea","historic")],original)
        self.assertNotIn(("synthea","new"),self.db.person)
    def test_A11_reconciliation_independent_snapshot(self):
        self.person()
        self.db.person[("synthea","p1")]["fingerprint"]="tampered"
        with self.assertRaises(Conflict):self.db.reconcile(self.b,"person")
    def test_visit_cannot_run_before_person(self):
        self.db.prepare(self.b,"visit",[row("v1","visit")])
        with self.assertRaises(Retryable):self.db.commit(self.b,"visit")
    def test_stage_same_batch_changed_payload_rejected(self):
        self.db.prepare(self.b,"person",[row("p1")])
        with self.assertRaises(Conflict):
            self.db.prepare(self.b,"person",[row("p1",payload={"code":"changed"})])
    def test_duplicate_source_key_rejected(self):
        with self.assertRaises(Conflict):self.db.prepare(self.b,"person",[row("p1"),row("p1")])
    def test_replay_stage_wrong_batch_rejected(self):
        with self.assertRaises(Conflict):
            self.db.prepare(self.b,"person",[row("p1",bid="not-this-batch")])
if __name__=="__main__":unittest.main()
