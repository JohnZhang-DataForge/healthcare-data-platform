from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"airflow/dags"))
from task004_cdm_materialization_plan import plan,same_plan
B="task004-airflow-test-123"
ROOT="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+B+"/"
def good():
    return dict(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,
        batch_id=B,manifest_sha256="a"*64,source_version="v3.3.0",
        manifest_uri="s3://health-landing/"+ROOT+"manifest.json",
        person_processing_uri="s3a://health-processing/"+ROOT+"entity=patient/run_id=abc/work/normalized/data/",
        visit_processing_uri="s3a://health-processing/"+ROOT+"entity=encounter/run_id=xyz/work/normalized/data/",
        person_rows=23,visit_rows=3592)
class DynamicBatch(unittest.TestCase):
    def test_dag_chain_is_preflight_then_plan(self):
        dag=(Path(__file__).resolve().parents[2]/"airflow/dags/task004_processing_pipeline.py").read_text()
        self.assertIn("reconcile >> cdm_load_preflight >> cdm_materialization_plan",dag)
        self.assertIn("python_callable=_prepare_cdm_plan_json",dag)
    def test_valid_is_deterministic_and_never_authorizes_write(self):
        a=plan(good());b=plan(good())
        self.assertEqual(a["plan_sha256"],b["plan_sha256"])
        self.assertEqual(a["load_order"],["person","visit","db_reconcile"])
        self.assertFalse(a["database_mutation_authorized"])
        self.assertTrue(same_plan(good(),good()))
    def test_foreign_batch_blocked(self):
        a=good();a["visit_processing_uri"]=a["visit_processing_uri"].replace(B,"some-other-batch")
        with self.assertRaises(ValueError):plan(a)
    def test_changed_immutable_input_blocked(self):
        a=good();b=good();b["visit_rows"]=3593
        with self.assertRaises(ValueError):same_plan(a,b)
    def test_unverified_or_write_permitted_blocked(self):
        a=good();a["cdm_write_permitted"]=True
        with self.assertRaises(ValueError):plan(a)
    def test_path_escape_blocked(self):
        a=good();a["person_processing_uri"]=a["person_processing_uri"].replace("run_id=abc","../run_id=abc")
        with self.assertRaises(ValueError):plan(a)
    def test_bad_schema_blocked(self):
        a=good();a["manifest_uri"]="https://health-landing/"+ROOT+"manifest.json"
        with self.assertRaises(ValueError):plan(a)
    def test_inconsistent_ingest_date_blocked(self):
        a=good();a["visit_processing_uri"]=a["visit_processing_uri"].replace("2026-10-13","2026-10-12")
        with self.assertRaises(ValueError):plan(a)
    def test_invalid_counts_blocked(self):
        a=good();a["person_rows"]=True
        with self.assertRaises(ValueError):plan(a)
if __name__=="__main__":unittest.main()
