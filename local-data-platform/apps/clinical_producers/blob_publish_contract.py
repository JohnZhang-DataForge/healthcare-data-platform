"""Pure source-to-Azure publishing PLAN contract; no cloud or Kubernetes side effects.

Actual immutable conditional-blob uploads, independent GET readback and final
commit manifest are separate guarded implementation and runtime gates.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import PurePosixPath
import re

from apps.clinical_producers.oie.hl7_readback import parse_adt_a01, Hl7ReadbackError

VERSION = "healthcare-azure-blob-publish-plan-v1"
SAFE_ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
TOP = {"schema_version", "hospital_id", "feed_id", "request_id",
       "source_manifest_sha256", "target_format", "verification_state",
       "objects", "skipped_non_admissions"}
OBJ = {"name", "size_bytes", "sha256", "source_event_id"}
FMT = {
    "FHIR_R4": ("SOURCE_HANDOFF_VERIFIED", "fhir", ".json"),
    "HL7_V2": ("OIE_HL7_READBACK_VERIFIED", "hl7", ".hl7"),
}


class BlobPlanRejected(ValueError):
    """Plan is unsafe, unauthenticated, or inconsistent with source bytes."""


def _unique_pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise BlobPlanRejected("DUPLICATE_JSON_KEY")
        obj[k] = v
    return obj


def load_plan_json(data: str | bytes) -> dict:
    try:
        obj = json.loads(data, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise BlobPlanRejected("INVALID_PLAN_JSON") from exc
    if not isinstance(obj, dict):
        raise BlobPlanRejected("INVALID_PLAN_TYPE")
    return obj


def _valid_path(value: object, fmt_dir: str, suffix: str) -> bool:
    if not isinstance(value, str) or len(value) > 250:
        return False
    if "\\" in value or "%" in value or "?" in value or "#" in value:
        return False
    p = PurePosixPath(value)
    return (len(p.parts) == 2 and not p.is_absolute()
            and p.parts[0] == fmt_dir and
            p.parts[1] not in (".", "..") and
            bool(COMPONENT.fullmatch(p.parts[1])) and
            p.suffix == suffix)


def verified_plan(plan: dict, source_bytes: dict[str, bytes], *,
                  landing_prefix: str) -> list[dict]:
    """Return deterministic relative Blob keys ONLY after all bytes validate.

    Does not claim an Azure upload or readback. Bytes may come from verified
    Generator FHIR files or independently read-back OIE ADT messages.
    """
    if not isinstance(plan, dict) or set(plan) != TOP or plan.get("schema_version") != VERSION:
        raise BlobPlanRejected("INVALID_PLAN_SHAPE")
    for field in ("hospital_id", "feed_id"):
        if not isinstance(plan[field], str) or not SAFE_ID.fullmatch(plan[field]):
            raise BlobPlanRejected("INVALID_SOURCE_ID")
    if not isinstance(plan["request_id"], str) or not REQUEST_ID.fullmatch(plan["request_id"]):
        raise BlobPlanRejected("INVALID_REQUEST_ID")
    if (not isinstance(plan["source_manifest_sha256"], str)
            or not HEX64.fullmatch(plan["source_manifest_sha256"])):
        raise BlobPlanRejected("INVALID_SOURCE_MANIFEST_SHA256")
    fmt = plan["target_format"]
    if not isinstance(fmt, str) or fmt not in FMT:
        raise BlobPlanRejected("INVALID_FORMAT")
    expected_state, fmt_dir, suffix = FMT[fmt]
    if plan["verification_state"] != expected_state:
        raise BlobPlanRejected("UNVERIFIED_DELIVERY_STATE")
    skipped = plan["skipped_non_admissions"]
    if type(skipped) is not int or skipped < 0:
        raise BlobPlanRejected("INVALID_SKIP_COUNT")
    if fmt == "FHIR_R4" and skipped:
        raise BlobPlanRejected("FHIR_SKIP_COUNT_NOT_ALLOWED")
    if (not isinstance(landing_prefix, str)
            or not landing_prefix
            or len(landing_prefix) > 80
            or any(not COMPONENT.fullmatch(s) or s in (".", "..")
                   for s in landing_prefix.split("/"))):
        raise BlobPlanRejected("INVALID_LANDING_PREFIX")
    objects = plan["objects"]
    if not isinstance(objects, list) or (fmt == "FHIR_R4" and not objects) or len(objects) > 5000:
        raise BlobPlanRejected("INVALID_OBJECT_COUNT")
    if not isinstance(source_bytes, dict):
        raise BlobPlanRejected("INVALID_BYTES_MAPPING")
    names = set()
    result = []
    for item in objects:
        if not isinstance(item, dict) or set(item) != OBJ:
            raise BlobPlanRejected("INVALID_OBJECT_SHAPE")
        name = item["name"]
        if not _valid_path(name, fmt_dir, suffix) or name in names:
            raise BlobPlanRejected("UNSAFE_OR_DUPLICATE_OBJECT_NAME")
        names.add(name)
        sha = item["sha256"]
        nbytes = item["size_bytes"]
        if (not isinstance(sha, str) or not HEX64.fullmatch(sha)
                or type(nbytes) is not int or nbytes <= 0):
            raise BlobPlanRejected("INVALID_OBJECT_METADATA")
        raw = source_bytes.get(name)
        if not isinstance(raw, bytes) or len(raw) != nbytes or hashlib.sha256(raw).hexdigest() != sha:
            raise BlobPlanRejected("SOURCE_BYTES_MISMATCH")
        event = item["source_event_id"]
        if fmt == "FHIR_R4":
            if event is not None:
                raise BlobPlanRejected("FHIR_EVENT_ID_UNEXPECTED")
            try:
                bundle = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise BlobPlanRejected("INVALID_FHIR_JSON") from exc
            if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
                raise BlobPlanRejected("NOT_FHIR_BUNDLE")
        else:
            if not isinstance(event, str) or not event or len(event) > 199:
                raise BlobPlanRejected("INVALID_HL7_CONTROL_ID")
            try:
                parsed = parse_adt_a01(raw)
            except Hl7ReadbackError as exc:
                raise BlobPlanRejected("HL7_NOT_INDEPENDENTLY_VERIFIED") from exc
            if parsed["control_id"] != event:
                raise BlobPlanRejected("HL7_CONTROL_ID_MISMATCH")
        blob_key = "/".join((landing_prefix, plan["hospital_id"], plan["feed_id"],
                             plan["request_id"], fmt, name))
        result.append({"blob_key": blob_key, "sha256": sha,
                       "size_bytes": nbytes, "source_event_id": event})
    if set(source_bytes) != names:
        raise BlobPlanRejected("UNDECLARED_SOURCE_BYTES")
    return sorted(result, key=lambda x: x["blob_key"])
