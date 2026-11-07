"""Restricted HL7 v2.5.1 projection for reviewed OIE V2 Johns Creek profile.

Promoted from the accepted Self-Runner isolated hl7-dbt POC (PR #584).
hl7apy handles the HL7 syntax; only verified clinical facts enter staging.
This is a source parser, NOT a second canonical/OMOP mapper.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from hl7apy.parser import parse_message
from hl7apy import VALIDATION_LEVEL

COLUMNS = (
    "source_system", "source_version", "source_batch_id", "source_ingest_date",
    "source_file", "source_file_sha256", "source_file_size_bytes",
    "adapter_name", "adapter_version", "canonical_version",
    "processing_run_id", "processed_at", "message_control_id", "event_type",
    "source_person_id", "source_encounter_id", "birth_date", "gender_code",
    "race_code", "ethnicity_code", "event_datetime_utc", "encounter_class",
    "source_code"
)
TS_PATTERN = re.compile(r"^[0-9]{14}[+-][0-9]{4}$")
AUTHORITY_TO_SOURCE = {
    "JC": "johns-creek-hl7",
    "ATL": "atlanta-hl7",
    # Live OIE v2.5.1 Source Connector assigns this actual authority.
    # It maps to the SAME Johns Creek source namespace, not a new entity.
    "JOHNSCREEKB": "johns-creek-hl7",
}
# Approved OIE V2 pilot FHIR US Core OMB mappings; never coerce unknown codes.
APPROVED_RACE = {
    "1002-5": "American Indian or Alaska Native",
    "2028-9": "Asian",
    "2054-5": "Black or African American",
    "2076-8": "Native Hawaiian or Other Pacific Islander",
    "2106-3": "White",
}
APPROVED_ETHNICITY = {
    "2135-2": "Hispanic or Latino",
    "2186-5": "Not Hispanic or Latino",
}

def _field(segment, name: str, pos: int) -> str:
    element = getattr(segment, f"{name.lower()}_{pos}", None)
    if element is None:
        return ""
    return element.to_er7().strip()


def _utc(timestamp: str) -> str:
    if not TS_PATTERN.fullmatch(timestamp):
        raise ValueError("HL7_TIME_OR_ZONE_MISSING")
    aware = datetime.strptime(timestamp, "%Y%m%d%H%M%S%z")
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_event(raw: str, *, source_name: str = "synthetic.hl7") -> dict[str, str]:
    """hl7apy parses syntax; a narrow, fail-closed projection extracts test facts."""
    if not raw.endswith("\r") or len(raw.encode("utf-8")) > 65536:
        raise ValueError("HL7_FRAMING_OR_SIZE")
    msg = parse_message(raw, find_groups=False, validation_level=VALIDATION_LEVEL.TOLERANT)
    msh, pid, pv1 = msg.msh, msg.pid, msg.pv1
    if _field(msh, "msh", 12) != "2.5.1":
        raise ValueError("UNSUPPORTED_HL7_VERSION")
    typ = _field(msh, "msh", 9)
    if typ not in {"ADT^A01^ADT_A01", "ADT^A03^ADT_A03"}:
        raise ValueError("UNSUPPORTED_HL7_ADT_EVENT")
    event_type = typ.split("^")[1]
    ctrl = _field(msh, "msh", 10)
    if not ctrl:
        raise ValueError("MISSING_MSH_10")
    patient_cx, visit_cx = _field(pid, "pid", 3), _field(pv1, "pv1", 19)
    patient_parts, visit_parts = patient_cx.split("^"), visit_cx.split("^")
    if len(patient_parts) < 5 or len(visit_parts) < 5:
        raise ValueError("MISSING_SOURCE_ENTITY_ID")
    patient_id, visit_id = patient_parts[0], visit_parts[0]
    if not patient_id or not visit_id:
        raise ValueError("MISSING_SOURCE_ENTITY_ID")
    authority = patient_parts[3]
    if (authority not in AUTHORITY_TO_SOURCE
            or authority != visit_parts[3]
            or _field(msh, "msh", 4) != authority):
        raise ValueError("HOSPITAL_ASSIGNING_AUTHORITY_CONFLICT_HOLD")
    dob = _field(pid, "pid", 7)
    gender, race, ethnicity = (
        _field(pid, "pid", 8), _field(pid, "pid", 10), _field(pid, "pid", 22)
    )
    if not re.fullmatch(r"[0-9]{8}", dob) or not gender or not race or not ethnicity:
        raise ValueError("CANONICAL_V1_REQUIRED_PATIENT_FACT_MISSING")
    birth = datetime.strptime(dob, "%Y%m%d").strftime("%Y-%m-%d")
    # Synthetic pilot profile only; do not claim this is a general HL7 vocabulary mapper.
    if gender not in {"M", "F"}:
        raise ValueError("UNSUPPORTED_SYNTHETIC_GENDER_CODE_HOLD")
    race_parts, eth_parts = race.split("^"), ethnicity.split("^")
    if (len(race_parts) != 3 or len(eth_parts) != 3
            or race_parts[0] not in APPROVED_RACE
            or race_parts[1] != APPROVED_RACE[race_parts[0]]
            or race_parts[2] != "CDCREC"
            or eth_parts[0] not in APPROVED_ETHNICITY
            or (eth_parts[1] != APPROVED_ETHNICITY[eth_parts[0]]
                # Preserve the existing *fixture-only* legacy abbreviation.
                and not (authority in {"JC", "ATL"}
                         and eth_parts == ["2186-5", "Non Hispanic", "CDCREC"]))
            or eth_parts[2] != "CDCREC"):
        raise ValueError("UNSUPPORTED_SYNTHETIC_DEMOGRAPHIC_CONCEPT_HOLD")
    if _field(pv1, "pv1", 2) != "I":
        raise ValueError("NOT_INPATIENT")
    event_ts = _utc(_field(msh, "msh", 7))
    if not _field(pv1, "pv1", 44):
        raise ValueError("ADMISSION_TIME_MISSING")
    admitted_at = _utc(_field(pv1, "pv1", 44))
    if event_type == "A01" and admitted_at != event_ts:
        raise ValueError("ADMISSION_EVENT_TIME_CONFLICT_HOLD")
    if event_type == "A03":
        end = _field(pv1, "pv1", 45)
        if not end or _utc(end) != event_ts or admitted_at > event_ts:
            raise ValueError("DISCHARGE_TIME_MISSING_OR_CONFLICT")
    raw_bytes = raw.encode("utf-8")
    return {
        "source_system": AUTHORITY_TO_SOURCE[authority],
        "source_version": "HL7v2.5.1",
        "source_batch_id": f"synthetic-hl7-{authority.lower()}-001",
        "source_ingest_date": "2026-11-05",
        "source_file": source_name,
        "source_file_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "source_file_size_bytes": str(len(raw_bytes)),
        "adapter_name": "hl7apy",
        "adapter_version": "1.3.5",
        "canonical_version": "v1",
        "processing_run_id": "synthetic-poc-001",
        "processed_at": "2026-11-06 00:00:00",
        "message_control_id": ctrl,
        "event_type": event_type,
        "source_person_id": patient_id,
        "source_encounter_id": visit_id,
        "birth_date": birth,
        "gender_code": gender,
        "race_code": race.split("^")[0],
        "ethnicity_code": ethnicity.split("^")[0],
        "event_datetime_utc": event_ts,
        "encounter_class": "inpatient",
        "source_code": "IMP",
    }
