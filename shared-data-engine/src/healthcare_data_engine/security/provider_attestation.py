"""P3.18 SOURCE-ONLY Ed25519 evidence transport contract for Fabric G5.

No production issuer key, trusted Native replay store, writer capability,
clinical/license authorization, Fabric I/O or durable ID allocation here.
This verifier MUST NOT be invoked from Notebook parameters or Pipeline flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import binascii
import hashlib
import json
import re
from typing import Callable, Mapping

SCHEMA = "fabric-g5-provider-attestation-v1"  # Legacy human-review envelope
TECHNICAL_SCHEMA = "fabric-g5-technical-evidence-transport-v2"  # Legacy frozen FHIR
DYNAMIC_TECHNICAL_SCHEMA = "fabric-g5-technical-evidence-transport-v3"
SOURCE_FORMATS = frozenset({"FHIR_R4", "HL7_V2"})
STAGES = frozenset({"CANDIDATE_APPROVED", "GOLD_COMMITTED"})
REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,127}\Z")
NAMESPACED_SOURCE = re.compile(
    r"[A-Za-z][A-Za-z0-9_.-]{0,47}:[A-Za-z0-9][A-Za-z0-9_.-]{0,95}:"
    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z"
)
ISSUER = "g5-trusted-evidence-provider"
AUDIENCE = "fabric-g5-native-controller"
PURPOSE = "PROVENANCE_ONLY_NO_WRITE"

WORKSPACE_ID = "745ce03b-15b6-4870-b0e5-8c5750aa18dc"
WAREHOUSE_ID = "7a6d08da-278d-4603-8a3b-28640110984c"
REQUEST_ID = "atlanta-fhir-gh-41552666929"
SOURCE_BATCH_ID = "2e110eb1971fcfa3ebb4dda6782c49a7608955855a2de45a3d77ada47fea8adb"
MANIFEST_SHA = "425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1"
MAPPING_PROFILE_SHA = "aab2d074fd5651a0d594dac1a8933e49b6ed2d2afadd02c37073537e033007de"

SHA64 = re.compile(r"[0-9a-f]{64}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
B64 = re.compile(r"[A-Za-z0-9+/]{86}==\Z")
MAX_ENVELOPE_BYTES = 8192
MAX_TTL_SECONDS = 300
CLOCK_SKEW_SECONDS = 30

PAYLOAD_FIELDS = frozenset({
    "schema_version", "issuer", "audience", "purpose",
    "workspace_id", "warehouse_id", "request_id", "source_batch_id",
    "manifest_sha256", "mapping_profile_sha256",
    "f1_release_metadata_sha256", "f2_identity_snapshot_fingerprint",
    "clinical_review_sha256", "license_review_sha256",
    "provider_commit_sha", "native_controller_sha256",
    "nonce_hex", "issued_at_utc", "expires_at_utc",
})
# Current technical contract has no two-person reviewer signatures.
TECHNICAL_PAYLOAD_FIELDS = (
    PAYLOAD_FIELDS - {"clinical_review_sha256", "license_review_sha256"}
    | {"technical_evidence_sha256"}
)
# New-batch v3 is source-neutral: exact FHIR/HL7 StageScope and verified F1/F2
# fingerprints are independently pinned by the controller, never trusted
# merely because the provider signed a caller-supplied JSON dictionary.
DYNAMIC_TECHNICAL_FIELDS = TECHNICAL_PAYLOAD_FIELDS | {
    "source_format", "source_system", "stage", "stage_scope_version",
}
ENVELOPE_FIELDS = frozenset({"payload", "key_id", "signature_ed25519"})

# Intentionally EMPTY. Only a separately reviewed immutable Native release
# may provision these; NEVER accept key material from a request, workflow,
# notebook parameter, signed JSON or provider-generated artifact.
NATIVE_TRUSTED_PROVIDER_KEYS: dict[str, bytes] = {}
NATIVE_PINNED_PROVIDER_COMMIT: str | None = None
NATIVE_PINNED_CONTROLLER_SHA256: str | None = None
NATIVE_ATOMIC_DURABLE_NONCE_CLAIM: Callable[[str, datetime], bool] | None = None
# Unpopulated until controller independently validates a physical StageScope
# against real approved Silver, Mapping, F1/F2 and authorized runtime identity.
NATIVE_EXPECTED_TECHNICAL_SCOPE: TrustedTechnicalScope | None = None


class TransportHold(ValueError):
    """Stable non-PHI diagnostics: never echo untrusted evidence or signatures."""


@dataclass(frozen=True)
class TrustedTechnicalScope:
    """Independently authenticated Stage evidence supplied by protected code.

    Neither this structure alone nor a signed transport permits SQL/Delta
    writes. Only a trusted controller may construct it from independently
    validated physical Batch/Manifest/StageScope + F1/F2/Concept evidence.
    """
    request_id: str
    source_batch_id: str
    manifest_sha256: str
    mapping_profile_sha256: str
    stage_scope_version: str
    source_format: str
    source_system: str
    stage: str
    f1_release_metadata_sha256: str
    f2_identity_snapshot_fingerprint: str
    technical_evidence_sha256: str
    workspace_id: str = WORKSPACE_ID
    warehouse_id: str = WAREHOUSE_ID

    def validate(self) -> None:
        if (type(self) is not TrustedTechnicalScope
                or not isinstance(self.request_id, str)
                or not REQUEST.fullmatch(self.request_id)
                or self.source_format not in SOURCE_FORMATS
                or self.stage not in STAGES
                or not isinstance(self.source_system, str)
                or not NAMESPACED_SOURCE.fullmatch(self.source_system)
                or self.workspace_id != WORKSPACE_ID
                or self.warehouse_id != WAREHOUSE_ID
                or any(not isinstance(value, str) or not SHA64.fullmatch(value)
                       for value in (
                           self.source_batch_id, self.manifest_sha256,
                           self.mapping_profile_sha256, self.stage_scope_version,
                           self.f1_release_metadata_sha256,
                           self.f2_identity_snapshot_fingerprint,
                           self.technical_evidence_sha256))):
            raise TransportHold("G5_TRANSPORT_TRUSTED_STAGE_SCOPE_INVALID")


@dataclass(frozen=True)
class VerifiedTransport:
    """Source-only provenance. This is NOT a release/writer token."""

    status: str
    attestation_sha256: str
    mapping_profile_sha256: str
    f1_release_metadata_sha256: str
    f2_identity_snapshot_fingerprint: str
    clinical_review_sha256: str
    license_review_sha256: str
    provider_commit_sha: str
    expires_at_utc: str
    candidate_write_authorized: bool = False
    gold_committed: bool = False
    provisional_ids_persisted: bool = False


@dataclass(frozen=True)
class VerifiedTechnicalTransport:
    """Signed technical provenance ONLY; not a Stage/Writer release."""
    status: str
    attestation_sha256: str
    mapping_profile_sha256: str
    f1_release_metadata_sha256: str
    f2_identity_snapshot_fingerprint: str
    technical_evidence_sha256: str
    provider_commit_sha: str
    expires_at_utc: str
    source_format: str | None = None
    source_system: str | None = None
    request_id: str | None = None
    source_batch_id: str | None = None
    manifest_sha256: str | None = None
    stage_scope_version: str | None = None
    stage: str | None = None
    candidate_write_authorized: bool = False
    gold_committed: bool = False
    provisional_ids_persisted: bool = False


def canonical_json(value: object) -> bytes:
    """The ONE canonical UTF-8 signing representation shared by both sides."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise TransportHold("G5_TRANSPORT_CANONICAL_JSON_INVALID") from None


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransportHold("G5_TRANSPORT_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _decode(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ENVELOPE_BYTES:
        raise TransportHold("G5_TRANSPORT_ENVELOPE_BYTES_INVALID")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               TransportHold("G5_TRANSPORT_NONFINITE_JSON")))
    except (UnicodeDecodeError, ValueError, TypeError, OverflowError):
        raise TransportHold("G5_TRANSPORT_ENVELOPE_JSON_INVALID") from None
    if not isinstance(value, dict) or set(value) != ENVELOPE_FIELDS:
        raise TransportHold("G5_TRANSPORT_ENVELOPE_SCHEMA_INVALID")
    if canonical_json(value) != raw:
        raise TransportHold("G5_TRANSPORT_NONCANONICAL_BYTES")
    return value


