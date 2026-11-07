#!/usr/bin/env python3
"""Isolated OIE 4.7.0 V2 import/deploy reproduction on GitHub-hosted Docker.

No worker01, K8s, existing OIE database/PVC, Azure, Fabric, live credentials,
or source messages. This uses ONLY a disposable local container with a fresh
random bootstrap admin secret. Unsafe localhost TLS is limited to loopback.
Do not use this script with an externally accessible URL.
"""
from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import hashlib
from pathlib import Path
import re
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import (
    Request, HTTPSHandler, HTTPCookieProcessor, build_opener,
)
import xml.etree.ElementTree as ET

BASE = "https://127.0.0.1:18443"
PINNED_SHA = "b63e89b8ebed04f8f371db95562413597c54295a"
V2_ID = "6b91681e-5b3b-59cb-b270-09412054110c"
STOPPED_SHA = "3a2af7d775cf62eb8b2f1c28cdff2d166034fd6252408dc32979e3928f246925"
ALLOWED_CLASSES = (
    "EvaluatorException", "ScriptException", "JavaScriptException",
    "ChannelException", "MirthApiException", "SQLException",
    "IllegalArgumentException", "NullPointerException", "DatabaseException",
    "NotFoundException", "ForbiddenException", "SecurityException",
    "NoClassDefFoundError", "ClassNotFoundException",
)


def hold(reason: str):
    raise RuntimeError("HOLD_OIE_DISPOSABLE_" + reason)


def xml_tree(body: bytes):
    if (not body or len(body) > 4_000_000 or b"<!DOCTYPE" in body.upper()
            or b"<!ENTITY" in body.upper()):
        hold("XML_UNSAFE")
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        hold("XML_INVALID")


def reviewed_xml(pinned_root: Path):
    rev = subprocess.run(["git", "-C", str(pinned_root), "rev-parse", "HEAD"],
                         capture_output=True, text=True, timeout=10, check=False)
    if rev.returncode or rev.stdout.strip() != PINNED_SHA:
        hold("PINNED_SOURCE_REVISION_MISMATCH")
    sys.path.insert(0, str((pinned_root / "local-data-platform").resolve()))
    from apps.clinical_producers.oie.build_adt_events_v2_channel import (
        CHANNEL_ID, CHANNEL_NAME, render_channel_v2)
    source = render_channel_v2()
    if CHANNEL_ID != V2_ID or CHANNEL_NAME != "Johns Creek HL7 ADT Events V2":
        hold("REVIEWED_CHANNEL_IDENTITY")
    needle = "<initialState>STARTED</initialState>"
    if source.count(needle) != 1:
        hold("REVIEWED_BUILDER_INITIAL_STATE")
    stopped = source.replace(needle, "<initialState>STOPPED</initialState>", 1)
    root = xml_tree(stopped.encode())
    if (root.findtext("id") != V2_ID
            or root.findtext("properties/initialState") != "STOPPED"
            or "fhirToHl7AdtEventsV2" not in (root.findtext("preprocessingScript") or "")):
        hold("REVIEWED_STOPPED_CHANNEL")
    if hashlib.sha256(stopped.encode()).hexdigest() != STOPPED_SHA:
        hold("STOPPED_CHANNEL_HASH_DRIFT")
    print("OIE_DISPOSABLE_REVIEWED_XML_SHA256=" + STOPPED_SHA)
    return stopped.encode()


def safe_category_report(raw):
    content = raw[:16000].lower()
    for cls in ALLOWED_CLASSES:
        if cls.lower().encode("ascii") in content:
            print("OIE_DISPOSABLE_ERROR_CLASS=" + cls)


