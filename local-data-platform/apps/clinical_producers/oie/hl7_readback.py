"""Independent, fail-closed HL7 v2.5.1 ADT A01 parse-back.

This verifies *returned OIE message bytes*, not mapper output and not
Blob publication. It must be used after OIE Server message retrieval.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

_SEGMENTS = ("MSH", "EVN", "PID", "PV1")
_TIME = re.compile(r"^[0-9]{14}[+-][0-9]{4}$")
_CONTROL = re.compile(r"^[A-Za-z0-9._-]{1,199}$")


class Hl7ReadbackError(ValueError):
    """A returned OIE payload failed the strict clinical contract."""


def parse_adt_a01(data: str | bytes) -> dict[str, str]:
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Hl7ReadbackError("HL7_INVALID_UTF8") from exc
    if not isinstance(data, str) or not data or len(data) > 65536:
        raise Hl7ReadbackError("HL7_SIZE_OR_SHAPE")
    if "\n" in data or "\x00" in data or "\r\r" in data or not data.endswith("\r"):
        raise Hl7ReadbackError("HL7_FRAMING")
    lines = data[:-1].split("\r")
    if len(lines) != 4:
        raise Hl7ReadbackError("HL7_SEGMENT_COUNT")
    segments = [line.split("|") for line in lines]
    if tuple(fields[0] for fields in segments) != _SEGMENTS:
        raise Hl7ReadbackError("HL7_SEGMENT_ORDER")
    msh, evn, pid, pv1 = segments
    if len(msh) < 12 or len(evn) < 3 or len(pid) < 6 or len(pv1) < 45:
        raise Hl7ReadbackError("HL7_FIELDS_MISSING")
    if msh[1] != r"^~\&" or msh[8] != "ADT^A01^ADT_A01" or msh[11] != "2.5.1":
        raise Hl7ReadbackError("HL7_MESSAGE_TYPE_VERSION")
    if evn[1] != "A01" or pv1[2] != "I":
        raise Hl7ReadbackError("HL7_NOT_INPATIENT_ADMISSION")
    if not _CONTROL.fullmatch(msh[9]):
        raise Hl7ReadbackError("HL7_CONTROL_ID")
    if not _TIME.fullmatch(msh[6]) or evn[2] != msh[6] or pv1[44] != msh[6]:
        raise Hl7ReadbackError("HL7_EVENT_TIME")
    patient = pid[3].split("^")
    visit = pv1[19].split("^")
    if len(patient) != 5 or len(visit) != 5:
        raise Hl7ReadbackError("HL7_ID_COMPONENT_COUNT")
    if not patient[0] or not visit[0] or patient[4] != "MR" or visit[4] != "VN":
        raise Hl7ReadbackError("HL7_ID_TYPE")
    if not patient[3] or patient[3] != visit[3]:
        raise Hl7ReadbackError("HL7_ASSIGNING_AUTHORITY")
    if not pid[5] or "^" not in pid[5]:
        raise Hl7ReadbackError("HL7_NAME_COMPONENTS")
    return {
        "message_type": "ADT^A01^ADT_A01",
        "version": "2.5.1",
        "control_id": msh[9],
        "event_time": msh[6],
        "patient_id": patient[0],
        "encounter_id": visit[0],
        "assigning_authority": patient[3],
    }


def verify_adt_against_fhir(
    raw_hl7: str | bytes, envelope: dict, *,
    hospital_id: str, feed_id: str, assigning_authority: str
) -> dict[str, str]:
    """Correlate an OIE-read message with the *exact* source encounter."""
    result = parse_adt_a01(raw_hl7)
    try:
        entries = envelope["bundle"]["entry"]
        request_id = envelope["request_id"]
        patients = [x["resource"] for x in entries if x["resource"]["resourceType"] == "Patient"]
        encounters = [x["resource"] for x in entries if x["resource"]["resourceType"] == "Encounter"]
        if len(patients) != 1 or len(encounters) != 1:
            raise Hl7ReadbackError("FHIR_EVENT_SHAPE")
        patient, encounter = patients[0], encounters[0]
        cls = encounter["class"]
        if (cls["system"] != "http://terminology.hl7.org/CodeSystem/v3-ActCode"
                or cls["code"] != "IMP" or encounter["status"] not in ("in-progress", "finished")):
            raise Hl7ReadbackError("FHIR_NOT_ADMISSION")
        if (result["patient_id"] != patient["id"]
                or result["encounter_id"] != encounter["id"]
                or result["assigning_authority"] != assigning_authority):
            raise Hl7ReadbackError("FHIR_HL7_ID_MISMATCH")
        expected_id = "-".join((hospital_id, feed_id, request_id, encounter["id"], "A01"))
        if result["control_id"] != expected_id:
            raise Hl7ReadbackError("FHIR_HL7_CONTROL_MISMATCH")
        instant = datetime.fromisoformat(encounter["period"]["start"].replace("Z", "+00:00"))
        if instant.tzinfo is None:
            raise Hl7ReadbackError("FHIR_UNZONED_ADMISSION_TIME")
        expected_time = instant.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S+0000")
        if result["event_time"] != expected_time:
            raise Hl7ReadbackError("FHIR_HL7_TIME_MISMATCH")
    except (TypeError, KeyError, IndexError, AttributeError, ValueError) as exc:
        if isinstance(exc, Hl7ReadbackError):
            raise
        raise Hl7ReadbackError("FHIR_EVENT_NOT_VERIFIABLE") from exc
    return result