def _utc(text: object) -> datetime:
    if (not isinstance(text, str) or len(text) > 32 or not text.endswith("Z")):
        raise TransportHold("G5_TRANSPORT_TIMESTAMP_INVALID")
    try:
        stamp = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        raise TransportHold("G5_TRANSPORT_TIMESTAMP_INVALID") from None
    if (stamp.tzinfo is None or stamp.utcoffset() != timedelta(0)
            or stamp.isoformat(timespec="seconds").replace("+00:00", "Z") != text):
        raise TransportHold("G5_TRANSPORT_TIMESTAMP_NONCANONICAL")
    return stamp


def _validate_payload(payload: object, *, expected_provider_commit: str,
                      expected_controller_sha256: str, now: datetime,
                      expected_technical_scope: TrustedTechnicalScope | None = None
                      ) -> datetime:
    schema = payload.get("schema_version") if isinstance(payload, dict) else None
    fields = (
        DYNAMIC_TECHNICAL_FIELDS if schema == DYNAMIC_TECHNICAL_SCHEMA else
        TECHNICAL_PAYLOAD_FIELDS if schema == TECHNICAL_SCHEMA else
        PAYLOAD_FIELDS if isinstance(payload, dict)
        and set(payload) == PAYLOAD_FIELDS else None
    )
    if fields is None or set(payload) != fields:
        raise TransportHold("G5_TRANSPORT_PAYLOAD_SCHEMA_INVALID")
    required = {
        "schema_version": (
            schema if schema in (TECHNICAL_SCHEMA, DYNAMIC_TECHNICAL_SCHEMA)
            else SCHEMA),
        "issuer": ISSUER, "audience": AUDIENCE, "purpose": PURPOSE,
        "workspace_id": WORKSPACE_ID, "warehouse_id": WAREHOUSE_ID,
        "provider_commit_sha": expected_provider_commit,
        "native_controller_sha256": expected_controller_sha256,
    }
    if schema == DYNAMIC_TECHNICAL_SCHEMA:
        # New FHIR/HL7 batches must be pinned from a distinct trusted source.
        # A signature alone authenticates only the issuer, NOT business facts.
        if type(expected_technical_scope) is not TrustedTechnicalScope:
            raise TransportHold("G5_TRANSPORT_TRUSTED_STAGE_SCOPE_REQUIRED")
        expected_technical_scope.validate()
        required.update({
            field: getattr(expected_technical_scope, field)
            for field in (
                "request_id", "source_batch_id", "manifest_sha256",
                "mapping_profile_sha256", "source_format", "source_system",
                "stage", "stage_scope_version",
                "f1_release_metadata_sha256", "f2_identity_snapshot_fingerprint",
                "technical_evidence_sha256",
            )
        })
    else:
        # Legacy frozen FHIR v1/v2 intentionally retain their exact pins and
        # original negative-test semantics. Never recast one as dynamic v3.
        required.update({
            "request_id": REQUEST_ID, "source_batch_id": SOURCE_BATCH_ID,
            "manifest_sha256": MANIFEST_SHA,
            "mapping_profile_sha256": MAPPING_PROFILE_SHA,
        })
    if any(payload.get(field) != value for field, value in required.items()):
        raise TransportHold("G5_TRANSPORT_SCOPE_OR_CODE_PIN_DRIFT")
    evidence_fields = (
        ("clinical_review_sha256", "license_review_sha256")
        if schema == SCHEMA else ("technical_evidence_sha256",)
    )
    for field in (
        "f1_release_metadata_sha256", "f2_identity_snapshot_fingerprint",
        *evidence_fields, "native_controller_sha256",
    ):
        if not isinstance(payload[field], str) or not SHA64.fullmatch(payload[field]):
            raise TransportHold("G5_TRANSPORT_EVIDENCE_DIGEST_INVALID")
    if (not isinstance(payload["provider_commit_sha"], str)
            or not SHA40.fullmatch(payload["provider_commit_sha"])
            or not isinstance(payload["nonce_hex"], str)
            or not NONCE.fullmatch(payload["nonce_hex"])):
        raise TransportHold("G5_TRANSPORT_PROVENANCE_NONCE_INVALID")
    issued = _utc(payload["issued_at_utc"])
    expires = _utc(payload["expires_at_utc"])
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() != timedelta(0)):
        raise TransportHold("G5_TRANSPORT_TRUSTED_CLOCK_REQUIRED")
    if (not issued < expires
            or expires - issued > timedelta(seconds=MAX_TTL_SECONDS)
            or issued > now + timedelta(seconds=CLOCK_SKEW_SECONDS)
            or expires <= now):
        raise TransportHold("G5_TRANSPORT_EXPIRED_FUTURE_OR_UNBOUNDED")
    return expires


