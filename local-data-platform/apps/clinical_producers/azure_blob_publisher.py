"""Fail-closed, hospital-neutral immutable Azure Blob Landing publisher.

No runtime side effects on import. Callers must supply independently verified
source bytes and an explicit, authorized destination/backend. A successful
return means each blob AND the final manifest passed an independent remote GET.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Protocol

from apps.clinical_producers.blob_publish_contract import verified_plan


MANIFEST_VERSION = "healthcare-azure-blob-landing-manifest-v1"
FHIR_CONTENT_TYPE = "application/fhir+json"
HL7_CONTENT_TYPE = "application/hl7-v2"
MANIFEST_CONTENT_TYPE = "application/json"


class PublishBlocked(RuntimeError):
    """Remote integrity, immutability or availability gate failed."""


class BlobNotFound(Exception):
    """Remote object does not exist (HTTP 404 only)."""


class BlobAlreadyExists(Exception):
    """Conditional create rejected because destination already exists."""


@dataclass(frozen=True)
class BlobSnapshot:
    """Properties plus the actual downloaded bytes, never cached source bytes."""

    data: bytes
    metadata: dict[str, str]
    content_type: str
    etag: str
    version_id: str | None = None


class BlobBackend(Protocol):
    def create(self, key: str, data: bytes, metadata: dict[str, str],
               content_type: str) -> str | None:
        """If-None-Match:* ONLY. Return new ETag, or raise BlobAlreadyExists."""

    def read(self, key: str) -> BlobSnapshot:
        """Independent remote HEAD/GET or raise BlobNotFound."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")


def _metadata(plan: dict, sha: str, size: int, *, kind: str,
              event_id: str | None = None) -> dict[str, str]:
    # Azure metadata names are case-insensitive. Values are ASCII only.
    metadata = {
        "kind": kind,
        "sha256": sha,
        "sizebytes": str(size),
        "hospitalid": plan["hospital_id"],
        "feedid": plan["feed_id"],
        "requestid": plan["request_id"],
        "sourcemanifestsha256": plan["source_manifest_sha256"],
        "targetformat": plan["target_format"],
    }
    if event_id is not None:
        metadata["sourceeventsha256"] = _sha(event_id.encode("utf-8"))
    return metadata


def _remote_read(backend: BlobBackend, key: str) -> BlobSnapshot:
    try:
        snapshot = backend.read(key)
    except BlobNotFound:
        raise PublishBlocked("REMOTE_OBJECT_MISSING") from None
    except Exception:
        # No SDK error strings, URL queries, credentials, or patient bytes in logs.
        raise PublishBlocked("REMOTE_GET_FAILED") from None
    if (not isinstance(snapshot, BlobSnapshot)
            or not isinstance(snapshot.data, bytes)
            or not isinstance(snapshot.etag, str) or not snapshot.etag
            or not isinstance(snapshot.metadata, dict)):
        raise PublishBlocked("INVALID_REMOTE_READBACK")
    return snapshot


def _verify(snapshot: BlobSnapshot, raw: bytes, metadata: dict[str, str],
            content_type: str, *, expected_etag: str | None = None) -> None:
    if (_sha(snapshot.data) != _sha(raw) or snapshot.data != raw
            or snapshot.metadata != metadata
            or snapshot.content_type != content_type):
        raise PublishBlocked("REMOTE_SHA256_OR_METADATA_CONFLICT")
    if expected_etag and snapshot.etag != expected_etag:
        raise PublishBlocked("REMOTE_ETAG_CHANGED")


def _create_or_verify(backend: BlobBackend, key: str, raw: bytes,
                      metadata: dict[str, str],
                      content_type: str) -> tuple[BlobSnapshot, str]:
    try:
        etag = backend.create(key, raw, metadata, content_type)
        state = "CREATED"
    except BlobAlreadyExists:
        etag = None
        state = "ALREADY_MATCHING"
    except Exception:
        raise PublishBlocked("REMOTE_CONDITIONAL_CREATE_FAILED") from None
    snapshot = _remote_read(backend, key)
    _verify(snapshot, raw, metadata, content_type, expected_etag=etag)
    return snapshot, state


