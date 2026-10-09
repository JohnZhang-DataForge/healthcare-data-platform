# TASK-002 — Person V2 Canonical Regression

## Goal

Use `patients.csv` from the verified TASK-001 batch as the first reusable V2 domain-processing template.

Target flow:

```text
TASK-001
INTAKE_VERIFIED
        ↓
patients.csv
        ↓
SparkApplication
        ↓
Processing
        ↓
Canonical Patient v1
        ↓
Canonical DQ
        ↓
Raw / Canonical Parquet
        ↓
OMOP Person mapping
        ↓
Processed
        ↓
PostgreSQL stage
        ↓
Transactional CDM UPSERT
        ↓
Reconciliation
```

## Regression baseline

Historical Phase3C result:

```text
cdm.person = 113
stable person IDs = 113
rerun does not inflate row count
```

The existing Phase3C implementation is protected and serves only as a regression reference.

## Execution model

TASK-002 will become a Kubernetes Spark workload:

```text
SparkApplication
    ↓
Driver Pod
    ↓
Executor Pod(s)
    ↓
PySpark Person application
```

The Person implementation is the template for later domains:

- Visit
- Condition
- Procedure
- Drug
- Observation

## Safety

TASK-002 must not overwrite or delete:

- TASK-001 Landing batch;
- historical Landing;
- `/data/spark/phase3c`;
- existing OMOP Person baseline until the new V2 output has passed validation;
- Secrets;
- PVC/PV.