def _verify_source_only(
    raw: bytes, *,
    pinned_keys: Mapping[str, bytes],
    expected_provider_commit: str,
    expected_controller_sha256: str,
    atomic_durable_nonce_claim: Callable[[str, datetime], bool] | None,
    now: datetime,
    expected_technical_scope: TrustedTechnicalScope | None = None,
) -> VerifiedTransport | VerifiedTechnicalTransport:
    """INTERNAL pure contract test seam. No release authority is returned.

    The caller at eventual Native runtime must derive pins and durable nonce
    claim from *protected controller configuration*, not transport arguments.
    An in-memory callback proves only offline ordering, not durability.
    """
    if (not isinstance(pinned_keys, Mapping) or not pinned_keys
            or not isinstance(expected_provider_commit, str)
            or not SHA40.fullmatch(expected_provider_commit)
            or not isinstance(expected_controller_sha256, str)
            or not SHA64.fullmatch(expected_controller_sha256)
            or not callable(atomic_durable_nonce_claim)):
        raise TransportHold("G5_TRANSPORT_NATIVE_TRUST_OR_LEDGER_NOT_ONBOARDED")
    envelope = _decode(raw)
    payload = envelope["payload"]
    expiry = _validate_payload(
        payload, expected_provider_commit=expected_provider_commit,
        expected_controller_sha256=expected_controller_sha256, now=now,
        expected_technical_scope=expected_technical_scope,
    )
    key_id = envelope["key_id"]
    if not isinstance(key_id, str) or not SHA64.fullmatch(key_id):
        raise TransportHold("G5_TRANSPORT_KEY_ID_INVALID")
    public = pinned_keys.get(key_id)
    if (not isinstance(public, bytes) or len(public) != 32
            or hashlib.sha256(public).hexdigest() != key_id):
        raise TransportHold("G5_TRANSPORT_PROVIDER_KEY_NOT_PINNED")
    signature = envelope["signature_ed25519"]
    if not isinstance(signature, str) or not B64.fullmatch(signature):
        raise TransportHold("G5_TRANSPORT_SIGNATURE_ENCODING_INVALID")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        raise TransportHold("G5_TRANSPORT_VERIFIER_DEPENDENCY_MISSING") from None
    try:
        sig = base64.b64decode(signature, validate=True)
        if len(sig) != 64 or base64.b64encode(sig).decode("ascii") != signature:
            raise ValueError("noncanonical signature")
        Ed25519PublicKey.from_public_bytes(public).verify(
            sig, canonical_json(payload))
    except (InvalidSignature, ValueError, binascii.Error):
        raise TransportHold("G5_TRANSPORT_SIGNATURE_INVALID") from None
    # Durable GLOBAL nonce reservation belongs to a trusted controller, not
    # per-process memory or a caller-supplied boolean, and is required even
    # for a transport-only receipt. Claim AFTER verifying all other evidence.
    claim_key = hashlib.sha256(
        canonical_json([payload["schema_version"], ISSUER, WORKSPACE_ID, AUDIENCE,
                        payload["nonce_hex"]])).hexdigest()
    try:
        accepted = atomic_durable_nonce_claim(claim_key, expiry)
    except Exception:
        raise TransportHold("G5_TRANSPORT_REPLAY_LEDGER_UNAVAILABLE") from None
    if accepted is not True:
        raise TransportHold("G5_TRANSPORT_REPLAY_OR_LEDGER_HOLD")
    if payload["schema_version"] in (TECHNICAL_SCHEMA, DYNAMIC_TECHNICAL_SCHEMA):
        dynamic = payload["schema_version"] == DYNAMIC_TECHNICAL_SCHEMA
        return VerifiedTechnicalTransport(
            status=(
                "G5_DYNAMIC_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE"
                if dynamic else
                "G5_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE"),
            attestation_sha256=hashlib.sha256(raw).hexdigest(),
            mapping_profile_sha256=payload["mapping_profile_sha256"],
            f1_release_metadata_sha256=payload["f1_release_metadata_sha256"],
            f2_identity_snapshot_fingerprint=payload["f2_identity_snapshot_fingerprint"],
            technical_evidence_sha256=payload["technical_evidence_sha256"],
            provider_commit_sha=payload["provider_commit_sha"],
            expires_at_utc=payload["expires_at_utc"],
            source_format=payload["source_format"] if dynamic else None,
            source_system=payload["source_system"] if dynamic else None,
            request_id=payload["request_id"] if dynamic else None,
            source_batch_id=payload["source_batch_id"] if dynamic else None,
            manifest_sha256=payload["manifest_sha256"] if dynamic else None,
            stage_scope_version=payload["stage_scope_version"] if dynamic else None,
            stage=payload["stage"] if dynamic else None,
        )
    return VerifiedTransport(
        status="G5_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE_AUTHORITY",
        attestation_sha256=hashlib.sha256(raw).hexdigest(),
        mapping_profile_sha256=payload["mapping_profile_sha256"],
        f1_release_metadata_sha256=payload["f1_release_metadata_sha256"],
        f2_identity_snapshot_fingerprint=payload["f2_identity_snapshot_fingerprint"],
        clinical_review_sha256=payload["clinical_review_sha256"],
        license_review_sha256=payload["license_review_sha256"],
        provider_commit_sha=payload["provider_commit_sha"],
        expires_at_utc=payload["expires_at_utc"],
    )


