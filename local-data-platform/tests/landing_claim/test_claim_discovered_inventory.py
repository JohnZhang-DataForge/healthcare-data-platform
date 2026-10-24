"""Discovery XCom -> guarded PostgreSQL ledger intake contract."""
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "landing_claim"))
from batch_ledger import ClaimError, ClaimResult
from claim_discovered_inventory import parse_inventory, build_report, run, revalidate_manifest_sha

def preview(batch="existing-001", count=1, truncated=False):
    return json.dumps({
        "status": "READ_ONLY_DISCOVERED", "ready_count": count,
        "ready_batches_preview": [{
            "source": "synthea", "source_version": "v3.3.0",
            "ingest_date": "2026-10-13", "batch_id": batch,
            "status": "INTAKE_VERIFIED", "manifest_sha256": "a"*64,
            "manifest_uri": f"s3://health-landing/source=synthea/"
                f"source_version=v3.3.0/ingest_date=2026-10-13/"
                f"batch_id={batch}/manifest.json",
        }], "quarantined_count": 1,
        "preview_truncated": truncated,
        "processing_authorized": False, "database_mutation": False,
    })

def preview_many(count: int):
    """Generated 100-row maximum preview, with optional truncation."""
    obj = json.loads(preview())
    row = obj["ready_batches_preview"][0]
    entries = []
    for i in range(min(count, 100)):
        batch = f"batch-{i:03d}"
        entries.append(dict(row, batch_id=batch,
            manifest_uri=row["manifest_uri"].replace("existing-001", batch)))
    obj["ready_batches_preview"] = entries
    obj["ready_count"] = count
    obj["preview_truncated"] = count > 100
    return json.dumps(obj)


class FakeCursor:
    def __init__(self, legacy=False, current=None):
        self.legacy = legacy
        self.current = current
        self.last = ""
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, parameters):
        self.last = sql
        assert parameters and all(isinstance(x, str) for x in parameters)
    def fetchone(self):
        if "task004_batch_ledger" in self.last:
            return (1 if self.legacy else 0,)
        return self.current

class DB:
    def __init__(self, legacy=False, current=None):
        self.legacy=legacy;self.current=current
        self.queries=0
    def cursor(self):
        self.queries+=1
        return FakeCursor(self.legacy,self.current)

