"""Final Airflow NEW_ONLY Writer routing contract: opt-in only, no implicit COMMIT."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("airflow/dags","apps/omop_writer","tests/omop_writer"):
    sys.path.insert(0,str(ROOT/p))
from new_only_omop_routing import select_verified_new_only,route_claim_status,route_new_only_writer_commit
from test_dynamic_airflow_new_only_commit import make
from new_only_omop_writer_handoff import prepare_new_only_writer_handoff

class WriterBranchGates(unittest.TestCase):
    def setup_batch(self):
        plan,people,visits,selected,claim,p,v=make(1)
        selection=selected|{"spark_processing":True,"writer_commit":False}
        handoff=prepare_new_only_writer_handoff(selected,claim,p,v)
        return selection,handoff,claim

    def test_default_processing_only_holds_writer(self):
        selected,handoff,claim=self.setup_batch()
        self.assertEqual(route_claim_status(selected,claim),["spark_patient","spark_encounter"])
        self.assertEqual(route_new_only_writer_commit(selected,handoff,"manual"),
                         "writer_awaits_live_preflight")

    def test_commit_opt_in_validates_handoff_and_all_identity(self):
        selected,handoff,claim=self.setup_batch()
        self.assertEqual(route_new_only_writer_commit(selected|{"writer_commit":True},
                                                     handoff,"manual"),
                         "execute_new_only_writer")
        for changed in ({"manifest_sha256":"f"*64},
                        {"manifest_uri":"s3://health-landing/foreign"},
                        {"batch_id":"synthea-new-only-bad"},
                        {"spark_processing":False}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                route_new_only_writer_commit(selected|{"writer_commit":True}|changed,
                                             handoff,"manual")
        for run_type in ("scheduled","backfill"):
            with self.assertRaisesRegex(ValueError,"ONLY_MANUAL"):
                route_new_only_writer_commit(selected|{"writer_commit":True},
                                             handoff,run_type)

    def test_completed_two_historic_batches_not_rearmed(self):
        selected,handoff,_=self.setup_batch()
        for batch in ("synthea-new-only-gh-38497355290","synthea-new-only-gh-38489944582"):
            stale=handoff | {"batch_id":batch,"plan":handoff["plan"]|{"batch_id":batch}}
            chosen=selected|{"batch_id":batch,"writer_commit":True}
            with self.subTest(batch=batch),self.assertRaises(ValueError):
                route_new_only_writer_commit(chosen,stale,"manual")

    def test_select_only_exact_three_modes_and_real_s3(self):
        selected,handoff,_=self.setup_batch()
        p=handoff["plan"];uri=p["manifest_uri"]
        batch=p["batch_id"]
        inventory={"status":"READ_ONLY_DISCOVERED","processing_authorized":False,
            "database_mutation":False,"preview_truncated":False,"ready_count":1,
            "ready_batches_preview":[{"batch_id":batch,"manifest_uri":uri,
            "manifest_sha256":p["manifest_sha256"],"source":"synthea",
            "source_version":"v3.3.0","file_count":18,"status":"INTAKE_VERIFIED"}]}
        inventory["verified_selected_batch"]=inventory["ready_batches_preview"][0].copy()
        conf={"consumer_readonly":True,"batch_id":batch,"manifest_uri":uri,
              "manifest_sha256":p["manifest_sha256"]}
        for extras,accepted in (({},False),({"spark_processing":True},False),
                                ({"spark_processing":True,"writer_commit":True},True)):
            out=select_verified_new_only(inventory,conf|extras,"manual")
            self.assertEqual(out["writer_commit"],accepted)
        for extras in ({"writer_commit":True},{"spark_processing":False,"writer_commit":True},
                       {"spark_processing":True,"writer_commit":False},
                       {"spark_processing":True,"writer_commit":"true"},
                       {"spark_processing":True,"auto_commit":True}):
            with self.subTest(extras=extras),self.assertRaises(ValueError):
                select_verified_new_only(inventory,conf|extras,"manual")

    def test_dag_writer_still_paused_and_twice_gated(self):
        dag=(ROOT/"airflow/dags/new_only_omop_consumer.py").read_text()
        self.assertIn("is_paused_upon_creation=True",dag)
        self.assertIn("schedule=None",dag)
        self.assertIn("max_active_runs=1",dag)
        self.assertIn("default_args={\"retries\":0}",dag)
        self.assertIn('task_id="route_writer_authorization"',dag)
        self.assertIn('task_id="execute_new_only_writer"',dag)
        self.assertIn("task004-new-only-writer-commit",dag)
        self.assertIn("TASK004_WRITER_AIRFLOW_COMMIT_SELECTION",dag)
        self.assertIn("TASK004_WRITER_DEPLOY_ENABLE",dag)
        self.assertIn("healthcare-data-platform-local-dp-omop-writer",dag)
        self.assertIn('":latest"',dag)
        self.assertIn('image_pull_policy="Always"',dag)
        self.assertNotIn("@sha256:",dag)
        self.assertIn("execute_new_only_writer >> writer_committed_verified",dag)
        self.assertIn("retries=0",dag)
        self.assertNotIn("INSERT INTO etl.",dag)
        self.assertNotIn("COMMIT;",dag)
if __name__=="__main__":unittest.main()
