from pathlib import Path
import hashlib,sys,unittest
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"airflow/dags"))
from task004_cdm_materialization_plan import plan
from task004_cdm_dynamic_source import read

B="task004-airflow-test-123"
ROOT="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+B+"/"
MANIFEST=b'{"batch":"test"}'
def context():
 return plan(dict(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,
 batch_id=B,source_version="v3.3.0",manifest_sha256=hashlib.sha256(MANIFEST).hexdigest(),
 manifest_uri="s3://health-landing/"+ROOT+"manifest.json",
 person_processing_uri="s3a://health-processing/"+ROOT+"entity=patient/run_id=1/data/",
 visit_processing_uri="s3a://health-processing/"+ROOT+"entity=encounter/run_id=1/data/",
 person_rows=1,visit_rows=1))
def row():
 return dict(source_record_id="person-01",source_system="synthea",source_version="v3.3.0",source_batch_id=B,source_ingest_date="2026-10-13",birth_date="1990-01-03",gender_code="F",race_code="other",ethnicity_code="nonhispanic")
class FakeS3:
 def __init__(self,c,manifest=MANIFEST,nfiles=1):
  self.manifest=manifest;self.nfiles=nfiles;self.c=c
 def get_object(self,Bucket,Key):
  return {"Body":BytesIO(self.manifest if Bucket=="health-landing" else b"PARQUET_DATA")}
 def get_paginator(self,name):
  parent=self
  class Pager:
   def paginate(self,**kw):
    yield {"Contents":[{"Key":kw["Prefix"]+"part-%02d.parquet"%i} for i in range(parent.nfiles)]}
  return Pager()
class Source(unittest.TestCase):
 def test_source_read_is_batch_bounded(self):
  c=context();result=read(FakeS3(c),c,"person",lambda raw:[row()])
  self.assertEqual(result[0]["source_key"],"person-01")
  self.assertEqual(result[0]["canonical_payload"]["race_concept_id"],0)
 def test_manifest_modified_fails(self):
  c=context()
  with self.assertRaisesRegex(ValueError,"manifest_sha_mismatch"):read(FakeS3(c,b"altered"),c,"person",lambda raw:[row()])
 def test_multiple_parquet_files_fail_closed(self):
  c=context()
  with self.assertRaisesRegex(ValueError,"parquet_cardinality"):read(FakeS3(c,nfiles=2),c,"person",lambda raw:[row()])
 def test_empty_prefix_fails_closed(self):
  c=context()
  with self.assertRaisesRegex(ValueError,"parquet_cardinality"):read(FakeS3(c,nfiles=0),c,"person",lambda raw:[row()])
if __name__=="__main__":unittest.main()
