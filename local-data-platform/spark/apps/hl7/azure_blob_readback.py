"""Scoped Azure Blob GET-only HL7 V2 readback into an isolated local Candidate input.

No LIST, OIE POST, Blob PUT/DELETE, Spark, Fabric or Silver publishing.
The out-of-band manifest SHA and source SHA must be independently approved;
a Blob path or response cannot authorize itself. All objects and clinical facts
are verified before a newly created local staging directory becomes visible.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from typing import Mapping, Protocol
from urllib.parse import urlsplit

from landing_intake import (
    FEED, HOSPITAL, HEX, REQUEST, ROOT_PREFIX, _manifest,
    verified_seed_rows,
)

MAX_OBJECTS = 100  # bounded pilot; the published Johns Creek batch has 42 events
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_OBJECT_BYTES = 65536
CONTENT_HL7 = "application/hl7-v2"
CONTENT_MANIFEST = "application/json"
KEY_SUFFIX = "/landing-manifest.json"
_UNSET = object()


def _blocked(code: str):
    raise ValueError("HL7_AZURE_READBACK_" + code)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    metadata: dict[str, str]
    content_type: str
    etag: str
    version_id: str | None


class GetOnly(Protocol):
    def read(self, key: str) -> Snapshot:
        """One exact-key HEAD + conditional GET + HEAD; no enumeration."""


def _metadata(sha: str, size: int, request_id: str, source_sha: str,
              *, kind: str, source_event_id: str | None = None) -> dict[str, str]:
    result = {
        "kind": kind,
        "sha256": sha,
        "sizebytes": str(size),
        "hospitalid": HOSPITAL,
        "feedid": FEED,
        "requestid": request_id,
        "sourcemanifestsha256": source_sha,
        "targetformat": "HL7_V2",
    }
    if source_event_id is not None:
        result["sourceeventsha256"] = _sha(source_event_id.encode("utf-8"))
    return result


def _snapshot(reader: GetOnly, key: str, *, sha: str, size: int,
              metadata: dict[str, str] | None, content_type: str,
              etag: str | None = None, version: object = _UNSET) -> Snapshot:
    try:
        snap = reader.read(key)
    except Exception:
        # Do not disclose Azure SDK exception text, account, SAS, URL or HL7 PHI.
        _blocked("REMOTE_GET_HOLD")
    if (not isinstance(snap.data, bytes)
            or not 0 < len(snap.data) <= MAX_MANIFEST_BYTES
            or (size is not None and len(snap.data) != size)
            or _sha(snap.data) != sha
            or not isinstance(snap.metadata, dict)
            or any(not isinstance(k, str) or not isinstance(v, str)
                   for k, v in snap.metadata.items())
            or (metadata is not None and snap.metadata != metadata)
            or snap.content_type != content_type
            or not isinstance(snap.etag, str) or not snap.etag
            or (etag is not None and snap.etag != etag)
            or (version is not _UNSET and snap.version_id != version)):
        _blocked("REMOTE_BYTES_OR_PROVENANCE_HOLD")
    return snap


def _validated_objects(manifest: dict, request_id: str, expected_count: int) -> list[dict]:
    objects = manifest["objects"]
    if len(objects) != expected_count or len(objects) > MAX_OBJECTS:
        _blocked("EXACT_OBJECT_COUNT_HOLD")
    prefix = f"{ROOT_PREFIX}/{request_id}/HL7_V2/hl7/"
    keys: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict) or set(obj) != {
            "blob_key", "sha256", "size_bytes", "source_event_id", "etag", "version_id"
        }:
            _blocked("OBJECT_CONTRACT_HOLD")
        key = obj["blob_key"]
        if (not isinstance(key, str) or len(key) > 360
                or not key.startswith(prefix) or not key.endswith(".hl7")
                or any(c in key for c in ("\\", "%", "?", "#"))
                or PurePosixPath(key).is_absolute()
                or any(x in (".", "..", "") for x in PurePosixPath(key).parts)
                or key in keys):
            _blocked("FOREIGN_OR_DUPLICATE_OBJECT_HOLD")
        keys.add(key)
        stem = key[len(prefix):-4]
        match = re.fullmatch(r"([A-Za-z0-9-]{1,64})-(A01|A03)", stem)
        if not match:
            _blocked("UNAPPROVED_EVENT_KEY_HOLD")
        required_event_id = "-".join((
            HOSPITAL, FEED, request_id, match.group(1), match.group(2)))
        if (obj["source_event_id"] != required_event_id
                or not isinstance(obj["sha256"], str) or not HEX.fullmatch(obj["sha256"])
                or type(obj["size_bytes"]) is not int
                or not 0 < obj["size_bytes"] <= MAX_OBJECT_BYTES
                or not isinstance(obj["etag"], str) or not obj["etag"]
                or (obj["version_id"] is not None and
                    (not isinstance(obj["version_id"], str) or not obj["version_id"]))):
            _blocked("OBJECT_PROVENANCE_HOLD")
    if [obj["blob_key"] for obj in objects] != sorted(keys):
        _blocked("MANIFEST_ORDER_HOLD")
    return objects


def _safe_output(root: Path) -> Path:
    if not root.is_absolute() or root in (Path("/"), Path("/tmp")) or ".." in root.parts:
        _blocked("OUTPUT_PATH_HOLD")
    if not root.parent.is_dir() or root.parent.is_symlink():
        _blocked("OUTPUT_PARENT_HOLD")
    if root.exists() and not root.is_dir() or root.is_symlink():
        _blocked("OUTPUT_UNSAFE_HOLD")
    if any(part.is_symlink() for part in (root.parent, *root.parent.parents)):
        _blocked("OUTPUT_PARENT_SYMLINK_HOLD")
    return root


def _verify_local(root: Path, *, manifest_sha256: str, source_sha256: str,
                  request_id: str, expected_objects: int,
                  ingest_date: str, processing_run_id: str,
                  processed_at: str) -> int:
    manifest_path = root / "landing-manifest.json"
    blob_root = root / "staged-local-blob-keys"
    if manifest_path.is_symlink() or not manifest_path.is_file() or blob_root.is_symlink():
        _blocked("LOCAL_REPLAY_FILES_HOLD")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = _manifest(manifest_bytes, manifest_sha256=manifest_sha256,
                             source_sha256=source_sha256, request_id=request_id)
        objects = _validated_objects(manifest, request_id, expected_objects)
        expected = {x["blob_key"] for x in objects}
        actual = {p.relative_to(blob_root).as_posix() for p in blob_root.rglob("*")
                  if p.is_file()}
        if expected != actual or any(p.is_symlink() for p in blob_root.rglob("*")):
            _blocked("LOCAL_REPLAY_INVENTORY_HOLD")
        rows = verified_seed_rows(
            manifest_bytes, blob_root, manifest_sha256=manifest_sha256,
            source_sha256=source_sha256, request_id=request_id,
            ingest_date=ingest_date, processing_run_id=processing_run_id,
            processed_at=processed_at)
        return len(rows)
    except (OSError, ValueError):
        _blocked("LOCAL_REPLAY_HOLD")


def stage_exact_readback(reader: GetOnly, *, request_id: str,
                         manifest_key: str, manifest_sha256: str,
                         source_sha256: str, expected_objects: int,
                         output_root: Path, ingest_date: str,
                         processing_run_id: str, processed_at: str) -> dict:
    """GET only approved manifest + its exact objects, then locally verify.

    Existing identical local output is replay-skipped without a network request.
    Existing conflicting output always HOLD; no overwrite or delete.
    """
    _validate_pins(request_id, manifest_key, manifest_sha256,
                   source_sha256, expected_objects)
    root = _safe_output(Path(output_root))
    opts = dict(manifest_sha256=manifest_sha256, source_sha256=source_sha256,
                request_id=request_id, expected_objects=expected_objects,
                ingest_date=ingest_date, processing_run_id=processing_run_id,
                processed_at=processed_at)
    if root.exists():
        count = _verify_local(root, **opts)
        return {"status": "ALREADY_MATCHING_LOCAL_REPLAY_SKIP",
                "objects": count, "scope": "LOCAL_SOURCE_CANDIDATE_ONLY"}
    manifest_snapshot = _snapshot(
        reader, manifest_key, sha=manifest_sha256,
        size=None, metadata=None, content_type=CONTENT_MANIFEST)
    # Independently pinned bytes and strict publisher metadata are checked
    # before any object GET. An exact manifest length is not known beforehand.
    manifest = _manifest(manifest_snapshot.data,
                         manifest_sha256=manifest_sha256,
                         source_sha256=source_sha256,
                         request_id=request_id)
    objects = _validated_objects(manifest, request_id, expected_objects)
    final_meta = _metadata(
        manifest_sha256, len(manifest_snapshot.data), request_id, source_sha256,
        kind="manifest")
    if manifest_snapshot.metadata != final_meta:
        _blocked("MANIFEST_REMOTE_METADATA_HOLD")
    temp = Path(tempfile.mkdtemp(prefix=".hl7-get-", dir=root.parent))
    try:
        manifest_dest = temp / "landing-manifest.json"
        manifest_dest.write_bytes(manifest_snapshot.data)
        manifest_dest.chmod(0o600)
        local_blob_root = temp / "staged-local-blob-keys"
        local_blob_root.mkdir(mode=0o700)
        for obj in objects:
            key = obj["blob_key"]
            snap = _snapshot(
                reader, key, sha=obj["sha256"], size=obj["size_bytes"],
                metadata=_metadata(
                    obj["sha256"], obj["size_bytes"], request_id,
                    source_sha256, kind="data",
                    source_event_id=obj["source_event_id"]),
                content_type=CONTENT_HL7,
                etag=obj["etag"], version=obj["version_id"])
            target = local_blob_root / key
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(snap.data)
            target.chmod(0o600)
        count = _verify_local(temp, **opts)
        # Detect changed manifest after all object GETs; no remote writes.
        second = _snapshot(
            reader, manifest_key, sha=manifest_sha256,
            size=len(manifest_snapshot.data), metadata=final_meta,
            content_type=CONTENT_MANIFEST, etag=manifest_snapshot.etag,
            version=manifest_snapshot.version_id)
        if second.data != manifest_snapshot.data:
            _blocked("REMOTE_MANIFEST_CHANGED_HOLD")
        if root.exists() or root.is_symlink():
            _blocked("OUTPUT_RACE_HOLD")
        os.rename(temp, root)
        return {"status": "EXACT_GET_LOCAL_STAGED", "objects": count,
                "scope": "LOCAL_SOURCE_CANDIDATE_ONLY"}
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def _validate_pins(request_id: str, manifest_key: str,
                   manifest_sha256: str, source_sha256: str,
                   expected_objects: int) -> None:
    if (not isinstance(request_id, str) or not REQUEST.fullmatch(request_id)
            or manifest_key != f"{ROOT_PREFIX}/{request_id}{KEY_SUFFIX}"
            or not isinstance(manifest_sha256, str) or not HEX.fullmatch(manifest_sha256)
            or not isinstance(source_sha256, str) or not HEX.fullmatch(source_sha256)
            or type(expected_objects) is not int
            or not 1 <= expected_objects <= MAX_OBJECTS):
        _blocked("OUT_OF_BAND_SOURCE_PIN_REQUIRED")

def _validate_cloud(account_url: str, container: str) -> None:
    url = urlsplit(account_url)
    if (url.scheme != "https" or not url.hostname
            or not re.fullmatch(r"[a-z0-9]{3,24}[.]blob[.]core[.]windows[.]net",
                                url.hostname)
            or url.username or url.password or url.port
            or url.path not in ("", "/") or url.query or url.fragment):
        _blocked("ACCOUNT_SCOPE_HOLD")
    if (not isinstance(container, str) or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])", container)):
        _blocked("CONTAINER_SCOPE_HOLD")


class AzureGetOnly:
    """Minimal remote interface: blob properties and conditional download only."""

    def __init__(self, container_client):
        self._container = container_client

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> AzureGetOnly:
        _validate_cloud(env.get("AZURE_BLOB_ACCOUNT_URL", ""),
                        env.get("AZURE_BLOB_CONTAINER", ""))
        if (env.get("AZURE_AUTH_MODE", "client-secret") != "client-secret"
                or env.get("AZURE_STORAGE_BEARER_TOKEN")
                or env.get("AZURE_STORAGE_TOKEN_EXPIRES_ON")):
            _blocked("READ_ONLY_CLIENT_SECRET_MODE_REQUIRED")
        names = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
        if not all(env.get(name) for name in names):
            _blocked("SCOPED_AZURE_IDENTITY_REQUIRED")
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient
        credential = ClientSecretCredential(
            tenant_id=env["AZURE_TENANT_ID"], client_id=env["AZURE_CLIENT_ID"],
            client_secret=env["AZURE_CLIENT_SECRET"])
        service = BlobServiceClient(
            account_url=env["AZURE_BLOB_ACCOUNT_URL"], credential=credential)
        return cls(service.get_container_client(env["AZURE_BLOB_CONTAINER"]))

    def read(self, key: str) -> Snapshot:
        from azure.core import MatchConditions
        blob = self._container.get_blob_client(key)
        before = blob.get_blob_properties()
        if (not isinstance(before.size, int) or before.size < 1
                or before.size > MAX_MANIFEST_BYTES):
            _blocked("REMOTE_OBJECT_SIZE_HOLD")
        etag = str(before.etag)
        payload = blob.download_blob(
            etag=etag, match_condition=MatchConditions.IfNotModified,
            max_concurrency=1, connection_timeout=10, read_timeout=30).readall()
        after = blob.get_blob_properties()
        if str(after.etag) != etag or after.version_id != before.version_id:
            _blocked("REMOTE_CHANGED_DURING_GET_HOLD")
        return Snapshot(
            data=payload, metadata=dict(after.metadata or {}),
            content_type=after.content_settings.content_type,
            etag=etag, version_id=after.version_id)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Authorized GET-only HL7 source staging")
    for flag in ("request-id", "manifest-key", "manifest-sha256",
                 "source-sha256", "ingest-date", "processing-run-id",
                 "processed-at"):
        p.add_argument("--" + flag, required=True)
    p.add_argument("--expected-objects", required=True, type=int)
    p.add_argument("--output-root", required=True, type=Path)
    p.add_argument("--approved-get-only", action="store_true")
    args = p.parse_args(argv)
    if not args.approved_get_only:
        print("HL7_AZURE_READBACK_NOT_APPROVED", file=sys.stderr)
        return 2
    try:
        # Validate out-of-band source scope and local target BEFORE SDK creation.
        _validate_pins(args.request_id, args.manifest_key,
                       args.manifest_sha256, args.source_sha256,
                       args.expected_objects)
        _safe_output(args.output_root)
        reader = AzureGetOnly.from_env(os.environ)
        result = stage_exact_readback(
            reader, request_id=args.request_id, manifest_key=args.manifest_key,
            manifest_sha256=args.manifest_sha256, source_sha256=args.source_sha256,
            expected_objects=args.expected_objects, output_root=args.output_root,
            ingest_date=args.ingest_date, processing_run_id=args.processing_run_id,
            processed_at=args.processed_at)
    except Exception:
        print("HL7_AZURE_READBACK_BLOCKED_NO_SOURCE_DISCLOSED", file=sys.stderr)
        return 1
    print("HL7_AZURE_GET_LOCAL_STATUS=" + result["status"])
    print("HL7_AZURE_GET_LOCAL_OBJECTS=" + str(result["objects"]))
    print("HL7_APPROVED_SILVER_OR_OMOP=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
