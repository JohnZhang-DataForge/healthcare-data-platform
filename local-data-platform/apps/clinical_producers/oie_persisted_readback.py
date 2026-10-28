"""Bounded, independently fetched OIE persisted source-connector readback.

This module only GETs explicitly supplied message IDs on the existing Channel.
It never submits, replays, enumerates or deletes OIE messages. An authenticated
scoped API identity and trusted TLS certificate are mandatory for real I/O.
The exact FHIR/HL7 correlation and skip coverage remain in oie_hl7_publisher.
"""
from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
import os
import re
import ssl
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import (
    HTTPCookieProcessor, HTTPSHandler, Request, build_opener,
)
from uuid import UUID
import xml.etree.ElementTree as ET

from apps.clinical_producers.oie_hl7_publisher import (
    OIEReadback, OIEDeliveryBlocked, SKIP_MARKER, SAFE_ENCOUNTER,
)

SERVICE_URL = "https://oie-debug.dw-oie.svc.cluster.local:8443"
MAX_XML_BYTES = 2_000_000
MESSAGE_ID = re.compile(r"^[1-9][0-9]{0,17}$")


class OIEReadbackBlocked(OIEDeliveryBlocked):
    """The OIE service, readback identity or content is not trustworthy."""


class MessageFetcher(Protocol):
    def get(self, path: str) -> bytes:
        """Authenticate independently and GET a single explicit channel message."""


def _xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ET.Element, tag: str) -> str | None:
    return next((v.text for v in node if _xml_local(v.tag) == tag), None)


def parse_persisted_source_message(
    raw_xml: bytes, *, channel_id: str, message_id: str,
    encounter_id: str,
) -> OIEReadback:
    """Return precise original transformed bytes or the explicit SKIP marker.

    Only the persisted OIE SOURCE connector is accepted, never destination
    connector content nor the original input FHIR payload.
    """
    try:
        UUID(channel_id)
    except (TypeError, ValueError, AttributeError):
        raise OIEReadbackBlocked("INVALID_OIE_CHANNEL_ID") from None
    if (not isinstance(message_id, str) or not MESSAGE_ID.fullmatch(message_id)
            or not isinstance(encounter_id, str)
            or not SAFE_ENCOUNTER.fullmatch(encounter_id)):
        raise OIEReadbackBlocked("INVALID_EXPLICIT_OIE_MESSAGE_ID")

    if (not isinstance(raw_xml, bytes) or not 0 < len(raw_xml) <= MAX_XML_BYTES
            or b"<!DOCTYPE" in raw_xml.upper()
            or b"<!ENTITY" in raw_xml.upper()):
        raise OIEReadbackBlocked("UNSAFE_OIE_MESSAGE_XML")
    try:
        doc = ET.fromstring(raw_xml)
    except ET.ParseError:
        raise OIEReadbackBlocked("INVALID_OIE_MESSAGE_XML") from None
    if _xml_local(doc.tag) != "message":
        raise OIEReadbackBlocked("INVALID_OIE_MESSAGE_ROOT")

    # The observed accepted OIE 4.7 readback exposes <processed>true</processed>.
    if (_child_text(doc, "processed") or "").lower() != "true":
        raise OIEReadbackBlocked("OIE_MESSAGE_NOT_PROCESSED")
    returned_channel = _child_text(doc, "channelId")
    returned_id = _child_text(doc, "messageId")
    if (returned_channel is not None and returned_channel != channel_id) or (
            returned_id is not None and returned_id != message_id):
        raise OIEReadbackBlocked("OIE_RESPONSE_IDENTITY_MISMATCH")

    sources = [
        v for v in doc.iter()
        if _xml_local(v.tag) == "connectorMessage"
        and _child_text(v, "metaDataId") == "0"
    ]
    if len(sources) != 1:
        raise OIEReadbackBlocked("OIE_SOURCE_CONNECTOR_MISSING_OR_AMBIGUOUS")
    source = sources[0]
    if _child_text(source, "status") != "TRANSFORMED":
        raise OIEReadbackBlocked("OIE_SOURCE_NOT_TRANSFORMED")
    content = None
    for kind in ("processedRaw", "encoded", "transformed"):
        envelope = next((x for x in source if _xml_local(x.tag) == kind), None)
        if envelope is None:
            continue
        value = _child_text(envelope, "content")
        if value:
            content = value
            break
    if not isinstance(content, str) or not content:
        raise OIEReadbackBlocked("OIE_SOURCE_TRANSFORMED_CONTENT_MISSING")
    try:
        payload = content.encode("utf-8")
    except UnicodeError:
        raise OIEReadbackBlocked("OIE_SOURCE_CONTENT_INVALID") from None
    if len(payload) > 65536:
        raise OIEReadbackBlocked("OIE_SOURCE_CONTENT_TOO_LARGE")
    if payload == SKIP_MARKER:
        disposition = "SKIP"
    elif payload.startswith(b"MSH|"):
        # Full HL7 v2.5.1 semantic validation is performed by prepare_oie_hl7.
        disposition = "ADT_A01"
    else:
        raise OIEReadbackBlocked("OIE_UNEXPECTED_TRANSFORMED_PAYLOAD")
    return OIEReadback(
        encounter_id=encounter_id, channel_id=channel_id,
        message_id=message_id, disposition=disposition, payload=payload,
    )


