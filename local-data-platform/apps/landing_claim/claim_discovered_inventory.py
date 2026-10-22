#!/usr/bin/env python3
"""Receive Airflow's discovered READY manifest preview and evaluate safe claims.

Producer-independent; read-only by default. The opt-in claim gate requires
both CLAIM_ENABLE=YES and an explicit per-batch allowlist. No Spark/CDM writes.
Do not enable claiming real READY batches until an ETL consumer can finish
and reconcile work; a claim alone would strand a processing lease.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from batch_ledger import Candidate, ClaimError, claim

MAX_INVENTORY_BYTES = 128 * 1024
MAX_ITEMS = 100  # match the read-only Discovery XCom preview contract


def parse_inventory(raw: str, *, allow_truncated_readonly: bool = False) -> list[Candidate]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_INVENTORY_BYTES:
        raise ClaimError("BLOCKED:XCOM_SIZE")
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ClaimError("BLOCKED:XCOM_JSON") from exc
    if not isinstance(obj, dict):
        raise ClaimError("BLOCKED:XCOM_OBJECT")
    truncated = obj.get("preview_truncated")
    if (obj.get("status") != "READ_ONLY_DISCOVERED"
        or obj.get("processing_authorized") is not False
        or obj.get("database_mutation") is not False
        or not isinstance(truncated, bool)):
        raise ClaimError("BLOCKED:DISCOVERY_SAFETY_GATE")
    rows = obj.get("ready_batches_preview")
    ready_count = obj.get("ready_count")
    quarantined_count = obj.get("quarantined_count")
    if (not isinstance(rows, list) or len(rows) > MAX_ITEMS
        or type(ready_count) is not int or ready_count < len(rows)
        or type(quarantined_count) is not int or quarantined_count < 0
        or truncated != (ready_count > len(rows))
        or (truncated and len(rows) != MAX_ITEMS)):
        raise ClaimError("BLOCKED:INCOMPLETE_INVENTORY")
    # Scheduled observation is always read-only (CLAIM_ENABLE=NO).
    # A bounded, truncated preview is sufficient to observe the first
    # MAX_ITEMS; never permit atomic claims from an incomplete inventory.
    if truncated and not allow_truncated_readonly:
        raise ClaimError("BLOCKED:DISCOVERY_SAFETY_GATE")
    seen = set()
    results = []
    for r in rows:
        if not isinstance(r, dict):
            raise ClaimError("BLOCKED:CANDIDATE_TYPE")
        try:
            c = Candidate.from_discovery(r)
            c.check()
        except (KeyError, TypeError) as exc:
            raise ClaimError("BLOCKED:CANDIDATE_FIELDS") from exc
        if c.manifest_uri in seen or (c.source_system, c.batch_id) in seen:
            raise ClaimError("BLOCKED:DUPLICATE_CANDIDATE")
        seen.add(c.manifest_uri)
        seen.add((c.source_system, c.batch_id))
        results.append(c)
    return results


def build_report(candidates: list[Candidate], *, db, enabled: bool,
                 allowlist: frozenset[str], s3=None) -> dict:
    """Legacy ledger exclusion, inspect new ledger, claim only opted-in rows.

    Even when enabled, a candidate is revalidated against immutable S3 bytes
    before invoking the database claim transaction.
    """
    decisions = []
    for c in candidates:
        with db.cursor() as cur:
            # Historical ETL ledger is authoritative for legacy batch handling.
            cur.execute(
                "SELECT count(*) FROM etl.task004_batch_ledger WHERE batch_id=%s AND source_system=%s",
                (c.batch_id, c.source_system),
            )
            legacy = cur.fetchone()[0] > 0
            cur.execute(
                """SELECT manifest_sha256, manifest_uri, status, attempt_count
                   FROM etl.landing_batch_ledger
                   WHERE source_system=%s AND batch_id=%s""",
                (c.source_system, c.batch_id),
            )
            existing = cur.fetchone()

        if existing is not None and (existing[0] != c.manifest_sha256 or existing[1] != c.manifest_uri):
            raise ClaimError("BLOCKED:IMMUTABLE_MANIFEST_DRIFT")
        if legacy:
            status = "SKIP_LEGACY_BATCH"
        elif existing is not None and existing[2] == "COMPLETED":
            status = "SKIP_COMPLETED"
        elif not enabled:
            status = "OBSERVED_ONLY"
        elif c.batch_id not in allowlist:
            status = "SKIP_NOT_ALLOWLISTED"
        elif existing is not None and existing[2] == "PROCESSING":
            status = "BUSY_OR_EXPIRED_LEASE"  # Actual atomic claim checks expiry.
        elif existing is not None and existing[2] == "FAILED":
            status = "FAILED_NEEDS_RECONCILIATION"
        else:
            # Exact-version S3 re-read is mandatory on claim activation.
            if s3 is None:
                raise ClaimError("BLOCKED:S3_REVALIDATION_REQUIRED")
            revalidate_manifest_sha(s3, c)
            result = claim(db, c, retry_failed=False)
            status = result.decision
        decisions.append({"batch_id": c.batch_id, "decision": status})

    tally: dict[str, int] = {}
    for r in decisions:
        tally[r["decision"]] = tally.get(r["decision"], 0) + 1
    return {
        "status": "EVALUATED",
        "input_count": len(candidates),
        "claim_enabled": enabled,
        "claim_count": tally.get("CLAIMED", 0),
        "decisions": decisions,
        "decision_counts": tally,
        "producer_trigger": False,
        "spark_trigger": False,
        "omop_business_mutation": False,
    }


def revalidate_manifest_sha(s3, c: Candidate) -> None:
    """Confirm published Manifest bytes still match Airflow's inventory."""
    uri = urlsplit(c.manifest_uri)
    if uri.scheme != "s3" or not uri.netloc or not uri.path:
        raise ClaimError("BLOCKED:URI")
    response = s3.get_object(Bucket=uri.netloc, Key=uri.path.lstrip("/"))
    if int(response.get("ContentLength", 1_048_577)) > 1_048_576:
        raise ClaimError("BLOCKED:MANIFEST_OVERSIZE")
    body = response["Body"].read(1_048_577)
    if len(body) > 1_048_576 or hashlib.sha256(body).hexdigest() != c.manifest_sha256:
        raise ClaimError("BLOCKED:MANIFEST_CHANGED")
    # Version-aware full validation was already done by scan_ready_manifests.
    # This revalidation locks the bytes; downstream Spark must also recheck.


