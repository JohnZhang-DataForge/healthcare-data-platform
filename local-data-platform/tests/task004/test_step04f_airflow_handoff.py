from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow/dags"))
from task004_cdm_preflight_contract import validate_handoff
B="task004-airflow-unit-test"
def fixture():
    g={"batch_id":B,"manifest_sha256":"a"*64,"source_version":"v3.3.0","status":"INTAKE_VERIFIED","manifest_uri":"s3://health-landing/source=synthea/batch_id="+B+"/manifest.json"}
    p={"processing_data_uri":"s3a://health-processing/source=synthea/batch_id="+B+"/entity=patient/run_id=one/","canonical_rows":23}
    v={"processing_data_uri":"s3a://health-processing/source=synthea/batch_id="+B+"/entity=encounter/run_id=one/","canonical_rows":3592}
    return g,p,v
class Handoff(unittest.TestCase):
    def test_accepted_contract_no_db_authorization(self):
        x=validate_handoff(*fixture())
        self.assertFalse(x["cdm_write_permitted"])
        self.assertEqual(x["state"],"HANDOFF_VERIFIED_NOT_LOADED")
        self.assertEqual(x["visit_rows"],3592)
    def test_wrong_batch_blocked(self):
        g,p,v=fixture();v["processing_data_uri"]=v["processing_data_uri"].replace(B,"other")
        with self.assertRaises(ValueError):validate_handoff(g,p,v)
    def test_wrong_manifest_blocked(self):
        g,p,v=fixture();g["manifest_sha256"]="bad"
        with self.assertRaises(ValueError):validate_handoff(g,p,v)
    def test_missing_stage_blocked(self):
        g,p,v=fixture()
        with self.assertRaises(ValueError):validate_handoff(g,{},v)
    def test_nonnumeric_counts_blocked(self):
        g,p,v=fixture();p["canonical_rows"]="23"
        with self.assertRaises(ValueError):validate_handoff(g,p,v)
    def test_dag_requires_reconciliation_before_handoff(self):
        dag=(ROOT/"airflow/dags/task004_processing_pipeline.py").read_text()
        self.assertIn("reconcile >> cdm_load_preflight",dag)
        self.assertIn("python_callable=_validate_handoff_json",dag)
        self.assertNotIn("task004_step04c_person_runner",dag)
        self.assertNotIn("step04d_visit_runner",dag)
if __name__=="__main__":unittest.main()