def verify_native_handoff_source_only(raw: bytes) -> VerifiedTransport | VerifiedTechnicalTransport:
    """Non-overridable runtime surface. DEFAULT UNCONDITIONALLY HOLD.

    No Notebook/Pipeline input can supply verifier keys or replay callback.
    Required trust/ledger pins remain EMPTY pending separate signed PR and
    live native deployment. This function is NOT on any Notebook run_mode.
    """
    if (not NATIVE_TRUSTED_PROVIDER_KEYS or not NATIVE_PINNED_PROVIDER_COMMIT
            or not NATIVE_PINNED_CONTROLLER_SHA256
            or NATIVE_ATOMIC_DURABLE_NONCE_CLAIM is None):
        raise TransportHold("G5_TRANSPORT_NATIVE_TRUST_OR_LEDGER_NOT_ONBOARDED")
    return _verify_source_only(
        raw,
        pinned_keys=NATIVE_TRUSTED_PROVIDER_KEYS,
        expected_provider_commit=NATIVE_PINNED_PROVIDER_COMMIT,
        expected_controller_sha256=NATIVE_PINNED_CONTROLLER_SHA256,
        atomic_durable_nonce_claim=NATIVE_ATOMIC_DURABLE_NONCE_CLAIM,
        now=datetime.now(timezone.utc),
        expected_technical_scope=NATIVE_EXPECTED_TECHNICAL_SCOPE,
    )
