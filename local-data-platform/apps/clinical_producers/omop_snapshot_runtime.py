"""Scoped OMOP snapshot Azure Blob runtime for an ephemeral dw-synthea Job."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Callable, Mapping

from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, BlobBackend, PublishBlocked,
)
from apps.clinical_producers.omop_snapshot_publisher import (
    BLOB_PREFIX, MAX_DUMP_BYTES, publish_omop_dump, verify_source,
)

AZURE_REQUIRED = ("AZURE_BLOB_ACCOUNT_URL", "AZURE_BLOB_CONTAINER")
SERVICE_PRINCIPAL_REQUIRED = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID",
                              "AZURE_CLIENT_SECRET")
TOKEN_REQUIRED = ("AZURE_STORAGE_BEARER_TOKEN", "AZURE_STORAGE_TOKEN_EXPIRES_ON")


def read_staged_dump(path: Path) -> bytes:
    """Read only a regular, bounded file without following final symlinks."""
    path = Path(path)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 5 or info.st_size > MAX_DUMP_BYTES:
            raise PublishBlocked("INVALID_STAGED_OMOP_DUMP")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            with os.fdopen(fd, "rb") as stream:
                raw = stream.read(MAX_DUMP_BYTES + 1)
        except BaseException:
            # fdopen takes ownership on success; no secrets in raised error.
            raise
        if len(raw) != info.st_size:
            raise PublishBlocked("STAGED_DUMP_SIZE_CHANGED")
        return raw
    except (OSError, ValueError):
        raise PublishBlocked("STAGED_DUMP_UNREADABLE") from None


def backend_from_env(env: Mapping[str, str], *,
                     backend_factory: Callable[..., BlobBackend] | None = None) -> BlobBackend:
    """Exactly one existing, scoped Azure auth mode. No fallback credentials."""
    if any(not isinstance(env.get(k), str) or not env.get(k) for k in AZURE_REQUIRED):
        raise PublishBlocked("MISSING_OMOP_BLOB_TARGET")
    mode = env.get("AZURE_AUTH_MODE", "client-secret")
    if mode == "client-secret":
        if any(env.get(k) for k in TOKEN_REQUIRED):
            raise PublishBlocked("CONFLICTING_AZURE_AUTH_MODES")
        if any(not isinstance(env.get(k), str) or not env.get(k)
               for k in SERVICE_PRINCIPAL_REQUIRED):
            raise PublishBlocked("MISSING_SCOPED_AZURE_IDENTITY")
        factory = backend_factory or AzureSDKBlobBackend.from_service_principal
        return factory(
            account_url=env["AZURE_BLOB_ACCOUNT_URL"],
            container=env["AZURE_BLOB_CONTAINER"],
            tenant_id=env["AZURE_TENANT_ID"],
            client_id=env["AZURE_CLIENT_ID"],
            client_secret=env["AZURE_CLIENT_SECRET"],
        )
    if mode == "temporary-access-token":
        if any(env.get(k) for k in SERVICE_PRINCIPAL_REQUIRED):
            raise PublishBlocked("CONFLICTING_AZURE_AUTH_MODES")
        if any(not isinstance(env.get(k), str) or not env.get(k)
               for k in TOKEN_REQUIRED):
            raise PublishBlocked("MISSING_TEMPORARY_STORAGE_TOKEN")
        expiration = env["AZURE_STORAGE_TOKEN_EXPIRES_ON"]
        if not re.fullmatch(r"[1-9][0-9]{9}", expiration):
            raise PublishBlocked("INVALID_TEMPORARY_TOKEN_EXPIRY")
        factory = backend_factory or AzureSDKBlobBackend.from_temporary_access_token
        return factory(
            account_url=env["AZURE_BLOB_ACCOUNT_URL"],
            container=env["AZURE_BLOB_CONTAINER"],
            access_token=env["AZURE_STORAGE_BEARER_TOKEN"],
            expires_on=int(expiration),
        )
    raise PublishBlocked("UNSUPPORTED_AZURE_AUTH_MODE")


def publish_from_stage(dump_path: Path, snapshot_id: str, *,
                       prefix: str = BLOB_PREFIX,
                       env: Mapping[str, str] | None = None,
                       backend_factory: Callable[..., BlobBackend] | None = None) -> dict:
    # Validate source and exact OMOP prefix BEFORE initializing Azure SDK.
    raw = read_staged_dump(dump_path)
    verify_source(snapshot_id, raw, prefix)
    backend = backend_from_env(os.environ if env is None else env,
                               backend_factory=backend_factory)
    return publish_omop_dump(snapshot_id, raw, backend=backend, prefix=prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Immutable LocalDP OMOP Blob snapshot")
    parser.add_argument("--dump-path", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--blob-prefix", default=BLOB_PREFIX)
    args = parser.parse_args(argv)
    try:
        receipt = publish_from_stage(args.dump_path, args.snapshot_id,
                                     prefix=args.blob_prefix)
    except Exception:
        # No credential, connection string, PG dump bytes or SDK details in logs.
        print("OMOP_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
