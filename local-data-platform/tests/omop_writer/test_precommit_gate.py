"""Deterministic NEW_ONLY source/PG pre-commit decision tests (no DB needed)."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT/"airflow"/"dags"))
sys.path.insert(0,str(ROOT/"apps"/"omop_writer"))
from task004_cdm_materialization_plan import plan
from task004_cdm_dynamic_adapters import digest
from precommit_gate import validate_input,inspect_new_only,PrecommitBlocked


def context(batch="task004-airflow-gate-test-01"):
    pre="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+batch+"/"
    return plan({"state":"HANDOFF_VERIFIED_NOT_LOADED",
     "cdm_write_permitted":False,"batch_id":batch,"manifest_sha256":"a"*64,
     "source_version":"v3.3.0",
     "manifest_uri":"s3://health-landing/"+pre+"manifest.json",
     "person_processing_uri":"s3a://health-processing/"+pre+"entity=patient/run_id=1/data/",
     "visit_processing_uri":"s3a://health-processing/"+pre+"entity=encounter/run_id=2/data/",
     "person_rows":1,"visit_rows":1})


def row(key,kind,parent=None):
    payload={"gender_concept_id":8507} if kind=="person" else {"visit_concept_id":9202}
    r={"source_key":key,"canonical_payload":payload}
    if kind=="visit":r["source_person_key"]=parent
    r["row_fingerprint"]=digest({"source_person_key":parent,"payload":payload})
    return r


class Cursor:
    def __init__(self,mode="on",role="cdm_reader",privilege=False,
                 historical=0,persons=0,visits=0,claim=None):
        self.mode=mode;self.role=role;self.privilege=privilege
        self.historical=historical;self.persons=persons;self.visits=visits
        self.claim=claim;self.reads=0;self.queries=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,args=None):
        self.queries.append((sql,args))
        if not sql.lstrip().startswith("SELECT"):raise AssertionError("DML in read-only precommit gate")
    def fetchone(self):
        q=self.queries[-1][0]
        if "current_setting" in q:return self.role,self.mode
        if "has_table_privilege" in q:return self.privilege,
        if "task004_batch_ledger" in q:return self.historical,
        if "person_id_map" in q:return self.persons,
        if "visit_occurrence_id_map" in q:return self.visits,
        if "landing_batch_ledger" in q:return self.claim
        raise AssertionError(q)
class Conn:
    def __init__(self,**kw):self.cur=Cursor(**kw)
    def cursor(self):return self.cur

class GateTests(unittest.TestCase):
    def setUp(self):
        self.c=context()
        self.p=[row("synthea-unique-person","person")]
        self.v=[row("synthea-unique-visit","visit","synthea-unique-person")]

    def test_new_only_safe_candidate_requires_no_collision(self):
        db=Conn()
        result=inspect_new_only(db,self.c,self.p,self.v)
        self.assertEqual(result.status,"READY_TO_CLAIM")
        self.assertFalse(result.commit_authorized)
        self.assertEqual(result.claim_status,"ABSENT")
        self.assertEqual(len(db.cur.queries),6)

    def test_rejects_historical_ledger(self):
        with self.assertRaisesRegex(PrecommitBlocked,"HISTORIC_BATCH"):
            inspect_new_only(Conn(historical=1),self.c,self.p,self.v)

    def test_rejects_existing_person_or_visit_source_ids(self):
        for kw in ({"persons":1},{"visits":1},{"persons":1,"visits":1}):
            with self.subTest(kw=kw),self.assertRaisesRegex(PrecommitBlocked,"SOURCE_KEY_COLLISION"):
                inspect_new_only(Conn(**kw),self.c,self.p,self.v)

    def test_rejects_writer_role_or_missing_readonly(self):
        for kw in ({"role":"cdm_writer"},{"mode":"off"},{"privilege":True}):
            with self.subTest(kw=kw),self.assertRaises(PrecommitBlocked):
                inspect_new_only(Conn(**kw),self.c,self.p,self.v)

    def test_rejects_claim_drift(self):
        with self.assertRaisesRegex(PrecommitBlocked,"CLAIM_MANIFEST_IDENTITY_DRIFT"):
            inspect_new_only(Conn(claim=("b"*64,self.c["manifest_uri"],"PROCESSING",True)),
                             self.c,self.p,self.v)

    def test_requires_claim_only_on_strict_mode(self):
        with self.assertRaisesRegex(PrecommitBlocked,"LIVE_EXCLUSIVE_CLAIM_REQUIRED"):
            inspect_new_only(Conn(),self.c,self.p,self.v,require_claim=True)
        rec=(self.c["manifest_sha256"],self.c["manifest_uri"],"PROCESSING",True)
        result=inspect_new_only(Conn(claim=rec),self.c,self.p,self.v,require_claim=True)
        self.assertEqual(result.status,"READY_TO_LOAD_CHECK")
        self.assertFalse(result.commit_authorized)
        self.assertEqual(result.claim_status,"PROCESSING_LIVE")

    def test_expired_claim_blocked(self):
        rec=(self.c["manifest_sha256"],self.c["manifest_uri"],"PROCESSING",False)
        with self.assertRaisesRegex(PrecommitBlocked,"INCOMPATIBLE_CLAIM_STATUS"):
            inspect_new_only(Conn(claim=rec),self.c,self.p,self.v)

    def test_tampered_plan_fingerprint_and_parent_blocked(self):
        c=dict(self.c);c["manifest_sha256"]="b"*64
        with self.assertRaises(PrecommitBlocked):validate_input(c,self.p,self.v)
        p=[dict(self.p[0])];p[0]["row_fingerprint"]="f"*64
        with self.assertRaisesRegex(PrecommitBlocked,"ROW_FINGERPRINT_DRIFT"):
            validate_input(self.c,p,self.v)
        with self.assertRaisesRegex(PrecommitBlocked,"VISIT_PARENT_NOT_IN_BATCH"):
            validate_input(self.c,self.p,[row("visit","visit","missing-person")])

    def test_no_mutation_anywhere_in_module(self):
        db=Conn()
        inspect_new_only(db,self.c,self.p,self.v)
        self.assertTrue(all(sql.lstrip().startswith("SELECT") for sql,_ in db.cur.queries))

if __name__=="__main__":
    unittest.main()
