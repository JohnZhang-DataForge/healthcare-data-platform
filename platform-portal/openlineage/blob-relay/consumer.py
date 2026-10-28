"""Committed OpenLineage Blob -> existing PRIVATE Marquez; lineage-only replay.

Nothing is connected or written at import. All IO is explicitly injected.
"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

class RelayError(ValueError):
    pass

def parse_json(raw: bytes) -> dict:
    def unique(pairs):
        obj = {}
        for key, val in pairs:
            if key in obj:
                raise RelayError("duplicate JSON key")
            obj[key] = val
        return obj
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    if not isinstance(obj, dict):
        raise RelayError("JSON object required")
    return obj

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")

def logical_id(event: dict) -> str:
    identity = {"eventType": event["eventType"], "eventTime": event["eventTime"],
                "job": {"namespace": event["job"]["namespace"],
                        "name": event["job"]["name"]},
                "runId": event["run"]["runId"]}
    return digest(canonical(identity))

def valid_event(event: dict) -> None:
    try:
        if not str(event["schemaURL"]).startswith("https://openlineage.io/spec/"):
            raise ValueError()
        if event["eventType"] not in {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"}:
            raise ValueError()
        if not event["eventTime"]:
            raise ValueError()
        uuid.UUID(event["run"]["runId"])
        if not event["job"]["namespace"] or not event["job"]["name"]:
            raise ValueError()
        for direction in ("inputs", "outputs"):
            datasets = event.get(direction, [])
            if not isinstance(datasets, list):
                raise ValueError()
            for ds in datasets:
                if not isinstance(ds["namespace"], str) or not ds["namespace"] or not isinstance(ds["name"], str) or not ds["name"]:
                    raise ValueError()
    except (KeyError, TypeError, ValueError) as exc:
        raise RelayError("invalid OpenLineage RunEvent") from exc

class Checkpoint:
    """Durable SQLite event checkpoint; use backed-up local persistent volume."""
    def __init__(self, path: str):
        if path == ":memory:":
            raise RelayError("durable checkpoint required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=30)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS delivered (event_key TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
        self.db.commit()

    def seen(self, key: str, sha: str) -> bool:
        row = self.db.execute("SELECT sha256 FROM delivered WHERE event_key=?", (key,)).fetchone()
        if row and row[0] != sha:
            raise RelayError("checkpoint key-content conflict")
        return row is not None

    def mark(self, key: str, sha: str) -> None:
        if self.seen(key, sha):
            return
        with self.db:
            self.db.execute("INSERT INTO delivered (event_key, sha256) VALUES (?, ?)", (key, sha))

    def close(self):
        self.db.close()

def consume(store, manifest_key: str, marquez, checkpoint: Checkpoint) -> int:
    """Require COMMITTED manifest, validate every event before any POST.

    Crash after POST/before checkpoint can replay only the lineage event.
    No business writer, Synthea, Spark, OMOP, or PG17 code is invoked.
    """
    match = re.fullmatch(r"openlineage/v1/batches/([A-Za-z0-9][A-Za-z0-9._-]{0,90})/manifest\.json", manifest_key)
    if not match:
        raise RelayError("manifest path outside reserved prefix")
    root = manifest_key.removesuffix("/manifest.json")
    manifest = parse_json(store.read(manifest_key))
    if (manifest.get("schema_version") != "openlineage.blob-manifest.v1" or
        manifest.get("state") != "COMMITTED" or manifest.get("batch_id") != match[1] or
        manifest.get("runtime") not in ("fabric", "local") or
        not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("source_manifest_sha256"))) or
        not isinstance(manifest.get("events"), list) or not manifest["events"] or
        manifest.get("event_count") != len(manifest["events"])):
        raise RelayError("missing/malformed committed manifest")
    seen_keys = set()
    staged = []
    for rec in manifest["events"]:
        if not isinstance(rec, dict):
            raise RelayError("invalid manifest record")
        eid, key, sha = rec.get("event_id"), rec.get("key"), rec.get("sha256")
        if (not isinstance(eid, str) or not re.fullmatch("[0-9a-f]{64}", eid) or
            key != f"{root}/events/{eid}.json" or not isinstance(sha, str) or
            not re.fullmatch("[0-9a-f]{64}", sha) or key in seen_keys):
            raise RelayError("bad event key/hash/duplicate")
        seen_keys.add(key)
        raw = store.read(key)
        if digest(raw) != sha:
            raise RelayError("event SHA mismatch")
        event = parse_json(raw)
        valid_event(event)
        if logical_id(event) != eid or canonical(event) != raw:
            raise RelayError("event identity/noncanonical JSON mismatch")
        staged.append((key, sha, event))
    delivered = 0
    for key, sha, event in staged:
        if checkpoint.seen(key, sha):
            continue
        marquez.ingest(event)
        marquez.verify(event)
        checkpoint.mark(key, sha)  # ONLY after independent readback
        delivered += 1
    return delivered

class MarquezHttp:
    """Caller supplies an authorized private Marquez host, never a public URL."""
    def __init__(self, base_url: str, *, timeout: int = 10):
        url = urlsplit(base_url)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise RelayError("invalid Marquez URL")
        if (url.hostname not in ("localhost", "127.0.0.1", "marquez", "marquez-api") and
            not url.hostname.endswith((".svc", ".svc.cluster.local"))):
            raise RelayError("Marquez must use private approved host")
        self.base = base_url.rstrip("/") + "/api/v1"
        self.timeout = timeout

    def request(self, method: str, path: str, event=None) -> dict:
        body = canonical(event) if event is not None else None
        req = Request(self.base + path, data=body, method=method,
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
        with urlopen(req, timeout=self.timeout) as response:
            raw = response.read()
            return parse_json(raw) if raw else {}

    def ingest(self, event: dict):
        self.request("POST", "/lineage", event)

    def verify(self, event: dict):
        ns, name = event["job"]["namespace"], event["job"]["name"]
        job = self.request("GET", f"/namespaces/{quote(ns, safe='')}/jobs/{quote(name, safe='')}")
        if job.get("namespace") != ns or job.get("name") != name:
            raise RelayError("Marquez job readback mismatch")
        run = self.request("GET", f"/jobs/runs/{quote(event['run']['runId'], safe='')}")
        if str(run.get("id", "")).lower() != event["run"]["runId"].lower():
            raise RelayError("Marquez run readback mismatch")
        if event["eventType"] == "COMPLETE" and run.get("state") != "COMPLETED":
            raise RelayError("Marquez terminal run not completed")
        for direction in ("inputs", "outputs"):
            for ds in event.get(direction, []):
                data = self.request("GET", f"/namespaces/{quote(ds['namespace'], safe='')}/datasets/{quote(ds['name'], safe='')}")
                if data.get("namespace") != ds["namespace"] or data.get("name") != ds["name"]:
                    raise RelayError("Marquez dataset readback mismatch")

def consume_with_retry(store, manifest_key: str, marquez, checkpoint: Checkpoint,
                       *, attempts: int = 3, sleep=None) -> int:
    """Bounded retry for transport outages; NEVER retries malformed manifests.

    A failed GET after an accepted POST is retried as lineage-only at-least-once
    delivery. Caller may inject a no-op sleeper for deterministic offline tests.
    """
    import time
    if not isinstance(attempts, int) or not 1 <= attempts <= 10:
        raise RelayError("attempts must be between 1 and 10")
    if sleep is None:
        sleep = time.sleep
    for attempt in range(attempts):
        try:
            return consume(store, manifest_key, marquez, checkpoint)
        except (ConnectionError, TimeoutError, OSError):
            if attempt + 1 == attempts:
                raise
            sleep(min(2 ** attempt, 30))
    raise AssertionError("unreachable")
