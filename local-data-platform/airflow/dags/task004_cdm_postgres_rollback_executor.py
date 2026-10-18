"""Fail-closed PostgreSQL writer executor: never COMMIT, even on success."""
import os
import psycopg
from task004_cdm_dynamic_pg_writer import render

def execute_rollback(context,rows,entity):
    if os.environ.get("PGUSER")!="cdm_writer":
        raise ValueError("BLOCKED=writer_identity")
    if not all(os.environ.get(k) for k in ("PGHOST","PGPORT","PGPASSWORD")):
        raise ValueError("BLOCKED=writer_connection")
    sql=render(context,rows,entity,allow_commit=False)
    if not sql.endswith("ROLLBACK;\n") or "COMMIT;" in sql:
        raise ValueError("BLOCKED=nonrollback_sql")
    # The SQL renderer emits psql meta-command; psycopg runs SQL, not psql.
    prefix="\\set ON_ERROR_STOP on\n"
    if not sql.startswith(prefix):
        raise ValueError("BLOCKED=unrecognized_sql")
    sql=sql[len(prefix):]
    with psycopg.connect(host=os.environ["PGHOST"],port=os.environ["PGPORT"],
                         dbname="omop",user="cdm_writer",password=os.environ["PGPASSWORD"],
                         connect_timeout=8,autocommit=True) as con:
        with con.cursor() as cur:
            cur.execute("SELECT current_user")
            if cur.fetchone()[0]!="cdm_writer":
                raise RuntimeError("BLOCKED=incorrect_db_user")
            cur.execute(sql,prepare=False)
        # Transaction ends in explicit ROLLBACK from checked renderer.
    return {"entity":entity,"row_count":len(rows),"rollback":True}
