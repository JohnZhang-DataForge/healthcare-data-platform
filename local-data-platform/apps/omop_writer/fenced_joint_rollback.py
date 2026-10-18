"""Rollback-only candidate: lock Claim inside EXACT Person+Visit Writer PG TX.

A SECURITY DEFINER gate must already have been independently reviewed and
deployed; the current SQL live probe ROLLBACKS its installation, so this code
is deliberately NOT enabled in Airflow or an actual Writer runtime.

No COMMIT path, no new connection, no detached preflight authorization.
"""
from __future__ import annotations

from typing import Any

from joint_s3_rollback import compose_joint_rollback, for_psycopg, verified_plan


FENCE_SQL = (
    "SELECT task004_writer_fence.assert_active_claim(%s,%s,%s,%s,%s,%s)"
)


def ticket_args(context: dict, ticket: Any) -> tuple:
    """Match immutable Writer plan and fresh Claim ticket before ANY PG DML."""
    verified_plan(context)
    ticket.check()
    candidate = ticket.candidate
    if (candidate.source_system != "synthea"
        or candidate.batch_id != context["batch_id"]
        or candidate.manifest_sha256 != context["manifest_sha256"]
        or candidate.manifest_uri != context["manifest_uri"]):
        raise ValueError("BLOCKED:WRITER_FENCE_PLAN_TICKET_DRIFT")
    return (candidate.source_system, candidate.batch_id,
            candidate.manifest_sha256, candidate.manifest_uri,
            ticket.lease_owner, ticket.attempt_count)


def fenced_joint_rollback(conn: Any, context: dict, people: list,
                          visits: list, ticket: Any) -> None:
    """One BEGIN → DB definer lock → Person+Visit → DB recheck → ROLLBACK.

    The same cursor/connection and transaction owns the Claim row lock and
    all (ultimately reverted) business DML. Never accepts allow_commit.
    """
    values = ticket_args(context, ticket)
    script = for_psycopg(compose_joint_rollback(context, people, visits))
    if not script.startswith("BEGIN;\n") or not script.endswith("ROLLBACK;\n"):
        raise ValueError("BLOCKED:WRITER_FENCE_UNEXPECTED_TX_SHELL")
    body = script[len("BEGIN;\n"):-len("ROLLBACK;\n")]
    # Explicit autocommit connection is required to create a single, visible
    # transaction boundary; the function itself always manually ROLLBACKs.
    if conn.autocommit is not True:
        raise ValueError("BLOCKED:WRITER_FENCE_REQUIRES_AUTOCOMMIT_CONN")
    with conn.cursor() as cur:
        cur.execute("SELECT current_user,current_setting('transaction_read_only')")
        if cur.fetchone() != ("cdm_writer", "off"):
            raise ValueError("BLOCKED:WRITER_FENCE_ROLE_OR_READONLY")
        cur.execute("BEGIN;")
        try:
            cur.execute("SET LOCAL lock_timeout='2500ms'")
            cur.execute(FENCE_SQL, values)
            cur.execute(body, prepare=False)
            # Must check DB clock again after both entities before TX ends.
            cur.execute(FENCE_SQL, values)
        finally:
            # Also works if a failed statement left PG TX in aborted state.
            cur.execute("ROLLBACK;")
