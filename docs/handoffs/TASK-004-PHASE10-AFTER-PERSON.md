# TASK-004 Handoff — After Standalone Person Runtime

## 1. Handoff Purpose

This document captures the exact development state immediately after TASK004 Phase 10 STEP01 standalone Person runtime passed.

The next implementation step is:

```text
TASK004_PHASE10_STEP02_STANDALONE_VISIT_RUNTIME
```

Do not start Airflow orchestration before standalone Visit runtime is independently verified.

---

## 2. Current Git Baseline

Local and remote `main` must start from:

```text
d31035b41141c905dd56e21d339342f8988998e3
```

Expected worktree state before the next development step:

```text
clean
```

TASK001, TASK002 and TASK003 remain frozen.

---

## 3. Phase 9 Status

Phase 9 is closed.

Verified TASK004 control runtime image:

```text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime@sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

Linux/amd64 digest:

```text
sha256:80dccbe023c062dbd245ca3f334dca5e1dfa44e10362a2eeeb4caabf153e2fa5
```

Runtime verification:

```text
node             = worker02
runtime user     = 10001:10001
kubectl          = v1.32.5
runtime files    = 14/14 readable
runtime dirs     = 0755
```

Direct in-cluster lineage resolution:

```text
patients   = PASS
encounters = PASS
```

Old failed image:

```text
sha256:9a94a36f5b393744e4ed2cca2f47b036c27c58797b7ca7e4b695787d74c034e6
```

must not be reused.

---

## 4. Authoritative Landing Lineage

Batch ID:

```text
task004-p20-first-landing-20261011
```

Manifest URI:

```text
s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=task004-p20-first-landing-20261011/manifest.json
```

Manifest SHA256:

```text
d7a1ce5fb3cc1e25737b2ed5c35b7d463bbc8e7523b6531dcd1ce819360ff445
```

Manifest status:

```text
INTAKE_VERIFIED
```

Patients:

```text
rows       = 20
size_bytes = 5833
sha256     = f4e249d17302acd8ffd53b54e92808547fe58af329f26ede89c6c0f5c74203e8
```

Encounters:

```text
rows       = 2459
size_bytes = 796850
sha256     = 8b39571d258380ccb8ebae2f19466a6430399210c0dcdce540bf5f0f00f83440
```

---

## 5. Standalone Person Runtime — VERIFIED

Run ID:

```text
task004-person-20261011T021241Z-2752601
```

SparkApplication:

```text
task004-person-20261011t021241z-2752601
```

Spark image:

```text
spark:3.5.7-python3
```

Driver:

```text
node       = worker02
node class = platform
```

Result:

```text
EXPECTED_ROWS=20
SOURCE_ROWS=20
CANONICAL_ROWS=20
PROCESSING_READBACK_ROWS=20

CANONICAL_CONTRACT=PASS
PROCESSING_WRITE=PASS
PROCESSING_READBACK=PASS

POSTGRESQL_MUTATION=NO
```

Processing output:

```text
s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=task004-p20-first-landing-20261011/entity=patient/run_id=task004-person-20261011T021241Z-2752601/work/normalized/data/
```

Successful temporary Kubernetes resources were removed.

---

## 6. Next Step — Standalone Visit

Runner:

```text
scripts/task004/05e-run-visit-canonical.sh
```

Adapter:

```text
spark/apps/visit/synthea_encounter_adapter.py
```

Contract:

```text
spark/contracts/canonical/encounter-v1.json
```

Frozen template reused from TASK003:

```text
spark/manifests/task003/encounter-canonical-adapter.yaml.tpl
```

Expected source evidence:

```text
dataset    = encounters
rows       = 2459
size_bytes = 796850
sha256     = 8b39571d258380ccb8ebae2f19466a6430399210c0dcdce540bf5f0f00f83440
```

Expected Processing entity:

```text
entity=encounter
```

Expected Spark image:

```text
spark:3.5.7-python3
```

Expected placement:

```text
workload=platform
```

---

## 7. Visit Success Markers

The current Visit wrapper requires the driver log to contain:

```text
SOURCE_ROWS=2459
SOURCE_UNIQUE_ENCOUNTERS=2459

