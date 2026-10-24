"""Strict NEW_ONLY Claim owner/attempt fence and lease heartbeat regressions."""
import pathlib
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/"apps"/"landing_claim"))
from batch_ledger import Candidate,ClaimError
from lease_fence import FenceTicket,assert_live_fence,renew_live_fence,ticket_from_claim

B="synthea-new-only-gh-38497355290"
URI=f"s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id={B}/manifest.json"
SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
OWNER="a"*48
def ticket(attempt=1,owner=OWNER):
    return FenceTicket(Candidate("synthea",B,SHA,URI),owner,attempt)

UNSET=object()

class Cursor:
    def __init__(self, row=UNSET, alive=True, renewed=True):
        self.calls=[]
        self.row=row if row is not UNSET else (SHA,URI,"PROCESSING",1,OWNER,"future timestamp")
        self.alive=alive
        self.renewed=renewed
    def execute(self,sql,values=None):
        self.calls.append((sql,values))
    def fetchone(self):
        sql=self.calls[-1][0]
        if "FOR UPDATE NOWAIT" in sql: return self.row
        if "SELECT %s > clock_timestamp()" in sql: return (self.alive,)
        if "RETURNING attempt_count" in sql: return (1,) if self.renewed else None
        raise AssertionError(sql)

class ClaimFenceTests(unittest.TestCase):
    def test_owner_receives_fence_only_after_real_claim(self):
        claimed=SimpleNamespace(decision="CLAIMED",attempt_count=1,lease_owner=OWNER)
        self.assertEqual(ticket_from_claim(ticket().candidate,claimed),ticket())
        for dec in ("BUSY","SKIP_COMPLETED","FAILED_NEEDS_RECONCILIATION","BLOCKED_EXPIRED_LEASE"):
            with self.subTest(dec=dec),self.assertRaisesRegex(ClaimError,"REQUIRES_FRESH_CLAIM"):
                ticket_from_claim(ticket().candidate,SimpleNamespace(decision=dec,lease_owner=OWNER,attempt_count=1))

    def test_valid_ticket_row_lock_and_postlock_db_time(self):
        cur=Cursor()
        assert_live_fence(cur,ticket())
        self.assertEqual(len(cur.calls),2)
        self.assertIn("FOR UPDATE NOWAIT",cur.calls[0][0])
        self.assertIn("clock_timestamp()",cur.calls[1][0])
        self.assertEqual(cur.calls[0][1],("synthea",B))
        self.assertEqual(cur.calls[1][1],("future timestamp",))

    def test_missing_claim_and_every_stale_state_fail_closed(self):
        rows=[(None,"FENCE_CLAIM_ABSENT"),
              ((SHA,URI,"COMPLETED",1,OWNER,"future"),"FENCE_NOT_PROCESSING"),
              ((SHA,URI,"FAILED",1,OWNER,"future"),"FENCE_NOT_PROCESSING"),
              (("f"*64,URI,"PROCESSING",1,OWNER,"future"),"FENCE_MANIFEST_DRIFT"),
              ((SHA,URI.replace("2026-10-14","2026-10-13"),"PROCESSING",1,OWNER,"future"),"FENCE_MANIFEST_DRIFT"),
              ((SHA,URI,"PROCESSING",2,OWNER,"future"),"FENCE_STALE_ATTEMPT_OR_OWNER"),
              ((SHA,URI,"PROCESSING",1,"b"*48,"future"),"FENCE_STALE_ATTEMPT_OR_OWNER")]
        for row,error in rows:
            cur=Cursor(row=row)
            with self.subTest(error=error,row=row),self.assertRaisesRegex(ClaimError,error):
                assert_live_fence(cur,ticket())
        with self.assertRaisesRegex(ClaimError,"FENCE_LEASE_EXPIRED"):
            assert_live_fence(Cursor(alive=False),ticket())

    def test_invalid_attempt_token_and_unrelated_batch_rejected_before_sql(self):
        items=[ticket(attempt=0),ticket(attempt=True),ticket(owner="abc"),
               FenceTicket(Candidate("synthea","task004-airflow-1",SHA,
                   URI.replace(B,"task004-airflow-1")),OWNER,1),
               FenceTicket(Candidate("synthea",B,"e"*64,URI),OWNER,-1)]
        for x in items:
            cur=Cursor()
            with self.subTest(item=x),self.assertRaises(ClaimError):
                assert_live_fence(cur,x)
            self.assertEqual(cur.calls,[])

    def test_heartbeat_cannot_renew_expired_or_wrong_attempt(self):
        for lease in (0,29,3601,False):
            with self.subTest(lease=lease),self.assertRaisesRegex(ClaimError,"FENCE_LEASE_SECONDS"):
                renew_live_fence(Cursor(),ticket(),lease_seconds=lease)
        c=Cursor()
        renew_live_fence(c,ticket(),lease_seconds=900)
        self.assertEqual(len(c.calls),3)
        self.assertIn("lease_expires_at>clock_timestamp()",c.calls[2][0])
        self.assertEqual(c.calls[2][1],(900,"synthea",B,SHA,URI,OWNER,1))
        with self.assertRaisesRegex(ClaimError,"FENCE_RENEWAL_RACE"):
            renew_live_fence(Cursor(renewed=False),ticket())
        with self.assertRaisesRegex(ClaimError,"FENCE_LEASE_EXPIRED"):
            renew_live_fence(Cursor(alive=False),ticket())
    def test_never_claim_or_commit_inside_fence(self):
        path=pathlib.Path(__file__).resolve().parents[2]/"apps"/"landing_claim"/"lease_fence.py"
        source=path.read_text()
        self.assertNotIn("conn.commit(",source)
        self.assertNotIn("conn.rollback(",source)
        self.assertNotIn("UPDATE cdm.",source)
        self.assertIn("FOR UPDATE NOWAIT",source)
        self.assertIn("attempt_count=%s",source)
        self.assertIn("lease_expires_at>clock_timestamp()",source)

if __name__=="__main__":unittest.main()
