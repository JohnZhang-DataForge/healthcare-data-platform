"""SOURCE/CI-only Blob control positive/negative/concurrency tests; no Azure."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
import json
import threading
import unittest

from blob_batch_ledger import (
    BlobConflict, BlobMissing, Claim, LedgerHold, Snapshot, StageScope,
    TargetProof, acquire, finalize, precheck, reconcile_unknown_finalize, verify_source,
)
from azure_blob_backend import AzureBlobBatchBackend
from healthcare_data_engine.models.batch_context import BatchContext


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class MemoryBackend:
    """Deterministic atomic fake. Its success is NOT Azure acceptance."""
    def __init__(self):
        self.items = {}
        self.leases = {}
        self.lock = threading.RLock()
        self.counter = 0
        self.fail_create_after_write = set()
        self.fail_cas = False

    def _put(self, key, data):
        self.counter += 1
        etag = f'"etag-{self.counter}"'
        self.items[key] = Snapshot(data, etag)
        return etag

    def seed(self, key, data):
        with self.lock:
            return self._put(key, data)

    def read(self, key):
        with self.lock:
            if key not in self.items:
                raise BlobMissing()
            return self.items[key]

    def create(self, key, data):
        with self.lock:
            if key in self.items:
                raise BlobConflict()
            etag = self._put(key, data)
            if key in self.fail_create_after_write:
                raise OSError("simulated ACK loss")
            return etag

    def acquire_lease(self, key, seconds):
        with self.lock:
            if key in self.leases or key not in self.items or seconds != 60:
                raise BlobConflict()
            lease = "lease-" + str(self.counter)
            self.leases[key] = lease
            return lease

    def renew_lease(self, key, lease_id):
        if self.leases.get(key) != lease_id:
            raise BlobConflict()

    def cas_control(self, key, data, etag, lease_id):
        with self.lock:
            if self.fail_cas or self.leases.get(key) != lease_id:
                raise BlobConflict()
            if self.items[key].etag != etag:
                raise BlobConflict()
            return self._put(key, data)

    def release_lease(self, key, lease_id):
        self.renew_lease(key, lease_id)
        del self.leases[key]


class BatchLedgerTest(unittest.TestCase):
    def setUp(self):
        self.backend = MemoryBackend()
        self.payload = b'{"resourceType":"Bundle","entry":[]}'
        self.scope = self.make_scope()
        self.seed_manifest(self.scope)

    def make_scope(self, *, hospital="atlanta-hospital-a", stage="SILVER_APPROVED",
                   processing="0.1.11", profile="a"*64, request="atlanta-fhir-gh-98765432100"):
        context = BatchContext(
            hospital_id=hospital, feed_id="atlanta-hospital-a-fhir-r4",
            source_system="FHIR_R4", request_id=request,
            manifest_sha256="b"*64, processing_version=processing,
            processing_run_id="unit-567", source_version="v1",
            source_ingest_date=date(2026, 11, 9),
            processed_at=datetime(2026, 11, 9, tzinfo=timezone.utc))
        manifest = {
            "schema_version": "healthcare-azure-blob-landing-manifest-v1",
            "hospital_id": context.hospital_id, "feed_id": context.feed_id,
            "request_id": context.request_id,
            "source_manifest_sha256": context.manifest_sha256,
            "target_format": context.source_system,
            "objects": [{
                "blob_key": f"clinical/v1/{context.hospital_id}/{context.feed_id}/{context.request_id}/FHIR_R4/Bundle-01.json",
                "sha256": sha(self.payload), "etag": '"payload-1"',
                "size_bytes": len(self.payload)
            }]
        }
        raw = canonical(manifest)
        return StageScope(
            context, stage, sha(raw), '"manifest-1"', "mapper-v1",
            "0.1.11", profile, "approved-release-987")

    def seed_manifest(self, scope):
        context = scope.context
        key = f"clinical/v1/{scope.root}/FHIR_R4/Bundle-01.json"
        manifest = {
            "schema_version": "healthcare-azure-blob-landing-manifest-v1",
            "hospital_id": context.hospital_id, "feed_id": context.feed_id,
            "request_id": context.request_id,
            "source_manifest_sha256": context.manifest_sha256,
            "target_format": context.source_system,
            "objects": [{
                "blob_key": key, "sha256": sha(self.payload),
                "etag": '"payload-1"', "size_bytes": len(self.payload)
            }]
        }
        self.backend.items[key] = Snapshot(self.payload, '"payload-1"')
        self.backend.items[scope.source_key] = Snapshot(canonical(manifest), '"manifest-1"')

    def proof(self, scope=None):
        scope = scope or self.scope
        return TargetProof(
            scope.stage, scope.publication_id,
            "fabric://healthcare-omop/verified-target",
            "f"*64, "2026-11-09T13:20:00Z", "reviewed-approval-987", True)

    def test_complete_and_replay_capacity_offline(self):
        self.assertEqual(precheck(self.backend, self.scope), "NEW")
        result, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(result, "CLAIMED")
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFIED_RECEIPT_WRITTEN")
        self.assertEqual(precheck(self.backend, self.scope), "SKIP")
        self.assertEqual(acquire(self.backend, self.scope, owner="runner-02", attempt=1)[0], "SKIP")
        self.assertEqual(sum(p.startswith("processed/v1/") for p in self.backend.items), 1)
        self.assertEqual(sum(p.startswith("clinical/v1/") for p in self.backend.items), 2)

    def test_parallel_single_winner(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda owner: acquire(self.backend, self.scope, owner=owner, attempt=1)[0],
                ("runner-01", "runner-02")))
        self.assertEqual(results.count("CLAIMED"), 1)
        self.assertIn(results.count("BUSY") + results.count("VERIFY_READONLY"), (1,))
        self.assertEqual(sum(p.startswith("_control/v1/") for p in self.backend.items), 1)

    def test_stale_worker_and_etag_race_hold(self):
        state, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(state, "CLAIMED")
        forged = Claim(claim.owner, claim.attempt, '"stale"', claim.lease_id)
        self.assertEqual(finalize(self.backend, self.scope, forged, self.proof()), "VERIFY_READONLY")
        self.backend.leases[self.scope.claim_key] = "new-owner-lease"
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()), "VERIFY_READONLY")
        self.assertNotIn(self.scope.receipt_key, self.backend.items)

    def test_unknown_claim_ack_no_second_write(self):
        self.backend.fail_create_after_write.add(self.scope.claim_key)
        self.assertEqual(acquire(self.backend, self.scope, owner="runner-01", attempt=1)[0],
                         "VERIFY_READONLY")
        self.assertEqual(precheck(self.backend, self.scope), "BUSY")
        self.assertEqual(sum(p.startswith("_control/v1/") for p in self.backend.items), 1)

    def test_unknown_receipt_ack_is_not_skip(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        self.backend.fail_create_after_write.add(self.scope.receipt_key)
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()), "VERIFY_READONLY")
        self.assertIn(self.scope.receipt_key, self.backend.items)
        self.assertEqual(precheck(self.backend, self.scope), "VERIFY_READONLY")

    def test_unknown_receipt_ack_reconciles_under_valid_lease(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        self.backend.fail_create_after_write.add(self.scope.receipt_key)
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFY_READONLY")
        self.assertEqual(precheck(self.backend, self.scope), "VERIFY_READONLY")
        self.assertEqual(reconcile_unknown_finalize(
            self.backend, self.scope, claim, self.proof()),
            "VERIFIED_RECEIPT_RECOVERED")
        self.assertEqual(precheck(self.backend, self.scope), "SKIP")

    def test_receipt_unknown_ack_recovery_stale_lease_holds(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        self.backend.fail_create_after_write.add(self.scope.receipt_key)
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFY_READONLY")
        self.backend.leases[self.scope.claim_key] = "expired-new-holder"
        self.assertEqual(reconcile_unknown_finalize(
            self.backend, self.scope, claim, self.proof()), "VERIFY_READONLY")
        self.assertEqual(precheck(self.backend, self.scope), "VERIFY_READONLY")

    def test_completed_receipt_source_manifest_drift_not_skip(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFIED_RECEIPT_WRITTEN")
        self.backend.items[self.scope.source_key] = Snapshot(b"{}",
                                                            self.scope.landing_manifest_etag)
        self.assertEqual(precheck(self.backend, self.scope), "VERIFY_READONLY")

    def test_manifest_drift_blocks_new_claim(self):
        self.backend.items[self.scope.source_key] = Snapshot(b"{}", '"manifest-1"')
        with self.assertRaisesRegex(LedgerHold, "LANDING_MANIFEST_DRIFT"):
            acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertNotIn(self.scope.claim_key, self.backend.items)

    def test_payload_drift_blocks_claim(self):
        key = f"clinical/v1/{self.scope.root}/FHIR_R4/Bundle-01.json"
        self.backend.items[key] = Snapshot(b"changed", '"payload-1"')
        with self.assertRaisesRegex(LedgerHold, "LANDING_PAYLOAD_DRIFT"):
            acquire(self.backend, self.scope, owner="runner-01", attempt=1)

    def test_wrong_hospital_and_version_hold(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        changed = self.make_scope(processing="0.1.12")
        self.assertEqual(precheck(self.backend, changed), "HOLD_VERSION")
        alternate = self.make_scope(hospital="johns-creek-hospital")
        self.assertNotEqual(self.scope.claim_key, alternate.claim_key)
        self.assertEqual(precheck(self.backend, alternate), "NEW")

    def test_silver_does_not_approve_gold(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFIED_RECEIPT_WRITTEN")
        gold = self.make_scope(stage="GOLD_COMMITTED")
        self.assertEqual(precheck(self.backend, gold), "NEW")
        with self.assertRaisesRegex(LedgerHold, "TARGET_PROOF_UNVERIFIED"):
            self.proof().verify(gold)

    def test_unverified_or_partial_proof_no_receipt(self):
        status, claim = acquire(self.backend, self.scope, owner="runner-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        bad = TargetProof(self.scope.stage, self.scope.publication_id,
                          "fabric://target", "f"*64, "2026-11-09T13:20:00Z",
                          "approval", False)
        with self.assertRaises(LedgerHold):
            finalize(self.backend, self.scope, claim, bad)
        self.assertNotIn(self.scope.receipt_key, self.backend.items)
        self.backend.fail_cas = True
        self.assertEqual(finalize(self.backend, self.scope, claim, self.proof()),
                         "VERIFY_READONLY")

    def test_conflicting_receipt_never_skip(self):
        self.backend.items[self.scope.receipt_key] = Snapshot(
            canonical({"status": "VERIFIED", "schema_version": "wrong"}), '"fake"')
        self.assertEqual(precheck(self.backend, self.scope), "VERIFY_READONLY")

    def test_no_delete_and_prefix_allowlist(self):
        backend = AzureBlobBatchBackend(object())
        for key in ("clinical/v1/atlanta-hospital-a/raw.json",
                    "_control/v1/../claim.json",
                    "processed/v1/a/../../receipt.json",
                    "_control/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/"
                    "atlanta-fhir-gh-98765432100/GOLD_COMMITTED/../claim.json"):
            with self.assertRaises(LedgerHold):
                backend.create(key, b"{}")
        self.assertFalse(hasattr(backend, "delete"))
        self.assertFalse(hasattr(backend, "copy"))
        self.assertFalse(hasattr(backend, "clear"))

    def test_path_traversal_and_invalid_sha(self):
        with self.assertRaisesRegex(LedgerHold, "UNSAFE_IDENTITY_PATH"):
            self.make_scope(hospital="../another")
        with self.assertRaisesRegex(LedgerHold, "INVALID_SHA256_PIN"):
            self.make_scope(profile="not-a-pin")
        with self.assertRaisesRegex(LedgerHold, "UNAPPROVED_STAGE"):
            self.make_scope(stage="SILVER_APPROVED/../../GOLD_COMMITTED")


if __name__ == "__main__":
    unittest.main()