class LocalOnlyOIE:
    def __init__(self):
        # Intentional temporary localhost-only TLS bypass: this Docker
        # instance has a generated self-signed cert; never use for live OIE.
        context = ssl._create_unverified_context()
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()),
                                   HTTPSHandler(context=context))

    def call(self, path, *, method="GET", body=None, accept="application/xml",
             content_type=None):
        allowed_get = {
            "/api/channels", f"/api/channels/{V2_ID}",
            f"/api/channels/{V2_ID}/status",
            "/api/server/channelMetadata",
            f"/api/channels/statuses?channelId={V2_ID}&includeUndeployed=true",
        }
        allowed_post = {
            "/api/users/_login", "/api/channels/",
            f"/api/channels/{V2_ID}/_deploy?returnErrors=true&debug=false",
            f"/api/channels/{V2_ID}/_start",
        }
        if not ((method == "GET" and path in allowed_get)
                or (method == "POST" and path in allowed_post)):
            hold("HTTP_VERB_OR_PATH_NOT_REVIEWED")
        headers = {"Accept": accept, "X-Requested-With": "XMLHttpRequest"}
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(BASE + path, headers=headers, method=method, data=body)
        try:
            with self.opener.open(request, timeout=65) as response:
                content = response.read(4_000_001)
                if len(content) > 4_000_000:
                    hold("HTTP_BODY_TOO_LARGE")
                return response.status, content
        except HTTPError as exc:
            payload = exc.read(16001)
            print("OIE_DISPOSABLE_HTTP_ERROR_CODE=" + str(exc.code))
            safe_category_report(payload)
            return exc.code, None

    def login(self, password):
        body = urlencode({"username": "admin", "password": password}).encode()
        code, data = self.call("/api/users/_login", method="POST", body=body,
                               content_type="application/x-www-form-urlencoded")
        if code != 200 or b"SUCCESS" not in (data or b"").upper():
            hold("ADMIN_LOGIN")
        print("OIE_DISPOSABLE_ADMIN_AUTH=PASS")


def single_v2_state(api):
    code, data = api.call(f"/api/channels/{V2_ID}/status")
    print("OIE_DISPOSABLE_SCALAR_STATUS_HTTP=" + str(code))
    if code == 200 and data:
        raw = data.strip()
        if raw in (b"STARTED", b"STOPPED", b"UNDEPLOYED"):
            return raw.decode("ascii")
        root = xml_tree(raw)
        # Only allowlisted XML structural facts; do not log the value or
        # serialized XML (which might include status details or other data).
        known_roots = {"string", "status", "state", "channelStatus",
                       "dashboardStatus", "list"}
        print("OIE_DISPOSABLE_SCALAR_STATUS_XML_ROOT=" +
              (root.tag if root.tag in known_roots else "OTHER"))
        print("OIE_DISPOSABLE_SCALAR_STATUS_STATE_NODE_COUNT=" +
              str(len(root.findall(".//state"))))
        if root.tag in ("string", "status", "state") and not len(root):
            return (root.text or "").strip()
        if root.tag == "channelStatus":
            return (root.findtext("state") or "").strip()
        if root.tag == "dashboardStatus":
            # Compare only direct Channel state + ID. This is the exact
            # structure accepted by Self-Runner OIE V2 gate (PR #566),
            # not any nested Source/Destination connector state.
            ids = [node for node in root if node.tag == "channelId"]
            states = [node for node in root if node.tag == "state"]
            matching = (len(ids) == 1 and len(states) == 1
                        and ids[0].text == V2_ID
                        and not ids[0].attrib and not len(ids[0])
                        and not states[0].attrib and not len(states[0]))
            print("OIE_DISPOSABLE_DASHBOARD_DIRECT_V2_ID_MATCH=" +
                  ("PASS" if matching else "HOLD"))
            if matching:
                state = (states[0].text or "").strip()
                if state in ("STOPPED", "STARTED", "PAUSED",
                             "UNDEPLOYED", "NOT_STARTED"):
                    return state
    return "UNKNOWN"


def list_state(api):
    path = f"/api/channels/statuses?channelId={V2_ID}&includeUndeployed=true"
    code, body = api.call(path)
    print("OIE_DISPOSABLE_STATUS_LIST_HTTP=" + str(code))
    if code != 200 or not body:
        return "UNKNOWN"
    root = xml_tree(body)
    records = list(root)
    if root.tag != "list" or len(records) != 1:
        return "UNKNOWN"
    node = records[0]
    if (node.tag != "dashboardStatus"
            or node.findtext("channelId") != V2_ID):
        return "UNKNOWN"
    state = (node.findtext("state") or "").strip()
    return state if state in ("UNDEPLOYED", "STOPPED", "STARTED") else "UNKNOWN"