@dataclass(frozen=True)
class OIEPersistedMessage:
    """One newly submitted source Encounter correlated to its POST response ID."""
    encounter_id: str
    message_id: str


def fetch_persisted_readbacks(
    client: MessageFetcher, *, channel_id: str,
    new_request_messages: list[OIEPersistedMessage],
) -> list[OIEReadback]:
    """GET only explicit new-message receipts. No message-history enumeration.

    Caller must bind receipts to one newly generated frozen Request and provide
    a genuine authenticated OIE API client. This helper does not submit data.
    """
    try:
        UUID(channel_id)
    except (TypeError, ValueError, AttributeError):
        raise OIEReadbackBlocked("INVALID_OIE_CHANNEL_ID") from None
    if not isinstance(new_request_messages, list) or not new_request_messages:
        raise OIEReadbackBlocked("NO_NEW_OIE_MESSAGE_RECEIPTS")
    ids = set()
    encounters = set()
    results = []
    for msg in new_request_messages:
        if (not isinstance(msg, OIEPersistedMessage)
                or not isinstance(msg.message_id, str)
                or not MESSAGE_ID.fullmatch(msg.message_id)
                or not isinstance(msg.encounter_id, str)
                or not SAFE_ENCOUNTER.fullmatch(msg.encounter_id)
                or msg.message_id in ids or msg.encounter_id in encounters):
            raise OIEReadbackBlocked("DUPLICATE_OR_INVALID_OIE_RECEIPT")
        ids.add(msg.message_id)
        encounters.add(msg.encounter_id)

    for msg in new_request_messages:
        path = f"/api/channels/{channel_id}/messages/{msg.message_id}"
        try:
            raw = client.get(path)
        except Exception:
            # Do not print URL query, cookies, authorization headers or PHI.
            raise OIEReadbackBlocked("OIE_SCOPED_API_READ_FAILED") from None
        results.append(parse_persisted_source_message(
            raw, channel_id=channel_id, message_id=msg.message_id,
            encounter_id=msg.encounter_id))
    return results


class OIEScopedHTTPSClient:
    """OIE 4.7 cookie login, fixed internal service and certificate trust.

    Default mode preserves the existing scoped-account+hostname policy.
    For the explicit internal-only MVP path, OIE_INTERNAL_ADMIN_MODE=1 permits
    admin login with trust restricted to the pinned existing OIE certificate,
    skipping only the missing Kubernetes DNS SAN (not certificate verification).
    This is internal-cluster compatibility, not native OIE RBAC.
    """

    def __init__(self, *, username: str, password: str, ca_file: Path):
        internal_admin_mode = os.environ.get("OIE_INTERNAL_ADMIN_MODE") == "1"
        if (not isinstance(username, str) or not re.fullmatch(
                r"[A-Za-z0-9._-]{3,64}", username)
                or (username.lower() == "admin" and not internal_admin_mode)
                or not isinstance(password, str) or not password
                or not isinstance(ca_file, Path)
                or ca_file.is_symlink() or not ca_file.is_file()):
            raise OIEReadbackBlocked("OIE_SCOPED_IDENTITY_OR_TLS_REQUIRED")
        try:
            context = ssl.create_default_context(cafile=str(ca_file))
            # The existing internal-only OIE certificate is issued without a
            # Kubernetes Service DNS SAN. In the explicitly enabled MVP mode,
            # trust the pinned OIE leaf PEM as CA rather than modifying its
            # persistent keystore; full certificate chain validation stays ON.
            # NEVER use CERT_NONE or a global urllib TLS override.
            if internal_admin_mode:
                context.check_hostname = False
            self._opener = build_opener(
                HTTPCookieProcessor(CookieJar()),
                HTTPSHandler(context=context))
            body = urlencode({"username": username, "password": password}).encode()
            status, result = self._call(
                "/api/users/_login", method="POST", data=body,
                mime="application/x-www-form-urlencoded", limit=4096)
            if status != 200 or b"SUCCESS" not in result.upper():
                raise OIEReadbackBlocked("OIE_SCOPED_LOGIN_FAILED")
        except OIEReadbackBlocked:
            raise
        except Exception:
            raise OIEReadbackBlocked("OIE_SCOPED_LOGIN_FAILED") from None

    def _call(self, path: str, *, method: str = "GET", data: bytes | None = None,
              mime: str | None = None, limit: int = MAX_XML_BYTES) -> tuple[int, bytes]:
        if (not isinstance(path, str) or not re.fullmatch(
                r"/api/(?:users/_login|channels/[0-9a-f-]{36}/messages/[1-9][0-9]{0,17})",
                path)):
            raise OIEReadbackBlocked("OIE_SCOPED_PATH_NOT_ALLOWED")
        headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/xml"}
        if mime is not None:
            headers["Content-Type"] = mime
        try:
            req = Request(SERVICE_URL + path, method=method, data=data, headers=headers)
            with self._opener.open(req, timeout=20) as response:
                output = response.read(limit + 1)
                if len(output) > limit:
                    raise OIEReadbackBlocked("OIE_RESPONSE_TOO_LARGE")
                return response.status, output
        except OIEReadbackBlocked:
            raise
        except Exception:
            raise OIEReadbackBlocked("OIE_SCOPED_API_READ_FAILED") from None

    def get(self, path: str) -> bytes:
        status, raw = self._call(path)
        if status != 200:
            raise OIEReadbackBlocked("OIE_SCOPED_GET_NOT_OK")
        return raw
