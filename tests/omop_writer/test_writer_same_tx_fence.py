"""Candidate rollout remains ROLLBACK-only; never touch business COMMIT."""
import pathlib
import sys
import unittest

root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "airflow" / "dags"))
sys.path.insert(0, str(root / "apps" / "omop_writer"))
sys.path.insert(0, str(root / "apps" / "landing_claim"))

from batch_ledger import Candidate
from lease_fence import FenceTicket
from fenced_joint_rollback import ticket_args, fenced_joint_rollback, FENCE_SQL
from test_new_only_joint_rollback import ctx, rows

B = "synthea-new-only-gh-38497355290"
OWNER = "a" * 48

def ticket(context):
    return FenceTicket(Candidate("synthea",B,context["manifest_sha256"],
                                  context["manifest_uri"]), OWNER, 1)

class Cursor:
    def __init__(self, fail_at=-1):
        self.calls = []
        self.fail_at = fail_at
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def execute(self, sql, params=None, **kwargs):
        self.calls.append((sql, params, kwargs))
        if len(self.calls) == self.fail_at:
            raise RuntimeError("test-injected-db-failure")
    def fetchone(self):
        return ("cdm_writer", "off")

class Connection:
    autocommit = True
    def __init__(self, fail_at=-1):
        self.cur = Cursor(fail_at=fail_at)
    def cursor(self): return self.cur

class SameTXTests(unittest.TestCase):
    def test_exact_plan_ticket_identity_required(self):
        c=ctx()
        self.assertEqual(ticket_args(c, ticket(c))[-2:], (OWNER,1))
        changed=dict(c);changed["batch_id"]="synthea-new-only-other"
        with self.assertRaises(ValueError):ticket_args(changed,ticket(c))
        other=ticket(c)
        other=FenceTicket(other.candidate,other.lease_owner,0)
        with self.assertRaises(ValueError):ticket_args(c,other)
    def test_single_cursor_rowlock_before_after_both_writes_and_rollback(self):
        c=ctx();p,v=rows();connection=Connection()
        fenced_joint_rollback(connection,c,p,v,ticket(c))
        calls=connection.cur.calls
        sqls=[x[0] for x in calls]
        self.assertEqual(sqls.count("BEGIN;"),1)
        self.assertEqual(sqls.count("ROLLBACK;"),1)
        self.assertEqual(sqls.count(FENCE_SQL),2)
        self.assertEqual(sqls[-1],"ROLLBACK;")
        self.assertLess(sqls.index(FENCE_SQL),sqls.index(next(s for s in sqls if "INSERT INTO cdm.person" in s)))
        self.assertLess(sqls.index(next(s for s in sqls if "INSERT INTO cdm.visit_occurrence" in s)), len(sqls)-2)
        self.assertIn("BLOCKED:EXISTING_TARGET_DRIFT", " ".join(sqls))
        self.assertNotIn("COMMIT;"," ".join(sqls))
    def test_fail_closed_rollback_on_sql_failure(self):
        c=ctx();p,v=rows()
        for step in (4,5,6):  # before lock, SQL DML, final recheck
            with self.subTest(step=step):
                conn=Connection(fail_at=step)
                with self.assertRaises(RuntimeError):
                    fenced_joint_rollback(conn,c,p,v,ticket(c))
                self.assertEqual(conn.cur.calls[-1][0],"ROLLBACK;")
    def test_reject_implicit_connection_transaction(self):
        c=ctx();p,v=rows();conn=Connection();conn.autocommit=False
        with self.assertRaisesRegex(ValueError,"REQUIRES_AUTOCOMMIT_CONN"):
            fenced_joint_rollback(conn,c,p,v,ticket(c))
        self.assertEqual(conn.cur.calls,[])
    def test_sql_live_proof_explicit_rollback_only(self):
        sql=(root/"sql/landing_claim/writer_fence_v1_rollback_proof.sql").read_text()
        self.assertIn("SECURITY DEFINER",sql)
        self.assertIn("SET search_path = pg_catalog, pg_temp",sql)
        self.assertIn("FOR UPDATE NOWAIT",sql)
        self.assertIn("REVOKE ALL ON FUNCTION",sql)
        self.assertIn("GRANT EXECUTE",sql)
        self.assertTrue(sql.rstrip().endswith("AS rollback_proof;"))
        self.assertEqual(len([s for s in sql.splitlines() if s.strip()=="ROLLBACK;"]),1)
        self.assertNotIn("\nCOMMIT;",sql)
        self.assertIn("UPDATE (updated_at)",sql)

if __name__=="__main__":
    unittest.main()
