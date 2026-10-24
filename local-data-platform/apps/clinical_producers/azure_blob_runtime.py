"""One-shot, fail-closed FHIR DIRECT publisher runtime for staged inputs.

Runs ONLY in an authorized, isolated dw-az-blob Job. This module does not
stage source data, mint Azure credentials, create namespaces/secrets, submit
OIE messages or deploy itself. OIE HL7 runtime remains disabled until an
independently authenticated persisted-message fetcher is implemented.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Callable, Mapping

from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, BlobBackend, publish_immutable,
)
from apps.clinical_producers.blob_publish_contract import verified_plan
from apps.clinical_producers.direct_fhir_publisher import prepare_direct_fhir


READY_BYTES = b"BLOB_HANDOFF_READY_V1\n"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
CONFIG_KEYS = (
    "AZURE_BLOB_ACCOUNT_URL", "AZURE_BLOB_CONTAINER",
    "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
)


class PublisherRuntimeBlocked(RuntimeError):
    """No real Azure I/O may occur after runtime safety gates fail."""


def ensure_ready(marker: Path) -> None:
    """An external trusted producer must atomically mark a completed stage."""
    marker = Path(marker)
    if (marker.is_symlink() or marker.parent.is_symlink()
            or not marker.is_file() or marker.read_bytes() != READY_BYTES):
        raise PublisherRuntimeBlocked("HANDOFF_NOT_READY")


def await_ready(marker: Path, timeout_seconds: int) -> None:
    """Wait for authenticated input staging without requiring a second PVC."""
    if type(timeout_seconds) is not int or not 0 <= timeout_seconds <= 1800:
        raise PublisherRuntimeBlocked("INVALID_HANDOFF_TIMEOUT")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            ensure_ready(marker)
            return
        except (PublisherRuntimeBlocked, OSError):
            if time.monotonic() >= deadline:
                raise PublisherRuntimeBlocked("HANDOFF_NOT_READY") from None
            time.sleep(min(2.0, max(0.0, deadline - time.monotonic())))


def publish_direct_from_stage(
    state_root: Path, profile_path: Path, request_id: str, *,
    ready_marker: Path, expected_source_manifest_sha256: str,
    landing_prefix: str, env: Mapping[str, str] | None = None,
    backend_factory: Callable[..., BlobBackend] | None = None,
) -> dict:
    """Verify fully staged bytes and trusted out-of-band SHA before any Azure I/O.

    The expected manifest SHA MUST come from the source-side audited preflight,
    never be derived from the staged payload by this process.
    """
    ensure_ready(ready_marker)
    if (not isinstance(expected_source_manifest_sha256, str)
            or not HEX64.fullmatch(expected_source_manifest_sha256)):
        raise PublisherRuntimeBlocked("INVALID_PINNED_SOURCE_MANIFEST_SHA")
    plan, sources = prepare_direct_fhir(
        Path(state_root), Path(profile_path), request_id)
    if plan["source_manifest_sha256"] != expected_source_manifest_sha256:
        raise PublisherRuntimeBlocked("PINNED_SOURCE_MANIFEST_MISMATCH")
    # Reject bad prefix, mutated payload or invalid Blob keys BEFORE SDK init.
    verified_plan(plan, sources, landing_prefix=landing_prefix)

    scope = os.environ if env is None else env
    if any(not isinstance(scope.get(k), str) or not scope.get(k)
           for k in CONFIG_KEYS):
        raise PublisherRuntimeBlocked("MISSING_SCOPED_AZURE_IDENTITY")
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
    parser = argparse.ArgumentParser(
        description="Publish a verified DIRECT FHIR handoff from ephemeral stage")
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--ready-marker", type=Path, required=True)
    parser.add_argument("--expected-source-manifest-sha256", required=True)
    parser.add_argument("--landing-prefix", required=True)
    parser.add_argument("--ready-timeout-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    try:
        await_ready(args.ready_marker, args.ready_timeout_seconds)
        receipt = publish_direct_from_stage(
            args.state_root, args.profile, args.request_id,
            ready_marker=args.ready_marker,
            expected_source_manifest_sha256=args.expected_source_manifest_sha256,
            landing_prefix=args.landing_prefix)
    except Exception:
        # Azure SDK error details can embed account URLs, SAS or HTTP headers.
        # No source FHIR bytes, access tokens or client secrets in CI/Pod logs.
        print("AZURE_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": receipt["status"],
        "manifest_key": receipt["manifest_key"],
        "manifest_sha256": receipt["manifest_sha256"],
        "manifest_create_status": receipt["manifest_create_status"],
        "objects_verified": len(receipt["objects"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
