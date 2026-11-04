"""No-I/O v1 contract boundary: Approved Fabric Silver -> independent OMOP F1.

This module NEVER opens Spark/Delta/Fabric/SQL, allocates OMOP IDs, validates
physical data, or authorizes a Candidate/Gold write. All results are
STRUCTURAL_ONLY even when the supplied Approval row looks legitimate.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

CONTRACT_ID = "healthcare.fabric.fhir-approved-silver-to-omop"
CONTRACT_VERSION = "1.0.0"
STRUCTURAL_ONLY = "STRUCTURAL_PASS_PHYSICAL_READBACK_REQUIRED"

PINNED_FABRIC = {
    "workspace_id": "745ce03b-15b6-4870-b0e5-8c5750aa18dc",
    "lakehouse_id": "e67c42ee-5ab2-4bc8-a013-7bdf9741ef68",
    "warehouse_item_id": "7a6d08da-278d-4603-8a3b-28640110984c",
    "warehouse_name": "dw-omop-5.4",
}
PINNED_CANONICAL_SHA = {
    "patient": "e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab",
    "encounter": "473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837",
}
SOURCE_KEYS = frozenset({
    "hospital_id", "feed_id", "raw_source_system", "canonical_source_system",
    "request_id", "source_batch_id", "manifest_sha256", "processing_version",
})
ENVELOPE_KEYS = frozenset({
    "contract_id", "contract_version", "producer", "paths", "approval", "consumer",
})
CONSUMER_KEYS = frozenset({
    "workspace_id", "lakehouse_id", "warehouse_item_id", "warehouse_name",
})
APPROVAL_KEYS = frozenset({
    "status", "source_batch_id", "manifest_sha256", "processing_version",
    "publication_id", "patient_count", "encounter_count", "quarantine_count",
    "patient_contract_sha256", "encounter_contract_sha256",
    "source_preservation_strategy",
})
PATH_KEYS = frozenset({"patient", "encounter", "approval"})
SHA = re.compile(r"[0-9a-f]{64}\Z")
SEGMENT = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}\Z")
RAW_SOURCE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


class HandoffHold(ValueError):
    """Safe structural error; no patient information in exception messages."""


def _exact(value: Any, keys: frozenset[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise HandoffHold("HANDOFF_" + label + "_FIELDS_INVALID")
    return value


def _text(value: Any, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if (not isinstance(value, str) or not value or len(value) > 192
            or (pattern is not None and not pattern.fullmatch(value))):
        raise HandoffHold("HANDOFF_" + label + "_INVALID")
    return value


def _sha(value: Any, label: str) -> str:
    return _text(value, label, SHA)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0 or value > 1_000_000_000:
        raise HandoffHold("HANDOFF_" + label + "_INVALID")
    return value


def _no_duplicate_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise HandoffHold("HANDOFF_DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def load_handoff_contract(raw: bytes, expected_sha256: str) -> Mapping[str, Any]:
    """Load exact reviewed Git bytes; expected digest comes from a trusted deploy."""
    if not isinstance(raw, bytes) or len(raw) > 40_000:
        raise HandoffHold("HANDOFF_CONTRACT_BYTES_INVALID")
    _sha(expected_sha256, "CONTRACT_PIN")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise HandoffHold("HANDOFF_CONTRACT_SHA_MISMATCH")
    try:
        contract = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_json)
    except (UnicodeError, ValueError) as exc:
        raise HandoffHold("HANDOFF_CONTRACT_JSON_INVALID") from exc
    if (not isinstance(contract, dict)
            or contract.get("contract_id") != CONTRACT_ID
            or contract.get("contract_version") != CONTRACT_VERSION
            or contract.get("status") != "CONTRACT_ONLY_NO_WRITE"
            or contract.get("fabric") != PINNED_FABRIC):
        raise HandoffHold("HANDOFF_CONTRACT_IDENTITY_INVALID")
    canonical = contract.get("canonical_contracts")
    if (not isinstance(canonical, dict)
            or set(canonical) != {"patient", "encounter"}
            or any(not isinstance(canonical[k], dict)
                   or canonical[k].get("raw_sha256") != PINNED_CANONICAL_SHA[k]
                   or canonical[k].get("contract_version") != "v1"
                   for k in PINNED_CANONICAL_SHA)):
        raise HandoffHold("HANDOFF_CANONICAL_PINS_INVALID")
    silver = contract.get("silver")
    if (not isinstance(silver, dict)
            or silver.get("root") != "Files/silver/fhir_r4"
            or silver.get("source_batch_id_algorithm") !=
            "SHA256_COMPACT_JSON_HOSPITAL_FEED_RAW_SOURCE_REQUEST_MANIFEST"
            or silver.get("processing_path_digest") !=
            "SHA256_UTF8_PROCESSING_VERSION"
            or silver.get("processing_version") !=
            "fhir-silver-canonical-v1:engine-0.1.1"
            or silver.get("source_preservation_strategy") !=
            "DELTA_RAW_SNAPSHOT_V1"
            or silver.get("approved_status") != "SILVER_APPROVED"
            or silver.get("approval_row_count") != 1
            or silver.get("approved_quarantine_count") != 0
            or set(silver.get("approval_required_fields", [])) != APPROVAL_KEYS
            or len(silver.get("approval_required_fields", [])) != len(APPROVAL_KEYS)):
        raise HandoffHold("HANDOFF_SILVER_RULES_INVALID")
    identity = contract.get("identity")
    if (not isinstance(identity, dict)
            or identity.get("person_source_scope") != [
                "hospital_id", "feed_id", "raw_source_system", "source_record_id"]
            or identity.get("visit_source_scope") != [
                "hospital_id", "feed_id", "raw_source_system", "source_encounter_id"]
            or identity.get("omop_person_id_owner") != "FABRIC_WAREHOUSE_F1"
            or identity.get("omop_visit_id_owner") != "FABRIC_WAREHOUSE_F2"):
        raise HandoffHold("HANDOFF_IDENTITY_SCOPE_INVALID")
    gates = contract.get("evidence", {})
    if (not isinstance(gates, dict)
            or gates.get("structural_validation_result") != STRUCTURAL_ONLY
            or gates.get("stage1_performs_cloud_reads") is not False
            or gates.get("stage1_performs_writes") is not False):
        raise HandoffHold("HANDOFF_PHYSICAL_EVIDENCE_SCOPE_INVALID")
    return contract


def calculate_source_batch_id(hospital_id: str, feed_id: str,
                              raw_source_system: str, request_id: str,
                              manifest_sha256: str) -> str:
    """Byte-compatible with Shared Engine BatchContext.source_batch_id."""
    payload = json.dumps(
        (hospital_id, feed_id, raw_source_system, request_id,
         manifest_sha256.lower()),
        separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_handoff_envelope(contract: Mapping[str, Any],
                              envelope: Mapping[str, Any]) -> str:
    """Validate structural consistency, never a durable approval or SQL write."""
    _exact(envelope, ENVELOPE_KEYS, "ENVELOPE")
    if (envelope["contract_id"] != CONTRACT_ID
            or envelope["contract_version"] != CONTRACT_VERSION):
        raise HandoffHold("HANDOFF_ENVELOPE_VERSION_INVALID")
    producer = _exact(envelope["producer"], SOURCE_KEYS, "SOURCE")
    consumer = _exact(envelope["consumer"], CONSUMER_KEYS, "CONSUMER")
    paths = _exact(envelope["paths"], PATH_KEYS, "PATHS")
    approval = _exact(envelope["approval"], APPROVAL_KEYS, "APPROVAL")
    if consumer != PINNED_FABRIC:
        raise HandoffHold("HANDOFF_CONSUMER_PHYSICAL_ID_MISMATCH")
    if (not isinstance(contract, Mapping)
            or contract.get("contract_id") != CONTRACT_ID
            or contract.get("contract_version") != CONTRACT_VERSION
            or contract.get("status") != "CONTRACT_ONLY_NO_WRITE"
            or contract.get("fabric") != PINNED_FABRIC):
        raise HandoffHold("HANDOFF_CONTRACT_NOT_REVIEWED")
    silver = contract.get("silver")
    canon = contract.get("canonical_contracts")
    if not isinstance(silver, Mapping) or not isinstance(canon, Mapping):
        raise HandoffHold("HANDOFF_CONTRACT_RULES_MISSING")

    hospital = _text(producer["hospital_id"], "HOSPITAL", SEGMENT)
    feed = _text(producer["feed_id"], "FEED", SEGMENT)
    raw_source = _text(producer["raw_source_system"], "RAW_SOURCE", RAW_SOURCE)
    request = _text(producer["request_id"], "REQUEST", SEGMENT)
    manifest_sha = _sha(producer["manifest_sha256"], "MANIFEST_SHA")
    batch_id = _sha(producer["source_batch_id"], "BATCH_ID")
    canonical_source = _text(producer["canonical_source_system"], "CANONICAL_SOURCE")
    if canonical_source != ":".join((raw_source, hospital, feed)):
        raise HandoffHold("HANDOFF_CANONICAL_NAMESPACE_MISMATCH")
    if batch_id != calculate_source_batch_id(
            hospital, feed, raw_source, request, manifest_sha):
        raise HandoffHold("HANDOFF_SOURCE_BATCH_ID_MISMATCH")
    processing = producer["processing_version"]
    if processing != silver.get("processing_version"):
        raise HandoffHold("HANDOFF_PROCESSING_VERSION_DRIFT")

    version_hash = hashlib.sha256(processing.encode("utf-8")).hexdigest()
    prefix = f"{silver['root']}/{hospital}/{feed}/{request}/processing={version_hash}"
    for key, directory in (("patient", "patient_directory"),
                           ("encounter", "encounter_directory"),
                           ("approval", "approval_directory")):
        if paths[key] != prefix + "/" + silver[directory]:
            raise HandoffHold("HANDOFF_PHYSICAL_" + key.upper() + "_PATH_MISMATCH")

    if (approval["status"] != "SILVER_APPROVED"
            or approval["source_batch_id"] != batch_id
            or approval["manifest_sha256"] != manifest_sha
            or approval["processing_version"] != processing
            or approval["source_preservation_strategy"] !=
            "DELTA_RAW_SNAPSHOT_V1"):
        raise HandoffHold("HANDOFF_APPROVAL_FENCE_DENIED_OR_DRIFT")
    _text(approval["publication_id"], "PUBLICATION_ID")
    _positive_int(approval["patient_count"], "PATIENT_COUNT")
    _positive_int(approval["encounter_count"], "ENCOUNTER_COUNT")
    if type(approval["quarantine_count"]) is not int or approval["quarantine_count"] != 0:
        raise HandoffHold("HANDOFF_QUARANTINE_NOT_EMPTY")
    if (approval["patient_contract_sha256"] !=
            canon["patient"]["raw_sha256"]
            or approval["encounter_contract_sha256"] !=
            canon["encounter"]["raw_sha256"]):
        raise HandoffHold("HANDOFF_CANONICAL_CONTRACT_DIGEST_DRIFT")
    # No Spark / Delta / Warehouse exists here: a metadata claim cannot prove
    # patient/encounter rows, unique keys, FK, Concepts or committed Gold.
    return STRUCTURAL_ONLY


def source_replay_identity(envelope: Mapping[str, Any]) -> tuple[str, ...]:
    """A *source* identity for F2 ledger comparison, not an OMOP stable ID."""
    producer = _exact(envelope["producer"], SOURCE_KEYS, "SOURCE")
    return tuple(producer[key] for key in (
        "hospital_id", "feed_id", "raw_source_system", "request_id"))


def classify_source_replay(previous: Mapping[str, Any],
                           current: Mapping[str, Any]) -> str:
    """Read-only source conflict classifier, not permission to skip Gold DQ."""
    if source_replay_identity(previous) != source_replay_identity(current):
        return "DIFFERENT_SOURCE_REQUEST"
    first, second = previous["producer"], current["producer"]
    if (first["manifest_sha256"] != second["manifest_sha256"]
            or first["source_batch_id"] != second["source_batch_id"]):
        return "HOLD_SOURCE_MANIFEST_CONFLICT"
    if first["processing_version"] != second["processing_version"]:
        return "HOLD_SOURCE_PROCESSING_VERSION"
    if previous["approval"] != current["approval"]:
        return "HOLD_APPROVAL_FENCE_DRIFT"
    return "SAME_SOURCE_ENVELOPE_STRUCTURAL_ONLY"
