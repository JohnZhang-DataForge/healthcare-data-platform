#!/usr/bin/env python3
"""Run actual claim state transitions inside one PostgreSQL ROLLBACK.

Runs only against synthetic probe IDs using a consumer-scoped database role.
No READY source batches are ever claimed, no CDM tables are changed.
"""
from __future__ import annotations
import os
import re
import sys
import psycopg
from batch_ledger import Candidate, ClaimError, claim, mark_failed, mark_completed

def candidate(batch_id: str, sha: str = "a" * 64) -> Candidate:
    return Candidate(
        "synthea",batch_id,sha,
        "s3://health-landing/source=synthea/source_version=v3.3.0/"
        f"ingest_date=2026-10-13/batch_id={batch_id}/manifest.json",
    )

def main() -> None:
    label = os.environ.get("PROBE_ID", "")
    if not re.fullmatch(r"landing-claim-test-[a-z0-9-]{4,80}",label):
        raise SystemExit("BLOCKED:INVALID_PROBE_ID")
    conn=psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT","5432"),
        dbname="omop",
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        connect_timeout=10,
        options="-c statement_timeout=30000 -c lock_timeout=3000",
    )
    c=candidate(label)
    expired_c=candidate(label+"-expired")
    try:
        # Begin outer transaction; library's per-operation transaction calls
        # execute nested SAVEPOINTs. Everything below is then rolled back.
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            who=cur.fetchone()[0]
            if who!="landing_claim_worker":
                raise ClaimError("BLOCKED:WRONG_DB_ROLE")
            cur.execute("""SELECT has_table_privilege(current_user,'etl.landing_batch_ledger','INSERT'),
                                 has_table_privilege(current_user,'etl.landing_batch_ledger','SELECT'),
                                 has_table_privilege(current_user,'etl.landing_batch_ledger','UPDATE'),
                                 has_table_privilege(current_user,'cdm.person','INSERT')""")
            privileges=cur.fetchone()
            if privileges!=(True,True,True,False):
                raise ClaimError("BLOCKED:PRIVILEGE_BOUNDARY")

        first=claim(conn,c)
        assert first.decision=="CLAIMED" and first.attempt_count==1
        assert claim(conn,c).decision=="BUSY"
        try:
            claim(conn,candidate(label,sha="b"*64))
        except ClaimError as ex:
            assert str(ex)=="BLOCKED:IMMUTABLE_MANIFEST_DRIFT"
        else:
            raise AssertionError("manifest drift was accepted")
        try:
            mark_failed(conn,c,lease_owner="c"*48)
        except ClaimError as ex:
            assert str(ex)=="BLOCKED:STALE_OR_WRONG_OWNER"
        else:
            raise AssertionError("unowned transition was accepted")
        mark_failed(conn,c,lease_owner=first.lease_owner)
        assert claim(conn,c).decision=="FAILED_NEEDS_RECONCILIATION"
        second=claim(conn,c,retry_failed=True)
        assert second.decision=="CLAIMED" and second.attempt_count==2
        assert second.lease_owner!=first.lease_owner
        try:
            mark_completed(conn,c,lease_owner=first.lease_owner,
                           reconciliation_sha256="d"*64)
        except ClaimError as ex:
            assert str(ex)=="BLOCKED:STALE_OR_WRONG_OWNER"
        else:
            raise AssertionError("stale owner was accepted")
        mark_completed(conn,c,lease_owner=second.lease_owner,
                       reconciliation_sha256="d"*64)
        assert claim(conn,c).decision=="SKIP_COMPLETED"
        expiry=claim(conn,expired_c)
        assert expiry.decision=="CLAIMED"
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE etl.landing_batch_ledger
                   SET lease_expires_at=clock_timestamp()-interval '1 second'
                   WHERE source_system=%s AND batch_id=%s""",
                (expired_c.source_system,expired_c.batch_id),
            )
        assert claim(conn,expired_c).decision=="BLOCKED_EXPIRED_LEASE"
        print("REAL_PG_ATOMIC_CLAIM_TRANSITIONS=PASS",flush=True)
        print("REAL_PG_IMMUTABLE_IDENTITY=PASS",flush=True)
        print("REAL_PG_OWNER_FENCING=PASS",flush=True)
        print("REAL_PG_FAILED_EXPLICIT_RETRY=PASS",flush=True)
        print("REAL_PG_EXPIRED_LEASE_BLOCK=PASS",flush=True)
        print("REAL_PG_LEAST_PRIVILEGE=PASS",flush=True)
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM etl.landing_batch_ledger WHERE batch_id IN (%s,%s)",
                (c.batch_id,expired_c.batch_id),
            )
            rows=cur.fetchone()[0]
        conn.rollback()
        conn.close()
    if rows != 0:
        raise RuntimeError("BLOCKED:ROLLBACK_PROBE_PERSISTED")
    print("REAL_PG_ROLLBACK_NO_PROBES=PASS",flush=True)
    print("OMOP_BUSINESS_MUTATION=NO",flush=True)

if __name__=="__main__":
    main()
