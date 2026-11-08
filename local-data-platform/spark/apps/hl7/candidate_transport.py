"""Pure, in-memory HL7 Canonical Candidate transfer envelope.

Only bytes passed by the caller are processed. No file/Blob/Delta/OneLake I/O,
secrets, Approval, Silver write, logging, cache or persisted Processing layer.
The caller must separately verify original immutable Raw and source Manifest,
and must deliver the resulting bytes over an independently approved channel.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Mapping

from healthcare_data_engine.canonical.validation import load_pinned_contract, validate_row
from healthcare_data_engine.models.batch_context import BatchContext

from silver_handoff import HL7CanonicalHandoff, HL7HandoffHold, HL7_HOSPITAL, HL7_FEED, HL7_SOURCE

SCHEMA = "healthcare-hl7-canonical-transport-v1"
NAMES = ("canonical_patient.json", "canonical_encounter.json", "candidate_manifest.json")
MAX_ENTITY_BYTES = 16 * 1024 * 1024
MAX_ROWS_PER_ENTITY = 50000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _wire_row(row: dict, contract: dict) -> dict:
    if validate_row(row, contract):
        raise HL7HandoffHold("CANDIDATE_CONTRACT_HOLD")
    result = {}
    for f in contract["fields"]:
        name, kind = f["name"], f["type"]
        value = row[name]
        if isinstance(value, datetime):
            if value.utcoffset() is None or kind != "timestamp":
                raise HL7HandoffHold("CANDIDATE_TIMESTAMP_NOT_UTC")
            value = value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        elif isinstance(value, date):
            if kind != "date":
                raise HL7HandoffHold("CANDIDATE_DATE_TYPE_HOLD")
            value = value.isoformat()
        elif isinstance(value, Decimal):
            if not kind.startswith("decimal("):
                raise HL7HandoffHold("CANDIDATE_DECIMAL_TYPE_HOLD")
            value = str(value)
        result[name] = value
    return result


def prepare_hl7_candidate_transport(
        handoff: HL7CanonicalHandoff, *, context: BatchContext,
        patient_contract_bytes: bytes, encounter_contract_bytes: bytes
) -> dict[str, bytes]:
    """Make exact deterministic three-blob envelope after successful Shared DQ.

    Returning a bundle is NOT an authorization to upload it, nor to publish.
    Only export a complete approved-source-scoped Candidate, never reject rows.
    """
    if (not isinstance(handoff, HL7CanonicalHandoff)
            or handoff.status != "CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED"
            or context.hospital_id != HL7_HOSPITAL
            or context.feed_id != HL7_FEED
            or context.source_system != HL7_SOURCE
            or any(handoff.metrics[k] for k in (
                "patient_rejected", "patient_quarantined",
                "encounter_rejected", "encounter_quarantined"))
            or handoff.metrics["patient_accepted"] < 1
            or handoff.metrics["encounter_accepted"] < 1):
        raise HL7HandoffHold("TRANSFER_REQUIRES_COMPLETE_SHARED_DQ_PASS")
    contracts = {
        "patient": load_pinned_contract(patient_contract_bytes, "patient"),
        "encounter": load_pinned_contract(encounter_contract_bytes, "encounter"),
    }
    blobs = {}
    for entity, accepted, key in (
        ("patient", handoff.patient.accepted, "source_record_id"),
        ("encounter", handoff.encounter.accepted, "source_encounter_id"),
    ):
        if len(accepted) > MAX_ROWS_PER_ENTITY:
            raise HL7HandoffHold("TRANSFER_ROW_LIMIT_HOLD")
        records = [_wire_row(row, contracts[entity]) for row in accepted]
        records.sort(key=lambda item: item[key])
        payload = _json_bytes({"entity": entity, "rows": records, "schema": SCHEMA})
        if len(payload) > MAX_ENTITY_BYTES:
            raise HL7HandoffHold("TRANSFER_BYTES_LIMIT_HOLD")
        blobs[f"canonical_{entity}.json"] = payload
    fingerprint = _sha(_json_bytes({
        "source_batch_id": context.source_batch_id,
        "processing_version": context.processing_version,
        "patient_sha256": _sha(blobs["canonical_patient.json"]),
        "encounter_sha256": _sha(blobs["canonical_encounter.json"]),
    }))
    manifest = {
        "schema": SCHEMA,
        "hospital_id": context.hospital_id,
        "feed_id": context.feed_id,
        "source_system": context.source_system,
        "request_id": context.request_id,
        "source_batch_id": context.source_batch_id,
        "source_manifest_sha256": context.manifest_sha256.lower(),
        "processing_version": context.processing_version,
        "source_version": context.source_version,
        "adapter_version": context.adapter_version,
        "canonical_version": context.canonical_version,
        "patient_contract_sha256": _sha(patient_contract_bytes),
        "encounter_contract_sha256": _sha(encounter_contract_bytes),
        "publication_id": fingerprint,
        "entities": {
            "patient": {"file": "canonical_patient.json",
                        "sha256": _sha(blobs["canonical_patient.json"]),
                        "bytes": len(blobs["canonical_patient.json"]),
                        "rows": len(handoff.patient.accepted)},
            "encounter": {"file": "canonical_encounter.json",
                          "sha256": _sha(blobs["canonical_encounter.json"]),
                          "bytes": len(blobs["canonical_encounter.json"]),
                          "rows": len(handoff.encounter.accepted)},
        },
        "status": "CANDIDATE_ONLY_NOT_SILVER_APPROVED",
    }
    blobs["candidate_manifest.json"] = _json_bytes(manifest)
    return blobs
