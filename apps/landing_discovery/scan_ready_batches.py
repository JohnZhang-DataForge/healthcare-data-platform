#!/usr/bin/env python3
"""READ-ONLY discovery of published, verified S3 Landing batches.

Producer independence: never call Synthea, Spark, Airflow or PostgreSQL.
A batch becomes discoverable only after its complete manifest.json is published.
No claim/processing decisions here; those require a separate atomic ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

# Keep the existing proven Landing v1 contract as a single validator.\n# IMPORTANT: Kubernetes ConfigMap volumes use symlinks; .resolve() follows\n# ..data timestamps and breaks sibling-module discovery under mounted volumes.
sys.path.insert(0, str(Path(__file__).absolute().parents[1] / "task004"))
from resolve_verified_landing_file import (  # noqa: E402
    ResolverError,
    manifest_lineage_from_key,
    validate_manifest,
)

DEFAULT_PREFIX = "source=synthea/source_version=v3.3.0/"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_MANIFESTS = 1000


class DiscoveryError(RuntimeError):
    """Fail closed on S3 errors, inconsistent identities and broken manifests."""


def _read_manifest(s3, bucket: str, key: str) -> tuple[bytes, dict]:
    response = s3.get_object(Bucket=bucket, Key=key)
    if int(response.get("ContentLength", MAX_MANIFEST_BYTES + 1)) > MAX_MANIFEST_BYTES:
        raise DiscoveryError("manifest exceeds allowed size")
    body = response["Body"].read(MAX_MANIFEST_BYTES + 1)
    if len(body) > MAX_MANIFEST_BYTES:
        raise DiscoveryError("manifest exceeds allowed size")
    try:
        obj = json.loads(body)
    except (UnicodeDecodeError, ValueError) as exc:
        raise DiscoveryError("invalid manifest JSON") from exc
    if not isinstance(obj, dict):
        raise DiscoveryError("manifest JSON root must be an object")
    return body, obj


def discover_ready_batches(
    s3,
    *,
    bucket: str = "health-landing",
    prefix: str = DEFAULT_PREFIX,
    max_manifests: int = MAX_MANIFESTS,
) -> dict:
    """List all pages, inspect only final manifests, validate source identity.

    The output is a discovery inventory, NOT a claim and NOT a COMMIT authorization.
    Reject conflicting identities rather than picking the newest arbitrarily.
    """
    if not bucket or not prefix or ".." in prefix or not prefix.endswith("/"):
        raise DiscoveryError("unsafe discovery bucket or prefix")
    if not 1 <= max_manifests <= MAX_MANIFESTS:
        raise DiscoveryError("invalid max_manifests")

    ready = []
    quarantined = []
    identities: dict[tuple[str, str], str] = {}
    examined = 0
    listed_objects = 0
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", ()):
                listed_objects += 1
                key = obj["Key"]
                if not key.endswith("/manifest.json"):
                    continue  # Partially uploaded CSV batches are NOT READY.
                examined += 1
                if examined > max_manifests:
                    raise DiscoveryError("manifest scan limit exceeded")
                try:
                    lineage = manifest_lineage_from_key(key)
                    if not key.startswith(prefix):
                        raise DiscoveryError("manifest is outside allowed prefix")
                    uri = f"s3://{bucket}/{key}"
                    body, manifest = _read_manifest(s3, bucket, key)
                    validate_manifest(manifest, lineage["batch_id"], uri)
                except (ResolverError, KeyError, TypeError, DiscoveryError) as exc:
                    # Legacy or malformed published manifests are NOT READY.
                    # Quarantine per batch so an old incompatible file cannot
                    # starve new, valid batches from being discovered.
                    quarantined.append({
                        "manifest_uri": f"s3://{bucket}/{key}",
                        "reason": "INVALID_MANIFEST_CONTRACT",
                    })
                    continue

                sha = hashlib.sha256(body).hexdigest()
                identity = (lineage["source"], lineage["batch_id"])
                previous = identities.get(identity)
                if previous is not None and previous != sha:
                    raise DiscoveryError("same source/batch_id has different manifests")
                if previous is not None:
                    raise DiscoveryError("same source/batch_id published multiple times")
                identities[identity] = sha

                ready.append({
                    "source": lineage["source"],
                    "source_version": lineage["source_version"],
                    "ingest_date": lineage["ingest_date"],
                    "batch_id": lineage["batch_id"],
                    "manifest_uri": uri,
                    "manifest_sha256": sha,
                    "status": "INTAKE_VERIFIED",
                    "file_count": len(manifest["files"]),
                })
    except DiscoveryError:
        raise
    except Exception as exc:
        raise DiscoveryError("S3 listing or manifest retrieval failed") from exc

    ready.sort(key=lambda row: (row["ingest_date"], row["batch_id"]))
    return {
        "discovery_status": (
            "READ_ONLY_PASS_WITH_QUARANTINE" if quarantined else "READ_ONLY_PASS"
        ),
        "bucket": bucket,
        "prefix": prefix,
        "objects_seen": listed_objects,
        "manifests_seen": examined,
        "ready_count": len(ready),
        "quarantined_count": len(quarantined),
        "quarantined_manifests": quarantined,
        "ready_batches": ready,
        "processing_authorized": False,
        "database_mutation": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="health-landing")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--max-manifests", type=int, default=MAX_MANIFESTS)
    args = parser.parse_args()
    endpoint = os.getenv("S3_ENDPOINT", "").strip()
    if not endpoint.startswith(("http://", "https://")):
        raise DiscoveryError("S3_ENDPOINT is required")
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        raise DiscoveryError("AWS S3 credentials are required")
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("S3_REGION", "us-east-1"),
        config=__import__("botocore.config", fromlist=["Config"]).Config(
            connect_timeout=8, read_timeout=30, retries={"max_attempts": 2},
            s3={"addressing_style": "path"},
        ),
    )
    result = discover_ready_batches(
        client, bucket=args.bucket, prefix=args.prefix, max_manifests=args.max_manifests
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    print("LANDING_BATCH_DISCOVERY_READONLY=PASS")
    print("DATABASE_MUTATION=NO")


if __name__ == "__main__":
    main()
