# TASK-004 Progress Checkpoint — After Standalone Person Runtime

## 1. Current Status

**TASK-004 is IN PROGRESS.**

This checkpoint records the verified state after:

- deterministic Synthea generation;
- guarded Landing publication;
- replay / conflict / recovery validation;
- generic verified Landing lineage resolution;
- TASK004 control-plane runtime image delivery;
- Phase 9 cluster runtime verification;
- Phase 10 STEP01 standalone Person Spark runtime.

Current execution boundary:

```text
Synthea
  ↓
Kubernetes Job
  ↓
Landing / SeaweedFS
  ↓
Verified manifest lineage
  ↓
Standalone Person Spark runtime    ← VERIFIED
  ↓
Standalone Visit Spark runtime     ← NEXT
  ↓
Batch reconciliation               ← NOT YET
  ↓
Airflow orchestration              ← NOT YET
```

TASK-004 must not yet be described as complete or closed.

---

## 2. Current Git Baseline

Current verified source checkpoint:

```text
d31035b41141c905dd56e21d339342f8988998e3
```

This checkpoint includes the final Phase 9 control-runtime image directory-permission fix.

TASK001, TASK002 and TASK003 remain frozen.

---

## 3. Synthea Source Baseline

Source system:

```text
synthea
```

Source version:

```text
v3.3.0
```

Pinned Synthea commit:

```text
995cf2fd33e67918d4e33110d9f68ad248002221
```

CSV contract:

```text
contracts/synthea/v3.3.0/csv-contract.json
```

Contract SHA256:

```text
70fe18b0a112404ee8b117a39ba6db53e93f555cedf1811d6617658c089ed614
```

The authoritative Synthea export contains exactly 18 CSV files.

Reference deterministic input:

```text
population_size=20
seed=20261010
clinician_seed=20261010
reference_date=20261010
state=Georgia
city=<blank>
```

Reference payload fingerprint:

```text
d3be9389df7d9d90acabb96198c8cea47a11b305e1042129ba9e27b92ee3ea54
```

Reference rows:

```text
patients.csv   = 20
encounters.csv = 2459
```

Downstream runtime expectations are derived from the verified manifest rather than hardcoded historical values.

---

## 4. Verified Synthea Generator Image

```text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d
```

Runtime placement:

```text
namespace = dw-synthea
node      = worker01
```

This remains a dedicated data-generator image.

---

## 5. Authoritative Landing Batch

Batch ID:

```text
task004-p20-first-landing-20261011
```

Ingest date:

```text
2026-10-11
```

Landing prefix:

```text
s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=task004-p20-first-landing-20261011/
```

Manifest URI:

```text
s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=task004-p20-first-landing-20261011/manifest.json
```

Manifest SHA256:

```text
d7a1ce5fb3cc1e25737b2ed5c35b7d463bbc8e7523b6531dcd1ce819360ff445
```

Publication status:

```text
INTAKE_VERIFIED
```

Verified publication semantics:

| Scenario | Result |
|---|---|
| new batch | payload first, independent readback, manifest LAST |
| same batch + same payload | reuse existing verified prefix |
| same batch + different payload | conflict, no overwrite |
| partial payload + no manifest | recover missing payload, then publish manifest |
| manifest present + incomplete payload | fail; no silent repair |

---

## 6. Generic Landing Resolver

TASK004 introduced a generic remote resolver based on:

```text
batch_id
manifest_uri
manifest_sha256
```

Verified `patients` metadata:

```text
rows       = 20
size_bytes = 5833
sha256     = f4e249d17302acd8ffd53b54e92808547fe58af329f26ede89c6c0f5c74203e8
```

Verified `encounters` metadata:

```text
rows       = 2459
size_bytes = 796850
sha256     = 8b39571d258380ccb8ebae2f19466a6430399210c0dcdce540bf5f0f00f83440
```

---

## 7. Phase 9 Control Runtime

Phase 9 is **CLOSED / VERIFIED**.

Final source commit:

```text
d31035b41141c905dd56e21d339342f8988998e3
```

Final immutable control image:

