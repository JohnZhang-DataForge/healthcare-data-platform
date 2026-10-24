"""NEW_ONLY Airflow atomic Writer runtime (no actual DB/S3 mutations in tests)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
for p in ("apps/omop_writer","airflow/dags","tests/omop_writer"):
    sys.path.insert(0,str(ROOT/p))
import new_only_airflow_writer as w
from build_s3_rollback_plan import build

def plan():
    return build(
      batch_id="synthea-new-only-gh-third-20261014-test",
      manifest_sha256="f"*64,
      manifest_uri="s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-third-20261014-test/manifest.json",
      person_processing_uri="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-third-20261014-test/entity=patient/run_id=task004-person-20261014T132000Z-1/work/normalized/data/",
      visit_processing_uri="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-third-20261014-test/entity=encounter/run_id=task004-encounter-20261014T132000Z-1/work/normalized/data/",
      person_rows=2, visit_rows=3,source_version="v3.3.0",writer_identity_version="synthea-new-only-v1")

def handoff(p):
    return {"status":"NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED",
      "source_system":"synthea", "batch_id":p["batch_id"],
      "manifest_uri":p["manifest_uri"], "manifest_sha256":p["manifest_sha256"],
      "plan_sha256":p["plan_sha256"],"plan":p,
      "claim_status_at_handoff":"ABSENT","person_rows":p["person_rows"],
      "visit_rows":p["visit_rows"],"business_commit_authorized":False,
      "claim_mutation":False,"writer_mutation":False}

def done(p):
    return {"claim":(p["manifest_sha256"],p["manifest_uri"],"COMPLETED",1,
                     None,None,"e"*64),
     "ledger":1,"stage":{"person":p["person_rows"],"visit":p["visit_rows"]},
     "checkpoints":[("person",p["person_rows"],p["person_rows"],"VERIFIED"),
                    ("visit",p["visit_rows"],p["visit_rows"],"VERIFIED")],
     "mapped_person":p["person_rows"],"mapped_visit":p["visit_rows"]}

def empty():
    return {"claim":None,"ledger":0,"stage":{},"checkpoints":[],
            "mapped_person":0,"mapped_visit":0}

class WriterRuntime(unittest.TestCase):
    def test_reader_handoff_requires_full_immutable_plan(self):
        import json
        p=plan();h=handoff(p)
        self.assertEqual(w.load_handoff(json.dumps(h))[1],p)
        for change in ({"manifest_sha256":"0"*64},{"business_commit_authorized":True},
                       {"writer_mutation":True},{"person_rows":99}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                w.load_handoff(json.dumps(h|change))
        with self.assertRaises(ValueError):
            w.load_handoff("x"*(w.MAX_HANDOFF_BYTES+1))
    def test_historic_committed_batches_never_reach_writer(self):
        import json
        p=plan();h=handoff(p)
        for old in w.COMMITTED_HISTORIC:
            fake=dict(p,batch_id=old);fake_h=dict(h,plan=fake,batch_id=old)
            with self.subTest(batch=old),self.assertRaises(ValueError):
                w.load_handoff(json.dumps(fake_h))
    def test_readonly_skip_never_fetches_s3_or_calls_admin(self):
        p=plan();h=handoff(p)
        with (patch.object(w,"durable_snapshot",return_value=done(p)),
              patch.object(w,"s3_rows") as s3,
              patch.object(w,"one_transaction_commit") as commit,
              patch.dict(w.os.environ,{"PGUSER":"cdm_reader"})):
            self.assertEqual(w.execute(h,p,can_commit=True),"SKIP_COMPLETED")
            s3.assert_not_called()
            commit.assert_not_called()
    def test_incomplete_or_identity_drift_never_writes(self):
        p=plan();h=handoff(p)
        for snapshot in (
          empty()|{"stage":{"person":1}},
          done(p)|{"claim":(p["manifest_sha256"],p["manifest_uri"],"PROCESSING",1,"e"*48,None,None)},
          done(p)|{"claim":("0"*64,p["manifest_uri"],"COMPLETED",1,None,None,"e"*64)},
          done(p)|{"mapped_visit":2},
          done(p)|{"checkpoints":[]},
        ):
            with (self.subTest(s=snapshot),
                  patch.object(w,"durable_snapshot",return_value=snapshot),
                  patch.object(w,"s3_rows") as s3,
                  patch.object(w,"one_transaction_commit") as commit,
                  patch.dict(w.os.environ,{"PGUSER":"cdm_reader"})):
                with self.assertRaises(ValueError):
                    w.execute(h,p,can_commit=True)
                s3.assert_not_called();commit.assert_not_called()
    def test_missing_physical_enable_secret_fails_closed(self):
        p=plan();h=handoff(p)
        with (patch.object(w,"durable_snapshot",return_value=empty()),
              patch.object(w,"s3_rows") as s3,
              patch.object(w,"one_transaction_commit") as commit,
              patch.dict(w.os.environ,{"PGUSER":"cdm_reader","TASK004_WRITER_DEPLOY_ENABLE":"NO"})):
            with self.assertRaisesRegex(ValueError,"NOT_EXPLICITLY_ENABLED"):
                w.execute(h,p,can_commit=True)
            s3.assert_not_called();commit.assert_not_called()
    def test_full_sql_has_exact_one_commit_and_all_original_fences(self):
        from test_dynamic_airflow_new_only_commit import make
        from commit_new_only_batch_once import _render_atomic_new_only_sql
        p,people,visits,*rest=make(1)
        h=rest[-1] if False else None
        # Real source rows from fixture, Airflow immutable plan for same identity.
        from new_only_omop_writer_handoff import prepare_new_only_writer_handoff
        _,_,_,s,claim,pr,vr=make(1)
        h=prepare_new_only_writer_handoff(s,claim,pr,vr)
        sql=w.transaction_sql(h,p,people,visits,"a"*48)
        self.assertEqual([x.strip() for x in sql.splitlines()].count("BEGIN;"),1)
        self.assertEqual([x.strip() for x in sql.splitlines()].count("COMMIT;"),1)
        self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),3)
        self.assertNotIn("\\set",sql)
    def test_runtime_packaging_and_manual_gate(self):
        docker=(ROOT/"images/new-only-omop-writer/Dockerfile").read_text()
        self.assertIn("ARG BASE_IMAGE=ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime:latest",docker)
        self.assertIn("FROM ${BASE_IMAGE}",docker)
        self.assertNotIn("@sha256:",docker)
        self.assertIn("new_only_airflow_writer.py",docker)
        self.assertIn("COPY --chown=10001:10001 airflow/dags/task004_cdm_materialization_plan.py /opt/task004/",docker)
        self.assertIn("COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_adapters.py /opt/task004/",docker)
        self.assertIn("COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_source.py /opt/task004/",docker)
        self.assertIn("COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_pg_writer.py /opt/task004/",docker)
        self.assertNotIn("POSTGRES_PASSWORD=",docker)
        src=(ROOT/"apps/omop_writer/new_only_airflow_writer.py").read_text()
        self.assertIn("autocommit=True",src)
        self.assertIn("prepare=False",src)
        self.assertIn("TASK004_WRITER_DEPLOY_ENABLE",src)
        self.assertIn("WRITER_UNKNOWN_OUTCOME_NO_RETRY",src)
        self.assertNotIn("subprocess",src)
if __name__=="__main__":unittest.main()
