"""Synthetic FHIR -> isolated OIE 4.7 Channel API -> independent HL7 readback.

THIS SCRIPT IS FOR EPHEMERAL CI ONLY. Connects strictly to 127.0.0.1.
No Kubernetes, Blob, OMOP, patient logs, or real-namespace operations.
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from apps.clinical_producers.oie.hl7_readback import verify_adt_against_fhir

CHANNEL_ID = "69ace705-a675-45f6-b126-a3b22a65212a"
DIGEST = "af41fd1c84001c9a11f721a0c0004bd12164997b5e243c7071257e38fca3c67d"
MANIFEST = "05fe2808331522f2b8dae77c7e844ce0fa2e75081fa41adbedda0e9a49246b81"
SKIP = "OIE_ADT_NON_INPATIENT_SKIPPED"


def local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xml_text_nodes(root: ET.Element, tag: str) -> list[str]:
    return [x.text or "" for x in root.iter() if local_tag(x.tag) == tag]


class OieApi:
    def __init__(self, password: str) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar),
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
        form = urllib.parse.urlencode(
            {"username": "admin", "password": password}).encode()
        status, body = self.call("/api/users/_login", form, "application/x-www-form-urlencoded")
        if status != 200 or b"SUCCESS" not in body.upper():
            raise RuntimeError("ISOLATED_OIE_AUTH_FAILED")

    def call(self, path: str, payload: bytes | None = None, mime: str | None = None) -> tuple[int, bytes]:
        headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/xml"}
        if mime:
            headers["Content-Type"] = mime
        req = urllib.request.Request("https://127.0.0.1:18443" + path, data=payload, headers=headers)
        try:
            with self.opener.open(req, timeout=45) as response:
                return response.status, response.read(5_000_000)
        except urllib.error.HTTPError as err:
            # Never include payload, admin Secret or patient fields in CI logs.
            raise RuntimeError(f"ISOLATED_OIE_API_HTTP_{err.code}_ON_{path.split('?')[0]}") from None


def read_events(root: Path) -> list[dict]:
    raw = (root / "encounter-events.ndjson").read_bytes()
    if hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError("IMMUTABLE_EVENT_ARTIFACT_HASH_MISMATCH")
    if (root / "events-sha256.txt").read_text().strip() != DIGEST:
        raise ValueError("EVENT_ARTIFACT_RECEIPT_MISMATCH")
    handoff = json.loads((root / "source-handoff.json").read_text())
    if not (handoff["status"] == "SOURCE_HANDOFF_VERIFIED"
            and handoff["request_id"] == "ci-johnscreek-fhir-0001"
            and handoff["hospital_id"] == "demo-johns-creek"
            and handoff["feed_id"] == "demo-johns-creek-hl7-v2"
            and handoff["source_manifest_sha256"] == MANIFEST):
        raise ValueError("SOURCE_HANDOFF_IDENTITY_MISMATCH")
    entries = [json.loads(x) for x in raw.splitlines()]
    if len(entries) != handoff["metrics"]["fhir_encounters"] or len(entries) != 31:
        raise ValueError("REAL_FHIR_COUNT_MISMATCH")
    codes = {}
    for entry in entries:
        if entry["request_id"] != handoff["request_id"]:
            raise ValueError("FROZEN_REQUEST_ID_CHANGED")
        enc = [x["resource"] for x in entry["bundle"]["entry"]
               if x["resource"]["resourceType"] == "Encounter"]
        if len(enc) != 1:
            raise ValueError("EVENT_NOT_SINGLE_ENCOUNTER")
        cls = enc[0].get("class", {}).get("code")
        codes[cls] = codes.get(cls, 0) + 1
    if codes != {"IMP": 1, "AMB": 30}:
        raise ValueError("REAL_EVENT_CLASSES_CHANGED")
    print("ISOLATED_FHIR_SHA256_VERIFIED=PASS")
    print("ISOLATED_FHIR_CLASS_DISTRIBUTION=IMP:1 AMB:30")
    return entries


def message_id(body: bytes) -> str:
    wire = body.decode().strip()
    try:
        if wire.startswith("<"):
            parsed = ET.fromstring(wire)
            wire = (parsed.text or "").strip()
    except ET.ParseError as exc:
        raise RuntimeError("OIE_MESSAGE_ID_XML_INVALID") from exc
    if not wire.isdigit():
        raise RuntimeError("OIE_MESSAGE_ID_INVALID")
    return wire


def get_record(api: OieApi, msgid: str) -> ET.Element:
    for _ in range(18):
        _, raw = api.call(f"/api/channels/{CHANNEL_ID}/messages/{msgid}")
        try:
            doc = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise RuntimeError("OIE_MESSAGE_RECORD_INVALID_XML") from exc
        if (doc.findtext("processed") or "").lower() == "true":
            return doc
        time.sleep(1)
    raise RuntimeError("OIE_MESSAGE_PROCESS_TIMEOUT")


def validate_record(doc: ET.Element, kind: str, envelope: dict) -> None:
    statuses = xml_text_nodes(doc, "status")
    processed = xml_text_nodes(doc, "processedRaw")
    encoded = xml_text_nodes(doc, "encoded")
    # OIE Content uses <processedRaw><content>VALUE</content></processedRaw>.
    # Use source connector's processed raw; never use original input as evidence.
    sources = [x for x in doc.iter() if local_tag(x.tag) == "connectorMessage"
               and (x.findtext("metaDataId") or "") == "0"]
    content = ""
    if sources:
        for key in ("processedRaw", "encoded", "transformed"):
            elem = sources[0].find(key)
            if elem is not None:
                content = elem.findtext("content") or ""
                if content:
                    break
    print(f"ISOLATED_{kind}_CONNECTOR_COUNT=" + str(len(sources)))
    print(f"ISOLATED_{kind}_STATUS_VALUES=" + ",".join(sorted(set(statuses))[:8]))
    print(f"ISOLATED_{kind}_SOURCE_CONTENT_PRESENT=" + str(bool(content)).upper())
    print(f"ISOLATED_{kind}_RAW_TYPE=" + ("HL7" if content.startswith("MSH|") else
          "SKIP" if content == SKIP else "OTHER"))
    if kind == "IMP":
        if not content.startswith("MSH|"):
            raise RuntimeError("ISOLATED_INPATIENT_NOT_PROCESSED_HL7")
        matched = verify_adt_against_fhir(
            content, envelope, hospital_id="demo-johns-creek",
            feed_id="demo-johns-creek-hl7-v2", assigning_authority="DEMOJC")
        if not matched["control_id"].endswith("-A01"):
            raise RuntimeError("ISOLATED_CONTROL_ID_WRONG")
        print("ISOLATED_OIE_REAL_IMP_ADT_A01_READBACK=PASS")
    else:
        if "ADT^A01" in content or content.startswith("MSH|"):
            raise RuntimeError("ISOLATED_AMB_WRONGLY_EMITTED_HL7")
        if content != SKIP:
            raise RuntimeError("ISOLATED_AMB_SKIP_NOT_RECORDED")
        print("ISOLATED_OIE_REAL_AMB_NO_ADT=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--admin-conf", type=Path, required=True)
    args = parser.parse_args()
    entries = read_events(args.artifact)
    secret = args.admin_conf.read_text()
    match = re.search(r"^\s*server\.initialadminpassword\s*=\s*(\S.+?)\s*$", secret, re.M)
    if not match:
        raise RuntimeError("ISOLATED_ADMIN_PASSWORD_NOT_SET")
    api = OieApi(match.group(1))
    status, _ = api.call(f"/api/channels/{CHANNEL_ID}/_deploy?returnErrors=true", b"")
    if status not in (200, 204):
        raise RuntimeError("ISOLATED_CHANNEL_DEPLOY_FAILED")
    _, channel_status = api.call(f"/api/channels/{CHANNEL_ID}/status")
    if "STARTED" not in channel_status.decode():
        raise RuntimeError("ISOLATED_CHANNEL_NOT_STARTED")
    print("ISOLATED_OIE_CHANNEL_DEPLOY=PASS")
    for code in ("IMP", "AMB"):
        envelope = next(x for x in entries
                        if x["bundle"]["entry"][1]["resource"]["class"]["code"] == code)
        payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        _, body = api.call(f"/api/channels/{CHANNEL_ID}/messages", payload, "text/plain")
        id_ = message_id(body)
        doc = get_record(api, id_)
        validate_record(doc, code, envelope)
    print("ISOLATED_OIE_CLINICAL_MAPPING_RUNTIME=PASS")
    print("ISOLATED_OIE_BLOB_PUBLICATION=NO")


if __name__ == "__main__":
    main()
