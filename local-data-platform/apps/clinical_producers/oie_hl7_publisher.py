"""External Profile OIE readback -> independent HL7 A01 -> immutable Blob.

This does not submit new messages to OIE, claim an actual OIE readback, or
replay accepted Derby messages. Callers must retrieve a *new* frozen source
and independent per-Encounter OIE persisted messages under runtime controls.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

from apps.clinical_producers.azure_blob_publisher import BlobBackend, publish_immutable
from apps.clinical_producers.blob_publish_contract import VERSION as PLAN_VERSION
from apps.clinical_producers.hospital_profiles import load_profile
from apps.clinical_producers.oie.fhir_events import events_from_bundle
from apps.clinical_producers.oie.hl7_readback import (
    verify_adt_against_fhir, Hl7ReadbackError,
)
from apps.clinical_producers.source_handoff import verify_handoff
from apps.synthea.synthea_new_generator.generator import sha256


SAFE_ENCOUNTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$")
SKIP_MARKER = b"OIE_ADT_NON_INPATIENT_SKIPPED"


class OIEDeliveryBlocked(ValueError):
    """OIE readback or source correlation insufficient for immutable delivery."""


@dataclass(frozen=True)
class OIEReadback:
    """Caller-supplied actual persisted OIE readback for one new Encounter.

    This record is not proof by itself. Only the guarded live OIE fetcher can
    attest its origin; this adapter independently verifies content/correlation.
    """

    encounter_id: str
    channel_id: str
    message_id: str
    disposition: str  # ADT_A01 or SKIP
    payload: bytes


def prepare_oie_hl7(state_root: Path, profile_path: Path, request_id: str, *,
                    channel_id: str, assigning_authority: str,
                    readbacks: list[OIEReadback]) -> tuple[dict, dict[str, bytes]]:
    """Check COMPLETE OIE event coverage and original bytes before Blob PUT."""
    profile = load_profile(Path(profile_path))
    if profile["delivery"] != {
        "source_format": "FHIR_R4",
        "target_format": "HL7_V2",
        "transformer": "OIE",
    }:
        raise OIEDeliveryBlocked("OIE_HL7_PROFILE_REQUIRED")

    try:
        UUID(channel_id)
    except (TypeError, ValueError, AttributeError):
        raise OIEDeliveryBlocked("INVALID_OIE_CHANNEL_ID") from None
    if not isinstance(assigning_authority, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", assigning_authority):
        raise OIEDeliveryBlocked("INVALID_ASSIGNING_AUTHORITY")

    handoff = verify_handoff(Path(state_root), Path(profile_path), request_id)
    if (handoff["hospital_id"] != profile["hospital_id"]
            or handoff["feed_id"] != profile["feed_id"]
            or handoff["target_format"] != "HL7_V2"
            or handoff["transformer"] != "OIE"):
        raise OIEDeliveryBlocked("OIE_HANDOFF_IDENTITY_MISMATCH")
    base = Path(state_root) / handoff["request_relative_path"]
    payload_dir = base / "payload"
    manifest = base / "generation-manifest.json"

    event_map = {}
    for file in handoff["files"]:
        name = file["path"]
        if (not isinstance(name, str) or not name.startswith("fhir/")
                or name.count("/") != 1):
            raise OIEDeliveryBlocked("UNSAFE_FHIR_SOURCE_PATH")
        source = payload_dir / name
        if (source.is_symlink() or source.parent.is_symlink()
                or not source.is_file()):
            raise OIEDeliveryBlocked("UNSAFE_FHIR_SOURCE_PATH")
        raw = source.read_bytes()
        if (len(raw) != file["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != file["sha256"]):
            raise OIEDeliveryBlocked("FHIR_SOURCE_CHANGED")
        try:
            envelopes = events_from_bundle(json.loads(raw), request_id)
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise OIEDeliveryBlocked("INVALID_SOURCE_EVENTS") from None
        for envelope in envelopes:
            encounter = envelope["bundle"]["entry"][1]["resource"]
            enc_id = encounter.get("id")
            if (not isinstance(enc_id, str)
                    or not SAFE_ENCOUNTER.fullmatch(enc_id)
                    or enc_id in event_map):
                raise OIEDeliveryBlocked("INVALID_OR_DUPLICATE_SOURCE_ENCOUNTER")
            event_map[enc_id] = envelope

    if sha256(manifest) != handoff["source_manifest_sha256"]:
        raise OIEDeliveryBlocked("SOURCE_MANIFEST_CHANGED")
    if not event_map:
        raise OIEDeliveryBlocked("EMPTY_FHIR_SOURCE_EVENTS")

    if (not isinstance(readbacks, list) or
            len(readbacks) != len(event_map)):
        raise OIEDeliveryBlocked("INCOMPLETE_OIE_MESSAGE_COVERAGE")
    data = {}
    objects = []
    seen_messages = set()
    skipped = 0
    for record in readbacks:
        if (not isinstance(record, OIEReadback)
                or record.channel_id != channel_id
                or record.encounter_id not in event_map
                or not isinstance(record.message_id, str)
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", record.message_id)
                or record.message_id in seen_messages
                or not isinstance(record.payload, bytes)):
            raise OIEDeliveryBlocked("INVALID_OIE_READBACK_RECEIPT")
        seen_messages.add(record.message_id)
        event = event_map.pop(record.encounter_id)
        encounter = event["bundle"]["entry"][1]["resource"]
        cls = encounter.get("class")
        is_admission = (
            isinstance(cls, dict) and
            cls.get("system") == "http://terminology.hl7.org/CodeSystem/v3-ActCode" and
            cls.get("code") == "IMP" and
            encounter.get("status") in ("in-progress", "finished")
        )
        if record.disposition == "SKIP":
            if is_admission or record.payload != SKIP_MARKER:
                raise OIEDeliveryBlocked("INVALID_NON_ADMISSION_SKIP")
            skipped += 1
            continue
        if record.disposition != "ADT_A01" or not is_admission:
            raise OIEDeliveryBlocked("ADMISSION_DISPOSITION_MISMATCH")
        try:
            parsed = verify_adt_against_fhir(
                record.payload, event, hospital_id=profile["hospital_id"],
                feed_id=profile["feed_id"],
                assigning_authority=assigning_authority)
        except Hl7ReadbackError:
            raise OIEDeliveryBlocked("OIE_HL7_SOURCE_CORRELATION_FAILED") from None

        name = "hl7/" + record.encounter_id + ".hl7"
        data[name] = record.payload
        objects.append({
            "name": name,
            "size_bytes": len(record.payload),
            "sha256": hashlib.sha256(record.payload).hexdigest(),
            "source_event_id": parsed["control_id"],
        })
    if event_map:
        raise OIEDeliveryBlocked("INCOMPLETE_OIE_MESSAGE_COVERAGE")

    # A SKIP-only request must remain uncommitted in Blob; upstream records
    # the skipped count. Never create a manifest that suggests HL7 delivery.
    if not objects:
        raise OIEDeliveryBlocked("NO_OIE_ADT_A01_TO_PUBLISH")
    plan = {
        "schema_version": PLAN_VERSION,
        "hospital_id": handoff["hospital_id"],
        "feed_id": handoff["feed_id"],
        "request_id": handoff["request_id"],
        "source_manifest_sha256": handoff["source_manifest_sha256"],
        "target_format": "HL7_V2",
        "verification_state": "OIE_HL7_READBACK_VERIFIED",
        "skipped_non_admissions": skipped,
        "objects": sorted(objects, key=lambda row: row["name"]),
    }
    return plan, data


def publish_oie_hl7(state_root: Path, profile_path: Path, request_id: str, *,
                    channel_id: str, assigning_authority: str,
                    readbacks: list[OIEReadback], landing_prefix: str,
                    backend: BlobBackend) -> dict:
    """Upload only after all independently correlated new OIE messages pass."""
    plan, source_bytes = prepare_oie_hl7(
        state_root, profile_path, request_id, channel_id=channel_id,
        assigning_authority=assigning_authority, readbacks=readbacks)
    return publish_immutable(plan, source_bytes, landing_prefix=landing_prefix,
                             backend=backend)
