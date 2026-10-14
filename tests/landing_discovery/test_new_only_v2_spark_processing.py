"""Dual-manual-opt-in NEW_ONLY v2 Spark Processing-only probe; no Airflow import."""
import ast
import json
import re
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow"/"dags"))
from task004_cdm_preflight_contract import validate_handoff

HELPER=ROOT/"airflow"/"dags"/"landing_spark_processing.py"
DAG=ROOT/"airflow"/"dags"/"landing_batch_discovery.py"
TREE=ast.parse(HELPER.read_text())
F={x.name:x for x in TREE.body if isinstance(x,ast.FunctionDef)}
ns={"json":json,"re":re,"IDENTITY":re.compile(r"^[A-Za-z0-9._-]{1,256}$"),"SHA":re.compile(r"^[0-9a-f]{64}$")}
exec(compile(ast.Module(body=[F["select_verified_processing_replay"],F["processing_gate"]],type_ignores=[]),str(HELPER),"exec"),ns)
select=ns["select_verified_processing_replay"]
gate=ns["processing_gate"]

B="synthea-new-only-gh-38497355290"
SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
U="s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id="+B+"/manifest.json"
ROOT_URI="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id="+B+"/entity="

def inventory():
    return {"status":"READ_ONLY_DISCOVERED","processing_authorized":False,"database_mutation":False,
        "preview_truncated":False,"ready_count":1,"ready_batches_preview":[
        {"batch_id":B,"manifest_uri":U,"manifest_sha256":SHA,"source":"synthea",
         "source_version":"v3.3.0","status":"INTAKE_VERIFIED","file_count":18}]}
def claim(decision="OBSERVED_ONLY"):
    return {"status":"EVALUATED","claim_enabled":False,"claim_count":0,"input_count":1,
            "spark_trigger":False,"omop_business_mutation":False,
            "decisions":[{"batch_id":B,"decision":decision}]}
def config():
    return {"processing_only":True,"new_only_processing_probe":True,
            "batch_id":B,"manifest_uri":U,"manifest_sha256":SHA}
def run(d=None,q=None,conf=None,typ="manual"):
    return select(json.dumps(inventory() if d is None else d),
        json.dumps(claim() if q is None else q),
        json.dumps(config() if conf is None else conf),typ)

def person_visit():
    p={"processing_data_uri":ROOT_URI+"patient/run_id=p1/work/normalized/data/",
       "canonical_rows":1}
    v={"processing_data_uri":ROOT_URI+"encounter/run_id=v1/work/normalized/data/",
       "canonical_rows":812}
    return p,v

class SafeV2Probe(unittest.TestCase):
    def test_explicit_v2_observed_only_allows_spark_no_database(self):
        x=run();self.assertEqual(x["batch_id"],B);self.assertEqual(x["manifest_sha256"],SHA)
        self.assertTrue(x["new_only_processing_probe"]);self.assertFalse(x["omop_business_mutation"])
        self.assertTrue(gate(json.dumps(x)))
        p,v=person_visit()
        h=validate_handoff(x,p,v)
        self.assertEqual(h["person_rows"],1);self.assertEqual(h["visit_rows"],812)
        self.assertFalse(h["cdm_write_permitted"])
    def test_not_automatic_even_with_opt_in(self):
        self.assertIsNone(run(typ="scheduled"))
        self.assertIsNone(run(conf={}))
    def test_double_manual_opt_in_required(self):
        for k,v in (("new_only_processing_probe",False),("new_only_processing_probe",None),
                    ("processing_only",False),("processing_only",None)):
            c=config();c[k]=v
            if k=="processing_only":
                self.assertIsNone(run(conf=c))
            else:
                with self.assertRaises(ValueError):run(conf=c)
        c=config();c.pop("new_only_processing_probe")
        with self.assertRaises(ValueError):run(conf=c)
    def test_ledger_state_requires_observed_only_not_claimed_or_legacy(self):
        for decision in ("SKIP_LEGACY_BATCH","CLAIMED","SKIP_COMPLETED",
                         "FAILED_NEEDS_RECONCILIATION","BUSY_OR_EXPIRED_LEASE"):
            with self.subTest(decision=decision),self.assertRaises(ValueError):
                run(q=claim(decision))
        q=claim();q["claim_enabled"]=True
        with self.assertRaises(ValueError):run(q=q)
        q=claim();q["claim_count"]=1
        with self.assertRaises(ValueError):run(q=q)
    def test_manifest_tampering_rejected(self):
        for field,value in (("manifest_sha256","f"*64),("manifest_uri",U.replace("2026-10-14","2026-10-15")),
                            ("batch_id","synthea-update-only-gh-12345678")):
            c=config();c[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):run(conf=c)
        d=inventory();d["preview_truncated"]=True
        with self.assertRaises(ValueError):run(d=d)
    def test_handoff_rejects_bad_provenance(self):
        x=run();p,v=person_visit()
        cases=[(dict(x,new_only_processing_probe=False),p,v),
            (x,dict(p,processing_data_uri=p["processing_data_uri"].replace(B,"wrong-batch")),v),
            (x,p,dict(v,canonical_rows=0)),
            (dict(x,manifest_uri=U.replace("2026-10-14","2026-10-15")),p,v)]
        for g,person,visit in cases:
            with self.assertRaises(ValueError):validate_handoff(g,person,visit)
    def test_v2_image_is_pinned_and_legacy_image_preserved(self):
        h=HELPER.read_text()
        self.assertIn("healthcare-landing-processing-v2",h)
        self.assertIn("9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937",h)
        self.assertIn("8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7",h)
        self.assertIn("image=PROCESSING_IMAGE_SELECT",h)
        d=DAG.read_text()
        self.assertIn('"CLAIM_ENABLE": "NO"',d)
        self.assertIn('"CLAIM_ALLOWLIST": ""',d)
        self.assertNotIn("cdm_load",d)

if __name__=="__main__":unittest.main()
