"""One-shot NEW_ONLY real COMMIT generator: exact batch, fenced and reconciled."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("airflow/dags","apps/omop_writer","apps/landing_claim"):
    sys.path.insert(0,str(ROOT/p))
from build_s3_rollback_plan import build
from test_new_only_joint_rollback import ctx,rows
from commit_new_only_batch_once import (generate_commit_sql,reconciliation_digest,
                                        BATCH,SHA,URI)

def fixture():
    old=ctx()
    keys=("batch_id","manifest_uri","manifest_sha256","person_processing_uri",
          "visit_processing_uri","source_version","writer_identity_version")
    plan=build(**{k:old[k] for k in keys},person_rows=1,visit_rows=812)
    p,v=rows()
    return plan,p,[dict(v[0],source_key=f"v-{i}") for i in range(812)]

class AuthorizedCommitTests(unittest.TestCase):
    def test_real_identity_one_begin_one_commit_one_transaction(self):
        plan,p,v=fixture()
        sql=generate_commit_sql(plan,p,v,"a"*48)
        self.assertEqual([s.strip() for s in sql.splitlines()].count("BEGIN;"),1)
        self.assertEqual([s.strip() for s in sql.splitlines()].count("COMMIT;"),1)
        self.assertEqual([s.strip() for s in sql.splitlines()].count("ROLLBACK;"),0)
        self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),3)
        self.assertEqual(sql.count("SET LOCAL ROLE landing_claim_worker;"),2)
        self.assertEqual(sql.count("SET LOCAL ROLE cdm_writer;"),1)
        self.assertIn("INSERT INTO cdm.person",sql)
        self.assertIn("INSERT INTO cdm.visit_occurrence",sql)
        self.assertIn("BLOCKED:EXISTING_TARGET_DRIFT",sql)
        self.assertIn("PERSON_DB_RECONCILIATION",sql)
        self.assertIn("VISIT_DB_RECONCILIATION",sql)
        self.assertIn("commit_state='VERIFIED'",sql)
        self.assertIn("REAL_NEW_ONLY_BUSINESS_COMMIT_AND_COMPLETED=PASS",sql)
        self.assertLess(sql.index("SET LOCAL ROLE landing_claim_worker;"),sql.index("SET LOCAL ROLE cdm_writer;"))
        self.assertLess(sql.index("SET LOCAL ROLE cdm_writer;"),sql.index("INSERT INTO cdm.person"))
        self.assertLess(sql.index("INSERT INTO cdm.visit_occurrence"),sql.index("DO $reconcile$"))
        self.assertLess(sql.index("DO $reconcile$"),sql.index("DO $complete$"))
        self.assertLess(sql.index("DO $complete$"),sql.index("\nCOMMIT;"))
    def test_altered_identity_and_invalid_token_fail_closed(self):
        plan,p,v=fixture()
        for token in ("X"*48,"f"*47,None):
            with self.subTest(token=token),self.assertRaises(ValueError):
                generate_commit_sql(plan,p,v,token)
        altered=dict(plan);altered["manifest_sha256"]="f"*64
        with self.assertRaises(ValueError):
            generate_commit_sql(altered,p,v,"a"*48)
        other=dict(plan);other["batch_id"]="synthea-new-only-other"
        with self.assertRaises(ValueError):
            generate_commit_sql(other,p,v,"a"*48)
        with self.assertRaises(ValueError):
            generate_commit_sql(plan,p,v[:-1],"a"*48)
    def test_proof_derived_from_both_stage_digests_and_plan(self):
        plan,p,v=fixture()
        x=reconciliation_digest(plan,p,v)
        self.assertEqual(len(x),64)
        self.assertIn(x,generate_commit_sql(plan,p,v,"a"*48))
        changed=[dict(row) for row in v]
        changed[1]["canonical_payload"]=dict(changed[1]["canonical_payload"],visit_source_value="different")
        self.assertNotEqual(x,reconciliation_digest(plan,p,changed))
    def test_source_contract_stays_immutable_and_auto_claim_stays_disabled(self):
        source=(ROOT/"apps/omop_writer/commit_new_only_batch_once.py").read_text()
        self.assertIn("inspect_new_only(connection,ctx,people,visits,require_claim=False)",source)
        self.assertIn('if os.environ.get("PGUSER")!="cdm_reader"',source)
        self.assertIn("s3_rows(ctx)",source)
        self.assertIn("BLOCKED:COMMIT_PRECONDITION_NOT_CLEAN",source)
        self.assertNotIn("workflow_dispatch",source)
        self.assertNotIn("kubectl",source)
        self.assertNotIn("allow_commit=True",source)
        self.assertNotIn("CLAIM_ENABLE=YES",source)

if __name__=="__main__":unittest.main()
