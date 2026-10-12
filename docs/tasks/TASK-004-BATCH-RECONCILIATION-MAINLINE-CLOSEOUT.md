# TASK-004 Batch Reconciliation — Mainline Closeout

> **CURRENT ACCEPTED CHECKPOINT**  
> Date: 2026-10-12  
> Status: **PASS / MAINLINE ACCEPTED**  
> TASK004 overall: **IN PROGRESS**  
> Next: **Airflow orchestration**

## 1. Acceptance decision

The test-period V9 implementation was not accepted automatically.

Mainline review concluded:

```text
REVIEW_DECISION=MODIFY_BEFORE_ACCEPTANCE
```

Required changes were completed in the formal Healthcare mainline:

- lineage values must be single-valued, non-null and non-blank;
- both Patient and Encounter must match the requested batch;
- `ORPHAN_ENCOUNTERS` counts orphan Encounter rows;
- Processing URIs are preflight-validated for bucket, source, version, ingest date, batch, entity and run identity;
- failures retain/report created SparkApplication / ConfigMap / driver Pod evidence;
- success cleanup is independently verified;
- reconciliation emits structured `run-state.json`;
- source acceptance tests are repo-relative and lock these rules.

## 2. Healthcare source identity

```text
Healthcare PR              = #24
Final tested PR HEAD        = ee16f5265b0ebb8c30e7e65ec665215613956e77
Healthcare merge/main SHA   = 91d96f436e7697d70025cc1c9a045ecfb20f41b1
```

Changed mainline files:

```text
scripts/task004/05f-reconcile-person-visit.sh
spark/apps/task004/reconcile_person_visit.py
tests/task004/test_person_visit_reconciliation_source.py
docs/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md
```

The SparkApplication template was reviewed and intentionally not changed.

## 3. Pre-merge exact-PR validation

```text
Self-Runner Run            = 38287060452
Healthcare target          = PR #24 exact HEAD
Healthcare SHA             = ee16f5265b0ebb8c30e7e65ec665215613956e77
Policy gate                = PASS
Source gate                = PASS
Real Spark runtime         = PASS
Evidence gate              = PASS
Artifact upload            = PASS
```

Artifact:

```text
ID      = 11763243392
Name    = m2-v9-task004-reconciliation-38287060452
Digest  = sha256:171fb1d9bdfd6506ef150c8e37a529fb26a2f3225ebce9deba344ec057307292
```

## 4. Post-merge exact-main validation

```text
Self-Runner Run            = 38287401518
Healthcare target          = main exact SHA
Healthcare SHA             = 91d96f436e7697d70025cc1c9a045ecfb20f41b1
Policy gate                = PASS
Source gate                = PASS
Real Spark runtime         = PASS
Evidence gate              = PASS
Artifact upload            = PASS
```

Artifact:

```text
ID      = 11764107251
Name    = m2-v9-task004-reconciliation-38287401518
Digest  = sha256:c0f72a2dc7c84bccfa96af344432241de0ab6ace8a69ae5c959e5bcf3ac2d1f7
```

## 5. Self-Runner control acceptance

Self-Runner was minimally enhanced to support:

```text
feature PR ref + PR number + exact SHA
main ref + exact SHA post-merge
```

and to verify:

- Healthcare exact source identity;
- `bash -n`;
- Python compile;
- reconciliation source tests;
- real ARC / Spark runtime;
- strong business markers;
- structured run-state;
- evidence artifact.

Final control identity:

```text
Self-Runner PR             = #31
Self-Runner merge/main SHA = 8ab26784cd0229cce96989e3691c122049e3c23a
```

## 6. Final business evidence

Both accepted runs demonstrated:

```text
PATIENT_ROWS=20
PATIENT_UNIQUE_IDS=20
ENCOUNTER_ROWS=2459
ENCOUNTER_UNIQUE_IDS=2459
REFERENCED_PATIENTS=20
ORPHAN_ENCOUNTERS=0

SOURCE_SYSTEM=synthea
SOURCE_VERSION=v3.3.0
SOURCE_BATCH_ID=task004-p20-first-landing-20261011
SOURCE_INGEST_DATE=2026-10-11

PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO

SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONFIGMAP_RESIDUAL=NO
SUCCESSFUL_DRIVER_POD_RESIDUAL=NO

RECONCILIATION_STATE_GATE=PASS
RESULT=PASS
```

## 7. Fail-fast evidence

Two failed attempts are intentionally preserved as development evidence:

### Run 38286850393

```text
Failure domain = GitHub Workflow YAML parse
jobs           = 0
Kubernetes     = NOT RUN
Spark          = NOT RUN
Data mutation  = NO
```

### Run 38286943030

```text
Policy                      = PASS
Exact PR HEAD               = PASS
Source tests                = FAIL (two test assertion defects)
Spark                        = SKIPPED
Kubernetes workload mutation = NO
Data mutation               = NO
```

The failures were fixed in the same bounded STEP rather than bypassed.

## 8. Mainline classification

```text
TASK004_BATCH_RECONCILIATION_MAINLINE=PASS
RECONCILIATION_MAINLINE_REVIEWED=YES
REVIEW_DECISION=MODIFY_BEFORE_ACCEPTANCE
RECONCILIATION_PREMERGE_EXACT_HEAD=PASS
RECONCILIATION_POSTMERGE_EXACT_MAIN=PASS
PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO
TEMPORARY_KUBERNETES_RESIDUAL=NO

TASK004_OVERALL=IN_PROGRESS
AIRFLOW_ORCHESTRATION=NOT_YET
NEXT=TASK004_AIRFLOW_ORCHESTRATION
```

## 9. Historical documents

The former current Candidate Status is archived unchanged at:

```text
docs/archive/2026-10-12-mainline-reconciliation-acceptance/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md
```

The earlier V9 test-period closeout remains at:

```text
docs/archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md
```

Neither historical document overrides this accepted checkpoint.
