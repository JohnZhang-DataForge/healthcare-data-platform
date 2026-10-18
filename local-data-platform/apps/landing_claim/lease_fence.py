"""Transaction-scoped Claim owner fencing for TASK004 NEW_ONLY.

IMPORTANT: assert_live_fence() MUST be called on the same PostgreSQL cursor
and transaction as future Person+Visit writes, once before any write and again
at the final COMMIT boundary. Merely checking on a second connection is unsafe.
This module does NOT create leases, enable Airflow claims, or COMMIT OMOP.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from batch_ledger import Candidate, ClaimError

_OWNER = re.compile(r"^[0-9a-f]{48}$")


@dataclass(frozen=True)
class FenceTicket:
    candidate: Candidate
    lease_owner: str
    attempt_count: int

    def check(self) -> None:
        self.candidate.check()
        if self.candidate.source_system != "synthea" or not re.fullmatch(
            r"synthea-new-only-[A-Za-z0-9][A-Za-z0-9._-]{1,127}",
            self.candidate.batch_id
        ):
            raise ClaimError("BLOCKED:FENCE_NEW_ONLY_ONLY")
        if not isinstance(self.lease_owner, str) or not _OWNER.fullmatch(self.lease_owner):
            raise ClaimError("BLOCKED:FENCE_OWNER_TOKEN")
        if (isinstance(self.attempt_count, bool)
            or not isinstance(self.attempt_count, int)
            or self.attempt_count < 1):
            raise ClaimError("BLOCKED:FENCE_ATTEMPT_COUNT")


def assert_live_fence(cur: Any, ticket: FenceTicket) -> None:
    """Acquire NOWAIT row lock within caller's transaction, then check DB time.

    Never commit, rollback or close the connection here. Lock lifetime must
    encompass every OMOP INSERT, checkpoint and final COMMIT decision.
    """
    ticket.check()
    cur.execute(
        """SELECT manifest_sha256,manifest_uri,status,attempt_count,lease_owner,
                  lease_expires_at
             FROM etl.landing_batch_ledger
            WHERE source_system=%s AND batch_id=%s
            FOR UPDATE NOWAIT""",
        (ticket.candidate.source_system, ticket.candidate.batch_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ClaimError("BLOCKED:FENCE_CLAIM_ABSENT")
    sha,uri,status,attempt,owner,expires_at=row
    if (sha != ticket.candidate.manifest_sha256
        or uri != ticket.candidate.manifest_uri):
        raise ClaimError("BLOCKED:FENCE_MANIFEST_DRIFT")
    if status != "PROCESSING":
        raise ClaimError("BLOCKED:FENCE_NOT_PROCESSING")
    if attempt != ticket.attempt_count or owner != ticket.lease_owner:
        raise ClaimError("BLOCKED:FENCE_STALE_ATTEMPT_OR_OWNER")
    # The time check deliberately runs AFTER acquiring the row lock and uses
    # database clock_timestamp(), not the potentially stale transaction now().
    cur.execute("SELECT %s > clock_timestamp()", (expires_at,))
    if cur.fetchone() != (True,):
        raise ClaimError("BLOCKED:FENCE_LEASE_EXPIRED")


def renew_live_fence(cur: Any, ticket: FenceTicket, *, lease_seconds: int = 900) -> None:
    """Fenced heartbeat. Caller decides whether to COMMIT this lease renewal.

    It must never implicitly revive an expired lease, or recover FAILED.
    """
    if isinstance(lease_seconds,bool) or not isinstance(lease_seconds,int) or not 30<=lease_seconds<=3600:
        raise ClaimError("BLOCKED:FENCE_LEASE_SECONDS")
    assert_live_fence(cur, ticket)
    cur.execute(
        """UPDATE etl.landing_batch_ledger
              SET lease_expires_at=clock_timestamp()+(%s * interval '1 second'),
                  updated_at=clock_timestamp()
            WHERE source_system=%s AND batch_id=%s
              AND manifest_sha256=%s AND manifest_uri=%s
              AND status='PROCESSING'
              AND lease_owner=%s AND attempt_count=%s
              AND lease_expires_at>clock_timestamp()
            RETURNING attempt_count""",
        (lease_seconds,ticket.candidate.source_system,ticket.candidate.batch_id,
         ticket.candidate.manifest_sha256,ticket.candidate.manifest_uri,
         ticket.lease_owner,ticket.attempt_count),
    )
    if cur.fetchone() != (ticket.attempt_count,):
        raise ClaimError("BLOCKED:FENCE_RENEWAL_RACE")


def ticket_from_claim(candidate: Candidate, claim_result: Any) -> FenceTicket:
    if getattr(claim_result,"decision",None)!="CLAIMED":
        raise ClaimError("BLOCKED:FENCE_REQUIRES_FRESH_CLAIM")
    token=getattr(claim_result,"lease_owner",None)
    attempt=getattr(claim_result,"attempt_count",None)
    t=FenceTicket(candidate,token,attempt)
    t.check()
    return t