class IntegrationTest(unittest.TestCase):
    def test_actual_unclaimed_history_is_observation_only(self):
        db=DB()
        result=run(preview(), db)
        self.assertEqual(result["decision_counts"], {"OBSERVED_ONLY": 1})
        self.assertEqual(result["claim_count"],0)
        self.assertFalse(result["claim_enabled"])
        self.assertEqual(db.queries,1)

    def test_legacy_batch_always_excluded_even_when_allowlisted(self):
        db=DB(legacy=True)
        result=run(preview(),db,enabled=True,allowlist=frozenset(["existing-001"]))
        self.assertEqual(result["decision_counts"], {"SKIP_LEGACY_BATCH":1})
        self.assertEqual(result["claim_count"],0)

    def test_explicit_authorized_new_manifest_calls_atomic_ledger(self):
        candidates=parse_inventory(preview())
        with patch("claim_discovered_inventory.revalidate_manifest_sha") as check, \
             patch("claim_discovered_inventory.claim",
                   return_value=ClaimResult("CLAIMED",1,"a"*48)) as claim:
            result=build_report(candidates,db=DB(),enabled=True,
                               allowlist=frozenset(["existing-001"]),s3=object())
            check.assert_called_once()
            claim.assert_called_once()
            self.assertEqual(result["claim_count"],1)

    def test_unauthorized_allowlist_is_not_enough(self):
        result=run(preview(),DB(),enabled=False,
                   allowlist=frozenset(["existing-001"]))
        self.assertEqual(result["decision_counts"], {"OBSERVED_ONLY":1})
        with self.assertRaisesRegex(ClaimError, "EMPTY_CLAIM_ALLOWLIST"):
            run(preview(),DB(),enabled=True)

    def test_same_batch_identity_drift_is_blocked_without_claim(self):
        c=parse_inventory(preview())[0]
        with self.assertRaisesRegex(ClaimError,"IMMUTABLE_MANIFEST_DRIFT"):
            run(preview(),DB(current=("f"*64,c.manifest_uri,"COMPLETED",1)))

    def test_completed_and_failed_are_not_claimed(self):
        c=parse_inventory(preview())[0]
        for status,decision in [("COMPLETED","SKIP_COMPLETED"),
                                ("FAILED","FAILED_NEEDS_RECONCILIATION"),
                                ("PROCESSING","BUSY_OR_EXPIRED_LEASE")]:
            with self.subTest(status=status):
                r=run(preview(),DB(current=(c.manifest_sha256,
                   c.manifest_uri,status,1)),enabled=True,
                   allowlist=frozenset(["existing-001"]))
                self.assertEqual(r["decision_counts"],{decision:1})

    def test_truncated_or_unverified_preview_fails_closed(self):
        for raw in [preview(truncated=True), preview(count=3),
                    preview().replace("READ_ONLY_DISCOVERED","BROKEN"),
                    preview().replace('"database_mutation": false',
                                      '"database_mutation": true'),
                    "{}","bad json"]:
            with self.subTest(raw=raw[:24]),self.assertRaises(ClaimError):
                parse_inventory(raw)

    def test_scheduled_readonly_handles_26_to_100_ready_batches(self):
        for count in (26, 35, 100):
            with self.subTest(count=count):
                db = DB()
                result = run(preview_many(count), db)
                self.assertEqual(result["input_count"], count)
                self.assertEqual(result["inventory_ready_count"], count)
                self.assertEqual(result["evaluation_scope"], "COMPLETE_INVENTORY")
                self.assertEqual(result["decision_counts"], {"OBSERVED_ONLY": count})
                self.assertFalse(result["claim_enabled"])
                self.assertEqual(result["claim_count"], 0)
                self.assertEqual(db.queries, count)

    def test_over_100_ready_bounded_observation_without_claim(self):
        db = DB()
        result = run(preview_many(107), db)
        self.assertEqual(result["input_count"], 100)
        self.assertEqual(result["inventory_ready_count"], 107)
        self.assertTrue(result["preview_truncated"])
        self.assertEqual(result["evaluation_scope"], "PREVIEW_ONLY")
        self.assertEqual(result["decision_counts"], {"OBSERVED_ONLY": 100})
        self.assertFalse(result["claim_enabled"])
        self.assertEqual(result["claim_count"], 0)
        self.assertEqual(db.queries, 100)

    def test_claim_enabled_rejects_truncated_inventory_before_db_access(self):
        db = DB()
        with self.assertRaisesRegex(ClaimError, "DISCOVERY_SAFETY_GATE"):
            run(preview_many(101), db, enabled=True,
                allowlist=frozenset(["batch-000"]))
        self.assertEqual(db.queries, 0)

    def test_invalid_preview_metadata_and_oversize_fail_closed(self):
        base = json.loads(preview_many(101))
        full = json.loads(preview_many(100))
        bad = [
            {**base, "preview_truncated": False},
            {**full, "preview_truncated": True},
            {**base, "ready_count": 99},
            {**base, "ready_batches_preview": []},
            {**full, "ready_count": True},
            {**full, "quarantined_count": -1},
            {**full, "processing_authorized": True},
            {**full, "database_mutation": True},
            {**full, "ready_batches_preview":
                full["ready_batches_preview"] + full["ready_batches_preview"]},
        ]
        for obj in bad:
            with self.subTest(count=obj.get("ready_count"),
                              rows=len(obj.get("ready_batches_preview", []))):
                with self.assertRaises(ClaimError):
                    parse_inventory(json.dumps(obj), allow_truncated_readonly=True)

    def test_s3_revalidation_detects_changed_manifest(self):
        c=parse_inventory(preview())[0]
        class Body:
            def read(self,n): return b"new data"
        class S3:
            def get_object(self,**kwargs): return {"ContentLength":8,"Body":Body()}
        with self.assertRaisesRegex(ClaimError,"MANIFEST_CHANGED"):
            revalidate_manifest_sha(S3(),c)

if __name__ == "__main__": unittest.main()
