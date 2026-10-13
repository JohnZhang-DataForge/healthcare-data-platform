#!/usr/bin/env python3
"""Read-only Airflow XCom inspection for the accepted TASK004 batch. No patient data."""
import re
import json
from sqlalchemy import text
from airflow.settings import Session

DAG="task004_processing_pipeline"
RUN="task004-step03e-38324111846"
BATCH="task004-airflow-"+RUN

def require(ok,why):
    if not ok: raise RuntimeError("BLOCKED="+why)

def validate(uri,entity):
    require(isinstance(uri,str),"uri_not_string")
    root="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/entity="+entity+"/"
    require(uri.startswith(root),"uri_lineage_mismatch_"+entity)
    require(re.fullmatch(r"[a-zA-Z0-9_:/=.-]+",uri) is not None,"unsafe_uri")
    require(uri.endswith("/work/normalized/data/"),"uri_suffix_"+entity)
    require(re.search(r"/run_id=[a-zA-Z0-9-]+/",uri) is not None,"run_id_"+entity)
    return uri

# Airflow 3 SDK XCom.get_one requires execution-time supervisor context.
# Query metadata storage directly in an explicitly READ ONLY transaction.
with Session() as session:
    session.execute(text("SET TRANSACTION READ ONLY"))
    for task,entity,expected in (("person","patient",23),("visit","encounter",3592)):
        rows=session.execute(text("""SELECT value FROM xcom
            WHERE dag_id=:dag AND run_id=:run AND task_id=:task AND key='return_value'
            ORDER BY map_index LIMIT 2"""),{"dag":DAG,"run":RUN,"task":task}).fetchall()
        require(len(rows)==1,"xcom_cardinality_"+task)
        raw=rows[0][0]
        val=json.loads(raw if isinstance(raw,(str,bytes)) else bytes(raw))
        require(isinstance(val,dict),"xcom_missing_"+task)
        require(int(val.get("canonical_rows",-1))==expected,"row_count_"+task)
        uri=validate(val.get("processing_data_uri"),entity)
        print(task.upper()+"_PROCESSING_URI="+uri)
        print(task.upper()+"_ROWS="+str(expected))
        print(task.upper()+"_URI_GATE=PASS")
print("XCOM_READBACK=PASS")
print("DATA_MUTATION=NO")
print("RESULT=PASS")
