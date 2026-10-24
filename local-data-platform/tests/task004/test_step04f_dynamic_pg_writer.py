from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"airflow/dags"))
from task004_cdm_materialization_plan import plan
from task004_cdm_dynamic_pg_writer import render
B="task004-airflow-test-999"
PREFIX="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+B+"/"
def context():
 return plan(dict(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,
 batch_id=B,manifest_sha256="a"*64,source_version="v3.3.0",
 manifest_uri="s3://health-landing/"+PREFIX+"manifest.json",
 person_processing_uri="s3a://health-processing/"+PREFIX+"entity=patient/run_id=1/data/",
 visit_processing_uri="s3a://health-processing/"+PREFIX+"entity=encounter/run_id=1/data/",
 person_rows=1,visit_rows=1))
def rows(entity):
 d={"source_key":"id-1","canonical_payload":{"gender_concept_id":8507} if entity=="person" else {"visit_concept_id":9202},"row_fingerprint":"f"*64}
 if entity=="visit":d["source_person_key"]="person-1"
 return [d]
class PgWriter(unittest.TestCase):
 def test_person_rollback_default(self):
  s=render(context(),rows("person"),"person")
  self.assertTrue(s.endswith("ROLLBACK;\n"))
  self.assertNotIn("\nCOMMIT;",s)
  for phrase in ("INSERT INTO etl.person_id_map","INSERT INTO cdm.person","BLOCKED:STAGE_DRIFT","BLOCKED:EXISTING_TARGET_DRIFT","BLOCKED:CHECKPOINT_DRIFT","BLOCKED:TARGET_RECONCILIATION"):
   self.assertIn(phrase,s)
 def test_native_omop_standard_race_is_vocabulary_checked(self):
  sql=render(context(),rows("person"),"person")
  self.assertIn("8657",sql)
  self.assertIn("BLOCKED:VOCABULARY_INVALID",sql)
 def test_visit_parent_and_no_update(self):
  s=render(context(),rows("visit"),"visit")
  self.assertIn("BLOCKED:PERSON_COMMIT_MISSING",s)
  self.assertIn("BLOCKED:PERSON_FK_MISSING",s)
  self.assertIn("INSERT INTO cdm.visit_occurrence",s)
  self.assertNotIn("UPDATE cdm.",s)
  self.assertNotIn("DELETE FROM",s)
 def test_commit_requires_explicit_opt_in(self):
  self.assertTrue(render(context(),rows("person"),"person",allow_commit=True).endswith("COMMIT;\n"))
 def test_batch_drift_blocked(self):
  c=context();c["manifest_sha256"]="b"*64
  with self.assertRaisesRegex(ValueError,"plan_changed"):render(c,rows("person"),"person")
 def test_wrong_count_blocked(self):
  with self.assertRaisesRegex(ValueError,"count"):render(context(),[],"person")
 def test_bad_fingerprint_blocked(self):
  r=rows("person");r[0]["row_fingerprint"]="bad"
  with self.assertRaisesRegex(ValueError,"fingerprint"):render(context(),r,"person")
 def test_bad_parent_blocked(self):
  r=rows("visit");r[0]["source_person_key"]=""
  with self.assertRaisesRegex(ValueError,"parent"):render(context(),r,"visit")
 def test_authorization_boundary(self):
  c=context();c["database_mutation_authorized"]=True
  with self.assertRaisesRegex(ValueError,"authorization_boundary"):render(c,rows("person"),"person")
if __name__=="__main__":unittest.main()
