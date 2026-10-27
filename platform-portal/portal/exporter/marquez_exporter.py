"""Offline, GET-only OpenLineage export from Marquez. No runtime writes or deployment."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class ExportError(ValueError):
    """Unsafe, inconsistent, or insufficiently evidenced input."""


EVENT_TYPES = {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"}
COL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
SHA40 = re.compile(r"^[a-f0-9]{40}$")
SHA64 = re.compile(r"^[a-f0-9]{64}$")
RUN_URL = re.compile(r"^https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+$")
SECRET = re.compile(r"(?i)(password|passwd|secret|bearer|token|api[_-]?key|access[_-]?key|credential|authorization|private[_-]?key)")
PRIVATE = re.compile(r"(?i)(localhost|[.]svc(?:[./]|$)|cluster[.]local|[.]internal\b|(?:jdbc|s3a?|gs|abfss?|wasbs?|file|postgres(?:ql)?):[/\\])")
IP = re.compile(r"(?<!\d)(?:\d{1,3}[.]){3}\d{1,3}(?!\d)")
LAYERS = {"LANDING", "PROCESSING", "OMOP", "LAKEHOUSE"}
BACKENDS = {"LOCAL_K8S", "FABRIC"}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def public_id(value):
    if not isinstance(value, str) or not 0 < len(value) <= 1024:
        raise ExportError("Invalid lineage identity")
    if SECRET.search(value) or PRIVATE.search(value) or "://" in value or any(x in value for x in ("?", "@", "\\", "\n", "\r")):
        raise ExportError("Unsafe lineage identity: publish gate HOLD")
    for address in IP.findall(value):
        try:
            ipaddress.ip_address(address)
        except ValueError:
            continue
        raise ExportError("Address in lineage identity: publish gate HOLD")
    return value


def time_utc(value):
    if not isinstance(value, str):
        raise ExportError("Missing timestamp")
    try:
        time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExportError("Invalid timestamp") from exc
    if time.tzinfo is None:
        raise ExportError("Timestamp must contain timezone")
    return time.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def key(dataset):
    return (dataset["namespace"], dataset["name"])


def dataset(raw):
    if not isinstance(raw, dict):
        raise ExportError("Invalid dataset object")
    result = {"namespace": public_id(raw.get("namespace")), "name": public_id(raw.get("name"))}
    facets = raw.get("facets") or {}
    if not isinstance(facets, dict):
        raise ExportError("Invalid dataset facets")
    clean = {}
    if "schema" in facets:
        schema = facets["schema"]
        fields = schema.get("fields") if isinstance(schema, dict) else None
        if not isinstance(fields, list):
            raise ExportError("Invalid schema fields")
        output = []
        for field in fields:
            if not isinstance(field, dict) or not COL.fullmatch(str(field.get("name", ""))):
                raise ExportError("Unsafe schema column")
            dtype = field.get("type", "UNKNOWN")
            if not isinstance(dtype, str) or not re.fullmatch(r"[A-Za-z0-9_(), .<>-]{1,80}", dtype):
                raise ExportError("Unsafe schema column type")
            output.append({"name": field["name"], "type": dtype})
        clean["schema"] = {"fields": output}
    if "columnLineage" in facets:
        lineage = facets["columnLineage"]
        fields = lineage.get("fields") if isinstance(lineage, dict) else None
        if not isinstance(fields, dict):
            raise ExportError("Invalid column lineage")
        cleaned = {}
        for target, info in sorted(fields.items()):
            if not COL.fullmatch(target) or not isinstance(info, dict) or not isinstance(info.get("inputFields"), list):
                raise ExportError("Invalid target column")
            upstream = {}
            for origin in info["inputFields"]:
                if not isinstance(origin, dict) or not COL.fullmatch(str(origin.get("field", ""))):
                    raise ExportError("Invalid source column")
                value = {"namespace": public_id(origin.get("namespace")), "name": public_id(origin.get("name")), "field": origin["field"]}
                upstream[(value["namespace"], value["name"], value["field"])] = value
            cleaned[target] = {"inputFields": [upstream[k] for k in sorted(upstream)]}
        clean["columnLineage"] = {"fields": cleaned}
    if clean:
        result["facets"] = clean
    return result


def clean_event(raw):
    if not isinstance(raw, dict) or raw.get("eventType") not in EVENT_TYPES:
        raise ExportError("Unsupported OpenLineage event")
    run, job = raw.get("run"), raw.get("job")
    if not isinstance(run, dict) or not isinstance(job, dict):
        raise ExportError("Missing job/run")
    run_id = run.get("runId")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", run_id):
        raise ExportError("Invalid runId")
    inputs, outputs = raw.get("inputs", []), raw.get("outputs", [])
    if not isinstance(inputs, list) or not isinstance(outputs, list):
        raise ExportError("Invalid dataset arrays")
    out = {
        "eventType": raw["eventType"], "eventTime": time_utc(raw.get("eventTime")),
        "producer": "https://github.com/JohnZhang-DataForge/healthcare-data-platform",
        "job": {"namespace": public_id(job.get("namespace")), "name": public_id(job.get("name"))},
        "run": {"runId": run_id}, "inputs": [dataset(x) for x in inputs],
        "outputs": [dataset(x) for x in outputs]
    }
    sources = {key(d) for d in out["inputs"]}
    for target in out["outputs"]:
        for field in target.get("facets", {}).get("columnLineage", {}).get("fields", {}).values():
            if any(key(upstream) not in sources for upstream in field["inputFields"]):
                raise ExportError("Column edge lacks run-level input dataset")
    return out


def normalize(events):
    if not isinstance(events, list) or not events:
        raise ExportError("Empty event export")
    unique = {}
    for raw in events:
        e = clean_event(raw)
        identity = (e["job"]["namespace"], e["job"]["name"], e["run"]["runId"], e["eventType"], e["eventTime"])
        if identity in unique and unique[identity] != e:
            raise ExportError("Conflicting events for the same job/run/type/time")
        unique[identity] = e
    return sorted(unique.values(), key=lambda x: (x["eventTime"], x["job"]["namespace"], x["job"]["name"], x["run"]["runId"], x["eventType"], canonical(x)))


def jsonl(events):
    return ("\n".join(canonical(e) for e in events) + "\n").encode("utf-8")


def fetch_events(base, limit=100, max_events=50000, opener=urlopen):
    """Use only the canonical GET /events/lineage API, bounded offset pagination."""
    url = urlsplit(base)
    if url.scheme not in ("http", "https") or not url.hostname or url.query or url.fragment or url.username or not base.rstrip("/").endswith("/api/v1"):
        raise ExportError("Marquez URL must be an /api/v1 base")
    if limit < 1 or limit > 500 or max_events < 1:
        raise ExportError("Invalid pagination bounds")
    events, offset, total = [], 0, None
    while True:
        uri = base.rstrip("/") + "/events/lineage?" + urlencode({"sortDirection": "asc", "limit": limit, "offset": offset})
        req = Request(uri, headers={"Accept": "application/json"}, method="GET")
        with opener(req, timeout=15) as response:
            body = json.load(response)
        if not isinstance(body, dict) or not isinstance(body.get("events"), list) or type(body.get("totalCount")) is not int:
            raise ExportError("Unexpected Marquez API shape")
        count, page = body["totalCount"], body["events"]
        if count < 0 or count > max_events or (total is not None and total != count) or len(page) > limit:
            raise ExportError("Inconsistent or unbounded Marquez pages")
        total = count
        if not page and offset < count:
            raise ExportError("Truncated Marquez pagination")
        events.extend(page)
        offset += len(page)
        if offset == count:
            return events
        if offset > count:
            raise ExportError("Marquez offset exceeds count")


def ref(prefix, value):
    return prefix + "-" + digest(value.encode("utf-8"))[:24]


def verified_snapshot(events, evidence, manifest, content_digest):
    """Offline evidence gate; source evidence must be independently audited before actual publication."""
    sha, manifest_sha, url = (evidence.get(k) for k in ("source_commit_sha", "source_manifest_sha256", "verification_run_url"))
    if not isinstance(sha, str) or not SHA40.fullmatch(sha) or not isinstance(manifest_sha, str) or not SHA64.fullmatch(manifest_sha) or not isinstance(url, str) or not RUN_URL.fullmatch(url):
        raise ExportError("Missing source SHA, manifest SHA256, or workflow URL")
    if digest(manifest) != manifest_sha:
        raise ExportError("Manifest bytes do not match evidence")
    proof = evidence.get("independent_readback")
    if not isinstance(proof, dict) or proof.get("passed") is not True:
        raise ExportError("Independent readback not verified")
    for k, v in (("source_commit_sha", sha), ("source_manifest_sha256", manifest_sha), ("verification_run_url", url), ("export_jsonl_sha256", content_digest)):
        if proof.get(k) != v:
            raise ExportError("Readback evidence mismatch: " + k)
    if proof.get("quality_status") != "PASS" or proof.get("dq_checks_failed") != 0:
        raise ExportError("Quality evidence not PASS")
    counts = ("patient_count", "encounter_count", "dq_checks_passed", "dq_checks_failed")
    if any(type(proof.get(k)) is not int or proof[k] < 0 for k in counts):
        raise ExportError("Missing measured counts")
    backend, hospitals, layers, run_ids = (proof.get(k) for k in ("source_backend", "hospitals", "dataset_layers", "verified_run_ids"))
    if backend not in BACKENDS | {"MIXED"} or not isinstance(hospitals, list) or not isinstance(layers, dict) or not isinstance(run_ids, list):
        raise ExportError("Missing verified backend/hospital/dataset/run metadata")
    if len({h.get("hospital_ref") for h in hospitals if isinstance(h, dict)}) != len(hospitals):
        raise ExportError("Duplicate hospital provenance")
    for h in hospitals:
        if not isinstance(h, dict) or set(h) != {"hospital_ref", "city", "source_type"} or h["source_type"] not in {"CSV", "FHIR_R4", "HL7_V2"}:
            raise ExportError("Invalid hospital provenance")
    groups, datasets = {}, {}
    for e in events:
        job_key = (e["job"]["namespace"], e["job"]["name"], e["run"]["runId"])
        groups.setdefault(job_key, []).append(e)
        for d in e["inputs"] + e["outputs"]:
            dk = key(d)
            datasets.setdefault(dk, set())
            datasets[dk].update(field["name"] for field in d.get("facets", {}).get("schema", {}).get("fields", []))
    runs, tables, columns = [], set(), set()
    for (ns, name, run_id), group in sorted(groups.items()):
        starts = [x["eventTime"] for x in group if x["eventType"] == "START"]
        ends = [x["eventTime"] for x in group if x["eventType"] == "COMPLETE"]
        if not starts or not ends:
            continue
        if run_id not in run_ids or max(ends) < min(starts):
            raise ExportError("COMPLETED run not independently attested")
        rb = proof.get("run_backends", {}).get(run_id) if backend == "MIXED" else backend
        if rb not in BACKENDS:
            raise ExportError("Run backend lacks provenance")
        run_ref = ref("run", ns + "::" + name + "::" + run_id)
        runs.append({"run_ref": run_ref, "display_name": name[:100], "backend": rb, "phase": "COMPLETE", "started_at": min(starts), "completed_at": max(ends)})
        for e in group:
            if e["eventType"] != "COMPLETE":
                continue
            for inp in e["inputs"]:
                for out in e["outputs"]:
                    source, target = key(inp), key(out)
                    tables.add((source, target, run_ref))
                    for dest_field, relation in out.get("facets", {}).get("columnLineage", {}).get("fields", {}).items():
                        datasets[target].add(dest_field)
                        for origin in relation["inputFields"]:
                            origin_key = key(origin)
                            datasets[origin_key].add(origin["field"])
                            columns.add((origin_key, origin["field"], target, dest_field, run_ref))
    observed_run_ids = {k[2] for k, group in groups.items() if any(e["eventType"] == "COMPLETE" for e in group) and any(e["eventType"] == "START" for e in group)}
    if set(run_ids) != observed_run_ids or not runs or not tables:
        raise ExportError("Verified run set or table evidence incomplete")
    def dref(dk):
        return ref("dataset", dk[0] + "::" + dk[1])
    ds = []
    for dk, cols in sorted(datasets.items()):
        layer = layers.get(dk[0] + "::" + dk[1])
        if layer not in LAYERS:
            raise ExportError("Dataset layer requires independent evidence")
        ds.append({"dataset_ref": dref(dk), "label": dk[1][-100:], "layer": layer, "columns": sorted(cols)})
    summary = {k: proof[k] for k in counts}
    summary.update({"hospital_count": len(hospitals), "quality_status": "PASS"})
    return {
        "schema_version": "portal.snapshot.v1", "snapshot_id": ref("snapshot", content_digest),
        "data_origin": "VERIFIED_EXPORT", "generated_at": time_utc(proof.get("checked_at")),
        "last_success_at": max(r["completed_at"] for r in runs), "source_backend": backend,
        "summary": summary, "hospitals": sorted(hospitals, key=lambda h: h["hospital_ref"]),
        "runs": sorted(runs, key=lambda r: (r["completed_at"], r["run_ref"])), "datasets": ds,
        "lineage": {"table_edges": [{"source_dataset_ref": dref(a), "target_dataset_ref": dref(b), "run_ref": r} for a, b, r in sorted(tables)],
                    "column_edges": [{"source_dataset_ref": dref(a), "source_column": f, "target_dataset_ref": dref(b), "target_column": t, "run_ref": r} for a, f, b, t, r in sorted(columns)]},
        "evidence": {"source_commit_sha": sha, "source_manifest_sha256": manifest_sha, "verification_run_url": url}
    }


def stage(destination: Path, raw_events, evidence=None, manifest=None):
    """Create a NEW local directory only; never overwrite a previously published success."""
    events = normalize(raw_events)
    content = jsonl(events)
    snapshot = None
    if evidence is not None:
        if manifest is None:
            raise ExportError("Manifest file is required")
        snapshot = verified_snapshot(events, evidence, manifest, digest(content))
    if destination.exists():
        raise ExportError("Output directory already exists; refusing overwrite")
    destination.mkdir(parents=True)
    if snapshot is None:
        (destination / "lineage.candidate.jsonl").write_bytes(content)
    else:
        (destination / "data" / "lineage").mkdir(parents=True)
        (destination / "data" / "snapshots").mkdir(parents=True)
        (destination / "data" / "lineage" / "latest.jsonl").write_bytes(content)
        body = (json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        (destination / "data" / "latest.json").write_bytes(body)
        (destination / "data" / "snapshots" / (snapshot["snapshot_id"] + ".json")).write_bytes(body)
    report = {"status": "VERIFIED_EXPORT" if snapshot else "CANDIDATE_ONLY", "event_count": len(events),
              "jsonl_sha256": digest(content), "publishable": snapshot is not None}
    (destination / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marquez-url", required=True, help="Marquez GET endpoint base ending in /api/v1")
    parser.add_argument("--output", required=True, type=Path, help="New offline staging directory")
    parser.add_argument("--evidence", type=Path, help="Externally verified readback evidence JSON")
    parser.add_argument("--manifest", type=Path, help="Exact original manifest bytes")
    parser.add_argument("--max-events", type=int, default=50000)
    args = parser.parse_args()
    if bool(args.evidence) != bool(args.manifest):
        parser.error("--evidence and --manifest must be supplied together")
    try:
        events = fetch_events(args.marquez_url, max_events=args.max_events)
        evidence = json.loads(args.evidence.read_text()) if args.evidence else None
        manifest = args.manifest.read_bytes() if args.manifest else None
        print(json.dumps(stage(args.output, events, evidence=evidence, manifest=manifest), sort_keys=True))
    except (ExportError, OSError, ValueError) as exc:
        parser.exit(2, "Export blocked: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
