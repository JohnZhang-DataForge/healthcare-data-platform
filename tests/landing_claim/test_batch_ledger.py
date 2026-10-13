"""No database credentials required: validate claim guards and decision protocol."""
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parents[2] / "apps" / "landing_claim"))
from batch_ledger import Candidate, ClaimError, claim, mark_completed, mark_failed


def candidate(batch="demo-001", sha="a"*64):
    return Candidate("synthea", batch, sha,
       "s3://health-landing/source=synthea/source_version=v3.3.0/"
       f"ingest_date=2026-10-13/batch_id={batch}/manifest.json")


class Transaction:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


class Cursor:
    def __init__(self, insert_rowcount, existing=None, updated=1, update_result=None):
        self.calls = []
        self.rowcount = insert_rowcount
        self.existing = existing
        self.updated = updated
        self.update_result = update_result
        self.last_query = ""

    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params):
        self.calls.append((sql, params))
        self.last_query = sql
        if sql.lstrip().startswith("INSERT"):
            self.rowcount = self.insert_rowcount
        elif sql.lstrip().startswith("UPDATE"):
            self.rowcount = self.updated
    def fetchone(self):
        if "SELECT manifest_sha256" in self.last_query:
            return self.existing
        return (self.update_result,)


class Conn:
    def __init__(self, cursor):
        self.cur = cursor
    def transaction(self):
        return Transaction()
    def cursor(self):
        return self.cur


class AtomicClaimTests(unittest.TestCase):
    def test_valid_candidate(self):
        candidate().check()

    def test_bad_uri_identity_sha_and_batch(self):
        for c in [candidate(sha="z"*64), candidate(batch="../oops"),
                  Candidate("other", "abc", "a"*64, candidate().manifest_uri),
                  Candidate("synthea", "abc", "a"*64, "https://example.test/object")]:
            with self.subTest(c=c), self.assertRaises(ClaimError):
                c.check()

    def test_unverified_discovery_rejected(self):
        with self.assertRaisesRegex(ClaimError, "NOT_VERIFIED"):
            Candidate.from_discovery({"status":"UPLOADING"})

    def test_first_claim_insert_wins(self):
        cur = Cursor(insert_rowcount=1)
        got = claim(Conn(cur), candidate())
        self.assertEqual(got.decision, "CLAIMED")
        self.assertEqual(got.attempt_count, 1)
        self.assertEqual(len(got.lease_owner), 48)
        self.assertIn("ON CONFLICT", cur.calls[0][0])

    def test_second_claim_with_live_lease_is_busy(self):
        c = candidate()
        cur = Cursor(0, existing=(c.manifest_sha256,c.manifest_uri,"PROCESSING",1,False))
        got = claim(Conn(cur), c)
        self.assertEqual(got.decision, "BUSY")
        self.assertIn("FOR UPDATE", cur.calls[1][0])

    def test_expired_lease_never_auto_stolen(self):
        c = candidate()
        cur = Cursor(0, existing=(c.manifest_sha256,c.manifest_uri,"PROCESSING",1,True))
        got = claim(Conn(cur), c, retry_failed=True)
        self.assertEqual(got.decision, "BLOCKED_EXPIRED_LEASE")
        self.assertEqual(len(cur.calls), 2)

    def test_different_sha_or_uri_blocked(self):
        c = candidate()
        for old in [("b"*64, c.manifest_uri), (c.manifest_sha256,"s3://other/batch")]:
            cur = Cursor(0,existing=(old[0],old[1],"FAILED",1,False))
            with self.subTest(old=old), self.assertRaisesRegex(ClaimError, "IMMUTABLE_MANIFEST_DRIFT"):
                claim(Conn(cur), c, retry_failed=True)

    def test_completed_skips_and_failed_requires_retry_gate(self):
        c = candidate()
        for status, expected in [("COMPLETED","SKIP_COMPLETED"),
                                 ("FAILED","FAILED_NEEDS_RECONCILIATION")]:
            cur = Cursor(0,existing=(c.manifest_sha256,c.manifest_uri,status,2,False))
            self.assertEqual(claim(Conn(cur),c).decision, expected)

    def test_explicit_failed_retry_renews_owner(self):
        c = candidate()
        cur = Cursor(0,existing=(c.manifest_sha256,c.manifest_uri,"FAILED",2,False),
                     update_result=3)
        got = claim(Conn(cur),c,retry_failed=True)
        self.assertEqual(got.decision,"CLAIMED")
        self.assertEqual(got.attempt_count,3)

    def test_completion_needs_digest_and_live_owner(self):
        c=candidate()
        for digest in ["invalid",""]:
            with self.assertRaisesRegex(ClaimError,"RECONCILIATION"):
                mark_completed(Conn(Cursor(1)),c,lease_owner="a"*48,
                               reconciliation_sha256=digest)
        cur=Cursor(1,updated=0)
        with self.assertRaisesRegex(ClaimError,"STALE_OR_WRONG_OWNER"):
            mark_completed(Conn(cur),c,lease_owner="a"*48,reconciliation_sha256="f"*64)

    def test_failure_requires_matching_live_owner(self):
        c=candidate()
        with self.assertRaisesRegex(ClaimError,"INVALID_LEASE_TOKEN"):
            mark_failed(Conn(Cursor(1)),c,lease_owner="incorrect")
        with self.assertRaisesRegex(ClaimError,"STALE_OR_WRONG_OWNER"):
            mark_failed(Conn(Cursor(1,updated=0)),c,lease_owner="a"*48)

    def test_lease_bounds(self):
        for lease in [0,29,3601]:
            with self.assertRaisesRegex(ClaimError,"LEASE_SECONDS"):
                claim(Conn(Cursor(1)),candidate(),lease_seconds=lease)


if __name__ == "__main__":
    unittest.main()
