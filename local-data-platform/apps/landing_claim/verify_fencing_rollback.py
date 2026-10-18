#!/usr/bin/env python3
"""Real PostgreSQL ROLLBACK-only NEW_ONLY lease token / attempt fencing probe.

Synthetic batch has no S3 READY data. Never references or claims the genuine
synthea-new-only-gh-38497355290 READY batch. No CDM or permanent ledger DML.
"""
from __future__ import annotations

import os
import re
import psycopg

from batch_ledger import Candidate,ClaimError,claim,mark_failed
from lease_fence import assert_live_fence,renew_live_fence,ticket_from_claim,FenceTicket


def check_rejected(f, expected: str):
    try:
        f()
    except ClaimError as e:
        if str(e) != "BLOCKED:"+expected:
            raise
    else:
        raise RuntimeError("BLOCKED:EXPECTED_FENCE_REJECTION_MISSING:"+expected)


def main():
    probe=os.getenv("PROBE_ID","")
    if not re.fullmatch(r"synthea-new-only-fence-[0-9]{6,24}",probe):
        raise ValueError("BLOCKED:PROBE_ID_NOT_SYNTHETIC")
    c=Candidate("synthea",probe,"f"*64,
        "s3://health-landing/source=synthea/source_version=v3.3.0/"
        f"ingest_date=2026-10-14/batch_id={probe}/manifest.json")
    # Synthetic probe has NO real READY, so the only authorized lifecycle is
    # BEGIN -> simulated claim state transitions -> ROLLBACK.
    with psycopg.connect(
        host=os.environ["PGHOST"],port=os.getenv("PGPORT","5432"),
        dbname="omop",user=os.environ["PGUSER"],password=os.environ["PGPASSWORD"],
        connect_timeout=8,
        options="-c statement_timeout=15000 -c lock_timeout=2500",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT current_user,
                          has_table_privilege(current_user,'etl.landing_batch_ledger','SELECT'),
                          has_table_privilege(current_user,'etl.landing_batch_ledger','UPDATE'),
                          has_schema_privilege(current_user,'cdm','USAGE'),
                          has_table_privilege(current_user,'etl.task004_batch_ledger','INSERT')"""
            )
            if cur.fetchone()!=("landing_claim_worker",True,True,False,False):
                raise RuntimeError("BLOCKED:CLAIM_ROLE_PRIVILEGES")
        try:
            first=claim(conn,c,lease_seconds=180)
            ticket=ticket_from_claim(c,first)
            assert ticket.attempt_count==1
            with conn.cursor() as cur:
                assert_live_fence(cur,ticket)
                print("PG_FENCE_REAL_OWNER_FIRST_ATTEMPT=PASS",flush=True)
                wrong=FenceTicket(c,"0"*48,1)
                check_rejected(lambda:assert_live_fence(cur,wrong),
                               "FENCE_STALE_ATTEMPT_OR_OWNER")
                altered=Candidate("synthea",probe,"a"*64,c.manifest_uri)
                check_rejected(lambda:assert_live_fence(cur,FenceTicket(altered,ticket.lease_owner,1)),
                               "FENCE_MANIFEST_DRIFT")
                renew_live_fence(cur,ticket,lease_seconds=120)
                assert_live_fence(cur,ticket)
                print("PG_FENCE_REAL_HEARTBEAT_AND_WRONG_OWNER=PASS",flush=True)

                cur.execute("""UPDATE etl.landing_batch_ledger
                               SET lease_expires_at=clock_timestamp()-interval '1 second'
                               WHERE source_system='synthea' AND batch_id=%s""",(probe,))
                check_rejected(lambda:assert_live_fence(cur,ticket),"FENCE_LEASE_EXPIRED")
                check_rejected(lambda:renew_live_fence(cur,ticket),"FENCE_LEASE_EXPIRED")
                print("PG_FENCE_REAL_EXPIRED_NO_REVIVAL=PASS",flush=True)

                cur.execute("""UPDATE etl.landing_batch_ledger
                               SET lease_expires_at=clock_timestamp()+interval '120 seconds'
                               WHERE source_system='synthea' AND batch_id=%s""",(probe,))
            mark_failed(conn,c,lease_owner=ticket.lease_owner)
            with conn.cursor() as cur:
                check_rejected(lambda:assert_live_fence(cur,ticket),"FENCE_NOT_PROCESSING")
            blocked=claim(conn,c,retry_failed=False)
            assert blocked.decision=="FAILED_NEEDS_RECONCILIATION",blocked
            print("PG_FENCE_REAL_FAILED_RECONCILIATION_HOLD=PASS",flush=True)

            # This second attempt is only a synthetic in-transaction proof of
            # owner rotation, NOT permission for real FAILED recovery.
            second=claim(conn,c,retry_failed=True)
            new_ticket=ticket_from_claim(c,second)
            assert new_ticket.attempt_count==2 and new_ticket.lease_owner!=ticket.lease_owner
            with conn.cursor() as cur:
                check_rejected(lambda:assert_live_fence(cur,ticket),
                               "FENCE_STALE_ATTEMPT_OR_OWNER")
                assert_live_fence(cur,new_ticket)
                check_rejected(lambda:assert_live_fence(cur,FenceTicket(c,new_ticket.lease_owner,1)),
                               "FENCE_STALE_ATTEMPT_OR_OWNER")
                print("PG_FENCE_REAL_ATTEMPT_ROTATION_AND_STALE_BLOCK=PASS",flush=True)
        finally:
            # This also reverts the artificial INSERT/UPDATE/heartbeat, while
            # pg sequences (none used by landing ledger) do not need resetting.
            conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM etl.landing_batch_ledger WHERE batch_id=%s",(probe,))
            if cur.fetchone()[0]!=0:
                raise RuntimeError("BLOCKED:SYNTHETIC_FENCE_LEDGER_PERSISTED")
            cur.execute("""SELECT count(*) FROM etl.landing_batch_ledger
                           WHERE source_system='synthea'
                             AND batch_id='synthea-new-only-gh-38497355290'""")
            if cur.fetchone()[0]!=0:
                raise RuntimeError("BLOCKED:ACTUAL_NEW_ONLY_WAS_CLAIMED")
        conn.rollback()
    print("PG_FENCE_SYNTHETIC_ROLLBACK_NO_LEDGER_ROW=PASS",flush=True)
    print("REAL_READY_BATCH_CLAIM=NO",flush=True)
    print("OMOP_COMMIT=NO",flush=True)


if __name__=="__main__":
    main()
