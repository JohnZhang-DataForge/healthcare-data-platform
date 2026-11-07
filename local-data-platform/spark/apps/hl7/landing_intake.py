"""OIE V2 immutable Azure Raw HL7 → strictly verified structured staging rows.

No Azure, Kubernetes, OIE or Fabric APIs. Caller supplies a locally staged,
complete, checksum-verified manifest and exact Blob-relative bytes from an
independent authorized readback. This stage DOES NOT approve Silver/OMOP; ingestion is local-files-only.

Fail closed on missing, duplicate, foreign, corrupt or cross-request objects.
The manifest is authoritative for bytes/provenance, not generated test values.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path, PurePosixPath
import re

from parse_oie_v2 import parse_event

SCHEMA = "healthcare-azure-blob-landing-manifest-v1"
HOSPITAL = "johns-creek-hospital-b"
FEED = "johns-creek-hospital-b-hl7-v2"
AUTHORITY = "JOHNSCREEKB"
SOURCE = "johns-creek-hl7"
PREFIX = "clinical/v1"
ROOT_PREFIX = f"{PREFIX}/{HOSPITAL}/{FEED}"
HEX = re.compile(r"[0-9a-f]{64}")
REQUEST = re.compile(r"johnscreek-hl7-gh-[1-9][0-9]{8,17}")
ENCOUNTER = re.compile(r"[A-Za-z0-9-]{1,64}")
RUN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,95}")


def blocked(code: str) -> None:
    raise ValueError("HL7_OIE_V2_LANDING_" + code)


def _object_pairs(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            blocked("DUPLICATE_MANIFEST_FIELD")
        obj[key] = value
    return obj


def _read_local_blob(root: Path, blob_key: str) -> bytes:
    """Read only files located at the exact approved local Blob key path."""
    if (not isinstance(blob_key, str) or len(blob_key) > 360
            or "\\" in blob_key or "%" in blob_key or "?" in blob_key
            or "#" in blob_key):
        blocked("UNSAFE_OBJECT_KEY")
    relative = PurePosixPath(blob_key)
    if (relative.is_absolute() or str(relative) != blob_key
            or any(part in ("", ".", "..") for part in relative.parts)):
        blocked("UNSAFE_OBJECT_KEY")
    try:
        parent = root.resolve(strict=True)
    except OSError:
        blocked("LOCAL_SOURCE_ROOT_MISSING")
    if not root.is_dir() or root.is_symlink():
        blocked("LOCAL_SOURCE_ROOT_UNSAFE")
    for part in relative.parts:
        parent = parent / part
        if parent.is_symlink():
            blocked("LOCAL_SOURCE_SYMLINK")
    if not parent.is_file():
        blocked("LOCAL_SOURCE_FILE_MISSING")
    try:
        payload = parent.read_bytes()
    except OSError:
        blocked("LOCAL_SOURCE_UNREADABLE")
    if not 0 < len(payload) <= 65536:
        blocked("LOCAL_SOURCE_SIZE")
    return payload


def _manifest(manifest_bytes: bytes, *, manifest_sha256: str,
              source_sha256: str, request_id: str) -> dict:
    if (not isinstance(manifest_sha256, str)
            or not HEX.fullmatch(manifest_sha256)
            or hashlib.sha256(manifest_bytes).hexdigest() != manifest_sha256):
        blocked("MANIFEST_SHA256_MISMATCH")
    if (not isinstance(source_sha256, str)
            or not HEX.fullmatch(source_sha256)
            or not isinstance(request_id, str)
            or not REQUEST.fullmatch(request_id)):
        blocked("EXPECTED_SOURCE_ID_REQUIRED")
    try:
        manifest = json.loads(manifest_bytes, object_pairs_hook=_object_pairs)
    except (ValueError, UnicodeDecodeError, TypeError):
        blocked("MANIFEST_NOT_VALID_JSON")
    if (not isinstance(manifest, dict)
            or set(manifest) != {
                "schema_version", "hospital_id", "feed_id", "request_id",
                "source_manifest_sha256", "target_format",
                "skipped_non_admissions", "objects"}
            or manifest["schema_version"] != SCHEMA
            or manifest["hospital_id"] != HOSPITAL
            or manifest["feed_id"] != FEED
            or manifest["request_id"] != request_id
            or manifest["source_manifest_sha256"] != source_sha256
            or manifest["target_format"] != "HL7_V2"
            or type(manifest["skipped_non_admissions"]) is not int
            or manifest["skipped_non_admissions"] < 0
            or not isinstance(manifest["objects"], list)
            or not 1 <= len(manifest["objects"]) <= 5000):
        blocked("MANIFEST_CONTRACT")
    return manifest


def verified_seed_rows(manifest_bytes: bytes, blob_root: Path, *,
                       manifest_sha256: str, source_sha256: str,
                       request_id: str, ingest_date: str,
                       processing_run_id: str, processed_at: str) -> list[dict]:
    """Verify *all* listed HL7 objects before returning *any* Candidate row."""
    manifest = _manifest(manifest_bytes, manifest_sha256=manifest_sha256,
                         source_sha256=source_sha256, request_id=request_id)
    try:
        if date.fromisoformat(ingest_date).isoformat() != ingest_date:
            blocked("INGEST_DATE")
        if (not RUN.fullmatch(processing_run_id or "")
                or not isinstance(processed_at, str)
                or datetime.strptime(processed_at, "%Y-%m-%d %H:%M:%S")
                   .strftime("%Y-%m-%d %H:%M:%S") != processed_at):
            blocked("PROCESSING_METADATA")
    except (ValueError, TypeError):
        blocked("PROCESSING_METADATA")
    path_prefix = f"{ROOT_PREFIX}/{request_id}/HL7_V2/hl7/"
    rows, keys, seen, encounters = [], set(), set(), {}
    for obj in manifest["objects"]:
        if not isinstance(obj, dict) or set(obj) != {
                "blob_key", "sha256", "size_bytes", "source_event_id",
                "etag", "version_id"}:
            blocked("OBJECT_SCHEMA")
        key = obj["blob_key"]
        if (not isinstance(key, str) or not key.startswith(path_prefix)
                or not key.endswith(".hl7") or key in keys):
            blocked("FOREIGN_OR_DUPLICATE_BLOB_KEY")
        keys.add(key)
        stem = key[len(path_prefix):-4]
        match = re.fullmatch(r"([A-Za-z0-9-]{1,64})-(A01|A03)", stem)
        if match is None or not ENCOUNTER.fullmatch(match.group(1)):
            blocked("OBJECT_EVENT_FILENAME")
        encounter_id, event_type = match.groups()
        source_event_id = "-".join((
            HOSPITAL, FEED, request_id, encounter_id, event_type))
        if (obj["source_event_id"] != source_event_id
                or not isinstance(obj["sha256"], str)
                or not HEX.fullmatch(obj["sha256"])
                or type(obj["size_bytes"]) is not int
                or not 0 < obj["size_bytes"] <= 65536
                or not isinstance(obj["etag"], str) or not obj["etag"]
                or (obj["version_id"] is not None
                    and not isinstance(obj["version_id"], str))):
            blocked("OBJECT_METADATA")
        payload = _read_local_blob(blob_root, key)
        if (len(payload) != obj["size_bytes"]
                or hashlib.sha256(payload).hexdigest() != obj["sha256"]):
            blocked("OBJECT_SHA256_OR_SIZE")
        try:
            row = parse_event(payload.decode("utf-8"), source_name=key)
        except (ValueError, TypeError, UnicodeDecodeError, AttributeError,
                IndexError, KeyError):
            blocked("HL7_PARSER_OR_CLINICAL_PROFILE")
        if (row["source_system"] != SOURCE
                or row["source_encounter_id"] != encounter_id
                or row["event_type"] != event_type
                or row["message_control_id"] != source_event_id
                or row["source_file_sha256"] != obj["sha256"]
                or row["source_file_size_bytes"] != str(obj["size_bytes"])):
            blocked("HL7_SOURCE_OR_CONTROL_ID_MISMATCH")
        semantic_key = (encounter_id, event_type)
        if semantic_key in seen:
            blocked("DUPLICATE_VISIT_EVENT")
        seen.add(semantic_key)
        previous = encounters.setdefault(encounter_id, row["source_person_id"])
        if previous != row["source_person_id"]:
            blocked("CROSS_PATIENT_VISIT_COLLISION")
        row.update({
            "source_batch_id": request_id,
            "source_ingest_date": ingest_date,
            "processing_run_id": processing_run_id,
            "processed_at": processed_at,
        })
        rows.append(row)
    if (not any(event == "A01" for _, event in seen)
            or not any(event == "A03" for _, event in seen)
            or any(event == "A03" and (enc, "A01") not in seen
                   for enc, event in seen)):
        blocked("INCOMPLETE_ADT_EVENT_SET")
    return sorted(rows, key=lambda r: (
        r["source_system"], r["source_encounter_id"], r["event_type"]))
