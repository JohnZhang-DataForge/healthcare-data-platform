"""Pure safety contract for manually authorized Spark processing-only replay.

Pure functions are extracted from the DAG helper AST; no Airflow packages
are needed on the GitHub-hosted unit runner.
"""
import ast
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/"airflow"/"dags"/"landing_spark_processing.py"
DAG=ROOT/"airflow"/"dags"/"landing_batch_discovery.py"
MODULE=ast.parse(HELPER.read_text())
FUNCS={x.name:x for x in MODULE.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
ns={"json":json,"re":re,"IDENTITY":re.compile(r"^[A-Za-z0-9._-]{1,256}$"),
    "SHA":re.compile(r"^[0-9a-f]{64}$")}
exec(compile(ast.Module(body=[FUNCS["select_verified_processing_replay"],
                              FUNCS["processing_gate"]],type_ignores=[]),
             str(HELPER),"exec"),ns)
select=ns["select_verified_processing_replay"]
gate=ns["processing_gate"]

MANIFEST=(
    "s3://health-landing/source=synthea/source_version=v3.3.0/"
    "ingest_date=2026-10-12/batch_id=task004-airflow-test-001/manifest.json"
)
SHA="a"*64
BATCH="task004-airflow-test-001"
def discovery():
    return json.dumps({
       "status":"READ_ONLY_DISCOVERED","processing_authorized":False,
       "database_mutation":False, "ready_count":1,
       "preview_truncated":False,"ready_batches_preview":[{
          "batch_id":BATCH,"manifest_uri":MANIFEST,"manifest_sha256":SHA,
          "source":"synthea","source_version":"v3.3.0",
          "status":"INTAKE_VERIFIED","file_count":18}],
    })
def claims(decision="SKIP_LEGACY_BATCH"):
    return json.dumps({"status":"EVALUATED","claim_enabled":False,
           "claim_count":0,"input_count":1,"spark_trigger":False,
           "omop_business_mutation":False,
           "decisions":[{"batch_id":BATCH,"decision":decision}]})
def conf():return {"processing_only":True,"batch_id":BATCH,
                    "manifest_uri":MANIFEST,"manifest_sha256":SHA}

class SparkSelectionTests(unittest.TestCase):
    def test_scheduled_run_never_launches_spark(self):
        self.assertIsNone(select(discovery(),claims(),conf(),"scheduled"))
        self.assertFalse(gate("null"))

    def test_normal_manual_without_opt_in_never_launches_spark(self):
        self.assertIsNone(select(discovery(),claims(),{},"manual"))
        self.assertIsNone(select(discovery(),claims(),None,"manual"))

    def test_explicit_verified_old_batch_permitted(self):
        r=select(discovery(),claims(),conf(),"manual")
        self.assertTrue(gate(json.dumps(r)))
        self.assertFalse(r["omop_business_mutation"])
        self.assertEqual(r["batch_id"],BATCH)
        self.assertEqual(r["manifest_sha256"],SHA)

    def test_airflow_jinja_conf_json_string_selects_exact_historic_batch(self):
        selected=select(discovery(),claims(),json.dumps(conf()),"manual")
        self.assertIsInstance(selected,dict)
        self.assertEqual(selected["batch_id"],BATCH)
        self.assertTrue(gate(json.dumps(selected)))

    def test_malformed_manual_conf_json_blocks(self):
        with self.assertRaisesRegex(ValueError,"INVALID_MANUAL_DAGRUN_CONF"):
            select(discovery(),claims(),"{bad","manual")

    def test_unknown_new_batch_blocked_until_real_ledger_claim(self):
        with self.assertRaisesRegex(ValueError,"HISTORICAL"):
            select(discovery(),claims("OBSERVED_ONLY"),conf(),"manual")

    def test_sha_mismatch_fails_closed(self):
        c=conf();c["manifest_sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"MANIFEST_NOT_IN"):
            select(discovery(),claims(),c,"manual")

    def test_truncated_xcom_fails_closed(self):
        d=json.loads(discovery());d["preview_truncated"]=True
        with self.assertRaisesRegex(ValueError,"NOT_READ_ONLY"):
            select(json.dumps(d),claims(),conf(),"manual")

    def test_active_claim_not_permitted_for_processing_only_replay(self):
        c=json.loads(claims());c["claim_enabled"]=True;c["claim_count"]=1
        with self.assertRaisesRegex(ValueError,"NOT_READ_ONLY"):
            select(discovery(),json.dumps(c),conf(),"manual")

    def test_wrong_record_count_fails_closed(self):
        d=json.loads(discovery());d["ready_count"]=3
        with self.assertRaisesRegex(ValueError,"NOT_READ_ONLY"):
            select(json.dumps(d),claims(),conf(),"manual")

    def test_structural_graph_and_no_generator_or_database_operators(self):
        s=DAG.read_text()
        for token in ["authorize_processing_replay","processing_only_gate",
                      "spark_patient","spark_encounter","spark_reconcile",
                      "verify_spark_processing","scan_ready_manifests",
                      "evaluate_batch_claims"]:
            self.assertIn(token,s)
        self.assertIn("processing_only_gate >> [spark_patient, spark_encounter]",s)
        self.assertIn("spark_encounter] >> spark_reconcile >> verify_spark_processing",s)
        self.assertNotIn("generate_publish",s)
        self.assertNotIn("cdm_load",s)

if __name__=="__main__":
    unittest.main()
