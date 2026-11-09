"""P3.18 SOURCE ONLY: synthetic Ed25519 fixtures, no secrets or cloud use."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "shared-data-engine/src"))
from healthcare_data_engine.security import provider_attestation as t

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

NOW = datetime(2026, 11, 8, 23, 40, 0, tzinfo=timezone.utc)
PROVIDER_SHA = "1" * 40
CONTROLLER_SHA = "2" * 64


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def claims():
    return {
        "schema_version": t.SCHEMA,
        "issuer": t.ISSUER,
        "audience": t.AUDIENCE,
        "purpose": t.PURPOSE,
        "workspace_id": t.WORKSPACE_ID,
        "warehouse_id": t.WAREHOUSE_ID,
        "request_id": t.REQUEST_ID,
        "source_batch_id": t.SOURCE_BATCH_ID,
        "manifest_sha256": t.MANIFEST_SHA,
        "mapping_profile_sha256": t.MAPPING_PROFILE_SHA,
        "f1_release_metadata_sha256": "3" * 64,
        "f2_identity_snapshot_fingerprint": "4" * 64,
        "clinical_review_sha256": "5" * 64,
        "license_review_sha256": "6" * 64,
        "provider_commit_sha": PROVIDER_SHA,
        "native_controller_sha256": CONTROLLER_SHA,
        "nonce_hex": "7" * 32,
        "issued_at_utc": iso(NOW - timedelta(seconds=10)),
        "expires_at_utc": iso(NOW + timedelta(seconds=120)),
    }


class SyntheticDurableClaim:
    """In-memory test fake only; explicitly NOT an actual durable store."""
    def __init__(self):
        self.seen = set()
        self.attempts = []

    def __call__(self, key, expiry):
        self.attempts.append((key, expiry))
        if key in self.seen:
            return False
        self.seen.add(key)
        return True


class G5ProviderAttestationOffline(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.kid = hashlib.sha256(self.pub).hexdigest()
        self.trust = {self.kid: self.pub}
        self.store = SyntheticDurableClaim()

    def sign(self, payload=None, *, key=None, key_id=None):
        value = deepcopy(claims() if payload is None else payload)
        private = self.key if key is None else key
        kid = self.kid if key_id is None else key_id
        return t.canonical_json({
            "payload": value, "key_id": kid,
            "signature_ed25519": base64.b64encode(
                private.sign(t.canonical_json(value))).decode("ascii"),
        })

    def check(self, raw, **overrides):
        params = dict(
            pinned_keys=self.trust,
            expected_provider_commit=PROVIDER_SHA,
            expected_controller_sha256=CONTROLLER_SHA,
            atomic_durable_nonce_claim=self.store,
            now=NOW,
        )
        params.update(overrides)
        return t._verify_source_only(raw, **params)

    def test_valid_transport_only_not_a_writer_capability(self):
        result = self.check(self.sign())
        self.assertEqual(result.status, "G5_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE_AUTHORITY")
        self.assertEqual(result.mapping_profile_sha256, t.MAPPING_PROFILE_SHA)
        self.assertEqual(result.f1_release_metadata_sha256, "3" * 64)
        self.assertEqual(result.f2_identity_snapshot_fingerprint, "4" * 64)
        self.assertFalse(result.candidate_write_authorized)
        self.assertFalse(result.provisional_ids_persisted)
        self.assertFalse(result.gold_committed)
        self.assertEqual(len(self.store.attempts), 1)
        self.assertEqual(self.store.attempts[0][1], NOW + timedelta(seconds=120))

    def test_no_production_keys_or_ledger_and_no_runtime_overrides(self):
        self.assertEqual(t.NATIVE_TRUSTED_PROVIDER_KEYS, {})
        self.assertIsNone(t.NATIVE_PINNED_PROVIDER_COMMIT)
        self.assertIsNone(t.NATIVE_PINNED_CONTROLLER_SHA256)
        self.assertIsNone(t.NATIVE_ATOMIC_DURABLE_NONCE_CLAIM)
        with self.assertRaisesRegex(t.TransportHold, "NOT_ONBOARDED"):
            t.verify_native_handoff_source_only(self.sign())
        for overrides in (
            {"pinned_keys": {}},
            {"expected_provider_commit": "not-a-sha"},
            {"expected_controller_sha256": "a"},
            {"atomic_durable_nonce_claim": None},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(t.TransportHold, "NOT_ONBOARDED"):
                    self.check(self.sign(), **overrides)
                self.assertEqual(self.store.attempts, [])

    def test_nonce_replay_and_ledger_error_fail_closed(self):
        raw = self.sign()
        self.check(raw)
        with self.assertRaisesRegex(t.TransportHold, "REPLAY_OR_LEDGER"):
            self.check(raw)
        self.assertEqual(len(self.store.attempts), 2)
        def uncertain(_k, _e):
            raise TimeoutError("unknown ACK; no retry")
        with self.assertRaisesRegex(t.TransportHold, "LEDGER_UNAVAILABLE"):
            self.check(self.sign(), atomic_durable_nonce_claim=uncertain)

    def test_source_target_and_approval_receipt_binding(self):
        mutations = {
            "schema_version": "wrong-version",
            "issuer": "other-provider",
            "audience": "other-controller",
            "purpose": "WRITER_AUTHORIZED",
            "workspace_id": "other-workspace",
            "warehouse_id": "other-warehouse",
            "request_id": "other-request",
            "source_batch_id": "a" * 64,
            "manifest_sha256": "a" * 64,
            "mapping_profile_sha256": "b" * 64,
            "provider_commit_sha": "f" * 40,
            "native_controller_sha256": "f" * 64,
        }
        for field, change in mutations.items():
            with self.subTest(field=field):
                p = claims()
                p[field] = change
                with self.assertRaisesRegex(t.TransportHold, "SCOPE_OR_CODE_PIN_DRIFT"):
                    self.check(self.sign(p))
                self.assertEqual(self.store.attempts, [])

    def test_every_evidence_sha_is_required_and_signed(self):
        for field in (
            "f1_release_metadata_sha256", "f2_identity_snapshot_fingerprint",
            "clinical_review_sha256", "license_review_sha256",
        ):
            with self.subTest(field=field):
                p = claims()
                p[field] = "not sha"
                with self.assertRaisesRegex(t.TransportHold, "EVIDENCE_DIGEST"):
                    self.check(self.sign(p))
        self.assertEqual(self.store.attempts, [])

    def test_tampering_rejects_signature_before_consuming_nonce(self):
        obj = __import__("json").loads(self.sign().decode("utf-8"))
        obj["payload"]["clinical_review_sha256"] = "e" * 64
        with self.assertRaisesRegex(t.TransportHold, "SIGNATURE_INVALID"):
            self.check(t.canonical_json(obj))
        self.assertEqual(self.store.attempts, [])

    def test_untrusted_key_and_key_id_substitution(self):
        other = Ed25519PrivateKey.generate()
        other_public = other.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        other_id = hashlib.sha256(other_public).hexdigest()
        with self.assertRaisesRegex(t.TransportHold, "KEY_NOT_PINNED"):
            self.check(self.sign(key=other, key_id=other_id))
        with self.assertRaisesRegex(t.TransportHold, "KEY_ID_INVALID"):
            self.check(self.sign(key_id="wrong"))
        with self.assertRaisesRegex(t.TransportHold, "KEY_NOT_PINNED"):
            self.check(self.sign(), pinned_keys={self.kid: b"x" * 32})
        self.assertEqual(self.store.attempts, [])

    def test_expired_future_and_long_ttl_are_rejected(self):
        bad_dates = [
            (NOW - timedelta(minutes=7), NOW - timedelta(minutes=1)),
            (NOW + timedelta(minutes=2), NOW + timedelta(minutes=4)),
            (NOW - timedelta(minutes=6), NOW + timedelta(minutes=1)),
            (NOW - timedelta(seconds=5), NOW - timedelta(seconds=5)),
        ]
        for issued, expires in bad_dates:
            with self.subTest(issued=issued, expires=expires):
                p = claims()
                p["issued_at_utc"], p["expires_at_utc"] = iso(issued), iso(expires)
                with self.assertRaisesRegex(t.TransportHold, "EXPIRED_FUTURE_OR_UNBOUNDED"):
                    self.check(self.sign(p))
        self.assertEqual(self.store.attempts, [])

    def test_rejects_missing_extra_duplicate_or_noncanonical_json(self):
        original = self.sign()
        for raw in (
            original + b"\n",
            original.replace(b'"key_id":', b'"unexpected":1,"key_id":', 1),
            original.replace(b'"key_id":', b'"key_id":"duplicate","key_id":', 1),
            b'{"key_id":"bad"}',
            b"\xff",
            b"x" * (t.MAX_ENVELOPE_BYTES + 1),
        ):
            with self.subTest(raw=raw[:40]):
                with self.assertRaises(t.TransportHold):
                    self.check(raw)
        p = claims()
        del p["license_review_sha256"]
        with self.assertRaisesRegex(t.TransportHold, "PAYLOAD_SCHEMA"):
            self.check(self.sign(p))
        p = claims()
        p["untrusted_approval"] = True
        with self.assertRaisesRegex(t.TransportHold, "PAYLOAD_SCHEMA"):
            self.check(self.sign(p))
        self.assertEqual(self.store.attempts, [])

    def test_no_boolean_flag_bypass_even_with_valid_signature(self):
        p = claims()
        p["candidate_write_authorized"] = True
        with self.assertRaisesRegex(t.TransportHold, "PAYLOAD_SCHEMA"):
            self.check(self.sign(p))
        p = claims()
        p["gold_committed"] = True
        with self.assertRaisesRegex(t.TransportHold, "PAYLOAD_SCHEMA"):
            self.check(self.sign(p))
        self.assertEqual(self.store.attempts, [])

    def test_fail_if_claim_returns_falsy_or_not_bool_true(self):
        for answer in (False, None, 1, "OK"):
            with self.subTest(answer=answer):
                with self.assertRaisesRegex(t.TransportHold, "REPLAY_OR_LEDGER"):
                    self.check(self.sign(), atomic_durable_nonce_claim=lambda *_: answer)

    def test_wrong_clock_and_wrong_nonce_hold(self):
        with self.assertRaisesRegex(t.TransportHold, "TRUSTED_CLOCK_REQUIRED"):
            self.check(self.sign(), now=NOW.replace(tzinfo=None))
        p = claims()
        p["nonce_hex"] = "short"
        with self.assertRaisesRegex(t.TransportHold, "PROVENANCE_NONCE_INVALID"):
            self.check(self.sign(p))
        self.assertEqual(self.store.attempts, [])


if __name__ == "__main__":
    unittest.main()
