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


def read_events(root: Path, expected_events_sha256: str, expected_manifest_sha256: str) -> list[dict]:
    raw = (root / "encounter-events.ndjson").read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_events_sha256:
        raise ValueError("IMMUTABLE_EVENT_ARTIFACT_HASH_MISMATCH")
    if (root / "events-sha256.txt").read_text().strip() != expected_events_sha256:
        raise ValueError("EVENT_ARTIFACT_RECEIPT_MISMATCH")
    handoff = json.loads((root / "source-handoff.json").read_text())
    if not (handoff["status"] == "SOURCE_HANDOFF_VERIFIED"
            and handoff["request_id"] == "ci-johnscreek-fhir-0001"
            and handoff["hospital_id"] == "johns-creek-hospital-b"
            and handoff["feed_id"] == "johns-creek-hospital-b-hl7-v2"
            and handoff["source_manifest_sha256"] == expected_manifest_sha256):
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


def validate_record(doc: ET.Element, kind: str, envelope: dict) -> str:
    statuses = xml_text_nodes(doc, "status")
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
    if len(sources) != 1 or "TRANSFORMED" not in statuses:
        raise RuntimeError("ISOLATED_SOURCE_CONNECTOR_NOT_TRANSFORMED")
    if kind == "IMP":
        if not content.startswith("MSH|"):
            raise RuntimeError("ISOLATED_INPATIENT_NOT_PROCESSED_HL7")
        matched = verify_adt_against_fhir(
            content, envelope, hospital_id="johns-creek-hospital-b",
            feed_id="johns-creek-hospital-b-hl7-v2", assigning_authority="JOHNSCREEKB")
        if not matched["control_id"].endswith("-A01"):
            raise RuntimeError("ISOLATED_CONTROL_ID_WRONG")
        # Test runner reports aggregate evidence below
    else:
        if "ADT^A01" in content or content.startswith("MSH|"):
            raise RuntimeError("ISOLATED_AMB_WRONGLY_EMITTED_HL7")
        if content != SKIP:
            raise RuntimeError("ISOLATED_AMB_SKIP_NOT_RECORDED")
        # No ADT; only a deterministic non-admission marker

    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--admin-conf", type=Path, required=True)
    parser.add_argument("--existing-channel", action="store_true",
                        help="Read back existing persistent Channel only; never deploy or overwrite")
    parser.add_argument("--expected-events-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    for value in (args.expected_events_sha256, args.expected_manifest_sha256):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("UNSAFE_UNPINNED_ISOLATED_SOURCE")
    entries = read_events(args.artifact, args.expected_events_sha256, args.expected_manifest_sha256)
    secret = args.admin_conf.read_text()
    match = re.search(r"^\s*server\.initialadminpassword\s*=\s*(\S.+?)\s*$", secret, re.M)
    if not match:
        raise RuntimeError("ISOLATED_ADMIN_PASSWORD_NOT_SET")
    api = OieApi(match.group(1))
    if args.existing_channel:
        from apps.clinical_producers.oie.build_channel import render_channel
        _, xml = api.call(f"/api/channels/{CHANNEL_ID}")
        observed = ET.fromstring(xml)
        expected = ET.fromstring(render_channel())
        if (observed.findtext("id") != CHANNEL_ID
                or observed.findtext("name") != expected.findtext("name")
                or observed.findtext("preprocessingScript") != expected.findtext("preprocessingScript")):
            raise RuntimeError("OIE_LIVE_CHANNEL_CONFIG_MISMATCH")
        _, count_body = api.call(f"/api/channels/{CHANNEL_ID}/messages/count")
        if message_id(count_body) != "0":
            raise RuntimeError("HOLD_LIVE_CHANNEL_PREEXISTING_MESSAGES")
        print("OIE_LIVE_EXISTING_CHANNEL_UNCHANGED_AND_EMPTY=PASS")
    else:
        status, _ = api.call(f"/api/channels/{CHANNEL_ID}/_deploy?returnErrors=true", b"", "application/xml")
        if status not in (200, 204):
            raise RuntimeError("ISOLATED_CHANNEL_DEPLOY_FAILED")
    _, channel_status = api.call(f"/api/channels/{CHANNEL_ID}/status")
    if "STARTED" not in channel_status.decode():
        raise RuntimeError("OIE_CHANNEL_NOT_STARTED")
    print("OIE_CHANNEL_STARTED_READBACK=PASS")
    actual = {"IMP": 0, "AMB": 0}
    inpatient_event = None
    inpatient_hl7 = None
    def submit(envelope: dict, kind: str) -> str:
        payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        _, body = api.call(f"/api/channels/{CHANNEL_ID}/messages", payload, "text/plain")
        doc = get_record(api, message_id(body))
        return validate_record(doc, kind, envelope)

    for envelope in entries:
        cls = envelope["bundle"]["entry"][1]["resource"]["class"]["code"]
        content = submit(envelope, cls)
        actual[cls] += 1
        if cls == "IMP":
            inpatient_event = envelope
            inpatient_hl7 = content
    if actual != {"IMP": 1, "AMB": 30}:
        raise RuntimeError("ISOLATED_OIE_CLINICAL_COUNTS_WRONG")
    if inpatient_event is None or inpatient_hl7 is None:
        raise RuntimeError("ISOLATED_OIE_NO_ADMISSION_MESSAGE")
    retry_hl7 = submit(inpatient_event, "IMP")
    if retry_hl7 != inpatient_hl7:
        raise RuntimeError("ISOLATED_OIE_RETRY_HL7_NOT_STABLE")
    print("ISOLATED_OIE_REAL_IMP_ADT_A01_READBACK=PASS")
    print("ISOLATED_OIE_REAL_AMB_NO_ADT_COUNT=30")
    print("ISOLATED_OIE_REAL_31_ENCOUNTER_READBACK=PASS")
    print("ISOLATED_OIE_SAME_REQUEST_RETRY_IDENTICAL_HL7=PASS")
    print("ISOLATED_OIE_CLINICAL_MAPPING_RUNTIME=PASS" if not args.existing_channel
          else "OIE_LIVE_WORKER01_CLINICAL_MAPPING_RUNTIME=PASS")
    if args.existing_channel:
        _, after_count = api.call(f"/api/channels/{CHANNEL_ID}/messages/count")
        if message_id(after_count) != "32":
            raise RuntimeError("OIE_LIVE_EXPECTED_32_MESSAGE_RECORDS")
        print("OIE_LIVE_32_MESSAGE_RECORDS_READBACK=PASS")
        print("OIE_LIVE_PERSISTENT_DERBY_MESSAGE_WRITES=YES")
    print("AZURE_BLOB_PUBLICATION=NOT_STARTED")


if __name__ == "__main__":
    main()
