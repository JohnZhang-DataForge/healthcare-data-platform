"""Guarded Johns Creek HL7 readback-to-Blob handoff (no OIE replay).

A trusted same-request controller must first submit a NEW frozen FHIR request
to the canonical OIE Channel and capture genuine POST message IDs. This
module never submits FHIR, deploys Channels or discovers historical messages.
Receipts alone do not prove provenance: the controller must bind and audit
their creation in its own reviewed, single-attempt execution. Until that
controller, scoped OIE user and TLS trust are verified, live use is HOLD.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable, Mapping
from uuid import UUID

from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, BlobBackend, publish_immutable,
)
from apps.clinical_producers.azure_blob_runtime import CONFIG_KEYS, HEX64
from apps.clinical_producers.blob_publish_contract import verified_plan
from apps.clinical_producers.hospital_profiles import load_profile
from apps.clinical_producers.oie_hl7_publisher import prepare_oie_hl7
from apps.clinical_producers.oie_persisted_readback import (
    MESSAGE_ID, OIEPersistedMessage, OIEScopedHTTPSClient,
    fetch_persisted_readbacks,
)
from apps.clinical_producers.source_handoff import verify_handoff

RECEIPT_VERSION = "healthcare-oie-new-request-receipts-v1"
RUN_ID = re.compile(r"^[1-9][0-9]{8,17}$")
MAX_RECEIPT_BYTES = 4_000_000
MAX_EVENTS = 20_000


class HL7RuntimeBlocked(RuntimeError):
    """A source, controller receipt, OIE readback or scoped auth gate failed."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HL7RuntimeBlocked("DUPLICATE_RECEIPT_KEY")
        result[key] = value
    return result


def load_new_request_receipts(path: Path, *, run_id: str, request_id: str,
                              channel_id: str, handoff: dict) -> list[OIEPersistedMessage]:
    """Validate a controller-owned *new* request handoff before any remote I/O.

    This is an integrity contract, NOT cryptographic provenance proof. The
    upstream controller must enforce new-request ownership and never recover
    an unknown POST by guessing/reusing historical Derby message IDs.
    """
    path = Path(path)
    if (not RUN_ID.fullmatch(run_id)
            or request_id != "johnscreek-hl7-gh-" + run_id):
        raise HL7RuntimeBlocked("UNBOUND_NEW_REQUEST_RUN_ID")
    try:
        UUID(channel_id)
    except (ValueError, TypeError, AttributeError):
        raise HL7RuntimeBlocked("INVALID_CHANNEL_ID") from None
    if (path.is_symlink() or path.parent.is_symlink() or
            not path.is_file() or not 0 < path.stat().st_size <= MAX_RECEIPT_BYTES):
        raise HL7RuntimeBlocked("UNSAFE_OR_MISSING_RECEIPTS")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"),
                         object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise HL7RuntimeBlocked("INVALID_RECEIPT_JSON") from None
    required = {
        "schema_version", "run_id", "request_id", "hospital_id", "feed_id",
        "source_manifest_sha256", "channel_id", "messages",
    }
    if (not isinstance(doc, dict) or set(doc) != required
            or doc["schema_version"] != RECEIPT_VERSION
            or doc["run_id"] != run_id or doc["request_id"] != request_id
            or doc["channel_id"] != channel_id
            or any(doc[k] != handoff[k] for k in (
                "hospital_id", "feed_id", "source_manifest_sha256"))):
        raise HL7RuntimeBlocked("OIE_RECEIPT_SOURCE_IDENTITY_MISMATCH")
    messages = doc["messages"]
    if not isinstance(messages, list) or not 0 < len(messages) <= MAX_EVENTS:
        raise HL7RuntimeBlocked("INVALID_OIE_RECEIPT_COUNT")
    expected = handoff.get("metrics", {}).get("fhir_encounters")
    if type(expected) is not int or expected != len(messages):
        raise HL7RuntimeBlocked("OIE_RECEIPTS_DO_NOT_COVER_FROZEN_ENCOUNTERS")
    result = []
    ids, encounters = set(), set()
    for item in messages:
        if (not isinstance(item, dict)
                or set(item) != {"encounter_id", "message_id"}
                or not isinstance(item["message_id"], str)
                or not MESSAGE_ID.fullmatch(item["message_id"])
                or not isinstance(item["encounter_id"], str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,150}",
                                    item["encounter_id"])
                or item["message_id"] in ids
                or item["encounter_id"] in encounters):
            raise HL7RuntimeBlocked("INVALID_OR_DUPLICATE_OIE_RECEIPT")
        ids.add(item["message_id"])
        encounters.add(item["encounter_id"])
        result.append(OIEPersistedMessage(item["encounter_id"], item["message_id"]))
    return result