def run(raw: str, db, *, enabled: bool = False, allowlist: frozenset[str] = frozenset(),
        s3=None) -> dict:
    candidates = parse_inventory(raw, allow_truncated_readonly=not enabled)
    if enabled and not allowlist:
        raise ClaimError("BLOCKED:EMPTY_CLAIM_ALLOWLIST")
    report = build_report(candidates, db=db, enabled=enabled, allowlist=allowlist, s3=s3)
    inventory = json.loads(raw)
    report["inventory_ready_count"] = inventory["ready_count"]
    report["preview_truncated"] = inventory["preview_truncated"]
    report["evaluation_scope"] = (
        "PREVIEW_ONLY" if inventory["preview_truncated"] else "COMPLETE_INVENTORY"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--xcom-path", default="/airflow/xcom/return.json")
    args = parser.parse_args()
    enabled = os.getenv("CLAIM_ENABLE", "NO") == "YES"
    if os.getenv("CLAIM_ENABLE", "NO") not in {"NO", "YES"}:
        raise ClaimError("BLOCKED:INVALID_CLAIM_FLAG")
    allowlist = frozenset(x.strip() for x in os.getenv("CLAIM_ALLOWLIST", "").split(",") if x.strip())
    if not enabled and allowlist:
        raise ClaimError("BLOCKED:ALLOWLIST_WITH_DISABLED_CLAIM")
    if enabled and not allowlist:
        raise ClaimError("BLOCKED:EMPTY_CLAIM_ALLOWLIST")

    import psycopg
    with psycopg.connect(
        host=os.environ["PGHOST"], port=os.getenv("PGPORT", "5432"),
        dbname="omop", user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        options="-c statement_timeout=30000 -c lock_timeout=3000",
        connect_timeout=10,
    ) as db:
        s3 = None
        if enabled:
            import boto3
            from botocore.config import Config
            endpoint = os.getenv("S3_ENDPOINT", "")
            if not endpoint.startswith(("https://", "http://")):
                raise ClaimError("BLOCKED:S3_ENDPOINT")
            s3 = boto3.client(
                "s3", endpoint_url=endpoint,
                config=Config(s3={"addressing_style": "path"}),
            )
        report = run(args.inventory_json, db, enabled=enabled,
                     allowlist=allowlist, s3=s3)
        # Read-only default has no writes, and explicit claims are already
        # transactionally committed by claim() in this connection.
        if not enabled:
            db.rollback()

    path = Path(args.xcom_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    print("LANDING_DISCOVERY_CLAIM_INTEGRATION=PASS")
    print("CLAIM_ENABLED=" + ("YES" if enabled else "NO"))
    print("BATCHES_EVALUATED=" + str(report["input_count"]))
    print("INVENTORY_READY_COUNT=" + str(report["inventory_ready_count"]))
    print("INVENTORY_EVALUATION_SCOPE=" + report["evaluation_scope"])
    print("LEGACY_BATCHES_EXCLUDED=" + str(report["decision_counts"].get("SKIP_LEGACY_BATCH", 0)))
    print("CLAIMED_BATCHES=" + str(report["claim_count"]))
    print("PRODUCER_TRIGGER=NO")
    print("SPARK_TRIGGER=NO")
    print("OMOP_BUSINESS_MUTATION=NO")


if __name__ == "__main__":
    main()
