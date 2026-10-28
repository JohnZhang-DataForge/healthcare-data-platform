"""One-shot, bounded submission of a NEW frozen FHIR request to a scoped OIE Channel.

SECURITY: no old message replay, no Channel deployment, no admin credentials,
no TLS bypass, no auto retry. A POST with unknown outcome is a HARD HOLD.
Receipts are only emitted after ALL POSTs acknowledged, and must be captured
and guarded by the same-run Self-Runner controller before the Blob publisher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Protocol
from urllib.request import Request
from uuid import UUID
import xml.etree.ElementTree as ET

from apps.clinical_producers.hospital_profiles import load_profile
from apps.clinical_producers.oie.fhir_events import events_from_bundle
from apps.clinical_producers.oie_persisted_readback import (
    MESSAGE_ID, OIEScopedHTTPSClient, OIEReadbackBlocked, SERVICE_URL,
)
from apps.clinical_producers.hl7_blob_runtime import (
    RECEIPT_VERSION, RUN_ID,
)
from apps.clinical_producers.source_handoff import verify_handoff

ENCOUNTER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$")
MAX_EVENTS = 1000
MAX_POST_BYTES = 131_072
MAX_ACK_BYTES = 4096


class OIEPostBlocked(RuntimeError):
    """Submission or frozen source identity is incomplete; NEVER auto-retry."""


class OIEPoster(Protocol):
    def submit(self, channel_id: str, event: bytes) -> str:
        """Return the actual numeric OIE source Message ID from one POST ACK."""


class ScopedOIEPoster(OIEScopedHTTPSClient):
    """Dedicated non-admin TLS client permitting only one explicit Channel POST.

    Its parent GET interface remains limited to individual persisted Message IDs.
    No mutation except new message delivery is exposed; no Channel management.
    """

    def submit(self, channel_id: str, event: bytes) -> str:
        try:
            UUID(channel_id)
        except (ValueError, TypeError, AttributeError):
            raise OIEPostBlocked("INVALID_OIE_CHANNEL_ID") from None
        if (not isinstance(event, bytes) or not 0 < len(event) <= MAX_POST_BYTES):
            raise OIEPostBlocked("OIE_POST_SIZE_INVALID")
        path = "/api/channels/" + channel_id + "/messages"
        request = Request(
            SERVICE_URL + path, method="POST", data=event,
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Accept": "application/xml", "Content-Type": "text/plain"})
        try:
            with self._opener.open(request, timeout=20) as response:
                if response.status not in (200, 201):
                    raise OIEPostBlocked("OIE_POST_ACK_STATUS_UNKNOWN")
                raw = response.read(MAX_ACK_BYTES + 1)
        except OIEPostBlocked:
            raise
        except Exception:
            # For network timeouts the POST may have been committed in Derby.
            # Never include URL, source bytes, cookies or credentials.
            raise OIEPostBlocked("OIE_POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") from None
        if not 0 < len(raw) <= MAX_ACK_BYTES or b"<!DOCTYPE" in raw.upper():
            raise OIEPostBlocked("OIE_POST_ACK_INVALID")
        try:
            wire = raw.decode("ascii").strip()
            if wire.startswith("<"):
                root = ET.fromstring(wire)
                if root.tag not in ("long", "string", "int"):
                    raise ValueError("unexpected response shape")
                wire = (root.text or "").strip()
        except (UnicodeError, ET.ParseError, ValueError):
            raise OIEPostBlocked("OIE_POST_ACK_INVALID") from None
        if not MESSAGE_ID.fullmatch(wire):
            raise OIEPostBlocked("OIE_POST_ACK_MISSING_MESSAGE_ID")
        return wire


def prepare_new_fhir_events(state_root: Path, profile_path: Path,
                            request_id: str, *, run_id: str,
                            expected_source_manifest_sha256: str) -> tuple[dict, list[tuple[str, bytes]]]:
    """Read-only audit each original frozen source before ANY POST."""
    if (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)
            or request_id != "johnscreek-hl7-gh-" + run_id
            or not isinstance(expected_source_manifest_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_source_manifest_sha256)):
        raise OIEPostBlocked("UNBOUND_NEW_SOURCE_REQUEST")
    profile = load_profile(Path(profile_path))
    if (profile["hospital_id"] != "johns-creek-hospital-b"
            or profile["feed_id"] != "johns-creek-hospital-b-hl7-v2"
            or profile["delivery"] != {
                "source_format": "FHIR_R4", "target_format": "HL7_V2",
                "transformer": "OIE"}):
        raise OIEPostBlocked("JOHNS_CREEK_PROFILE_REQUIRED")
    try:
        handoff = verify_handoff(Path(state_root), Path(profile_path), request_id)
    except Exception:
        # Keep validation failures stable and redact any underlying source path.
        raise OIEPostBlocked("FROZEN_SOURCE_HANDOFF_FAILED") from None
    if handoff["source_manifest_sha256"] != expected_source_manifest_sha256:
        raise OIEPostBlocked("PINNED_MANIFEST_SHA_CHANGED")
    base = Path(state_root) / handoff["request_relative_path"] / "payload"
    events = []
    seen = set()
    for file in handoff["files"]:
        name = file.get("path")
        if (not isinstance(name, str) or not name.startswith("fhir/")
                or name.count("/") != 1
                or name.split("/")[-1] in ("", ".", "..")):
            raise OIEPostBlocked("UNSAFE_FHIR_SOURCE_PATH")
        source = base / name
        if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
            raise OIEPostBlocked("UNSAFE_FHIR_SOURCE_PATH")
        raw = source.read_bytes()
        if (len(raw) != file["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != file["sha256"]):
            raise OIEPostBlocked("FHIR_SOURCE_CHANGED")
        try:
            bundles = events_from_bundle(json.loads(raw), request_id)
        except (KeyError, ValueError, TypeError, UnicodeError):
            raise OIEPostBlocked("FHIR_EVENTS_INVALID") from None
        for envelope in bundles:
            eid = envelope["bundle"]["entry"][1]["resource"].get("id")
            if (not isinstance(eid, str) or not ENCOUNTER_ID.fullmatch(eid)
                    or eid in seen):
                raise OIEPostBlocked("FHIR_ENCOUNTER_DUPLICATE_OR_UNSAFE")
            seen.add(eid)
            wire = json.dumps(envelope, separators=(",", ":"), sort_keys=True,
                              ensure_ascii=False).encode("utf-8")
            if not 0 < len(wire) <= MAX_POST_BYTES:
                raise OIEPostBlocked("FHIR_EVENT_EXCEEDS_OIE_POST_LIMIT")
            events.append((eid, wire))
    if (not events or len(events) > MAX_EVENTS
            or len(events) != handoff.get("metrics", {}).get("fhir_encounters")):
        raise OIEPostBlocked("FHIR_ENCOUNTER_COUNT_INVALID")
    return handoff, sorted(events, key=lambda row: row[0])


def submit_new_fhir_request(state_root: Path, profile_path: Path,
                            request_id: str, *, run_id: str,
                            channel_id: str,
                            expected_source_manifest_sha256: str,
                            poster: OIEPoster) -> dict:
    """Only successful one-POST-per-event ACKs yield a complete handoff receipt.

    Any ambiguous POST result requires HOLD and independent live investigation;
    a new caller MUST NOT re-submit the same request. The receipt is not
    cryptographic evidence: the trusted, gated controller must capture it
    directly from the exact Job and use it exactly once.
    """
    try:
        UUID(channel_id)
    except (TypeError, ValueError, AttributeError):
        raise OIEPostBlocked("INVALID_OIE_CHANNEL_ID") from None
    handoff, events = prepare_new_fhir_events(
        state_root, profile_path, request_id, run_id=run_id,
        expected_source_manifest_sha256=expected_source_manifest_sha256)
    outputs = []
    seen_msg = set()
    for eid, raw in events:
        try:
            msgid = poster.submit(channel_id, raw)
        except Exception:
            raise OIEPostBlocked("OIE_POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") from None
        if not isinstance(msgid, str) or not MESSAGE_ID.fullmatch(msgid) or msgid in seen_msg:
            raise OIEPostBlocked("OIE_POST_RECEIPT_INVALID_HOLD_NO_RETRY")
        seen_msg.add(msgid)
        outputs.append({"encounter_id": eid, "message_id": msgid})
    if len(outputs) != len(events):
        raise OIEPostBlocked("INCOMPLETE_POST_ACK_COVERAGE")
    return {
        "schema_version": RECEIPT_VERSION,
        "run_id": run_id,
        "request_id": request_id,
        "hospital_id": handoff["hospital_id"],
        "feed_id": handoff["feed_id"],
        "source_manifest_sha256": handoff["source_manifest_sha256"],
        "channel_id": channel_id,
        "messages": outputs,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="One-shot scoped OIE FHIR POST; no retries")
    p.add_argument("--state-root", required=True, type=Path)
    p.add_argument("--profile", required=True, type=Path)
    p.add_argument("--request-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.add_argument("--expected-source-manifest-sha256", required=True)
    args = p.parse_args(argv)
    try:
        scope = os.environ
        if not all(scope.get(k) for k in (
                "OIE_SCOPED_USERNAME", "OIE_SCOPED_PASSWORD",
                "OIE_TRUSTED_CA_FILE")):
            raise OIEPostBlocked("OIE_SCOPED_TLS_IDENTITY_REQUIRED")
        poster = ScopedOIEPoster(
            username=scope["OIE_SCOPED_USERNAME"],
            password=scope["OIE_SCOPED_PASSWORD"],
            ca_file=Path(scope["OIE_TRUSTED_CA_FILE"]))
        receipt = submit_new_fhir_request(
            args.state_root, args.profile, args.request_id,
            run_id=args.run_id, channel_id=args.channel_id,
            expected_source_manifest_sha256=args.expected_source_manifest_sha256,
            poster=poster)
    except Exception:
        print("OIE_POST_RESULT=HOLD_NO_RETRY", file=sys.stderr)
        return 1
    # Synthetic Encounter UUIDs and OIE numeric Message IDs only; no FHIR
    # resources, patient names or access credentials in the receipt output.
    print("OIE_NEW_REQUEST_RECEIPTS_JSON=" +
          json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    print("OIE_POST_RESULT=ALL_MESSAGES_ACKNOWLEDGED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
