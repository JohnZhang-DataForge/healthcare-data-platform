#!/usr/bin/env python3
"""STEP04A: inspect accepted Airflow task logs without writes or source identifiers."""
import json
import re
from pathlib import Path

DAG="task004_processing_pipeline"
RUN="task004-step03e-38324111846"
BATCH="task004-airflow-"+RUN
BASE=Path("/opt/airflow/logs")/f"dag_id={DAG}"/f"run_id={RUN}"
EXPECTED={"person":23,"visit":3592}
FIELDS={
  "generate_publish": ("BATCH_ID","MANIFEST_URI","MANIFEST_SHA256","RESULT"),
  "person": ("BATCH_ID","CANONICAL_ROWS","PROCESSING_READBACK","RESULT"),
  "visit": ("BATCH_ID","CANONICAL_ROWS","PROCESSING_READBACK","RESULT"),
  "reconcile": ("SOURCE_BATCH_ID","SOURCE_VERSION","RESULT"),
}

def fields(task):
    logs=sorted((BASE/f"task_id={task}").glob("attempt=*.log"))
    if not logs: raise RuntimeError(f"missing log: {task}")
    events=[]
    for line in logs[-1].read_text(errors="replace").splitlines():
        try: event=json.loads(line).get("event","")
        except (ValueError,AttributeError): continue
        if isinstance(event,str): events.append(event.strip())
    data={}
    for key in FIELDS[task]:
        marker="[base] "+key+"="
        vals=[event[len(marker):] for event in events if event.startswith(marker)]
        if not vals: raise RuntimeError(f"missing marker: {task}.{key}")
        data[key]=vals[-1]
    # These markers are emitted by the existing processing control runtime.
    optional={}
    for key in ("PROCESSING_DATA_URI","PROCESSING_URI","MANIFEST_URI","MANIFEST_SHA256"):
        marker="[base] "+key+"="
        vals=[event[len(marker):] for event in events if event.startswith(marker)]
        if vals: optional[key]=vals[-1]
    return data,optional

def main():
    result={}; optional={}
    for task in FIELDS:
        result[task],optional[task]=fields(task)
    g=result["generate_publish"]
    assert g["BATCH_ID"]==BATCH
    assert g["RESULT"]=="PASS"
    assert re.fullmatch(r"[0-9a-f]{64}",g["MANIFEST_SHA256"])
    assert g["MANIFEST_URI"].startswith("s3://health-landing/")
    assert BATCH in g["MANIFEST_URI"]
    for task,n in EXPECTED.items():
        t=result[task]
        assert t["BATCH_ID"]==BATCH
        assert int(t["CANONICAL_ROWS"])==n
        assert t["PROCESSING_READBACK"]=="PASS" and t["RESULT"]=="PASS"
    assert result["reconcile"]["SOURCE_BATCH_ID"]==BATCH
    assert result["reconcile"]["SOURCE_VERSION"]=="v3.3.0"
    assert result["reconcile"]["RESULT"]=="PASS"
    print("TASK004_STEP04A_SOURCE_LINEAGE_BEGIN=YES")
    print("SOURCE_BATCH_ID="+BATCH)
    print("MANIFEST_SHA256="+g["MANIFEST_SHA256"])
    print("MANIFEST_URI="+g["MANIFEST_URI"])
    for task in EXPECTED:
        print(task.upper()+"_ROWS="+str(EXPECTED[task]))
        u=optional[task].get("PROCESSING_DATA_URI") or optional[task].get("PROCESSING_URI")
        if u:
            assert u.startswith("s3a://health-processing/") and f"batch_id={BATCH}/" in u
            print(task.upper()+"_PROCESSING_URI="+u)
            print(task.upper()+"_URI_GATE=PASS")
        else:
            print(task.upper()+"_URI_GATE=NOT_OBSERVED")
    print("SOURCE_LINEAGE_GATE=PASS")
    print("SOURCE_DATA_READBACK=NOT_RUN")
    print("POSTGRESQL_MUTATION=NO")
    print("AIRFLOW_TRIGGER=NO")
    print("RESULT=PASS")

if __name__=="__main__":
    main()
