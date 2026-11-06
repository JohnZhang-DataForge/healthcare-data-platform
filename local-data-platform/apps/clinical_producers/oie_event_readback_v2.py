"""Versioned OIE V2 *bounded GET-only* ADT A01/A03 persisted event receipts.

Do not use the old one-message-per-Encounter OIEPersistedMessage API for
A01+A03. This adapter only verifies explicit newly supplied message IDs
through the existing scoped readback transport. It neither POSTs messages,
publishes Blob, accesses OIE by itself nor approves Canonical Silver.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Protocol
from uuid import UUID

from apps.clinical_producers.oie.build_adt_events_v2_channel import (
    CHANNEL_ID as ADT_V2_CHANNEL_ID,
)
from apps.clinical_producers.oie.hl7_readback import (
    Hl7ReadbackError, parse_adt_a01, parse_adt_a03,
)
from apps.clinical_producers.oie_persisted_readback import (
    MESSAGE_ID, OIEReadbackBlocked, parse_persisted_source_message,
)
from apps.clinical_producers.oie_hl7_publisher import SAFE_ENCOUNTER


_SOURCE_SCOPE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")
_AUTHORITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_ALLOWED = {"A01", "A03"}


class OIEV2EventBlocked(ValueError):
    """V2 event receipt or original returned HL7 bytes cannot be verified."""


class ScopedOIEGetter(Protocol):
    def get(self, path: str) -> bytes:
        """GET explicit allowed OIE message resource using scoped TLS auth."""


@dataclass(frozen=True)
class OIEV2EventReceipt:
    source_encounter_id: str
    event_type: str
    message_id: str


@dataclass(frozen=True)
class OIEV2EventReadback:
    source_encounter_id: str
    event_type: str
    channel_id: str
    message_id: str
    control_id: str
    patient_id: str
    payload: bytes
    payload_sha256: str


def _patient_v2_facts(raw: bytes, *, event_type: str) -> None:
    """Fail closed for the source-specific v1-compatible demographic subset."""
    try:
        segments = raw.decode("utf-8").split("\r")
        pid = segments[2].split("|")
    except (UnicodeDecodeError, IndexError):
        raise OIEV2EventBlocked("OIE_V2_PATIENT_FIELDS_MISSING") from None
    if len(pid) < 23 or pid[0] != "PID" or not re.fullmatch(r"[0-9]{8}", pid[7]):
        raise OIEV2EventBlocked("OIE_V2_PATIENT_FIELDS_MISSING")
    if pid[8] not in {"M", "F"}:
        raise OIEV2EventBlocked("OIE_V2_GENDER_MAPPING_PROFILE")
    race, ethnicity = pid[10].split("^"), pid[22].split("^")
    if (len(race) != 3 or race[0] not in
        {"1002-5", "2028-9", "2054-5", "2076-8", "2106-3"}
        or race[2] != "CDCREC"
        or len(ethnicity) != 3 or ethnicity[0] not in {"2135-2", "2186-5"}
        or ethnicity[2] != "CDCREC"):
        raise OIEV2EventBlocked("OIE_V2_DEMOGRAPHIC_MAPPING_PROFILE")
    if event_type == "A01":
        pv1 = segments[3].split("|")
        if len(pv1) < 46 or pv1[45]:
            raise OIEV2EventBlocked("OIE_V2_A01_NOT_DISCHARGED")
    # A03 structure and dates independently checked by parse_adt_a03.


def fetch_v2_event_readbacks(
    client: ScopedOIEGetter, *, channel_id: str,
    hospital_id: str, feed_id: str, request_id: str,
    assigning_authority: str, receipts: list[OIEV2EventReceipt],
) -> list[OIEV2EventReadback]:
    """Retrieve ONLY the caller's explicit, verified new message receipts.

    The source handoff / genuine OIE POST receipt association is an upstream
    authorization gate. The function checks that the returned durable message
    belongs to the named event, hospital/feed/request and approved Channel.
    """
    try:
        UUID(channel_id)
    except (TypeError, ValueError, AttributeError):
        raise OIEV2EventBlocked("OIE_V2_CHANNEL_INVALID") from None
    if channel_id != ADT_V2_CHANNEL_ID:
        raise OIEV2EventBlocked("OIE_V2_UNAPPROVED_CHANNEL")
    if not (_SOURCE_SCOPE.fullmatch(hospital_id or "")
            and _SOURCE_SCOPE.fullmatch(feed_id or "")
            and _REQUEST_ID.fullmatch(request_id or "")
            and _AUTHORITY.fullmatch(assigning_authority or "")):
        raise OIEV2EventBlocked("OIE_V2_INVALID_SOURCE_SCOPE")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 5000:
        raise OIEV2EventBlocked("OIE_V2_RECEIPT_LIST")
    ids, event_keys = set(), set()
    per_encounter = {}
    for record in receipts:
        if (not isinstance(record, OIEV2EventReceipt)
                or not isinstance(record.source_encounter_id, str)
                or not SAFE_ENCOUNTER.fullmatch(record.source_encounter_id)
                or record.event_type not in _ALLOWED
                or not isinstance(record.message_id, str)
                or not MESSAGE_ID.fullmatch(record.message_id)):
            raise OIEV2EventBlocked("OIE_V2_RECEIPT_INVALID")
        event_key = (record.source_encounter_id, record.event_type)
        if event_key in event_keys or record.message_id in ids:
            raise OIEV2EventBlocked("OIE_V2_DUPLICATE_RECEIPT")
        event_keys.add(event_key)
        ids.add(record.message_id)
        per_encounter.setdefault(record.source_encounter_id, set()).add(record.event_type)
    for types in per_encounter.values():
        if "A03" in types and "A01" not in types:
            # A03 arriving in a later batch needs a separately evidenced
            # A01 lookup and versioned reconciliation; not implied success.
            raise OIEV2EventBlocked("OIE_V2_A03_WITHOUT_APPROVED_A01_HOLD")

    results: list[OIEV2EventReadback] = []
    for record in receipts:
        url_path = f"/api/channels/{channel_id}/messages/{record.message_id}"
        try:
            returned = client.get(url_path)
        except Exception:
            raise OIEV2EventBlocked("OIE_V2_SCOPED_GET_FAILED") from None
        try:
            payload_record = parse_persisted_source_message(
                returned, channel_id=channel_id,
                message_id=record.message_id,
                encounter_id=record.source_encounter_id,
            )
        except OIEReadbackBlocked:
            raise OIEV2EventBlocked("OIE_V2_PERSISTED_SOURCE_READBACK_FAILED") from None

        # Legacy transport accessor classifies all well-formed MSH payloads as
        # ADT_A01; NEVER trust its legacy disposition for V2 subtype. Parse raw.
        raw = payload_record.payload
        try:
            parsed = (parse_adt_a03(raw) if record.event_type == "A03"
                      else parse_adt_a01(raw))
        except Hl7ReadbackError:
            raise OIEV2EventBlocked("OIE_V2_INDEPENDENT_ADT_VERIFICATION_FAILED") from None
        _patient_v2_facts(raw, event_type=record.event_type)
        expected_control = "-".join((
            hospital_id, feed_id, request_id,
            record.source_encounter_id, record.event_type,
        ))
        if (parsed["control_id"] != expected_control
                or parsed["encounter_id"] != record.source_encounter_id
                or parsed["assigning_authority"] != assigning_authority
                or parsed["message_type"] !=
                    f"ADT^{record.event_type}^ADT_{record.event_type}"):
            raise OIEV2EventBlocked("OIE_V2_SOURCE_EVENT_CORRELATION_HOLD")
        results.append(OIEV2EventReadback(
            source_encounter_id=record.source_encounter_id,
            event_type=record.event_type,
            channel_id=channel_id,
            message_id=record.message_id,
            control_id=parsed["control_id"],
            patient_id=parsed["patient_id"],
            payload=raw,
            payload_sha256=hashlib.sha256(raw).hexdigest(),
        ))
    return results
