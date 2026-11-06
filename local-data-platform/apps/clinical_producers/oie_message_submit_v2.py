"""Versioned one-shot OIE ADT V2 submission from a NEW frozen FHIR Request.

This module never creates a Channel, Kubernetes object, Azure Blob, or source
batch. It only prepares exact per-event messages and (when an authorized
controller supplies a scoped poster) collects new OIE POST ACK Message IDs.
A missing/ambiguous ACK is a HARD HOLD: no retry, no partial success receipt.
All OIE HTTP/TLS is reused from the existing A01 ScopedOIEPoster.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Protocol

from apps.clinical_producers.oie.build_adt_events_v2_channel import (
    CHANNEL_ID, CHANNEL_NAME, render_channel_v2,
)
from apps.clinical_producers.oie_event_readback_v2 import OIEV2EventReceipt
from apps.clinical_producers.oie_hl7_publisher_v2 import (
    OIEV2HandoffBlocked, _expected_for_envelope, _source_inventory,
)
from apps.clinical_producers.oie_message_submit import (
    MAX_EVENTS, MAX_POST_BYTES, OIEPostBlocked, ScopedOIEPoster,
)
from apps.clinical_producers.oie_persisted_readback import MESSAGE_ID
from apps.clinical_producers.hl7_blob_runtime import RUN_ID
from apps.clinical_producers.source_handoff import verify_handoff

VERSION = "healthcare-oie-adt-v2-new-event-receipts-v1"
AUTHORITY = "JOHNSCREEKB"


class V2Poster(Protocol):
    def preflight_channel(self, channel_id: str) -> None:
        """Bounded GET: verify exact V2 mapping and STARTED state."""

    def submit(self, channel_id: str, event: bytes) -> str:
        """One POST returning a genuine numeric OIE Message ID, no retries."""


class ScopedOIEV2Poster(ScopedOIEPoster):
    """Use the existing authenticated, TLS-pinned OIE client; V2 Channel ONLY."""

    def preflight_channel(self, channel_id: str) -> None:
        if channel_id != CHANNEL_ID:
            raise OIEPostBlocked("OIE_V2_UNAPPROVED_CHANNEL")
        super().preflight_channel(
            channel_id, expected_channel_xml=render_channel_v2(),
            expected_channel_name=CHANNEL_NAME,
        )

    def submit(self, channel_id: str, event: bytes) -> str:
        if channel_id != CHANNEL_ID:
            raise OIEPostBlocked("OIE_V2_UNAPPROVED_CHANNEL")
        return super().submit(channel_id, event)


def _bound_request(run_id: str, request_id: str) -> None:
    if (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)
            or request_id != "johnscreek-hl7-gh-" + run_id):
        raise OIEPostBlocked("OIE_V2_NEW_RUN_ID_REQUIRED")


def prepare_v2_new_events(
    state_root: Path, profile_path: Path, request_id: str, *,
    run_id: str, expected_source_manifest_sha256: str,
) -> tuple[dict, list[tuple[str, str, bytes]]]:
    """Read-only source verification and deterministic bounded event envelopes.

    The source is allowed to nominate A01/A03 candidates, but the independent
    OIE V2 mapper is still responsible for clinical event eligibility and HL7
    bytes, as checked later by persisted readback/source correlation.
    """
    _bound_request(run_id, request_id)
    if (not isinstance(expected_source_manifest_sha256, str) or
            not re.fullmatch(r"[0-9a-f]{64}", expected_source_manifest_sha256)):
        raise OIEPostBlocked("OIE_V2_MANIFEST_SHA_PIN_REQUIRED")
    try:
        handoff, event_map = _source_inventory(
            Path(state_root), Path(profile_path), request_id)
        if (handoff["source_manifest_sha256"] != expected_source_manifest_sha256
                or handoff["hospital_id"] != "johns-creek-hospital-b"
                or handoff["feed_id"] != "johns-creek-hospital-b-hl7-v2"):
            raise OIEPostBlocked("OIE_V2_SOURCE_IDENTITY_OR_SHA_MISMATCH")
        events = []
        skipped = 0
        for encounter_id in sorted(event_map):
            envelope = event_map[encounter_id]
            event_types = _expected_for_envelope(envelope, AUTHORITY)
            if not event_types:
                skipped += 1
            for event_type in ("A01", "A03"):
                if event_type not in event_types:
                    continue
                control = "-".join((
                    handoff["hospital_id"], handoff["feed_id"], request_id,
                    encounter_id, event_type,
                ))
                if len(control) > 199:
                    raise OIEPostBlocked("OIE_V2_CONTROL_ID_LENGTH_HOLD")
                payload = dict(envelope, requested_event_type=event_type)
                raw = json.dumps(
                    payload, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
                if not 0 < len(raw) <= MAX_POST_BYTES:
                    raise OIEPostBlocked("OIE_V2_EVENT_SIZE_HOLD")
                events.append((encounter_id, event_type, raw))
        if not 0 < len(events) <= MAX_EVENTS:
            raise OIEPostBlocked("OIE_V2_EVENT_COUNT_HOLD")
        # Close the original frozen source again BEFORE contacting any OIE host.
        if verify_handoff(
            Path(state_root), Path(profile_path), request_id) != handoff:
            raise OIEPostBlocked("OIE_V2_SOURCE_CHANGED_BEFORE_POST")
        return {
            "schema_version": VERSION, "run_id": run_id,
            "request_id": request_id,
            "hospital_id": handoff["hospital_id"], "feed_id": handoff["feed_id"],
            "source_manifest_sha256": expected_source_manifest_sha256,
            "channel_id": CHANNEL_ID, "skipped_non_admissions": skipped,
            "event_count": len(events),
        }, events
    except OIEPostBlocked:
        raise
    except (OIEV2HandoffBlocked, OSError, ValueError, TypeError):
        raise OIEPostBlocked("OIE_V2_FROZEN_SOURCE_OR_MAPPING_HOLD") from None


def submit_v2_new_request(
    state_root: Path, profile_path: Path, request_id: str, *,
    run_id: str, channel_id: str, expected_source_manifest_sha256: str,
    poster: V2Poster,
) -> dict:
    """One-shot, never replay; ALL actual OIE ACKs required for receipt output.

    Do not use returned records as cryptographic provenance: the approved,
    single-attempt controller must preserve run/batch identity and original
    POST responses. No actual readback or Blob publication is claimed here.
    """
    if channel_id != CHANNEL_ID:
        raise OIEPostBlocked("OIE_V2_UNAPPROVED_CHANNEL")
    identity, events = prepare_v2_new_events(
        state_root, profile_path, request_id, run_id=run_id,
        expected_source_manifest_sha256=expected_source_manifest_sha256)
    try:
        poster.preflight_channel(channel_id)
    except Exception:
        raise OIEPostBlocked("OIE_V2_CHANNEL_PREFLIGHT_HOLD_NO_POST") from None

    receipts = []
    seen = set()
    for encounter_id, event_type, wire in events:
        try:
            message_id = poster.submit(channel_id, wire)
        except Exception:
            # A network timeout may occur AFTER Derby durable persistence.
            # Abort; never re-post or guess Message IDs from history.
            raise OIEPostBlocked("OIE_V2_POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") from None
        if (not isinstance(message_id, str)
                or not MESSAGE_ID.fullmatch(message_id)
                or message_id in seen):
            raise OIEPostBlocked("OIE_V2_INVALID_ACK_HOLD_NO_RETRY")
        seen.add(message_id)
        receipts.append({
            "source_encounter_id": encounter_id, "event_type": event_type,
            "message_id": message_id,
        })
    return dict(identity, messages=receipts)


def verify_v2_receipts_against_frozen_source(
    state_root: Path, profile_path: Path, request_id: str, *,
    run_id: str, expected_source_manifest_sha256: str, document: dict,
) -> list[OIEV2EventReceipt]:
    """Recompute expected event coverage from immutable source before ANY GET.

    The document must come directly from the approved single-attempt controller,
    never a guessed/reconstructed list of historical OIE Message IDs.
    """
    identity, events = prepare_v2_new_events(
        state_root, profile_path, request_id, run_id=run_id,
        expected_source_manifest_sha256=expected_source_manifest_sha256)
    if (not isinstance(document, dict)
            or document.get("skipped_non_admissions") !=
               identity["skipped_non_admissions"]
            or document.get("event_count") != identity["event_count"]):
        raise OIEPostBlocked("OIE_V2_RECEIPT_SOURCE_EVENT_COVERAGE_HOLD")
    try:
        handoff = verify_handoff(
            Path(state_root), Path(profile_path), request_id)
    except Exception:
        raise OIEPostBlocked("OIE_V2_RECEIPT_SOURCE_CHANGED_HOLD") from None
    return verified_v2_post_receipts(
        document, run_id=run_id, request_id=request_id,
        handoff=handoff,
        expected_events=[(eid, event_type) for eid, event_type, _ in events],
    )


def verified_v2_post_receipts(
    document: dict, *, run_id: str, request_id: str,
    handoff: dict, expected_events: list[tuple[str, str]],
) -> list[OIEV2EventReceipt]:
    """Strict same-run receipt-envelope validation BEFORE scoped OIE GET.

    Caller supplies a trusted, captured controller receipt (not a recovered
    historical list). Match source, immutable manifest, channel and coverage.
    """
    _bound_request(run_id, request_id)
    required = {
        "schema_version", "run_id", "request_id", "hospital_id",
        "feed_id", "source_manifest_sha256", "channel_id",
        "skipped_non_admissions", "event_count", "messages",
    }
    if (not isinstance(document, dict) or set(document) != required
            or document["schema_version"] != VERSION
            or document["run_id"] != run_id
            or document["request_id"] != request_id
            or document["channel_id"] != CHANNEL_ID
            or any(document[k] != handoff.get(k) for k in (
                "hospital_id", "feed_id", "source_manifest_sha256"))):
        raise OIEPostBlocked("OIE_V2_RECEIPT_SOURCE_HOLD")
    messages = document["messages"]
    if (not isinstance(messages, list)
            or type(document["event_count"]) is not int
            or document["event_count"] != len(messages)
            or not 0 < len(messages) <= MAX_EVENTS
            or type(document["skipped_non_admissions"]) is not int
            or document["skipped_non_admissions"] < 0):
        raise OIEPostBlocked("OIE_V2_RECEIPT_COUNT_HOLD")
    if (not isinstance(expected_events, list) or
            any(not isinstance(x, tuple) or len(x) != 2
                or not isinstance(x[0], str) or x[1] not in {"A01", "A03"}
                for x in expected_events)):
        raise OIEPostBlocked("OIE_V2_EXPECTED_EVENT_COVERAGE_HOLD")
    expected = set(expected_events)
    admissions = {eid for eid, event_type in expected if event_type == "A01"}
    if (len(expected) != len(expected_events) or len(expected) != len(messages)
            or any(event_type == "A03" and (eid, "A01") not in expected
                   for eid, event_type in expected)
            or type(handoff.get("metrics", {}).get("fhir_encounters")) is not int
            or document["skipped_non_admissions"] !=
               handoff["metrics"]["fhir_encounters"] - len(admissions)):
        raise OIEPostBlocked("OIE_V2_EXPECTED_EVENT_COVERAGE_HOLD")
    found, ids, receipts = set(), set(), []
    for row in messages:
        if (not isinstance(row, dict)
                or set(row) != {"source_encounter_id", "event_type", "message_id"}):
            raise OIEPostBlocked("OIE_V2_RECEIPT_SHAPE_HOLD")
        if (not isinstance(row["source_encounter_id"], str)
                or not isinstance(row["event_type"], str)):
            raise OIEPostBlocked("OIE_V2_RECEIPT_SHAPE_HOLD")
        key = (row["source_encounter_id"], row["event_type"])
        msg = row["message_id"]
        if (key not in expected or key in found
                or not isinstance(msg, str) or not MESSAGE_ID.fullmatch(msg)
                or msg in ids):
            raise OIEPostBlocked("OIE_V2_RECEIPT_ID_OR_COVERAGE_HOLD")
        found.add(key)
        ids.add(msg)
        receipts.append(OIEV2EventReceipt(key[0], key[1], msg))
    if found != expected:
        raise OIEPostBlocked("OIE_V2_RECEIPT_COVERAGE_HOLD")
    return receipts


def main(argv: list[str] | None = None) -> int:
    """Explicit one-shot CLI for a separately approved V2 OIE Sender Job.

    No automatic retry or resuming a partially submitted Request. Message IDs
    are only ACK receipts, not accepted Blob or verified OIE durable data.
    """
    import argparse
    import os
    import sys

    p = argparse.ArgumentParser(description="One-shot OIE ADT V2 A01/A03 source events")
    p.add_argument("--state-root", required=True, type=Path)
    p.add_argument("--profile", required=True, type=Path)
    p.add_argument("--request-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.add_argument("--expected-source-manifest-sha256", required=True)
    args = p.parse_args(argv)
    try:
        if args.channel_id != CHANNEL_ID:
            raise OIEPostBlocked("OIE_V2_UNAPPROVED_CHANNEL")
        scope = os.environ
        if not all(scope.get(name) for name in (
                "OIE_SCOPED_USERNAME", "OIE_SCOPED_PASSWORD",
                "OIE_TRUSTED_CA_FILE")):
            raise OIEPostBlocked("OIE_V2_SCOPED_TLS_IDENTITY_REQUIRED")
        poster = ScopedOIEV2Poster(
            username=scope["OIE_SCOPED_USERNAME"],
            password=scope["OIE_SCOPED_PASSWORD"],
            ca_file=Path(scope["OIE_TRUSTED_CA_FILE"]))
        receipt = submit_v2_new_request(
            args.state_root, args.profile, args.request_id,
            run_id=args.run_id, channel_id=args.channel_id,
            expected_source_manifest_sha256=args.expected_source_manifest_sha256,
            poster=poster)
    except Exception:
        # Source names, raw HL7/FHIR and OIE/HTTP credentials never reach logs.
        print("OIE_V2_POST_RESULT=HOLD_NO_RETRY", file=sys.stderr)
        return 1
    print("OIE_V2_NEW_REQUEST_RECEIPTS_JSON=" +
          json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    print("OIE_V2_POST_RESULT=ALL_EVENTS_ACKNOWLEDGED")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