def publish_immutable(plan: dict, source_bytes: dict[str, bytes], *,
                      landing_prefix: str, backend: BlobBackend) -> dict:
    """Validate before ANY writes, publish and GET data, commit manifest LAST.

    A failed attempt may leave immutable data objects; a retry performs GET
    verification and never replaces them. Manifest absence means NOT committed.
    A skip-only HL7 delivery must be recorded upstream, not as a fake publish.
    """
    entries = verified_plan(plan, source_bytes, landing_prefix=landing_prefix)
    if not entries:
        raise PublishBlocked("NO_PUBLISHABLE_OBJECTS")
    request_root = "/".join((landing_prefix, plan["hospital_id"],
                              plan["feed_id"], plan["request_id"]))
    manifest_key = request_root + "/landing-manifest.json"

    # A completed request must be verified, never blindly trusted or overwritten.
    # Preflight also prevents writing extra objects for a changed source on retry.
    try:
        existing_manifest = backend.read(manifest_key)
    except BlobNotFound:
        existing_manifest = None
    except Exception:
        raise PublishBlocked("MANIFEST_PREFLIGHT_FAILED") from None
    if existing_manifest is not None:
        if not isinstance(existing_manifest, BlobSnapshot):
            raise PublishBlocked("MANIFEST_PREFLIGHT_INVALID")
        try:
            recorded = json.loads(existing_manifest.data)
        except (ValueError, UnicodeError, TypeError):
            raise PublishBlocked("MANIFEST_PREFLIGHT_INVALID") from None
        if (not isinstance(recorded, dict)
                or not isinstance(recorded.get("objects"), list)
                or recorded.get("schema_version") != MANIFEST_VERSION
                or any(recorded.get(k) != plan[k] for k in (
                    "hospital_id", "feed_id", "request_id",
                    "source_manifest_sha256", "target_format",
                    "skipped_non_admissions"))
                or [e["blob_key"] for e in entries] !=
                   [e.get("blob_key") for e in recorded.get("objects", [])
                    if isinstance(e, dict)]):
            raise PublishBlocked("IMMUTABLE_REQUEST_CONFLICT")

    objects = []
    statuses = []
    content_type = (FHIR_CONTENT_TYPE if plan["target_format"] == "FHIR_R4"
                    else HL7_CONTENT_TYPE)
    # Prefix segments may themselves equal the format name; never split on it.
    data_root = request_root + "/" + plan["target_format"] + "/"
    for entry in entries:
        if not entry["blob_key"].startswith(data_root):
            raise PublishBlocked("INVALID_VERIFIED_OBJECT_KEY")
        name = entry["blob_key"][len(data_root):]
        raw = source_bytes[name]
        metadata = _metadata(plan, entry["sha256"], entry["size_bytes"],
                             kind="data", event_id=entry["source_event_id"])
        snapshot, state = _create_or_verify(
            backend, entry["blob_key"], raw, metadata, content_type)
        statuses.append(state)
        objects.append({
            "blob_key": entry["blob_key"],
            "sha256": entry["sha256"],
            "size_bytes": entry["size_bytes"],
            "source_event_id": entry["source_event_id"],
            "etag": snapshot.etag,
            "version_id": snapshot.version_id,
        })

    manifest = {
        "schema_version": MANIFEST_VERSION,
        "hospital_id": plan["hospital_id"],
        "feed_id": plan["feed_id"],
        "request_id": plan["request_id"],
        "source_manifest_sha256": plan["source_manifest_sha256"],
        "target_format": plan["target_format"],
        "skipped_non_admissions": plan["skipped_non_admissions"],
        "objects": objects,
    }
    manifest_bytes = _canonical(manifest)
    manifest_metadata = _metadata(plan, _sha(manifest_bytes),
                                  len(manifest_bytes), kind="manifest")
    readback, manifest_status = _create_or_verify(
        backend, manifest_key, manifest_bytes, manifest_metadata,
        MANIFEST_CONTENT_TYPE)
    # Do not trust preexisting manifest until actual bytes and metadata match.
    return {
        "status": "BLOB_MANIFEST_COMMITTED",
        "manifest_key": manifest_key,
        "manifest_sha256": _sha(readback.data),
        "manifest_etag": readback.etag,
        "manifest_version_id": readback.version_id,
        "manifest_create_status": manifest_status,
        "object_create_statuses": statuses,
        "objects": objects,
    }