def metadata_enabled(api):
    code, body = api.call("/api/server/channelMetadata")
    if code != 200 or not body:
        return "UNKNOWN"
    root = xml_tree(body)
    for entry in root.findall("entry"):
        if entry.findtext("string") != V2_ID:
            continue
        for meta in entry:
            if meta.tag.endswith("ChannelMetadata"):
                val = (meta.findtext("enabled") or "").strip()
                return val if val in ("true", "false") else "UNKNOWN"
    return "MISSING"


def run(pinned_root, password, *, sender_source_root=None):
    api = LocalOnlyOIE()
    expected = reviewed_xml(pinned_root)
    api.login(password)
    code, data = api.call("/api/channels")
    if code != 200 or xml_tree(data).findall(".//channel/id"):
        hold("PREEXISTING_CHANNELS_IN_FRESH_CONTAINER")
    print("OIE_DISPOSABLE_FRESH_CHANNEL_LIST=PASS")
    code, data = api.call("/api/channels/", method="POST", body=expected,
                          accept="text/plain", content_type="application/xml")
    if code not in (200, 201) or (data or b"").strip().lower() not in (
            b"true", b"<boolean>true</boolean>"):
        hold("IMPORT_FAILED")
    print("OIE_DISPOSABLE_IMPORT_HTTP_CODE=" + str(code))
    code, data = api.call(f"/api/channels/{V2_ID}")
    if code != 200:
        hold("CONFIG_GET_FAILED")
    readback = xml_tree(data)
    if (readback.findtext("id") != V2_ID
            or readback.findtext("properties/initialState") != "STOPPED"
            or readback.findtext("preprocessingScript")
               != xml_tree(expected).findtext("preprocessingScript")):
        hold("IMPORT_READBACK_DRIFT")
    print("OIE_DISPOSABLE_IMPORT_READBACK=PASS")
    print("OIE_DISPOSABLE_METADATA_ENABLED=" + metadata_enabled(api))
    print("OIE_DISPOSABLE_STATE_BEFORE_DEPLOY=" + list_state(api))
    deploy_path = f"/api/channels/{V2_ID}/_deploy?returnErrors=true&debug=false"
    # First prove production's original Accept: text/plain fails without
    # deployment in this *disposable* isolated OIE only. The previous
    # hosted Run #42352098003 confirmed HTTP 406 and UNDEPLOYED.
    bad_code, _ = api.call(
        deploy_path, method="POST", body=b"",
        content_type="application/xml", accept="text/plain")
    bad_state = list_state(api)
    print("OIE_DISPOSABLE_NEGATIVE_TEXT_PLAIN_HTTP_CODE=" + str(bad_code))
    print("OIE_DISPOSABLE_NEGATIVE_TEXT_PLAIN_STATE=" + bad_state)
    if bad_code != 406 or bad_state != "UNDEPLOYED":
        hold("NEGATIVE_CONTENT_NEGOTIATION_NOT_REPRODUCED")
    # Then change *only* Accept header on the same isolated Channel. This
    # never calls the real worker01 engine, nor repeats an unknown live POST.
    code, data = api.call(
        deploy_path, method="POST", body=b"",
        content_type="application/xml", accept="application/xml")
    print("OIE_DISPOSABLE_DEPLOY_ACCEPT_HEADER=APPLICATION_XML")
    print("OIE_DISPOSABLE_DEPLOY_HTTP_CODE=" + str(code))
    state = list_state(api)
    print("OIE_DISPOSABLE_STATE_AFTER_DEPLOY=" + state)
    scalar_state = single_v2_state(api)
    print("OIE_DISPOSABLE_SCALAR_STATE_AFTER_DEPLOY=" + scalar_state)
    if scalar_state != "STOPPED":
        hold("SCALAR_DASHBOARD_CHANNEL_STATE_MISMATCH")
    print("OIE_DISPOSABLE_DASHBOARD_IDENTITY_AND_STATE=PASS")
    if code not in (200, 204) or state != "STOPPED":
        hold("DEPLOY_NOT_STOPPED")
    print("OIE_DISPOSABLE_V2_DEPLOY_STOPPED_ACCEPTANCE=PASS")

    if sender_source_root is None:
        print("OIE_DISPOSABLE_START_POST=NO")
    else:
        # This START happens ONLY in a fresh 127.0.0.1 hosted Docker
        # container, solely to test the real new sender's GET-only preflight.
        # It does NOT authorize or perform a clinical message POST.
        start_code, _ = api.call(
            f"/api/channels/{V2_ID}/_start", method="POST",
            body=b"", content_type="application/xml",
            accept="application/xml")
        print("OIE_DISPOSABLE_START_HTTP_CODE=" + str(start_code))
        if start_code not in (200, 204):
            hold("EPHEMERAL_START_FAILED")
        if list_state(api) != "STARTED" or single_v2_state(api) != "STARTED":
            hold("EPHEMERAL_START_NOT_INDEPENDENTLY_PROVEN")
        print("OIE_DISPOSABLE_START_POST=EPHEMERAL_LOCAL_ONLY")

        # The pinned historical Builder is used for import above. Reload
        # the checked-out PR's apps package for this sender-under-test;
        # otherwise Python's module cache would silently load the old pinned
        # sender instead of the changed source. The Builder output must
        # still match the reviewed immutable STOPPED SHA256.
        root = Path(sender_source_root).resolve()
        src = root / "local-data-platform" / "apps" / "clinical_producers" / "oie_message_submit_v2.py"
        if not src.is_file():
            hold("SENDER_SOURCE_NOT_IN_WORKTREE")
        for module_name in tuple(sys.modules):
            if module_name == "apps" or module_name.startswith("apps."):
                del sys.modules[module_name]
        sys.path.insert(0, str((root / "local-data-platform").resolve()))
        import apps.clinical_producers.oie_message_submit_v2 as sender
        if Path(sender.__file__).resolve() != src:
            hold("SENDER_MODULE_WORKTREE_MISMATCH")
        source = sender.render_channel_v2()
        if (source.count("<initialState>STARTED</initialState>") != 1 or
                hashlib.sha256(source.replace(
                    "<initialState>STARTED</initialState>",
                    "<initialState>STOPPED</initialState>", 1).encode()).hexdigest()
                != STOPPED_SHA):
            hold("SENDER_REVIEWED_BUILDER_CHANGED")
        from unittest.mock import patch
        scoped = object.__new__(sender.ScopedOIEV2Poster)
        scoped._opener = api.opener
        with patch.object(sender, "SERVICE_URL", BASE):
            scoped.preflight_channel(V2_ID)
        print("OIE_DISPOSABLE_V2_SENDER_GET_ONLY_PREFLIGHT=PASS")

    print("OIE_DISPOSABLE_FHIR_HL7_MESSAGE_POST=NO")
    print("OIE_DISPOSABLE_AZURE_BLOB_PUT=NO")
    print("OIE_LIVE_WORKER01_OIE_DERBY_PVC_MUTATION=NO")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned-root", required=True)
    ap.add_argument("--admin-password-file", required=True)
    ap.add_argument("--verify-sender-preflight", action="store_true",
                    help="Only start disposable OIE locally and verify current sender GET")
    args = ap.parse_args()
    secret_file = Path(args.admin_password_file)
    if not secret_file.is_file():
        hold("ADMIN_SECRET_FILE_MISSING")
    password_line = secret_file.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"server\.initialadminpassword\s*=\s*(\S+)", password_line)
    if not match or len(match.group(1)) < 24:
        hold("ADMIN_SECRET_FORMAT")
    run(Path(args.pinned_root), match.group(1),
        sender_source_root=Path.cwd() if args.verify_sender_preflight else None)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error = str(exc)
        if not re.fullmatch(r"HOLD_OIE_DISPOSABLE_[A-Z0-9_]+", error):
            # Class name only; never print raw exception body, URL, password
            # file path or potentially PHI-bearing server response.
            known = ("PermissionError", "ModuleNotFoundError", "ImportError",
                     "ValueError", "TypeError", "OSError", "FileNotFoundError",
                     "AttributeError", "RuntimeError", "HTTPError")
            cls = type(exc).__name__
            print("OIE_DISPOSABLE_PYTHON_ERROR_CLASS=" +
                  (cls if cls in known else "OTHER"), file=sys.stderr)
            error = "HOLD_OIE_DISPOSABLE_UNKNOWN"
        print(error, file=sys.stderr)
        sys.exit(1)