CANONICAL_ROWS=2459
CANONICAL_UNIQUE_ENCOUNTERS=2459

CANONICAL_INVALID_REQUIRED=0
CANONICAL_INVALID_CLASSES=0
CANONICAL_INVALID_TIME_ORDER=0

CANONICAL_ENCOUNTER_CONTRACT=PASS
CANONICAL_ENCOUNTER_DQ=PASS

PROCESSING_WRITE=PASS

PROCESSING_READBACK_ROWS=2459
PROCESSING_READBACK_UNIQUE_ENCOUNTERS=2459
PROCESSING_READBACK=PASS

RAW_PUBLISH=NO
POSTGRESQL_WRITE=NO
TASK003_ENCOUNTER_ADAPTER=PASS
```

The `TASK003_ENCOUNTER_ADAPTER=PASS` marker belongs to the frozen reused adapter and should not be changed merely for TASK004 naming.

---

## 8. Visit Failure Policy

If Visit fails:

```text
retain SparkApplication
retain ConfigMap
retain driver Pod/log
retain runtime report
```

Do not blindly retry.

First classify the failure layer:

```text
lineage
Maven/JAR dependency
Spark startup
S3 input
transformation
contract/DQ
Processing write
Processing readback
wrapper verification
```

Only then patch and retry.

---

## 9. Known Visit Risk

The frozen TASK003 Visit runtime uses Maven/JAR dependency behavior.

The first standalone Visit run may expose:

```text
Maven repository reachability
dependency download behavior
JAR compatibility
```

If this occurs:

- do not modify frozen TASK003 source directly;
- implement a TASK004-safe wrapper/runtime change;
- add regression coverage;
- retain the failed runtime evidence until the replacement passes.

---

## 10. After Visit PASS

Recommended sequence:

```text
Person PASS
  ↓
Visit PASS
  ↓
freeze standalone downstream checkpoint
  ↓
batch reconciliation
  ↓
Airflow DAG
  ↓
minimal Airflow RBAC
  ↓
end-to-end orchestration
```

---

## 11. Airflow Constraints

Current Airflow service account:

```text
dw-airflow-scheduler
```

Previous discovery showed additional RBAC work is required.

The final Airflow runtime should use:

```text
TASK004_RUNTIME_CONTEXT=in-cluster
```

and must not depend on:

```text
runner01 local repository
kubectl exec back into scheduler
```

---

## 12. Development Rules to Preserve

1. One implementation step at a time.
2. One directly pasteable Bash block per runtime step.
3. Temporary development scripts live under `/data/spark/temp_shell`.
4. Permanent runtime logic must be reconstructable from canonical repo source.
5. Frozen TASK001-003 files must not be modified.
6. Failed runtime resources remain until diagnosis is complete.
7. Successful temporary resources are cleaned.
8. Runtime evidence stays outside normal Git source.
9. `git diff --check` is a mandatory checkpoint gate.
10. Airflow waits until standalone Visit passes.
11. Large Markdown documents are generated as standalone `.md` files, not embedded in Bash heredocs.

---

## 13. Immediate Next Action

The next runtime step should implement only:

```text
TASK004_PHASE10_STEP02_STANDALONE_VISIT_RUNTIME
```

It should:

- verify Git baseline;
- resolve current `encounters` lineage;
- launch the real SparkApplication;
- capture actual driver placement;
- verify all 2459 rows;
- verify canonical contract and DQ;
- verify Processing write and independent readback;
- verify PostgreSQL remains untouched;
- clean successful SparkApplication / ConfigMap / driver Pod;
- retain failure resources if the run fails.

No Airflow execution should occur in that step.
