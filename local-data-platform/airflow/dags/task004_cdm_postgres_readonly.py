"""Read-only PostgreSQL validation for CDM Runtime. No DML API."""
import os
import psycopg

def validate_readonly(context):
    required=("PGHOST","PGPORT","PGUSER","PGPASSWORD")
    if any(not os.environ.get(k) for k in required):
        raise ValueError("BLOCKED=postgres_credentials")
    if os.environ["PGUSER"]!="cdm_reader":
        raise ValueError("BLOCKED=postgres_principal")
    with psycopg.connect(host=os.environ["PGHOST"],port=os.environ["PGPORT"],
                         user=os.environ["PGUSER"],password=os.environ["PGPASSWORD"],
                         dbname="omop",connect_timeout=7,
                         options="-c default_transaction_read_only=on -c statement_timeout=15000") as con:
        con.read_only=True
        with con.cursor() as cur:
            cur.execute("SELECT current_user,current_setting('transaction_read_only')")
            username,mode=cur.fetchone()
            if (username,mode)!=("cdm_reader","on"):
                raise RuntimeError("BLOCKED=not_readonly")
            cur.execute("SELECT has_table_privilege(current_user,'cdm.person','INSERT')")
            if cur.fetchone()[0]:
                raise RuntimeError("BLOCKED=unexpected_write_privilege")
            cur.execute("SELECT count(*) FROM cdm.person")
            people=cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM cdm.visit_occurrence")
            visits=cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM etl.task004_batch_ledger WHERE batch_id=%s",
                        (context["batch_id"],))
            ledger=cur.fetchone()[0]
        con.rollback()
    return {"person_rows":people,"visit_rows":visits,"ledger_rows":ledger}
