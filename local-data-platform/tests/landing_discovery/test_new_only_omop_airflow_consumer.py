"""TASK004 new Airflow DAG safe NEW_ONLY routing; no Spark/PG writes."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow/dags"))
from new_only_omop_routing import select_verified_new_only,route_claim_status

BATCH="synthea-new-only-gh-38497355290"
SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
URI=f"s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id={BATCH}/manifest.json"

def conf():
    return {"batch_id":BATCH,"manifest_uri":URI,"manifest_sha256":SHA,"consumer_readonly":True}
def inventory():
    return {"status":"READ_ONLY_DISCOVERED","processing_authorized":False,
        "database_mutation":False,"preview_truncated":False,"ready_count":1,
        "ready_batches_preview":[{"batch_id":BATCH,"manifest_sha256":SHA,
        "manifest_uri":URI,"source":"synthea","source_version":"v3.3.0",
        "status":"INTAKE_VERIFIED","file_count":18}]}
def db_row(status="COMPLETED"):
    return {"source_system":"synthea","batch_id":BATCH,"manifest_sha256":SHA,
            "manifest_uri":URI,"role":"landing_claim_worker",
            "pg_transaction_readonly":True,"business_mutation":False,
            "claim_status":status,
            "writer_ledger_rows":1 if status=="COMPLETED" else 0,
            "attempt_count":1 if status=="COMPLETED" else 0}

class NewOnlyAirflowConsumerRouting(unittest.TestCase):
    def test_completed_branch_is_always_skip(self):
        c=select_verified_new_only(inventory(),conf(),"manual")
        self.assertEqual(c["batch_id"],BATCH)
        self.assertEqual(route_claim_status(c,db_row()),"already_completed_no_replay")
    def test_unclaimed_batches_remain_hold_without_claim_or_spark(self):
        self.assertEqual(route_claim_status(conf()|{"source_system":"synthea"},db_row("ABSENT")),
                         "unclaimed_batch_hold")
    def test_manual_new_only_spark_selects_both_real_spark_tasks(self):
        selected=select_verified_new_only(inventory(),conf()|{"spark_processing":True},"manual")
        self.assertEqual(route_claim_status(selected,db_row("ABSENT")),
                         ["spark_patient","spark_encounter"])
        # Even an explicit stale spark flag cannot relaunch an already
        # COMMITTED batch or skip the Claim reader.
        self.assertEqual(route_claim_status(selected,db_row("COMPLETED")),
                         "already_completed_no_replay")
        self.assertEqual(route_claim_status(
            select_verified_new_only(inventory(),conf(),"manual"),db_row("ABSENT")),
            "unclaimed_batch_hold")
        for invalid in (False,None,"true",0,{}):
            with self.subTest(value=invalid),self.assertRaises(ValueError):
                select_verified_new_only(inventory(),conf()|{"spark_processing":invalid},"manual")

    def test_spark_dag_is_processing_only_and_handoff_ends_without_writer(self):
        dag=(ROOT/"airflow/dags/new_only_omop_consumer.py").read_text()
        factory=(ROOT/"airflow/dags/landing_spark_processing.py").read_text()
        self.assertIn('task_id="spark_patient"',dag) if 'task_id="spark_patient"' in dag else self.assertIn('"spark_patient",process="person"',dag)
        self.assertIn('"spark_encounter",process="visit"',dag)
        self.assertIn('"spark_reconcile",process="reconcile"',dag)
        self.assertIn('task_id="prepare_writer_handoff"',dag)
        self.assertIn('task_id="writer_awaits_live_preflight"',dag)
        self.assertIn("image_override=NEW_ONLY_PROCESSING_IMAGE",dag)
        self.assertIn("route_new_only_status >> [already_completed_no_replay,unclaimed_batch_hold,",dag)
        self.assertIn("image=PROCESSING_IMAGE_SELECT",factory)
        self.assertIn("pod.image=image_override",factory)
        self.assertIn("BLOCKED:UNTRUSTED_SPARK_IMAGE_OVERRIDE",factory)
        self.assertNotIn("generate_dynamic_commit_sql(",dag)
        self.assertNotIn("CLAIM_ENABLE",dag)
        self.assertNotIn("COMMIT;",dag)

    def test_invalid_identity_and_schedule_rejected(self):
        for run_type in ("scheduled","backfill"):
            with self.assertRaisesRegex(ValueError,"MANUAL_ONLY"):
                select_verified_new_only(inventory(),conf(),run_type)
        for changes in ({"consumer_readonly":False},{"batch_id":"task004-airflow-old"},
                        {"manifest_sha256":"a"*64},{"auto_claim":True}):
            candidate=conf()|changes
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                select_verified_new_only(inventory(),candidate,"manual")
        bad=inventory();bad["preview_truncated"]=True
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            select_verified_new_only(bad,conf(),"manual")
        bad=inventory();bad["ready_batches_preview"][0]["manifest_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"DISCOVERY_DRIFT"):
            select_verified_new_only(bad,conf(),"manual")
    def test_db_safety_fails_closed(self):
        s=select_verified_new_only(inventory(),conf(),"manual")
        for changes in ({"manifest_sha256":"f"*64},{"role":"omop_admin"},
                        {"pg_transaction_readonly":False},{"business_mutation":True},
                        {"writer_ledger_rows":0}):
            db=db_row()|changes
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                route_claim_status(s,db)
        for status in ("PROCESSING","FAILED","garbled"):
            with self.subTest(status=status),self.assertRaises(ValueError):
                route_claim_status(s,db_row(status))
    def test_airflow_dag_wiring_has_no_claim_or_business_commit(self):
        src=(ROOT/"airflow/dags/new_only_omop_consumer.py").read_text()
        self.assertIn('dag_id="new_only_omop_consumer"',src)
        self.assertIn("schedule=None",src)
        self.assertIn("is_paused_upon_creation=True",src)
        self.assertIn("max_active_runs=1",src)
        self.assertIn("default_transaction_read_only=on",src)
        self.assertIn("SELECT manifest_sha256,manifest_uri,status,attempt_count",src)
        self.assertIn('task_id="already_completed_no_replay"',src)
        self.assertIn('task_id="unclaimed_batch_hold"',src)
        self.assertNotIn("CLAIM_ENABLE",src)
        self.assertNotIn("INSERT INTO etl.",src)
        self.assertNotIn("INSERT INTO cdm.",src)
        self.assertNotIn("SparkApplication",src)
        self.assertNotIn("COMMIT;",src)
if __name__=="__main__": unittest.main()
