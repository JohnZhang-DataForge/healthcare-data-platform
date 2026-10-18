"""Atomic PostgreSQL Landing batch claims (not an ETL executor).

The producer owns the immutable S3 manifest. This ledger owns only the
consumer's lifecycle. All transitions are serialized by a per-batch SQL
row lock, identity is immutable, and expired processing leases are NEVER
automatically stolen: completion by an old worker must be fenced before
a future recovery protocol can safely reassign work.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Literal

HEX64 = re.compile(r"^[0-9a-f]{64}$")
S3_URI = re.compile(
    r"^s3://[a-z0-9][a-z0-9.-]*/source=[^/]+/"
    r"source_version=[^/]+/ingest_date=[0-9]{4}-[0-9]{2}-[0-9]{2}/"
    r"batch_id=[^/]+/manifest\.json$"
)

class ClaimError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    source_system: str
    batch_id: str
    manifest_sha256: str
    manifest_uri: str

    @classmethod
    def from_discovery(cls, row: dict):
        if row.get("status") != "INTAKE_VERIFIED":
            raise ClaimError("BLOCKED:NOT_VERIFIED")
        return cls(
            source_system=row["source"],
            batch_id=row["batch_id"],
            manifest_sha256=row["manifest_sha256"],
            manifest_uri=row["manifest_uri"],
        )

    def check(self) -> None:
        if not 1 <= len(self.source_system) <= 64 or not re.fullmatch(r"[a-z0-9_-]+", self.source_system):
            raise ClaimError("BLOCKED:SOURCE")
        if not 1 <= len(self.batch_id) <= 256 or not re.fullmatch(r"[A-Za-z0-9._-]+", self.batch_id):
            raise ClaimError("BLOCKED:BATCH_ID")
        if not HEX64.fullmatch(self.manifest_sha256):
            raise ClaimError("BLOCKED:MANIFEST_SHA")
        if len(self.manifest_uri) > 2048 or not S3_URI.fullmatch(self.manifest_uri):
            raise ClaimError("BLOCKED:MANIFEST_URI")
        expected = "/source=" + self.source_system + "/"
        expected_batch = "/batch_id=" + self.batch_id + "/manifest.json"
        if expected not in self.manifest_uri or not self.manifest_uri.endswith(expected_batch):
            raise ClaimError("BLOCKED:MANIFEST_IDENTITY")


@dataclass(frozen=True)
class ClaimResult:
    decision: Literal["CLAIMED", "BUSY", "SKIP_COMPLETED", "BLOCKED_EXPIRED_LEASE", "FAILED_NEEDS_RECONCILIATION"]
    attempt_count: int
    lease_owner: str | None = None


def claim(conn, candidate: Candidate, *, lease_seconds: int = 900, retry_failed: bool = False) -> ClaimResult:
    """Claim one ready manifest or return a safe non-claim decision.

    Cursor uses PostgreSQL ON CONFLICT and SELECT FOR UPDATE inside a single
    transaction; simultaneous claims have exactly one winner. Database time
    (not Python host time) defines the lease.
    """
    candidate.check()
    if not 30 <= lease_seconds <= 3600:
        raise ClaimError("BLOCKED:LEASE_SECONDS")
    token = secrets.token_hex(24)
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO etl.landing_batch_ledger
                    (source_system,batch_id,manifest_sha256,manifest_uri,
                     status,attempt_count,lease_owner,lease_expires_at)
                   VALUES (%s,%s,%s,%s,'PROCESSING',1,%s,
                           clock_timestamp() + (%s * interval '1 second'))
                   ON CONFLICT (source_system,batch_id) DO NOTHING""",
                (candidate.source_system,candidate.batch_id,candidate.manifest_sha256,
                 candidate.manifest_uri,token,lease_seconds),
            )
            if cur.rowcount == 1:
                return ClaimResult("CLAIMED", 1, token)

            cur.execute(
                """SELECT manifest_sha256,manifest_uri,status,attempt_count,
                          (lease_expires_at <= clock_timestamp()) AS expired
                   FROM etl.landing_batch_ledger
                   WHERE source_system=%s AND batch_id=%s FOR UPDATE""",
                (candidate.source_system,candidate.batch_id),
            )
            old = cur.fetchone()
            if old is None:
                raise ClaimError("BLOCKED:CONCURRENT_LEDGER_MISSING")
            old_sha, old_uri, status, attempts, expired = old
            if old_sha != candidate.manifest_sha256 or old_uri != candidate.manifest_uri:
                raise ClaimError("BLOCKED:IMMUTABLE_MANIFEST_DRIFT")
            if status == "COMPLETED":
                return ClaimResult("SKIP_COMPLETED", attempts)
            if status == "PROCESSING":
                return ClaimResult("BLOCKED_EXPIRED_LEASE" if expired else "BUSY", attempts)
            if status != "FAILED":
                raise ClaimError("BLOCKED:UNKNOWN_LEDGER_STATE")
            # Failed may follow a partially completed/unknown downstream commit:
            # callers must explicitly reconcile before authorizing retry.
            if not retry_failed:
                return ClaimResult("FAILED_NEEDS_RECONCILIATION", attempts)
            cur.execute(
                """UPDATE etl.landing_batch_ledger
                   SET status='PROCESSING',attempt_count=attempt_count+1,
                       lease_owner=%s,
                       lease_expires_at=clock_timestamp()+(%s * interval '1 second'),
                       updated_at=clock_timestamp()
                   WHERE source_system=%s AND batch_id=%s AND status='FAILED'
                   RETURNING attempt_count""",
                (token,lease_seconds,candidate.source_system,candidate.batch_id),
            )
            return ClaimResult("CLAIMED", cur.fetchone()[0], token)


