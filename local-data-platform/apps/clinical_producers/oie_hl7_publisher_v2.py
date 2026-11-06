"""Versioned frozen FHIR manifest -> scoped OIE A01/A03 GET -> shared Blob plan.

READ-ONLY preparation; no OIE POST, Channel deployment, Azure connection or
historical batch replay. The publish entrypoint uses the existing immutable
Azure Blob Publisher unchanged and requires a separately authorized backend.
Legacy one-A01-per-Encounter interfaces are intentionally not modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from apps.clinical_producers.azure_blob_publisher import BlobBackend, publish_immutable
from apps.clinical_producers.blob_publish_contract import VERSION as PLAN_VERSION
from apps.clinical_producers.hospital_profiles import load_profile
from apps.clinical_producers.oie.build_adt_events_v2_channel import CHANNEL_ID
from apps.clinical_producers.oie.fhir_events import events_from_bundle
from apps.clinical_producers.oie_event_readback_v2 import (
    OIEV2EventReceipt, ScopedOIEGetter, fetch_v2_event_readbacks,
    OIEV2EventBlocked,
)
from apps.clinical_producers.oie_hl7_publisher import SAFE_ENCOUNTER
from apps.clinical_producers.source_handoff import verify_handoff
from apps.synthea.synthea_new_generator.generator import GenerationBlocked

RACE_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
ETHNICITY_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
CDCREC = "urn:oid:2.16.840.1.113883.6.238"
RACE = {
    "1002-5": "American Indian or Alaska Native",
    "2028-9": "Asian",
    "2054-5": "Black or African American",
    "2076-8": "Native Hawaiian or Other Pacific Islander",
    "2106-3": "White",
}
ETHNICITY = {"2135-2": "Hispanic or Latino", "2186-5": "Not Hispanic or Latino"}
INPATIENT_CLASS = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
BIRTH = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class OIEV2HandoffBlocked(ValueError):
    """Frozen source, mapping facts, message coverage or readback mismatch."""


def _blocked(reason: str) -> None:
    raise OIEV2HandoffBlocked("OIE_V2_" + reason)


def _escape(value: str) -> str:
    if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
        _blocked("PATIENT_NAME_UNSAFE")
    return "".join({
        "\\": r"\E\", "|": r"\F\", "^": r"\S\",
        "~": r"\R\", "&": r"\T\",
    }.get(c, c) for c in value)


def _coding(patient: dict, url: str, allowed: dict[str, str], field: str) -> str:
    extensions = patient.get("extension", [])
    if not isinstance(extensions, list):
        _blocked(field + "_EXTENSION_SHAPE")
    matches = [x for x in extensions if isinstance(x, dict) and x.get("url") == url]
    if len(matches) != 1 or not isinstance(matches[0].get("extension"), list):
        _blocked(field + "_EXTENSION_MISSING")
    categories = [x.get("valueCoding") for x in matches[0]["extension"]
                  if isinstance(x, dict) and x.get("url") == "ombCategory"]
    if len(categories) != 1 or not isinstance(categories[0], dict):
        _blocked(field + "_OMB_CATEGORY")
    coding = categories[0]
    if coding.get("system") != CDCREC or coding.get("code") not in allowed:
        _blocked(field + "_CODING_PROFILE")
    code = coding["code"]
    return code + "^" + _escape(allowed[code]) + "^CDCREC"


def _time(value: object, reason: str) -> tuple[datetime, str]:
    if not isinstance(value, str) or not INSTANT.fullmatch(value):
        _blocked(reason)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            _blocked(reason)
        utc = parsed.astimezone(timezone.utc)
        return utc, utc.strftime("%Y%m%d%H%M%S+0000")
    except (ValueError, OverflowError):
        _blocked(reason)


def _patient_fields(patient: dict) -> dict[str, str]:
    if not isinstance(patient, dict) or patient.get("resourceType") != "Patient":
        _blocked("PATIENT_INVALID")
    names = patient.get("name")
    if not isinstance(names, list) or not names or not isinstance(names[0], dict):
        _blocked("PATIENT_NAME_MISSING")
    name = names[0]
    family = name.get("family") or ""
    given = name.get("given") or []
    if not isinstance(given, list) or (given and not isinstance(given[0], str)):
        _blocked("PATIENT_NAME_INVALID")
    pid5 = _escape(family) + "^" + _escape(given[0] if given else "")
    birth = patient.get("birthDate")
    if not isinstance(birth, str) or not BIRTH.fullmatch(birth):
        _blocked("DOB_MISSING_OR_INVALID")
    try:
        if datetime.fromisoformat(birth).date().isoformat() != birth:
            _blocked("DOB_INVALID")
    except ValueError:
        _blocked("DOB_INVALID")
    gender = {"male": "M", "female": "F"}.get(patient.get("gender"))
    if not gender:
        _blocked("GENDER_MAPPING_PROFILE")
    return {
        "pid5": pid5, "dob": birth.replace("-", ""), "gender": gender,
        "race": _coding(patient, RACE_URL, RACE, "RACE"),
        "ethnicity": _coding(patient, ETHNICITY_URL, ETHNICITY, "ETHNICITY"),
    }


def _expected_for_envelope(envelope: dict, authority: str) -> dict[str, dict]:
    patient = envelope["bundle"]["entry"][0]["resource"]
    enc = envelope["bundle"]["entry"][1]["resource"]
    ident = enc.get("id")
    if not isinstance(ident, str) or not SAFE_ENCOUNTER.fullmatch(ident):
        _blocked("SOURCE_ENCOUNTER_ID")
    cls = enc.get("class")
    if (not isinstance(cls, dict) or cls.get("system") != INPATIENT_CLASS
            or cls.get("code") != "IMP"
            or enc.get("status") not in ("in-progress", "finished")):
        return {}  # Non-IMP/planned requests are NOT publication candidates.
    patient_id = patient.get("id")
    if (not isinstance(patient_id, str) or not SAFE_ENCOUNTER.fullmatch(patient_id)):
        _blocked("SOURCE_PATIENT_ID")
    facts = _patient_fields(patient)
    period = enc.get("period")
    if not isinstance(period, dict):
        _blocked("ENCOUNTER_PERIOD_MISSING")
    admission, admission_hl7 = _time(period.get("start"), "ADMISSION_TIME_INVALID")
    base = {
        "patient_id": patient_id, "encounter_id": ident, "authority": authority,
        "facts": facts, "start": admission_hl7,
    }
    result = {"A01": dict(base, event_time=admission_hl7, end="")}
    if enc["status"] == "finished":
        discharge, discharge_hl7 = _time(period.get("end"), "DISCHARGE_TIME_INVALID")
        if discharge < admission:
            _blocked("END_BEFORE_START")
        result["A03"] = dict(base, event_time=discharge_hl7, end=discharge_hl7)
    return result


def _source_inventory(state_root: Path, profile_path: Path, request_id: str):
    """Validate original files and manifest; build a scoped source inventory."""
    profile = load_profile(Path(profile_path))
    if profile["delivery"] != {
        "source_format": "FHIR_R4", "target_format": "HL7_V2", "transformer": "OIE",
    }:
        _blocked("HL7_HOSPITAL_PROFILE_REQUIRED")
    try:
        handoff = verify_handoff(Path(state_root), Path(profile_path), request_id)
    except (GenerationBlocked, OSError, ValueError):
        _blocked("SOURCE_HANDOFF_NOT_VERIFIED")
    if (handoff["status"] != "SOURCE_HANDOFF_VERIFIED"
            or handoff["hospital_id"] != profile["hospital_id"]
            or handoff["feed_id"] != profile["feed_id"]):
        _blocked("SOURCE_HANDOFF_SCOPE")
    payload_root = Path(state_root) / handoff["request_relative_path"] / "payload"
    events = {}
    for f in handoff["files"]:
        relative = f["path"]
        if (not isinstance(relative, str) or not relative.startswith("fhir/")
                or relative.count("/") != 1):
            _blocked("SOURCE_FILE_PATH")
        source = payload_root / relative
        if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
            _blocked("SOURCE_FILE_UNSAFE")
        raw = source.read_bytes()
        if (len(raw) != f["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != f["sha256"]):
            _blocked("SOURCE_FILE_CHANGED")
        try:
            rows = events_from_bundle(json.loads(raw), request_id)
        except (ValueError, KeyError, TypeError, UnicodeError, AttributeError):
            _blocked("SOURCE_FHIR_EVENTS_INVALID")
        for row in rows:
            ident = row["bundle"]["entry"][1]["resource"].get("id")
            if ident in events or not isinstance(ident, str) or not SAFE_ENCOUNTER.fullmatch(ident):
                _blocked("DUPLICATE_OR_UNSAFE_SOURCE_ENCOUNTER")
            events[ident] = row
    if not events or len(events) != handoff["metrics"]["fhir_encounters"]:
        _blocked("SOURCE_ENCOUNTER_COVERAGE")
    return handoff, events


def audit_frozen_adt_profile(state_root: Path, profile_path: Path, request_id: str,
                             *, assigning_authority: str = "JOHNSCREEKB") -> dict:
    """Read-only aggregate compatibility evidence; never print patient facts."""
    handoff, envelopes = _source_inventory(state_root, profile_path, request_id)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", assigning_authority):
        _blocked("ASSIGNING_AUTHORITY")
    issues = Counter()
    counts = Counter()
    for envelope in envelopes.values():
        try:
            expected = _expected_for_envelope(envelope, assigning_authority)
        except OIEV2HandoffBlocked as exc:
            issues[str(exc)] += 1
            continue
        if not expected:
            counts["non_admission_skipped"] += 1
        else:
            counts["admissions"] += 1
            counts["a01_eligible"] += 1
            counts["a03_eligible"] += int("A03" in expected)
    return {
        "status": "PROFILE_COMPATIBLE" if not issues and counts["admissions"] else "HOLD",
        "source_manifest_sha256": handoff["source_manifest_sha256"],
        "source_request_sha256": handoff["request_sha256"],
        "hospital_id": handoff["hospital_id"], "feed_id": handoff["feed_id"],
        "total_encounters": len(envelopes),
        "admissions": counts["admissions"],
        "a01_eligible": counts["a01_eligible"],
        "a03_eligible": counts["a03_eligible"],
        "non_admission_skipped": counts["non_admission_skipped"],
        "hold_count": sum(issues.values()),
        "hold_reasons": dict(sorted(issues.items())),
    }


def _assert_returned_source(raw: bytes, item, expected: dict) -> None:
    """Independently compare returned HL7 clinical facts to the frozen FHIR."""
    try:
        msh, evn, pid, pv1, tail = raw.decode("utf-8").split("\r")
        msh, evn, pid, pv1 = [x.split("|") for x in (msh, evn, pid, pv1)]
        facts = expected["facts"]
        checks = (
            tail == "" and msh[6] == expected["event_time"]
            and evn[2] == expected["event_time"]
            and pid[3] == expected["patient_id"] + "^^^" + expected["authority"] + "^MR"
            and pid[5] == facts["pid5"] and pid[7] == facts["dob"]
            and pid[8] == facts["gender"] and pid[10] == facts["race"]
            and pid[22] == facts["ethnicity"]
            and pv1[19] == expected["encounter_id"] + "^^^" + expected["authority"] + "^VN"
            and pv1[44] == expected["start"] and pv1[45] == expected["end"]
            and item.patient_id == expected["patient_id"]
            and item.payload_sha256 == hashlib.sha256(raw).hexdigest()
        )
    except (UnicodeDecodeError, IndexError, TypeError, ValueError):
        _blocked("SOURCE_CLINICAL_CORRELATION_HOLD")
    if not checks:
        _blocked("SOURCE_CLINICAL_CORRELATION_HOLD")


def prepare_oie_hl7_v2(
    state_root: Path, profile_path: Path, request_id: str, *,
    channel_id: str, assigning_authority: str,
    receipts: list[OIEV2EventReceipt], client: ScopedOIEGetter,
) -> tuple[dict, dict[str, bytes]]:
    """Source manifest + every eligible event + bounded persisted GET, no writes."""
    if channel_id != CHANNEL_ID:
        _blocked("UNAPPROVED_V2_CHANNEL")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", assigning_authority or ""):
        _blocked("ASSIGNING_AUTHORITY")
    handoff, events = _source_inventory(state_root, profile_path, request_id)
    expected = {}
    skipped = 0
    for ident, envelope in events.items():
        for event_type, data in _expected_for_envelope(envelope, assigning_authority).items():
            expected[(ident, event_type)] = data
        if not any(key[0] == ident for key in expected):
            skipped += 1
    if not expected:
        _blocked("NO_ELIGIBLE_ADT_EVENTS")
    if (not isinstance(receipts, list) or len(receipts) != len(expected)
            or {(r.source_encounter_id, r.event_type)
                for r in receipts if isinstance(r, OIEV2EventReceipt)} != set(expected)):
        _blocked("INCOMPLETE_OR_UNEXPECTED_EVENT_RECEIPTS")

    # Only after local source/coverage preflight do we touch the scoped GET.
    try:
        readbacks = fetch_v2_event_readbacks(
            client, channel_id=channel_id,
            hospital_id=handoff["hospital_id"], feed_id=handoff["feed_id"],
            request_id=handoff["request_id"], assigning_authority=assigning_authority,
            receipts=receipts,
        )
    except OIEV2EventBlocked:
        _blocked("PERSISTED_OIE_V2_READBACK_HOLD")
    objects, data = [], {}
    for item in readbacks:
        key = (item.source_encounter_id, item.event_type)
        if key not in expected:
            _blocked("UNEXPECTED_PERSISTED_EVENT")
        _assert_returned_source(item.payload, item, expected[key])
        name = "hl7/" + item.source_encounter_id + "-" + item.event_type + ".hl7"
        if name in data:
            _blocked("DUPLICATE_BLOB_OBJECT")
        data[name] = item.payload
        objects.append({
            "name": name, "size_bytes": len(item.payload),
            "sha256": item.payload_sha256, "source_event_id": item.control_id,
        })
    if len(objects) != len(expected):
        _blocked("INCOMPLETE_PERSISTED_MESSAGE_COVERAGE")
    # Revalidate original source bytes after remote OIE GET, before a PUT.
    try:
        if verify_handoff(Path(state_root), Path(profile_path), request_id) != handoff:
            _blocked("SOURCE_CHANGED_DURING_GET")
    except (GenerationBlocked, OSError, ValueError):
        _blocked("SOURCE_CHANGED_DURING_GET")
    plan = {
        "schema_version": PLAN_VERSION,
        "hospital_id": handoff["hospital_id"], "feed_id": handoff["feed_id"],
        "request_id": handoff["request_id"],
        "source_manifest_sha256": handoff["source_manifest_sha256"],
        "target_format": "HL7_V2",
        "verification_state": "OIE_HL7_READBACK_VERIFIED",
        "skipped_non_admissions": skipped,
        "objects": sorted(objects, key=lambda x: x["name"]),
    }
    return plan, data


def publish_oie_hl7_v2(
    state_root: Path, profile_path: Path, request_id: str, *,
    channel_id: str, assigning_authority: str,
    receipts: list[OIEV2EventReceipt], client: ScopedOIEGetter,
    landing_prefix: str, backend: BlobBackend,
) -> dict:
    """Use ONE existing publisher; runtime must separately authorize the PUT."""
    plan, source_bytes = prepare_oie_hl7_v2(
        state_root, profile_path, request_id,
        channel_id=channel_id, assigning_authority=assigning_authority,
        receipts=receipts, client=client,
    )
    return publish_immutable(plan, source_bytes, landing_prefix=landing_prefix,
                             backend=backend)


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only frozen Synthea OIE V2 ADT profile audit")
    p.add_argument("--state-root", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--request-id", required=True)
    args = p.parse_args()
    try:
        result = audit_frozen_adt_profile(args.state_root, args.profile, args.request_id)
    except (OIEV2HandoffBlocked, OSError, ValueError):
        print("OIE_V2_SOURCE_PROFILE_AUDIT_BLOCKED", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    # Incompatibility is an observed HOLD; do not misreport as compatible.
    return 0


if __name__ == "__main__":
    sys.exit(main())
