#!/usr/bin/env python3
"""Read-only Airflow XCom inspection for the accepted TASK004 batch. No patient data."""
import re
from airflow.models.xcom import XCom

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

for task,entity,expected in (("person","patient",23),("visit","encounter",3592)):
        val=XCom.get_one(run_id=RUN,task_id=task,dag_id=DAG,key='return_value')
        require(isinstance(val,dict),"xcom_missing_"+task)
        require(int(val.get("canonical_rows",-1))==expected,"row_count_"+task)
        uri=validate(val.get("processing_data_uri"),entity)
        print(task.upper()+"_PROCESSING_URI="+uri)
        print(task.upper()+"_ROWS="+str(expected))
        print(task.upper()+"_URI_GATE=PASS")
print("XCOM_READBACK=PASS")
print("DATA_MUTATION=NO")
print("RESULT=PASS")