def mark_failed(conn, candidate: Candidate, *, lease_owner: str) -> None:
    candidate.check()
    _require_token(lease_owner)
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE etl.landing_batch_ledger
                   SET status='FAILED',lease_owner=NULL,lease_expires_at=NULL,
                       updated_at=clock_timestamp()
                   WHERE source_system=%s AND batch_id=%s AND manifest_sha256=%s
                     AND manifest_uri=%s AND status='PROCESSING'
                     AND lease_owner=%s AND lease_expires_at>clock_timestamp()""",
                (candidate.source_system,candidate.batch_id,candidate.manifest_sha256,
                 candidate.manifest_uri,lease_owner),
            )
            if cur.rowcount != 1:
                raise ClaimError("BLOCKED:STALE_OR_WRONG_OWNER")


def mark_completed(
    conn, candidate: Candidate, *, lease_owner: str, reconciliation_sha256: str
) -> None:
    candidate.check()
    _require_token(lease_owner)
    if not HEX64.fullmatch(reconciliation_sha256):
        raise ClaimError("BLOCKED:RECONCILIATION_PROOF_REQUIRED")
    # Proof is a caller-supplied reference only; actual database reconciliation
    # is NOT implemented in this phase. Do not expose this method via Airflow.
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE etl.landing_batch_ledger
                   SET status='COMPLETED',lease_owner=NULL,lease_expires_at=NULL,
                       reconciliation_sha256=%s,completed_at=clock_timestamp(),
                       updated_at=clock_timestamp()
                   WHERE source_system=%s AND batch_id=%s AND manifest_sha256=%s
                     AND manifest_uri=%s AND status='PROCESSING'
                     AND lease_owner=%s AND lease_expires_at>clock_timestamp()""",
                (reconciliation_sha256,candidate.source_system,candidate.batch_id,
                 candidate.manifest_sha256,candidate.manifest_uri,lease_owner),
            )
            if cur.rowcount != 1:
                raise ClaimError("BLOCKED:STALE_OR_WRONG_OWNER")


def _require_token(token: str) -> None:
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{48}", token):
        raise ClaimError("BLOCKED:INVALID_LEASE_TOKEN")
