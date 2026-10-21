from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"airflow/dags"))
from task004_cdm_materialization_plan import plan
from task004_cdm_dynamic_adapters import transform,source_keys_match,manifest_matches
B="task004-airflow-run-001"
BASE="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+B+"/"
def context():
 return plan(dict(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,batch_id=B,source_version="v3.3.0",manifest_sha256="a"*64,
  manifest_uri="s3://health-landing/"+BASE+"manifest.json",
  person_processing_uri="s3a://health-processing/"+BASE+"entity=patient/run_id=1/data/",
  visit_processing_uri="s3a://health-processing/"+BASE+"entity=encounter/run_id=1/data/",
  person_rows=2,visit_rows=2))
def person(i):
 return dict(source_record_id=str(i),source_system="synthea",source_version="v3.3.0",source_batch_id=B,source_ingest_date="2026-10-13",birth_date="1990-01-03",gender_code="F",race_code="other",ethnicity_code="nonhispanic")
def visit(i):
 return dict(source_encounter_id="v"+str(i),source_person_id=str(i),source_system="synthea",source_version="v3.3.0",source_batch_id=B,source_ingest_date="2026-10-13",encounter_class="ambulatory",start_datetime="2026-01-01 01:00:00",end_datetime="2026-01-01 02:00:00")
class DynamicAdapters(unittest.TestCase):
 def test_new_batch_and_fk(self):
  c=context();p=transform([person(1),person(2)],c,"person");v=transform([visit(1),visit(2)],c,"visit")
  self.assertTrue(source_keys_match(p,v))
  self.assertEqual(p[0]["canonical_payload"]["race_concept_id"],0)
  self.assertEqual(v[0]["canonical_payload"]["visit_type_concept_id"],32827)
  self.assertEqual(v[0]["canonical_payload"]["visit_start_datetime"],"2026-01-01 01:00:00.000000")
  self.assertEqual(p,transform([person(2),person(1)],c,"person"))
 def test_native_race_maps_to_omop_8657_and_preserves_source(self):
  a=person(1);a["race_code"]="native"
  b=person(2);b["race_code"]="white"
  mapped=transform([a,b],context(),"person")
  self.assertEqual(mapped[0]["canonical_payload"]["race_concept_id"],8657)
  self.assertEqual(mapped[0]["canonical_payload"]["race_source_value"],"native")
  self.assertEqual(mapped[1]["canonical_payload"]["race_concept_id"],8527)
  self.assertEqual(mapped,transform([b,a],context(),"person"))
  self.assertNotEqual(mapped[0]["row_fingerprint"],mapped[1]["row_fingerprint"])
 def test_existing_supported_races_unchanged(self):
  for code,expected in (("asian",8515),("black",8516),("hawaiian",8557),("white",8527),("other",0)):
   with self.subTest(race=code):
    a=person(1);a["race_code"]=code
    result=transform([a,person(2)],context(),"person")[0]
    self.assertEqual(result["canonical_payload"]["race_concept_id"],expected)
    self.assertEqual(result["canonical_payload"]["race_source_value"],code)
 def test_unknown_demographics_rejected_with_field_and_value(self):
  for field,invalid in (("gender_code","X"),("race_code","alien"),("ethnicity_code","unknown")):
   with self.subTest(field=field):
    a=person(1);a[field]=invalid
    with self.assertRaisesRegex(ValueError,"BLOCKED=unknown_demographic:"+field+"="+invalid):
     transform([a,person(2)],context(),"person")
 def test_wrong_batch(self):
  a=[person(1),person(2)];a[0]["source_batch_id"]="wrong"
  with self.assertRaisesRegex(ValueError,"mixed_batch"):transform(a,context(),"person")
 def test_mismatched_plan(self):
  c=context();c["plan_sha256"]="0"*64
  with self.assertRaisesRegex(ValueError,"plan_drift"):transform([person(1),person(2)],c,"person")
 def test_duplicate(self):
  with self.assertRaisesRegex(ValueError,"duplicate"):transform([person(1),person(1)],context(),"person")
 def test_row_count(self):
  with self.assertRaisesRegex(ValueError,"row_count"):transform([person(1)],context(),"person")
 def test_unmapped_visit(self):
  a=[visit(1),visit(2)];a[0]["encounter_class"]="bad"
  with self.assertRaisesRegex(ValueError,"unknown_visit_class"):transform(a,context(),"visit")
 def test_missing_parent(self):
  a=[visit(1),visit(2)];a[0]["source_person_id"]="missing"
  with self.assertRaisesRegex(ValueError,"visit_person_reference_missing"):
   source_keys_match(transform([person(1),person(2)],context(),"person"),transform(a,context(),"visit"))
 def test_timestamp_inversion(self):
  a=[visit(1),visit(2)];a[0]["end_datetime"]="2025-12-01 01:00:00"
  with self.assertRaisesRegex(ValueError,"reversed_visit"):transform(a,context(),"visit")
 def test_manifest_hash_mismatch(self):
  with self.assertRaisesRegex(ValueError,"manifest_sha_mismatch"):manifest_matches(b"wrong",context())
 def test_write_authority_closed(self):
  c=context();c["database_mutation_authorized"]=True
  with self.assertRaisesRegex(ValueError,"authorization_boundary"):transform([person(1),person(2)],c,"person")
if __name__=="__main__":unittest.main()
