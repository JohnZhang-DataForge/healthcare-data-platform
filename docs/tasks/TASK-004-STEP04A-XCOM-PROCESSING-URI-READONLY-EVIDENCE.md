# TASK004 STEP04A — XCom Processing URI read-only verification (partial)

Status: **SOURCE URI PASS / Workflow FAILURE / STEP04A overall IN PROGRESS**

## Exact evidence
- Healthcare source commit: `164fff38a7335a66c19f5fd186c6f37115450b96`.
- Self-Runner feature commit: `d3742246e2f5c530121b5e4216b2de51ea92d7ac`.
- ARC run: https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38339701366 (overall **failure**).
- Actual Airflow 3 metadata XCom SQL read succeeded under `SET TRANSACTION READ ONLY`.
- Runner failure is a **post-readback incorrect marker gate**: workflow expects `AIRFLOW_TRIGGER=NO` but source prints `DATA_MUTATION=NO`; no evidence of SQL/XCom failure in this run.
- Previous runs (38338757546, 38338785504, 38338845756, 38339542661, 38339644692) are failures. Stop further iterations for this bounded turn per retry budget.

## Accepted batch verified from actual XCom
```text
BATCH_ID=task004-airflow-task004-step03e-38324111846
PERSON_ROWS=23
VISIT_ROWS=3592
PERSON_PROCESSING_URI=s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id=task004-airflow-task004-step03e-38324111846/entity=patient/run_id=task004-person-20261012T235028Z-8/work/normalized/data/
VISIT_PROCESSING_URI=s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id=task004-airflow-task004-step03e-38324111846/entity=encounter/run_id=task004-encounter-20261012T235028Z-8/work/normalized/data/
PERSON_URI_GATE=PASS
VISIT_URI_GATE=PASS
XCOM_READBACK=PASS
DATA_MUTATION=NO
RESULT=PASS
```

## Outstanding to close STEP04A
1. Correct only the Self-Runner marker gate to check existing `DATA_MUTATION=NO` and `RESULT=PASS`, then re-test in a **new bounded session**. No new batch or database mutation.
2. Independently read Parquet schemas and counts at these fixed URIs, verify exact source business keys and same-batch Person FK lineage.
3. Compare source keys against read-only PostgreSQL ID maps using aggregate-only privacy-preserving mechanism. Record NEW/EXISTING/CONFLICT counts, unverified gates and safety implications.
4. Publish canonical STEP04A aggregate report and explicit gates. Do not mark full STEP04A PASS until actual Parquet + database readback evidence exists.

No mutation of OMOP, S3, Kubernetes workloads or Airflow triggers was performed in this URI investigation.