```text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime@sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

Linux/amd64 manifest digest:

```text
sha256:80dccbe023c062dbd245ca3f334dca5e1dfa44e10362a2eeeb4caabf153e2fa5
```

Image config digest:

```text
sha256:11fe25ad746e9375e8b401d6831a62b2056d50840180924451cd8802a8857cc5
```

Runtime properties:

```text
platform        = linux/amd64
runtime user    = 10001:10001
kubectl         = v1.32.5
project root    = /data/spark/healthcare-data-platform
runtime context = in-cluster
```

The control image intentionally contains no Synthea, Java, Spark or Airflow runtime.

Spark processing remains on:

```text
spark:3.5.7-python3
```

---

## 8. Phase 9 Failure and Recovery

Initial failed root digest:

```text
sha256:9a94a36f5b393744e4ed2cca2f47b036c27c58797b7ca7e4b695787d74c034e6
```

This image must not be reused.

Diagnostic:

```text
runtime files readable   = 8
runtime files unreadable = 6
```

Root cause:

```text
Docker COPY --chmod=0644
```

created parent directories without execute/traverse permission.

The permanent image generator now normalizes runtime directories to:

```text
0755
```

Replacement runtime verification:

```text
runtime file count       = 14
runtime readable count   = 14
runtime unreadable count = 0
```

The replacement image passed on `worker02`.

---

## 9. Direct In-Cluster Lineage Resolution

TASK004 now supports:

```text
TASK004_RUNTIME_CONTEXT=manual
TASK004_RUNTIME_CONTEXT=in-cluster
```

In-cluster mode:

- executes the resolver directly inside the control Pod;
- receives S3 credentials via Kubernetes Secret injection;
- does not `kubectl exec` back into the Airflow scheduler;
- does not depend on runner01 files.

Phase 9 verified direct resolution for both `patients` and `encounters`.

---

## 10. Phase 10 STEP01 — Standalone Person Runtime

**PASS / VERIFIED.**

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

Driver placement:

```text
node       = worker02
node class = platform
```

Input:

```text
dataset = patients
rows    = 20
sha256  = f4e249d17302acd8ffd53b54e92808547fe58af329f26ede89c6c0f5c74203e8
```

Runtime result:

```text
SOURCE_ROWS              = 20
CANONICAL_ROWS           = 20
PROCESSING_READBACK_ROWS = 20
CANONICAL_CONTRACT       = PASS
PROCESSING_WRITE         = PASS
PROCESSING_READBACK      = PASS
POSTGRESQL_MUTATION      = NO
```

Processing output:

```text
s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=task004-p20-first-landing-20261011/entity=patient/run_id=task004-person-20261011T021241Z-2752601/work/normalized/data/
```

Successful temporary Kubernetes resources were cleaned:

```text
SparkApplication residual = NO
ConfigMap residual         = NO
Driver Pod residual        = NO
```

This was a real Spark execution, not render-only.

---

## 11. Still Open

### Standalone Visit runtime

Not yet executed.

Expected source:

```text
dataset    = encounters
rows       = 2459
size_bytes = 796850
sha256     = 8b39571d258380ccb8ebae2f19466a6430399210c0dcdce540bf5f0f00f83440
```

### Batch reconciliation

Not yet completed.

### Airflow orchestration

Not yet executed.

### Airflow RBAC

Additional narrow RBAC is still required and remains deferred until standalone Visit passes.

---

## 12. Next Development Sequence

```text
Standalone Visit runtime
  ↓
verify 2459 source rows
  ↓
verify Canonical Encounter
  ↓
verify Processing write/readback
  ↓
freeze standalone downstream checkpoint
  ↓
batch reconciliation
  ↓
Airflow DAG
  ↓
minimal RBAC
  ↓
Airflow end-to-end execution
```

---

## 13. Checkpoint Summary

```text
TASK004 overall                    = IN PROGRESS

Synthea generator                  = VERIFIED
Landing publication                = VERIFIED
Landing replay/conflict/recovery   = VERIFIED
Generic lineage resolver           = VERIFIED
Phase 9 control runtime            = CLOSED / VERIFIED
Standalone Person                  = PASS
Standalone Visit                   = NOT YET
Batch reconciliation               = NOT YET
Airflow orchestration              = NOT YET
PostgreSQL mutation in TASK004     = NO
```
