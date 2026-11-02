"""Immutable, OMOP-only PostgreSQL custom-dump delivery to Azure Blob.

This is a narrow adapter to the already-verified immutable Azure Blob backend.
It never opens PostgreSQL, deletes/overwrites Azure objects, or changes FHIR/HL7
Landing semantics. The PostgreSQL read-only snapshot is produced separately.
"""
from __future__ import annotations

import hashlib
import json
import re

from apps.clinical_producers.azure_blob_publisher import (
    BlobBackend, BlobNotFound, BlobSnapshot, PublishBlocked, _create_or_verify,
)

MANIFEST_VERSION = "healthcare-omop-blob-snapshot-v1"
BLOB_PREFIX = "omop/snapshots"
MAX_DUMP_BYTES = 256 * 1024 * 1024
DUMP_CONTENT_TYPE = "application/octet-stream"
MANIFEST_CONTENT_TYPE = "application/json"
SNAPSHOT_ID_RE = re.compile(r"omop-[0-9]{8}-[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?\Z")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")


def verify_source(snapshot_id: str, dump: bytes, prefix: str) -> None:
    """Fail closed before any Azure call, including manifest preflight."""
    if not isinstance(snapshot_id, str) or not SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise PublishBlocked("INVALID_OMOP_SNAPSHOT_ID")
    if prefix != BLOB_PREFIX:
        raise PublishBlocked("UNAPPROVED_OMOP_BLOB_PREFIX")
    if (type(dump) is not bytes or not 5 < len(dump) <= MAX_DUMP_BYTES
            or not dump.startswith(b"PGDMP")):
        raise PublishBlocked("INVALID_OR_OVERSIZE_PG_CUSTOM_DUMP")


def _existing_commit(backend: BlobBackend, key: str, *, snapshot_id: str,
                     object_key: str, sha: str, size: int) -> None:
    """Do not add new data under an already-committed but changed snapshot."""
    try:
        snapshot = backend.read(key)
    except BlobNotFound:
        return
    except Exception:
        raise PublishBlocked("OMOP_MANIFEST_PREFLIGHT_FAILED") from None
    if (not isinstance(snapshot, BlobSnapshot)
            or snapshot.content_type != MANIFEST_CONTENT_TYPE
            or not isinstance(snapshot.data, bytes)
            or not isinstance(snapshot.metadata, dict)
            or snapshot.metadata.get("kind") != "omopmanifest"
            or snapshot.metadata.get("sha256") != _sha256(snapshot.data)
            or snapshot.metadata.get("snapshotid") != snapshot_id):
        raise PublishBlocked("OMOP_MANIFEST_PREFLIGHT_INVALID")
    try:
        recorded = json.loads(snapshot.data)
    except (ValueError, UnicodeError, TypeError):
        raise PublishBlocked("OMOP_MANIFEST_PREFLIGHT_INVALID") from None
    if (not isinstance(recorded, dict)
            or recorded.get("schema_version") != MANIFEST_VERSION
            or recorded.get("snapshot_id") != snapshot_id
            or recorded.get("postgres_schema") != "cdm"
            or recorded.get("format") != "pg-custom"
            or not isinstance(recorded.get("objects"), list)
            or len(recorded["objects"]) != 1
            or recorded["objects"][0].get("blob_key") != object_key
            or recorded["objects"][0].get("sha256") != sha
            or recorded["objects"][0].get("size_bytes") != size):
        raise PublishBlocked("OMOP_IMMUTABLE_SNAPSHOT_CONFLICT")


def publish_omop_dump(snapshot_id: str, dump: bytes, *,
                      backend: BlobBackend, prefix: str = BLOB_PREFIX) -> dict:
    """Commit a bounded, verified CDM dump. Final manifest is the success marker.

    An identical-byte retry is safe. Repeating pg_dump with the *same*
    snapshot_id is NOT an identical retry because dump headers can differ;
    use a new snapshot_id for a new export.
    """
    verify_source(snapshot_id, dump, prefix)
    root = f"{prefix}/{snapshot_id}"
    object_key = root + "/omop-cdm.dump"
    manifest_key = root + "/snapshot-manifest.json"
    sha, size = _sha256(dump), len(dump)

    # A completed but conflicting snapshot must be rejected before ANY PUT.
    _existing_commit(backend, manifest_key, snapshot_id=snapshot_id,
                     object_key=object_key, sha=sha, size=size)
    metadata = {
        "kind": "omopdump", "sha256": sha, "sizebytes": str(size),
        "snapshotid": snapshot_id, "postgresschema": "cdm",
        "targetformat": "pg-custom",
    }
    saved, object_status = _create_or_verify(
        backend, object_key, dump, metadata, DUMP_CONTENT_TYPE)
    manifest = {
        "schema_version": MANIFEST_VERSION,
        "snapshot_id": snapshot_id,
        "postgres_schema": "cdm",
        "format": "pg-custom",
        "objects": [{
            "blob_key": object_key, "sha256": sha, "size_bytes": size,
            "etag": saved.etag, "version_id": saved.version_id,
        }],
    }
    manifest_data = _manifest_bytes(manifest)
    manifest_metadata = {
        "kind": "omopmanifest", "sha256": _sha256(manifest_data),
        "sizebytes": str(len(manifest_data)), "snapshotid": snapshot_id,
        "postgresschema": "cdm", "targetformat": "pg-custom",
    }
    committed, manifest_status = _create_or_verify(
        backend, manifest_key, manifest_data, manifest_metadata,
        MANIFEST_CONTENT_TYPE)
    return {
        "status": "OMOP_SNAPSHOT_MANIFEST_COMMITTED",
        "snapshot_id": snapshot_id,
        "dump_sha256": sha,
        "dump_size_bytes": size,
        "object_create_status": object_status,
        "manifest_create_status": manifest_status,
        "manifest_key": manifest_key,
        "manifest_sha256": _sha256(committed.data),
    }
