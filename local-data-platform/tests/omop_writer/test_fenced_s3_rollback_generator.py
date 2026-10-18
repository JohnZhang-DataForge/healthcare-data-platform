"""Bounded same-TX NEW_ONLY real-S3 rollback generator contract tests."""
import pathlib,sys,unittest
root=pathlib.Path(__file__).resolve().parents[2]
for p in ("airflow/dags","apps/omop_writer","apps/landing_claim"):
    sys.path.insert(0,str(root/p))
from build_s3_rollback_plan import build
from generate_fenced_s3_rollback_sql import generate_rollback_sql
from test_new_only_joint_rollback import ctx,rows

class FencedS3ScriptTests(unittest.TestCase):
    def valid(self):
        base=ctx()
        keys=("batch_id","manifest_uri","manifest_sha256","person_processing_uri",
              "visit_processing_uri","source_version","writer_identity_version")
        context=build(**{k:base[k] for k in keys},person_rows=1,visit_rows=812)
        p,v=rows()
        v=[dict(v[0],source_key="v-"+str(i)) for i in range(812)]
        return context,p,v
    def test_one_transaction_real_parquet_sql_is_rollback_only(self):
        c,p,v=self.valid()
        sql=generate_rollback_sql(c,p,v,"a"*48)
        self.assertEqual(sql.splitlines().count("BEGIN;"),1)
        self.assertEqual(sql.splitlines().count("ROLLBACK;"),1)
        self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),2)
        self.assertIn("SET LOCAL ROLE cdm_writer;",sql)
        self.assertIn("INSERT INTO cdm.person",sql)
        self.assertIn("INSERT INTO cdm.visit_occurrence",sql)
        self.assertIn("BLOCKED:EXISTING_TARGET_DRIFT",sql)
        self.assertIn("REAL_S3_FENCED_PERSON_VISIT_PG_ROLLBACK=PASS",sql)
        self.assertNotIn("\nCOMMIT;",sql)
        self.assertLess(sql.index("SET LOCAL ROLE cdm_writer;"),sql.index("INSERT INTO cdm.person"))
        self.assertLess(sql.index("INSERT INTO cdm.visit_occurrence"),sql.rindex("SELECT task004_writer_fence.assert_active_claim("))
        self.assertLess(sql.rindex("SELECT task004_writer_fence.assert_active_claim("),sql.index("\nROLLBACK;"))
    def test_untrusted_or_different_batch_refused(self):
        c,p,v=self.valid()
        for tok in ("x","a"*47,"A"*48):
            with self.subTest(token=tok),self.assertRaises(ValueError):
                generate_rollback_sql(c,p,v,tok)
        with self.assertRaises(ValueError):
            generate_rollback_sql(c,p,v[:-1],"a"*48)
        c=dict(c)
        c["batch_id"]="synthea-new-only-gh-unsafe"
        with self.assertRaises(ValueError):
            generate_rollback_sql(c,p,v,"a"*48)
    def test_authorized_ddl_deploy_is_separate_from_business_tx(self):
        sql=(root/"sql/landing_claim/writer_fence_v1_deploy.sql").read_text()
        self.assertIn("CREATE ROLE task004_writer_fence_owner NOLOGIN",sql)
        self.assertIn("SECURITY DEFINER",sql)
        self.assertIn("REVOKE ALL ON FUNCTION",sql)
        self.assertIn("FOR UPDATE NOWAIT",sql)
        self.assertIn("FENCE_DDL_DEPLOY_SAFETY=PASS",sql)
        self.assertNotIn("INSERT INTO cdm.",sql)
        self.assertNotIn("UPDATE cdm.",sql)
        self.assertNotIn("INSERT INTO etl.landing_batch_ledger",sql)
if __name__=="__main__":unittest.main()
