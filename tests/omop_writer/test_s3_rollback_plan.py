"""Strict no-COMMIT S3 writer plan tests without S3 or PostgreSQL."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT/"airflow"/"dags"))
sys.path.insert(0,str(ROOT/"apps"/"omop_writer"))
from build_s3_rollback_plan import build

BATCH="task004-airflow-task004-step03e-38431103586"
PREFIX="source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id="+BATCH+"/"
def inputs():
    return dict(batch_id=BATCH,
        manifest_uri="s3://health-landing/"+PREFIX+"manifest.json",
        manifest_sha256="e6dc34dd45357a43561f5e970185c5e44da4368647440a78363f43b1a762bc8a",
        person_processing_uri="s3a://health-processing/"+PREFIX+"entity=patient/run_id=person-01/work/normalized/data/",
        visit_processing_uri="s3a://health-processing/"+PREFIX+"entity=encounter/run_id=visit-01/work/normalized/data/",
        person_rows=23,visit_rows=3588)

class PlanTests(unittest.TestCase):
    def test_valid_plan_rollback_only(self):
        x=build(**inputs())
        self.assertEqual(x["person_rows"],23)
        self.assertEqual(x["visit_rows"],3588)
        self.assertEqual(x["load_order"],["person","visit","db_reconcile"])
        self.assertIs(x["database_mutation_authorized"],False)
        self.assertEqual(len(x["plan_sha256"]),64)

    def test_manifest_sha_and_processing_change_plan(self):
        original=inputs();one=build(**original)
        another=dict(original);another["manifest_sha256"]="f"*64
        self.assertNotEqual(one["plan_sha256"],build(**another)["plan_sha256"])
        another=dict(original);another["person_processing_uri"]=another["person_processing_uri"].replace("person-01","person-02")
        self.assertNotEqual(one["plan_sha256"],build(**another)["plan_sha256"])

    def test_rejects_wrong_source_batch_and_mixed_uri(self):
        for name,value in (("manifest_uri","s3://other/"+PREFIX+"manifest.json"),
                           ("visit_processing_uri","s3a://health-processing/foreign"),
                           ("batch_id","different-batch"),
                           ("source_version","v4")):
            a=inputs();a[name]=value
            with self.subTest(field=name),self.assertRaises(ValueError):
                build(**a)

    def test_rejects_missing_or_invalid_counts(self):
        for people,visits in ((0,1),(1,0),(False,1),(1,True),(-1,1),(1010000,1)):
            a=inputs();a["person_rows"]=people;a["visit_rows"]=visits
            with self.subTest(rows=(people,visits)),self.assertRaises(ValueError):
                build(**a)

if __name__=="__main__":unittest.main()
