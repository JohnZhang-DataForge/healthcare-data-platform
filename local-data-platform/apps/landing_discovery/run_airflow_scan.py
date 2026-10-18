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


def xcom_preview(inventory: dict) -> dict:
    """Return bounded, non-authoritative inventory preview, not a claim."""
    if inventory.get("database_mutation") is not False or inventory.get("processing_authorized") is not False:
        raise DiscoveryError("read-only discovery invariant violated")
    batches = inventory["ready_batches"]
    return {
        "status": "READ_ONLY_DISCOVERED",
        "ready_count": inventory["ready_count"],
        "quarantined_count": inventory["quarantined_count"],
        "ready_batches_preview": batches[:MAX_XCOM_PREVIEW],
        "preview_truncated": len(batches) > MAX_XCOM_PREVIEW,
        "processing_authorized": False,
        "database_mutation": False,
    }


def run(*, s3, bucket: str, prefix: str, xcom_path: Path) -> dict:
    inventory = discover_ready_batches(s3, bucket=bucket, prefix=prefix)
    report = xcom_preview(inventory)
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
    )
    print("LANDING_BATCH_DISCOVERY_AIRFLOW_READONLY=PASS", flush=True)
    print("DISCOVERED_READY_BATCHES=" + str(report["ready_count"]), flush=True)
    print("QUARANTINED_LEGACY_MANIFESTS=" + str(report["quarantined_count"]), flush=True)
    print("S3_MUTATION=NO", flush=True)
    print("DATABASE_MUTATION=NO", flush=True)
    print("GENERATOR_TRIGGER=NO", flush=True)


if __name__ == "__main__":
    main()
