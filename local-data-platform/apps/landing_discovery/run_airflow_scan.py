#!/usr/bin/env python3
"""Run read-only Landing discovery from a KubernetesPodOperator Pod.

This program is not a batch consumer: it NEVER claims a batch, starts ETL,
calls the producer, or writes to PostgreSQL/S3. One run writes a small,
bounded Airflow XCom preview so downstream claim tasks can be added later.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from scan_ready_batches import (
    DEFAULT_PREFIX, DiscoveryError, discover_ready_batches,
)

MAX_XCOM_PREVIEW = 25


def xcom_preview(
    inventory: dict, *,
    batch_id: str | None = None,
    manifest_uri: str | None = None,
    manifest_sha256: str | None = None,
) -> dict:
    """Return bounded preview plus optional S3-verified exact Batch identity.

    Match against the complete validated inventory, never the preview.
    This is not an authorization to process or commit data.
    """
    if inventory.get("database_mutation") is not False or inventory.get("processing_authorized") is not False:
        raise DiscoveryError("read-only discovery invariant violated")
    batches = inventory["ready_batches"]
    report = {
        "status": "READ_ONLY_DISCOVERED",
        "ready_count": inventory["ready_count"],
        "quarantined_count": inventory["quarantined_count"],
        "ready_batches_preview": batches[:MAX_XCOM_PREVIEW],
        "preview_truncated": len(batches) > MAX_XCOM_PREVIEW,
        "processing_authorized": False,
        "database_mutation": False,
    }
    target = (batch_id, manifest_uri, manifest_sha256)
    if any(value is not None for value in target):
        if not all(isinstance(value, str) and value for value in target):
            raise DiscoveryError("exact Batch selection requires all three identifiers")
        matched = [row for row in batches if row["batch_id"] == batch_id]
        if len(matched) != 1:
            raise DiscoveryError("requested Batch missing from verified S3 inventory")
        row = matched[0]
        if (row["manifest_uri"] != manifest_uri
                or row["manifest_sha256"] != manifest_sha256
                or row["source"] != "synthea"
                or row["source_version"] != "v3.3.0"
                or row["status"] != "INTAKE_VERIFIED"
                or row["file_count"] != 18):
            raise DiscoveryError("requested Batch immutable Manifest drift")
        report["verified_selected_batch"] = row
    return report


def run(
    *, s3, bucket: str, prefix: str, xcom_path: Path,
    batch_id: str | None = None,
    manifest_uri: str | None = None,
    manifest_sha256: str | None = None,
) -> dict:
    inventory = discover_ready_batches(s3, bucket=bucket, prefix=prefix)
    report = xcom_preview(
        inventory, batch_id=batch_id,
        manifest_uri=manifest_uri, manifest_sha256=manifest_sha256,
    )
    xcom_path.parent.mkdir(parents=True, exist_ok=True)
    # XCom volume is provided by Airflow KPO's xcom-sidecar, not a
    # persisted producer or consumer ledger.
    xcom_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="health-landing")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument(
        "--xcom-path",
        default="/airflow/xcom/return.json",
        help="Location writable by KubernetesPodOperator XCom sidecar",
    )
    parser.add_argument("--batch-id", help="Exact manual Batch, independent of preview index")
    parser.add_argument("--manifest-uri", help="Exact verified Landing manifest URI")
    parser.add_argument("--manifest-sha256", help="Exact immutable manifest SHA256")
    args = parser.parse_args()
    endpoint = os.getenv("S3_ENDPOINT", "")
    if not endpoint.startswith(("http://", "https://")):
        raise DiscoveryError("S3_ENDPOINT must be an HTTP(S) URL")
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        raise DiscoveryError("missing S3 access credentials")

    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("S3_REGION", "us-east-1"),
        config=Config(connect_timeout=8, read_timeout=30,
                      retries={"max_attempts": 2},
                      s3={"addressing_style": "path"}),
    )
    report = run(
        s3=client, bucket=args.bucket, prefix=args.prefix,
        xcom_path=Path(args.xcom_path),
        batch_id=args.batch_id, manifest_uri=args.manifest_uri,
        manifest_sha256=args.manifest_sha256,
    )
    print("LANDING_BATCH_DISCOVERY_AIRFLOW_READONLY=PASS", flush=True)
    print("DISCOVERED_READY_BATCHES=" + str(report["ready_count"]), flush=True)
    print("QUARANTINED_LEGACY_MANIFESTS=" + str(report["quarantined_count"]), flush=True)
    print("S3_MUTATION=NO", flush=True)
    print("DATABASE_MUTATION=NO", flush=True)
    print("GENERATOR_TRIGGER=NO", flush=True)


if __name__ == "__main__":
    main()
