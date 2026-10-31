"""Strict FHIR R4 Bundle entry and standalone-resource parser (no I/O)."""
from __future__ import annotations

from collections import Counter
import json
from typing import Iterable

from healthcare_data_engine.models.batch_context import BatchContext, SourceObject
from healthcare_data_engine.quality.result import Finding, ParsedResource, ParsedResources

SUPPORTED = {"Patient", "Encounter"}
HOSPITAL_TAG_SYSTEM = "urn:healthcare:hospital-id"


def _finding(reason: str, detail: str, item: ParsedResource | None,
             source_file: str, resource_type: str = "", resource_id: str = "") -> Finding:
    return Finding("REJECTED", reason, detail,
                   item.resource_type if item else resource_type,
                   item.resource_id if item else resource_id,
                   source_file)


def parse_fhir_resources(raw_objects: Iterable[SourceObject],
                         context: BatchContext) -> ParsedResources:
    accepted: list[ParsedResource] = []
    rejected: list[Finding] = []
    for obj in raw_objects:
        issue = obj.verify(context)
        if issue:
            rejected.append(_finding(issue, "source receipt or namespace mismatch", None, obj.source_file))
            continue
        try:
            payload = json.loads(obj.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            rejected.append(_finding("INVALID_FHIR_JSON", "invalid UTF-8 JSON", None, obj.source_file))
            continue
        if not isinstance(payload, dict):
            rejected.append(_finding("INVALID_FHIR_RESOURCE", "top-level object required", None, obj.source_file))
            continue
        if payload.get("resourceType") == "Bundle":
            if payload.get("type") not in ("collection", "transaction", "batch", "document",
                                           "message", "searchset", "history"):
                rejected.append(_finding("INVALID_BUNDLE_TYPE", "unsupported or missing Bundle.type",
                                         None, obj.source_file))
                continue
            entries = payload.get("entry")
            if not isinstance(entries, list):
                rejected.append(_finding("INVALID_BUNDLE_ENTRY", "Bundle.entry must be array",
                                         None, obj.source_file))
                continue
        else:
            entries = [{"resource": payload}]
        for entry in entries:
            resource = entry.get("resource") if isinstance(entry, dict) else None
            full_url = entry.get("fullUrl") if isinstance(entry, dict) else None
            if not isinstance(resource, dict):
                rejected.append(_finding("MISSING_BUNDLE_RESOURCE", "entry.resource is required",
                                         None, obj.source_file))
                continue
            kind, rid = resource.get("resourceType"), resource.get("id")
            if not isinstance(kind, str) or not isinstance(rid, str) or not rid.strip():
                rejected.append(_finding("INVALID_RESOURCE_ID_TYPE", "non-empty resourceType and id required",
                                         None, obj.source_file, str(kind or ""), str(rid or "")))
                continue
            if kind not in SUPPORTED:
                rejected.append(_finding("UNSUPPORTED_RESOURCE_TYPE", kind, None,
                                         obj.source_file, kind, rid))
                continue
            if full_url is not None and (not isinstance(full_url, str) or not full_url.strip()):
                rejected.append(_finding("INVALID_FULLURL", "fullUrl must be a non-empty string",
                                         None, obj.source_file, kind, rid))
                continue
            tags = resource.get("meta", {}).get("tag", []) if isinstance(resource.get("meta", {}), dict) else []
            if isinstance(tags, list) and any(
                    isinstance(t, dict) and t.get("system") == HOSPITAL_TAG_SYSTEM
                    and t.get("code") != context.hospital_id for t in tags):
                rejected.append(_finding("CROSS_HOSPITAL_RESOURCE_CONFLICT",
                                         "FHIR meta.tag hospital differs from source context",
                                         None, obj.source_file, kind, rid))
                continue
            accepted.append(ParsedResource(resource, kind, rid, full_url, obj))
    by_key = Counter((x.resource_type, x.resource_id) for x in accepted)
    by_url = Counter(x.full_url for x in accepted if x.full_url is not None)
    final = []
    for item in accepted:
        if by_key[(item.resource_type, item.resource_id)] > 1:
            rejected.append(_finding("DUPLICATE_RESOURCE_ID", "ambiguous resource ID in source batch",
                                     item, item.source.source_file))
        elif item.full_url is not None and by_url[item.full_url] > 1:
            rejected.append(_finding("DUPLICATE_FULLURL", "ambiguous Bundle.fullUrl",
                                     item, item.source.source_file))
        else:
            final.append(item)
    return ParsedResources(tuple(final), tuple(rejected))
