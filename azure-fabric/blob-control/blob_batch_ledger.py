"""Stage-scoped Fabric batch control; Blob I/O is injected, never in Shared Engine.

SOURCE/CI ONLY until a new synthetic Azure run checks the credential, ETags,
leases and target readback. No Pipeline/Gold authorization is provided here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Protocol

from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.reconciliation.replay import PublicationRecord, decide_replay

CONTRACT = "fabric-blob-batch-control-v1"
STAGES = frozenset({"SILVER_APPROVED", "CANDIDATE_APPROVED", "GOLD_COMMITTED"})
SAFE_HOSPITAL = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")
SAFE_REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{7,65}\Z")
SAFE_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{2,79}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")


class LedgerHold(RuntimeError):
    """Sanitized fail-closed state; never expose Blob response or credentials."""


class BlobMissing(Exception):
    """Exact-key 404 only."""


class BlobConflict(Exception):
    """Confirmed conditional create/CAS/lease conflict only."""


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    etag: str


class BlobControlBackend(Protocol):
    def read(self, key: str) -> Snapshot: ...
    def create(self, key: str, data: bytes) -> str: ...
    def acquire_lease(self, key: str, seconds: int) -> str: ...
    def renew_lease(self, key: str, lease_id: str) -> None: ...
    def cas_control(self, key: str, data: bytes, etag: str, lease_id: str) -> str: ...
    def release_lease(self, key: str, lease_id: str) -> None: ...


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _decode(data: bytes) -> dict:
    if not isinstance(data, bytes) or not 0 < len(data) <= 262144:
        raise LedgerHold("INVALID_JSON_BYTES")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise LedgerHold("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        result = json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError):
        raise LedgerHold("INVALID_JSON") from None
    if not isinstance(result, dict):
        raise LedgerHold("INVALID_JSON_OBJECT")
    return result


def _utc(value: str) -> bool:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0
    except (TypeError, ValueError, AttributeError):
        return False


@dataclass(frozen=True)
class StageScope:
    context: BatchContext
    stage: str
    landing_manifest_sha256: str
    landing_manifest_etag: str
    mapper_version: str
    wheel_version: str
    mapping_profile_sha256: str
    publication_id: str

    def __post_init__(self):
        if not isinstance(self.context, BatchContext):
            raise LedgerHold("BATCH_CONTEXT_REQUIRED")
        c = self.context
        if not (SAFE_HOSPITAL.fullmatch(c.hospital_id)
                and SAFE_HOSPITAL.fullmatch(c.feed_id)
                and SAFE_REQUEST.fullmatch(c.request_id)):
            raise LedgerHold("UNSAFE_IDENTITY_PATH")
        if self.stage not in STAGES:
            raise LedgerHold("UNAPPROVED_STAGE")
        if c.source_system not in ("FHIR_R4", "HL7_V2"):
            raise LedgerHold("UNAPPROVED_SOURCE_FORMAT")
        for value in (self.landing_manifest_sha256, self.mapping_profile_sha256):
            if not isinstance(value, str) or not HEX.fullmatch(value):
                raise LedgerHold("INVALID_SHA256_PIN")
        for value in (self.landing_manifest_etag, self.mapper_version,
                      self.wheel_version, self.publication_id):
            if not isinstance(value, str) or not 0 < len(value) <= 160 or any(
                    ord(ch) < 33 or ord(ch) > 126 for ch in value):
                raise LedgerHold("INVALID_RELEASE_PIN")

    @property
    def root(self) -> str:
        c = self.context
        return f"{c.hospital_id}/{c.feed_id}/{c.request_id}"

    @property
    def source_key(self) -> str:
        return f"clinical/v1/{self.root}/landing-manifest.json"

    @property
    def claim_key(self) -> str:
        return f"_control/v1/{self.root}/{self.stage}/claim.json"

    def identity(self) -> dict:
        c = self.context
        return {
            "hospital_id": c.hospital_id, "feed_id": c.feed_id,
            "source_system": c.source_system, "request_id": c.request_id,
            "batch_id": c.source_batch_id,
            "source_manifest_sha256": c.manifest_sha256.lower(),
            "landing_manifest_sha256": self.landing_manifest_sha256,
            "landing_manifest_etag": self.landing_manifest_etag,
            "processing_version": c.processing_version,
            "mapper_version": self.mapper_version,
            "wheel_version": self.wheel_version,
            "mapping_profile_sha256": self.mapping_profile_sha256,
            "publication_id": self.publication_id,
            "stage": self.stage,
        }

    @property
    def version(self) -> str:
        return _sha(_json(self.identity()))

    @property
    def receipt_key(self) -> str:
        return f"processed/v1/{self.root}/{self.stage}/{self.version}/receipt.json"


@dataclass(frozen=True)
class Claim:
    owner: str
    attempt: int
    etag: str
    lease_id: str


@dataclass(frozen=True)
class TargetProof:
    """Must be independently obtained by the stage owner, never self-generated."""
    stage: str
    publication_id: str
    target_reference: str
    evidence_sha256: str
    verified_at_utc: str
    approval_id: str
    verified: bool

    def verify(self, scope: StageScope) -> None:
        if (self.verified is not True or self.stage != scope.stage
                or self.publication_id != scope.publication_id
                or not isinstance(self.target_reference, str)
                or not 1 <= len(self.target_reference) <= 512
                or any(ord(c) < 33 or ord(c) > 126 for c in self.target_reference)
                or not isinstance(self.evidence_sha256, str)
                or not HEX.fullmatch(self.evidence_sha256)
                or not isinstance(self.approval_id, str) or not self.approval_id.strip()
                or not _utc(self.verified_at_utc)):
            raise LedgerHold("TARGET_PROOF_UNVERIFIED")


def _read(backend: BlobControlBackend, key: str) -> Snapshot | None:
    try:
        result = backend.read(key)
    except BlobMissing:
        return None
    except Exception:
        raise LedgerHold("BLOB_GET_UNKNOWN_HOLD") from None
    if (not isinstance(result, Snapshot) or not isinstance(result.data, bytes)
            or not isinstance(result.etag, str) or not result.etag):
        raise LedgerHold("UNTRUSTED_BLOB_READBACK")
    return result


def _record(scope: StageScope) -> PublicationRecord:
    c = scope.context
    return PublicationRecord(c.hospital_id, c.feed_id, c.source_system,
                             c.request_id, c.manifest_sha256, c.processing_version,
                             scope.publication_id, True)


def precheck(backend: BlobControlBackend, scope: StageScope) -> str:
    """Read-only precheck; SKIP never starts Fabric Capacity."""
    receipt = _read(backend, scope.receipt_key)
    if receipt is not None:
        try:
            obj = _decode(receipt.data)
            proof = TargetProof(**obj["proof"])
            proof.verify(scope)
        except (KeyError, TypeError, LedgerHold):
            return "VERIFY_READONLY"
        if (obj.get("schema_version") != CONTRACT
                or obj.get("identity") != scope.identity()
                or obj.get("version") != scope.version
                or obj.get("status") != "VERIFIED"):
            return "HOLD_CONFLICT"
        # A receipt after an unknown ACK may be durable while its claim is
        # still FINALIZING. Require both immutable receipt and terminal claim.
        control = _read(backend, scope.claim_key)
        if control is None:
            return "VERIFY_READONLY"
        try:
            control_state = _decode(control.data)
        except LedgerHold:
            return "VERIFY_READONLY"
        if control_state.get("identity") != scope.identity():
            return "HOLD_CONFLICT"
        if control_state.get("status") != "COMPLETED":
            return "VERIFY_READONLY"
        # A tiny Manifest GET is cheaper than waking Fabric and catches a
        # changed/deleted source even when a prior receipt is unchanged.
        source = _read(backend, scope.source_key)
        if (source is None or source.etag != scope.landing_manifest_etag
                or _sha(source.data) != scope.landing_manifest_sha256):
            return "VERIFY_READONLY"
        return decide_replay(scope.context, [_record(scope)])
    claim = _read(backend, scope.claim_key)
    if claim is not None:
        try:
            state = _decode(claim.data)
        except LedgerHold:
            return "VERIFY_READONLY"
        if state.get("identity") != scope.identity():
            other = state.get("identity")
            return ("HOLD_VERSION" if isinstance(other, dict) and
                    other.get("batch_id") == scope.context.source_batch_id
                    else "HOLD_CONFLICT")
        return "VERIFY_READONLY" if state.get("status") == "COMPLETED" else "BUSY"
    return decide_replay(scope.context, [])


def verify_source(backend: BlobControlBackend, scope: StageScope) -> None:
    """Manifest LAST, exact SHA/ETag and complete bounded payload inventory."""
    snap = _read(backend, scope.source_key)
    if snap is None:
        raise LedgerHold("LANDING_MANIFEST_MISSING")
    if _sha(snap.data) != scope.landing_manifest_sha256 or snap.etag != scope.landing_manifest_etag:
        raise LedgerHold("LANDING_MANIFEST_DRIFT")
    obj = _decode(snap.data)
    c = scope.context
    if (obj.get("schema_version") != "healthcare-azure-blob-landing-manifest-v1"
            or obj.get("hospital_id") != c.hospital_id
            or obj.get("feed_id") != c.feed_id
            or obj.get("request_id") != c.request_id
            or obj.get("source_manifest_sha256") != c.manifest_sha256
            or obj.get("target_format") != c.source_system):
        raise LedgerHold("LANDING_MANIFEST_IDENTITY_CONFLICT")
    inventory = obj.get("objects")
    if not isinstance(inventory, list) or not 0 < len(inventory) <= 5000:
        raise LedgerHold("LANDING_INVENTORY_INVALID")
    seen = set()
    data_prefix = f"clinical/v1/{scope.root}/{c.source_system}/"
    for entry in inventory:
        if not isinstance(entry, dict):
            raise LedgerHold("LANDING_INVENTORY_INVALID")
        key, digest, etag = (entry.get("blob_key"), entry.get("sha256"),
                             entry.get("etag"))
        if (not isinstance(key, str) or not key.startswith(data_prefix)
                or key in seen or any(v in key for v in ("..", "\\", "%", "?", "#"))
                or not isinstance(digest, str) or not HEX.fullmatch(digest)
                or not isinstance(etag, str) or not etag
                or type(entry.get("size_bytes")) is not int):
            raise LedgerHold("LANDING_INVENTORY_INVALID")
        seen.add(key)
        data = _read(backend, key)
        if (data is None or data.etag != etag or len(data.data) != entry["size_bytes"]
                or _sha(data.data) != digest):
            raise LedgerHold("LANDING_PAYLOAD_DRIFT")


def acquire(backend: BlobControlBackend, scope: StageScope, *,
            owner: str, attempt: int) -> tuple[str, Claim | None]:
    """Only a confirmed first conditional create may take a new claim."""
    if not isinstance(owner, str) or not SAFE_OWNER.fullmatch(owner):
        raise LedgerHold("INVALID_CLAIM_OWNER")
    if type(attempt) is not int or not 1 <= attempt <= 10000:
        raise LedgerHold("INVALID_ATTEMPT")
    state = precheck(backend, scope)
    if state != "NEW":
        return state, None
    verify_source(backend, scope)
    payload = _json({"schema_version": CONTRACT, "identity": scope.identity(),
                     "status": "CLAIMED", "owner": owner, "attempt": attempt})
    try:
        etag = backend.create(scope.claim_key, payload)
    except BlobConflict:
        return precheck(backend, scope), None
    except Exception:
        return "VERIFY_READONLY", None
    if not isinstance(etag, str) or not etag:
        return "VERIFY_READONLY", None
    try:
        actual = _read(backend, scope.claim_key)
        if actual is None or actual.data != payload or actual.etag != etag:
            return "VERIFY_READONLY", None
        lease_id = backend.acquire_lease(scope.claim_key, 60)
        if not isinstance(lease_id, str) or not lease_id:
            return "VERIFY_READONLY", None
    except Exception:
        return "VERIFY_READONLY", None
    return "CLAIMED", Claim(owner, attempt, etag, lease_id)


def finalize(backend: BlobControlBackend, scope: StageScope, claim: Claim,
             proof: TargetProof) -> str:
    """Receipt LAST; target proof MUST precede call; unknown ACK is HOLD.

    A lease renewal plus control CAS fences the caller immediately before
    receipt creation. Cross-blob/Blob-to-Fabric atomicity is NOT claimed.
    """
    proof.verify(scope)
    if (not isinstance(claim, Claim) or not SAFE_OWNER.fullmatch(claim.owner)
            or type(claim.attempt) is not int or claim.attempt < 1
            or not claim.etag or not claim.lease_id):
        raise LedgerHold("INVALID_CLAIM")
    prior = _read(backend, scope.claim_key)
    if prior is None or prior.etag != claim.etag:
        return "VERIFY_READONLY"
    current = _decode(prior.data)
    if (current.get("identity") != scope.identity() or current.get("owner") != claim.owner
            or current.get("attempt") != claim.attempt
            or current.get("status") != "CLAIMED"):
        return "HOLD_CONFLICT"
    finalizing = dict(current, status="FINALIZING")
    try:
        backend.renew_lease(scope.claim_key, claim.lease_id)
        etag = backend.cas_control(scope.claim_key, _json(finalizing),
                                   prior.etag, claim.lease_id)
        observed = _read(backend, scope.claim_key)
        if observed is None or observed.etag != etag or observed.data != _json(finalizing):
            return "VERIFY_READONLY"
        # A second renewal reduces expiry risk; never attempt a lease steal.
        backend.renew_lease(scope.claim_key, claim.lease_id)
    except Exception:
        return "VERIFY_READONLY"
    payload = _json({"schema_version": CONTRACT, "identity": scope.identity(),
                     "version": scope.version, "status": "VERIFIED",
                     "proof": vars(proof)})
    try:
        receipt_etag = backend.create(scope.receipt_key, payload)
    except Exception:
        # Including a 409 or a lost PUT ACK: reconcile by independent target
        # readback in a NEW call, never assume that the receipt committed.
        return "VERIFY_READONLY"
    found = _read(backend, scope.receipt_key)
    if found is None or found.data != payload or found.etag != receipt_etag:
        return "VERIFY_READONLY"
    try:
        backend.renew_lease(scope.claim_key, claim.lease_id)
        backend.cas_control(scope.claim_key, _json(dict(finalizing, status="COMPLETED")),
                            etag, claim.lease_id)
        backend.release_lease(scope.claim_key, claim.lease_id)
    except Exception:
        return "VERIFY_READONLY"
    return "VERIFIED_RECEIPT_WRITTEN"


def reconcile_unknown_finalize(backend: BlobControlBackend, scope: StageScope,
                               claim: Claim, proof: TargetProof) -> str:
    """Recover a lost receipt PUT ACK without creating a second receipt.

    A separately trusted stage owner MUST repeat target physical readback and
    issue a fresh TargetProof. Retain the original valid lease and attempt;
    after lease expiry or an uncertain target state, HOLD for manual review.
    """
    proof.verify(scope)
    if not isinstance(claim, Claim) or not claim.lease_id:
        raise LedgerHold("INVALID_RECOVERY_CLAIM")
    control = _read(backend, scope.claim_key)
    if control is None:
        return "VERIFY_READONLY"
    state = _decode(control.data)
    if (state.get("schema_version") != CONTRACT
            or state.get("identity") != scope.identity()
            or state.get("owner") != claim.owner
            or state.get("attempt") != claim.attempt
            or state.get("status") != "FINALIZING"):
        return "VERIFY_READONLY"
    # Re-validate exact immutable source; no historical source mutation.
    verify_source(backend, scope)
    receipt = _read(backend, scope.receipt_key)
    expected = _json({"schema_version": CONTRACT, "identity": scope.identity(),
                      "version": scope.version, "status": "VERIFIED",
                      "proof": vars(proof)})
    if receipt is None or receipt.data != expected:
        return "VERIFY_READONLY"
    try:
        backend.renew_lease(scope.claim_key, claim.lease_id)
        complete = _json(dict(state, status="COMPLETED"))
        complete_etag = backend.cas_control(
            scope.claim_key, complete, control.etag, claim.lease_id)
        readback = _read(backend, scope.claim_key)
        if (readback is None or readback.etag != complete_etag
                or readback.data != complete):
            return "VERIFY_READONLY"
        backend.release_lease(scope.claim_key, claim.lease_id)
    except Exception:
        return "VERIFY_READONLY"
    return "VERIFIED_RECEIPT_RECOVERED"
