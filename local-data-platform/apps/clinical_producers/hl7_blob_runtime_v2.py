"""Bounded V2 ADT A01/A03 ACK receipts -> OIE GET -> shared Azure Blob.

Real entrypoint is for a separately approved *new* Synthea Request only.
The controller, not this process, MUST capture POST ACKs in the same run
and prove they were not reconstructed from historical Derby messages.
All bytes/source checks and independent OIE GET finish BEFORE Azure SDK init.
No OIE POST, Channel deploy, Kubectl, source generation or old A01 override.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable, Mapping

from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, BlobBackend, publish_immutable,
)
from apps.clinical_producers.azure_blob_runtime import CONFIG_KEYS, HEX64
from apps.clinical_producers.blob_publish_contract import verified_plan
from apps.clinical_producers.hl7_blob_runtime import (
    MAX_RECEIPT_BYTES, _unique_pairs,
)
from apps.clinical_producers.oie.build_adt_events_v2_channel import CHANNEL_ID
from apps.clinical_producers.oie_hl7_publisher_v2 import prepare_oie_hl7_v2
from apps.clinical_producers.oie_message_submit_v2 import (
    AUTHORITY, verify_v2_receipts_against_frozen_source,
)
from apps.clinical_producers.oie_persisted_readback import OIEScopedHTTPSClient


class HL7V2RuntimeBlocked(RuntimeError):
    """Frozen source, same-run event receipt, or scoped runtime identity HOLD."""


def load_v2_receipts(path: Path) -> dict:
    """Reject duplicate JSON keys, missing files or oversized receipt input."""
    path = Path(path)
    if (path.is_symlink() or path.parent.is_symlink()
            or not path.is_file() or not 0 < path.stat().st_size <= MAX_RECEIPT_BYTES):
        raise HL7V2RuntimeBlocked("OIE_V2_RECEIPT_FILE_UNSAFE")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"),
                             object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, ValueError, TypeError):
        raise HL7V2RuntimeBlocked("OIE_V2_RECEIPT_JSON_REJECTED") from None
    if not isinstance(receipt, dict):
        raise HL7V2RuntimeBlocked("OIE_V2_RECEIPT_JSON_SHAPE")
    return receipt


def publish_hl7_v2_from_new_receipts(
    state_root: Path, profile_path: Path, request_id: str, *,
    receipt_path: Path, run_id: str, channel_id: str,
    assigning_authority: str, expected_source_manifest_sha256: str,
    landing_prefix: str, oie_client=None,
    env: Mapping[str, str] | None = None,
    backend_factory: Callable[..., BlobBackend] | None = None,
) -> dict:
    """Verify source+complete dual-event ACKs, remote bytes, then immutable PUT.

    One successful Blob manifest means *delivery only*, not Silver approval.
    Ambiguous OIE POST completion must be investigated independently without
    rerunning the original sender; this function has no POST capability.
    """
    if (channel_id != CHANNEL_ID or assigning_authority != AUTHORITY
            or not isinstance(expected_source_manifest_sha256, str)
            or not HEX64.fullmatch(expected_source_manifest_sha256)):
        raise HL7V2RuntimeBlocked("OIE_V2_EXACT_CHANNEL_SOURCE_PIN_REQUIRED")
    receipt_doc = load_v2_receipts(Path(receipt_path))
    try:
        receipts = verify_v2_receipts_against_frozen_source(
            Path(state_root), Path(profile_path), request_id,
            run_id=run_id,
            expected_source_manifest_sha256=expected_source_manifest_sha256,
            document=receipt_doc)
    except Exception:
        raise HL7V2RuntimeBlocked("OIE_V2_NEW_REQUEST_RECEIPT_HOLD") from None

    scope = os.environ if env is None else env
    if oie_client is None:
        if not all(scope.get(k) for k in (
                "OIE_SCOPED_USERNAME", "OIE_SCOPED_PASSWORD",
                "OIE_TRUSTED_CA_FILE")):
            raise HL7V2RuntimeBlocked("OIE_V2_SCOPED_TLS_IDENTITY_REQUIRED")
        try:
            oie_client = OIEScopedHTTPSClient(
                username=scope["OIE_SCOPED_USERNAME"],
                password=scope["OIE_SCOPED_PASSWORD"],
                ca_file=Path(scope["OIE_TRUSTED_CA_FILE"]))
        except Exception:
            raise HL7V2RuntimeBlocked("OIE_V2_SCOPED_LOGIN_HOLD") from None

    try:
        plan, payloads = prepare_oie_hl7_v2(
            Path(state_root), Path(profile_path), request_id,
            channel_id=channel_id, assigning_authority=assigning_authority,
            receipts=receipts, client=oie_client)
        if plan["source_manifest_sha256"] != expected_source_manifest_sha256:
            raise HL7V2RuntimeBlocked("OIE_V2_SOURCE_CHANGED_AFTER_GET")
        verified_plan(plan, payloads, landing_prefix=landing_prefix)
    except Exception:
        raise HL7V2RuntimeBlocked("OIE_V2_SOURCE_OR_PERSISTED_GET_HOLD") from None

    # Keep the Azure auth/operation policy identical to existing HL7 runtime.
    if (scope.get("AZURE_AUTH_MODE", "client-secret") != "client-secret"
            or any(scope.get(k) for k in (
                "AZURE_STORAGE_BEARER_TOKEN", "AZURE_STORAGE_TOKEN_EXPIRES_ON"))
            or not all(isinstance(scope.get(k), str) and scope.get(k)
                       for k in CONFIG_KEYS)):
        raise HL7V2RuntimeBlocked("OIE_V2_SCOPED_AZURE_IDENTITY_REQUIRED")
    factory = backend_factory or AzureSDKBlobBackend.from_service_principal
    backend = factory(
        account_url=scope["AZURE_BLOB_ACCOUNT_URL"],
        container=scope["AZURE_BLOB_CONTAINER"],
        tenant_id=scope["AZURE_TENANT_ID"],
        client_id=scope["AZURE_CLIENT_ID"],
        client_secret=scope["AZURE_CLIENT_SECRET"],
    )
    return publish_immutable(
        plan, payloads, landing_prefix=landing_prefix, backend=backend)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Newly ACKed V2 OIE ADT raw HL7 → immutable Blob")
    p.add_argument("--state-root", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--receipts", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.add_argument("--assigning-authority", required=True)
    p.add_argument("--expected-source-manifest-sha256", required=True)
    p.add_argument("--landing-prefix", required=True)
    args = p.parse_args(argv)
    try:
        result = publish_hl7_v2_from_new_receipts(
            args.state_root, args.profile, args.request_id,
            receipt_path=args.receipts, run_id=args.run_id,
            channel_id=args.channel_id,
            assigning_authority=args.assigning_authority,
            expected_source_manifest_sha256=args.expected_source_manifest_sha256,
            landing_prefix=args.landing_prefix)
    except Exception:
        # Never echo source patients, XML, OIE URLs, Azure secrets, or HTTP info.
        print("OIE_V2_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED", file=sys.stderr)
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
