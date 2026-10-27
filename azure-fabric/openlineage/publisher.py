"""Immutable standard OpenLineage RunEvent to Azure Blob batches (offline core).

Store contract: create(key, bytes) raises BlobExists on conditional-create conflict;
read(key) returns stored bytes. No clients or network initialized at import.
"""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Iterable

class BlobExists(Exception):
    """Conditional create failed because the key already exists."""

class IntegrityError(ValueError):
    pass

SAFE_BATCH = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,90}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
EVENT_TYPES = {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"}
BANNED_KEYS = {"sql", "query", "password", "secret", "token", "authorization",
               "credentials", "environmentvariables", "sparkproperties",
               "patientname", "patientid"}

def canonical(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")

def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def validate_event(event: dict) -> None:
    if not isinstance(event, dict) or not isinstance(event.get("schemaURL"), str) or not event["schemaURL"].startswith("https://openlineage.io/spec/"):
        raise IntegrityError("OpenLineage schemaURL required")
    if event.get("eventType") not in EVENT_TYPES or not isinstance(event.get("eventTime"), str):
        raise IntegrityError("eventType/eventTime invalid")
    try:
        datetime.fromisoformat(event["eventTime"].replace("Z", "+00:00"))
        uuid.UUID(event["run"]["runId"])
        if not event["job"]["namespace"] or not event["job"]["name"]:
            raise ValueError("empty job")
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("runId/job/eventTime invalid") from exc
    for direction in ("inputs", "outputs"):
        datasets = event.get(direction, [])
        if not isinstance(datasets, list):
            raise IntegrityError(f"{direction} must be a list")
        for ds in datasets:
            if not isinstance(ds, dict) or not isinstance(ds.get("namespace"), str) or not ds["namespace"] or not isinstance(ds.get("name"), str) or not ds["name"]:
                raise IntegrityError("dataset identity invalid")
    def scan(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if str(key).lower().replace("_", "") in BANNED_KEYS:
                    raise IntegrityError("unsafe metadata key rejected")
                scan(val)
        elif isinstance(value, list):
            for item in value:
                scan(item)
    scan(event)

def event_identity(event: dict) -> str:
    identity = {"eventType": event["eventType"], "eventTime": event["eventTime"],
                "job": {"namespace": event["job"]["namespace"],
                        "name": event["job"]["name"]},
                "runId": event["run"]["runId"]}
    return sha256(canonical(identity))

def create_or_check(store, key: str, payload: bytes) -> None:
    try:
        store.create(key, payload)
    except BlobExists:
        pass
    if store.read(key) != payload:
        raise IntegrityError(f"immutable blob collision: {key}")

def publish(store, *, batch_id: str, runtime: str, source_manifest_sha256: str,
            events: Iterable[dict], prefix: str = "openlineage/v1") -> str:
    """Validate all events, write immutable blobs, readback; commit Manifest LAST.

    An incomplete upload has orphan event objects and no commit marker.
    A same-key/different-content replay is a hard error, never an overwrite.
    """
    if not SAFE_BATCH.fullmatch(batch_id) or runtime not in ("fabric", "local") or not SHA.fullmatch(source_manifest_sha256):
        raise IntegrityError("bad batch, runtime or source manifest sha")
    if prefix != "openlineage/v1":
        raise IntegrityError("only reserved lineage prefix allowed")
    prepared: dict[str, tuple[str, bytes]] = {}
    for event in events:
        validate_event(event)
        eid = event_identity(event)
        payload = canonical(event)
        if eid in prepared and prepared[eid][1] != payload:
            raise IntegrityError("same logical event has different payload")
        prepared[eid] = (sha256(payload), payload)
    if not prepared:
        raise IntegrityError("empty event batch cannot commit")
    root = f"{prefix}/batches/{batch_id}"
    records = []
    for eid, (digest, payload) in sorted(prepared.items()):
        key = f"{root}/events/{eid}.json"
        records.append({"event_id": eid, "key": key, "sha256": digest})
    manifest = {"schema_version": "openlineage.blob-manifest.v1", "state": "COMMITTED",
                "batch_id": batch_id, "runtime": runtime,
                "source_manifest_sha256": source_manifest_sha256,
                "event_count": len(records), "events": records}
    for record in records:
        create_or_check(store, record["key"], prepared[record["event_id"]][1])
    marker = f"{root}/manifest.json"
    create_or_check(store, marker, canonical(manifest))
    return marker

class AzureBlobStore:
    """Opt-in SDK adapter; caller injects an already authorized ContainerClient.

    upload_blob(overwrite=False, BlockBlob) performs conditional create.
    A network error or unexpected exception must propagate; never mask it as exists.
    """
    def __init__(self, container_client):
        self.container = container_client

    def create(self, key: str, content: bytes) -> None:
        try:
            self.container.get_blob_client(key).upload_blob(content, blob_type="BlockBlob", overwrite=False)
        except Exception as exc:
            if exc.__class__.__name__ in ("ResourceExistsError", "BlobAlreadyExists"):
                raise BlobExists(key) from exc
            raise

    def read(self, key: str) -> bytes:
        return self.container.get_blob_client(key).download_blob().readall()
