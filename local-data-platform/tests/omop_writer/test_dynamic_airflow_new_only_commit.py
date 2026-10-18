"""TASK004 future NEW_ONLY per-batch Spark -> atomic Claim+OMOP Writer contract."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
for path in ("airflow/dags","apps/omop_writer","apps/landing_claim","tests/omop_writer"):
    sys.path.insert(0,str(ROOT/path))
from build_s3_rollback_plan import build
from commit_new_only_batch_once import generate_commit_sql
from dynamic_new_only_commit import generate_dynamic_commit_sql
from new_only_omop_writer_handoff import prepare_new_only_writer_handoff,assert_dynamic_handoff
from test_first_real_new_only_commit import fixture

BATCH="synthea-new-only-gh-future-20261014-smalltest"


def make(count=1):
    historic,person,visit=fixture()
    fields=("batch_id","manifest_uri","manifest_sha256","person_processing_uri",
            "visit_processing_uri","person_rows","visit_rows","source_version",
            "writer_identity_version")
    fresh={k:historic[k] for k in fields}
    fresh["batch_id"]=BATCH
    for name in ("manifest_uri","person_processing_uri","visit_processing_uri"):
        fresh[name]=fresh[name].replace(historic["batch_id"],BATCH)
    fresh["person_rows"]=1
    fresh["visit_rows"]=count
    plan=build(**fresh)
    selected={"source_system":"synthea","consumer_readonly":True,
              "batch_id":BATCH,"manifest_uri":plan["manifest_uri"],
              "manifest_sha256":plan["manifest_sha256"]}
    claim={"source_system":"synthea","batch_id":BATCH,
           "manifest_uri":plan["manifest_uri"],
           "manifest_sha256":plan["manifest_sha256"],"role":"landing_claim_worker",
           "pg_transaction_readonly":True,"business_mutation":False,
           "claim_status":"ABSENT","writer_ledger_rows":0,"attempt_count":0}
    x1={"processing_data_uri":plan["person_processing_uri"],"canonical_rows":1,
        "run_id":plan["person_processing_uri"].split("/run_id=")[1].split("/")[0],
        "processing_readback":"PASS"}
    x2={"processing_data_uri":plan["visit_processing_uri"],"canonical_rows":count,
        "run_id":plan["visit_processing_uri"].split("/run_id=")[1].split("/")[0],
        "processing_readback":"PASS"}
    return plan,person,visit[:count],selected,claim,x1,x2


class DynamicAtomicNewOnlyTests(unittest.TestCase):
    def verified(self,count=1):
        plan,people,visits,selected,claim,p,v=make(count)
        handoff=prepare_new_only_writer_handoff(selected,claim,p,v)
        self.assertFalse(handoff["business_commit_authorized"])
        self.assertFalse(handoff["claim_mutation"])
        self.assertFalse(handoff["writer_mutation"])
        self.assertEqual(handoff["plan"],plan)
        assert_dynamic_handoff(plan,handoff)
        return plan,people,visits,selected,claim,p,v,handoff

    def test_one_person_one_visit_dynamic_sql_is_not_stale_812(self):
        ctx,p,v,*_,handoff=self.verified(1)
        sql=generate_dynamic_commit_sql(ctx,p,v,"b"*48,handoff)
        self.assertEqual(sql.splitlines().count("BEGIN;"),1)
        self.assertEqual(sql.splitlines().count("COMMIT;"),1)
        self.assertEqual(sql.splitlines().count("ROLLBACK;"),0)
        self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),3)
        self.assertIn("INSERT INTO cdm.person",sql)
        self.assertIn("INSERT INTO cdm.visit_occurrence",sql)
        self.assertIn("entity='visit')<>1",sql)
        self.assertIn("entity='visit' AND stage_rows=1 AND mapped_rows=1",sql)
        self.assertIn("'person_id',pm.person_id))))<>1",sql)
        self.assertNotIn("entity='visit')<>812",sql)
        self.assertIn("status='COMPLETED'",sql)
        self.assertLess(sql.index("DO $reconcile$"),sql.index("DO $complete$"))
        self.assertLess(sql.index("DO $complete$"),sql.index("\nCOMMIT;"))
        self.assertIn("BLOCKED:EXISTING_TARGET_DRIFT",sql)

    def test_batched_812_visits_still_supported(self):
        ctx,p,v,*_,handoff=self.verified(812)
        sql=generate_dynamic_commit_sql(ctx,p,v,"a"*48,handoff)
        self.assertIn("entity='visit')<>812",sql)
        self.assertIn("entity='visit' AND stage_rows=812 AND mapped_rows=812",sql)

    def test_historic_one_shot_cannot_be_rearmed_as_dynamic(self):
        old,p,v=fixture()
        c,pp,vv,*_,h=self.verified()
        with self.assertRaisesRegex(ValueError,"ALREADY_COMMITTED_HISTORIC_BATCH"):
            fake=dict(h,plan=old,batch_id=old["batch_id"],manifest_sha256=old["manifest_sha256"],
                      manifest_uri=old["manifest_uri"],plan_sha256=old["plan_sha256"],
                      person_rows=old["person_rows"],visit_rows=old["visit_rows"])
            generate_dynamic_commit_sql(old,p,v,"a"*48,fake)
        with self.assertRaises(ValueError):
            generate_commit_sql(c,pp,vv,"a"*48)

    def test_no_spark_xcom_no_handoff_no_sql(self):
        ctx,p,v,selected,claim,px,vx,handoff=self.verified()
        for change in ({"processing_readback":"FAIL"},{"canonical_rows":0},
                       {"processing_data_uri":"s3a://health-processing/other/"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                prepare_new_only_writer_handoff(selected,claim,px,vx|change)
        for change in ({"claim_status":"COMPLETED","writer_ledger_rows":1,"attempt_count":1},
                       {"claim_status":"PROCESSING"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                prepare_new_only_writer_handoff(selected,claim|change,px,vx)
        for change in ({"business_commit_authorized":True},{"plan_sha256":"f"*64},
                       {"writer_mutation":True},{"claim_status_at_handoff":"PROCESSING"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                generate_dynamic_commit_sql(ctx,p,v,"a"*48,handoff|change)
        with self.assertRaises(ValueError):
            generate_dynamic_commit_sql(ctx,p,v,"INVALID",handoff)

    def test_same_tx_only_and_no_deployment_wiring(self):
        source=(ROOT/"apps/omop_writer/dynamic_new_only_commit.py").read_text()
        router=(ROOT/"airflow/dags/new_only_omop_writer_handoff.py").read_text()
        dag=(ROOT/"airflow/dags/new_only_omop_consumer.py").read_text()
        self.assertIn("_render_atomic_new_only_sql",source)
        self.assertIn("validate_input(plan, people, visits)",source)
        self.assertIn("writer_mutation",router)
        self.assertNotIn("generate_dynamic_commit_sql",dag)
        self.assertNotIn("CLAIM_ENABLE",dag)
        self.assertNotIn("SparkApplication",dag)
        self.assertNotIn("INSERT INTO",router)

if __name__=="__main__":unittest.main()
