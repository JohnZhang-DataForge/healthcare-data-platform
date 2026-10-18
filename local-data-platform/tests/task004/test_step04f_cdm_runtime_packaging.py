import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow/dags"))
from task004_cdm_materialization_plan import plan
B="task004-airflow-runtime-contract-test"
BASE="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+B+"/"
def case():
 return plan(dict(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,batch_id=B,source_version="v3.3.0",manifest_sha256="a"*64,
 manifest_uri="s3://health-landing/"+BASE+"manifest.json",
 person_processing_uri="s3a://health-processing/"+BASE+"entity=patient/run_id=x/data/",
 visit_processing_uri="s3a://health-processing/"+BASE+"entity=encounter/run_id=y/data/",
 person_rows=1,visit_rows=1))
class RuntimeCLI(unittest.TestCase):
 def run_cli(self,context):
  with tempfile.TemporaryDirectory() as directory:
   f=Path(directory)/"plan.json";f.write_text(json.dumps(context))
   return subprocess.run([sys.executable,str(ROOT/"apps/task004/cdm_runtime_cli.py"),"--plan-file",str(f)],
                         text=True,capture_output=True,env={"PYTHONPATH":str(ROOT/"airflow/dags")})
 def test_valid(self):
  p=self.run_cli(case())
  self.assertEqual(p.returncode,0,p.stderr)
  self.assertIn("DATABASE_MUTATION=NO",p.stdout)
 def test_tampered_plan_rejected(self):
  c=case();c["person_rows"]=2
  self.assertNotEqual(self.run_cli(c).returncode,0)
 def test_write_flag_rejected(self):
  c=case();c["database_mutation_authorized"]=True
  self.assertNotEqual(self.run_cli(c).returncode,0)
 def test_container_requires_nonroot(self):
  d=(ROOT/"images/task004-cdm-runtime/Dockerfile").read_text()
  self.assertIn("USER 10001:10001",d)
  self.assertNotIn("apt-get install postgresql",d)
  for module in ("task004_cdm_dynamic_adapters.py","task004_cdm_dynamic_source.py","task004_cdm_dynamic_pg_writer.py"):
   self.assertIn(module,d)
  self.assertIn("pyarrow==",d)
  self.assertIn("boto3==",d)
 def test_runtime_only_offers_source_validation(self):
  cli=(ROOT/"apps/task004/cdm_runtime_cli.py").read_text()
  self.assertIn("--validate-source",cli)
  self.assertNotIn("subprocess.run",cli)
  self.assertNotIn("allow_commit=True",cli)
if __name__=="__main__":unittest.main()