class AzureSDKBlobBackend:
    """Azure SDK implementation; constructor has no network side effects.

    overwrite=False is the SDK's atomic If-None-Match:* conditional create.
    Never use overwrite=True, delete_blob or upsert. No container creation.
    """

    def __init__(self, container_client):
        self._container = container_client

    @classmethod
    def from_service_principal(cls, *, account_url: str, container: str,
                               tenant_id: str, client_id: str,
                               client_secret: str) -> "AzureSDKBlobBackend":
        # Restrict this guarded live factory to public Azure Blob HTTPS endpoints.
        from urllib.parse import urlsplit
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient

        url = urlsplit(account_url)
        if (url.scheme != "https" or not url.hostname
                or not url.hostname.endswith(".blob.core.windows.net")
                or url.username or url.password or url.port
                or url.path not in ("", "/") or url.query or url.fragment):
            raise PublishBlocked("INVALID_AZURE_ACCOUNT_URL")
        if (not isinstance(container, str) or not container
                or len(container) > 63 or
                not all(c.islower() or c.isdigit() or c == "-" for c in container)
                or container.startswith("-") or container.endswith("-")):
            raise PublishBlocked("INVALID_CONTAINER")
        # These values are injected at runtime from a scoped secret, never Git.
        if not all(isinstance(s, str) and s for s in (
                tenant_id, client_id, client_secret)):
            raise PublishBlocked("MISSING_AZURE_IDENTITY")
        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id,
            client_secret=client_secret)
        service = BlobServiceClient(account_url=account_url,
                                    credential=credential)
        return cls(service.get_container_client(container))

    def create(self, key: str, data: bytes, metadata: dict[str, str],
               content_type: str) -> str | None:
        from azure.core.exceptions import (
            HttpResponseError, ResourceExistsError, ResourceModifiedError)
        from azure.storage.blob import ContentSettings

        try:
            response = self._container.get_blob_client(key).upload_blob(
                data, overwrite=False, metadata=metadata, validate_content=True,
                content_settings=ContentSettings(content_type=content_type))
        except (ResourceExistsError, ResourceModifiedError):
            raise BlobAlreadyExists() from None
        except HttpResponseError as exc:
            code = str(getattr(exc, "error_code", "")).lower().replace("_", "")
            if exc.status_code in (409, 412) and (
                    "blobalreadyexists" in code or "conditionnotmet" in code):
                raise BlobAlreadyExists() from None
            raise
        return response.get("etag") if isinstance(response, dict) else None

    def read(self, key: str) -> BlobSnapshot:
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceNotFoundError

        blob = self._container.get_blob_client(key)
        try:
            before = blob.get_blob_properties()
            etag = str(before.etag)
            # Separate Azure GET, guarded against a replacement after HEAD.
            raw = blob.download_blob(
                etag=etag, match_condition=MatchConditions.IfNotModified
            ).readall()
            after = blob.get_blob_properties()
        except ResourceNotFoundError:
            raise BlobNotFound() from None
        if etag != str(after.etag):
            raise PublishBlocked("REMOTE_ETAG_CHANGED")
        return BlobSnapshot(
            data=raw,
            metadata=dict(after.metadata or {}),
            content_type=after.content_settings.content_type,
            etag=etag,
            version_id=after.version_id,
        )