def publish_hl7_from_new_receipts(
    state_root: Path, profile_path: Path, request_id: str, *,
    receipt_path: Path, run_id: str, channel_id: str,
    assigning_authority: str, expected_source_manifest_sha256: str,
    landing_prefix: str, oie_client=None,
    env: Mapping[str, str] | None = None,
    backend_factory: Callable[..., BlobBackend] | None = None,
) -> dict:
    """Read one freshly submitted OIE request, verify HL7, then publish Azure.

    All source and message validation precedes construction of Azure backend.
    Retry of uncertain OIE POST is explicitly outside this function's scope.
    """
    if (not isinstance(expected_source_manifest_sha256, str)
            or not HEX64.fullmatch(expected_source_manifest_sha256)):
        raise HL7RuntimeBlocked("INVALID_PINNED_SOURCE_MANIFEST_SHA")
    profile = load_profile(Path(profile_path))
    if (profile["hospital_id"] != "johns-creek-hospital-b"
            or profile["feed_id"] != "johns-creek-hospital-b-hl7-v2"
            or profile["delivery"] != {
                "source_format": "FHIR_R4",
                "target_format": "HL7_V2",
                "transformer": "OIE",
            } or assigning_authority != "JOHNSCREEKB"):
        raise HL7RuntimeBlocked("JOHNS_CREEK_HL7_IDENTITY_REQUIRED")
    handoff = verify_handoff(Path(state_root), Path(profile_path), request_id)
    if handoff["source_manifest_sha256"] != expected_source_manifest_sha256:
        raise HL7RuntimeBlocked("PINNED_SOURCE_MANIFEST_MISMATCH")
    receipts = load_new_request_receipts(
        receipt_path, run_id=run_id, request_id=request_id,
        channel_id=channel_id, handoff=handoff)
    # Require scoped OIE credentials even for already committed Azure requests.
    scope = os.environ if env is None else env
    if oie_client is None:
        if (not all(scope.get(k) for k in (
                "OIE_SCOPED_USERNAME", "OIE_SCOPED_PASSWORD", "OIE_TRUSTED_CA_FILE"))):
            raise HL7RuntimeBlocked("OIE_SCOPED_IDENTITY_REQUIRED")
        oie_client = OIEScopedHTTPSClient(
            username=scope["OIE_SCOPED_USERNAME"],
            password=scope["OIE_SCOPED_PASSWORD"],
            ca_file=Path(scope["OIE_TRUSTED_CA_FILE"]))
    readbacks = fetch_persisted_readbacks(
        oie_client, channel_id=channel_id, new_request_messages=receipts)
    plan, sources = prepare_oie_hl7(
        Path(state_root), Path(profile_path), request_id,
        channel_id=channel_id, assigning_authority=assigning_authority,
        readbacks=readbacks)
    if plan["source_manifest_sha256"] != expected_source_manifest_sha256:
        raise HL7RuntimeBlocked("SOURCE_CHANGED_AFTER_OIE_READBACK")
    verified_plan(plan, sources, landing_prefix=landing_prefix)

    if (scope.get("AZURE_AUTH_MODE", "client-secret") != "client-secret"
            or any(scope.get(k) for k in (
                "AZURE_STORAGE_BEARER_TOKEN", "AZURE_STORAGE_TOKEN_EXPIRES_ON"))
            or not all(isinstance(scope.get(k), str) and scope.get(k)
                       for k in CONFIG_KEYS)):
        raise HL7RuntimeBlocked("SCOPED_AZURE_IDENTITY_REQUIRED")
    factory = backend_factory or AzureSDKBlobBackend.from_service_principal
    backend = factory(
        account_url=scope["AZURE_BLOB_ACCOUNT_URL"],
        container=scope["AZURE_BLOB_CONTAINER"],
        tenant_id=scope["AZURE_TENANT_ID"],
        client_id=scope["AZURE_CLIENT_ID"],
        client_secret=scope["AZURE_CLIENT_SECRET"],
    )
    return publish_immutable(
        plan, sources, landing_prefix=landing_prefix, backend=backend)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish fresh OIE HL7 readbacks to Azure Blob")
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--receipts", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--assigning-authority", required=True)
    parser.add_argument("--expected-source-manifest-sha256", required=True)
    parser.add_argument("--landing-prefix", required=True)
    args = parser.parse_args(argv)
    try:
        result = publish_hl7_from_new_receipts(
            args.state_root, args.profile, args.request_id,
            receipt_path=args.receipts, run_id=args.run_id,
            channel_id=args.channel_id,
            assigning_authority=args.assigning_authority,
            expected_source_manifest_sha256=args.expected_source_manifest_sha256,
            landing_prefix=args.landing_prefix)
    except Exception:
        # Avoid exposing PHI, cookies, TLS errors, Account URLs or credentials.
        print("HL7_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": result["status"],
        "manifest_key": result["manifest_key"],
        "manifest_sha256": result["manifest_sha256"],
        "manifest_create_status": result["manifest_create_status"],
        "objects_verified": len(result["objects"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
