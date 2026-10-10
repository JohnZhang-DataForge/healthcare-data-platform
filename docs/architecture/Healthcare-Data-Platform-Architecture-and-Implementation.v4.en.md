# Healthcare Data Platform — Architecture & Implementation Baseline V4

> **Version: V4.0 — Consolidated Runtime & Orchestration Baseline**
> **Updated: 2026-10-10**
> **Status: Authoritative Master Design**
> **Repository:** `JohnZhang-DataForge/healthcare-data-platform`
> **Current environment:** Kubernetes + SeaweedFS(S3) + Airflow + Spark Operator/PySpark + PostgreSQL 17 / OMOP CDM 5.4.3 + GitHub
> **Planned extensions:** Azure Blob/ADLS Gen2, Microsoft Fabric, dbt-fabric, MLflow, Mirth/HL7, FHIR, GitHub Actions, Argo CD

---

## 0. Document Role and Version Relationship

This document becomes the authoritative project architecture and implementation baseline as of 2026-10-10.

It consolidates two previously separate design lines:

1. `Emory-Healthcare-Data-Platform-Architecture.v3.md`
   - dated 2026-10-05;
   - focused on the three-node Kubernetes platform, SeaweedFS, Airflow, Spark, PostgreSQL/OMOP, Mirth, and component boundaries;
   - remains a useful historical infrastructure baseline.
2. `Healthcare-Batch-ETL-Hybrid-Fabric-ML-Implementation-Design.zh-CN.v2.1.md`
   - dated 2026-10-08;
   - focused on Batch-first implementation, Canonical/Processed layers, OMOP, Airflow batch orchestration, and Azure/Fabric/ML roadmap;
   - newer by date, despite the lower version number because it belonged to a different document line.

Therefore V3 was not simply a newer replacement for V2.1. V4 merges both lines.

Historical documents remain in Git for design traceability.

---

## 1. V4 Executive Decisions

1. **Make the platform run end to end before adding every OMOP table.** The immediate priority moves from table-by-table expansion to Kubernetes/Airflow orchestration of the already proven Person + Visit pipeline using newly generated data.
2. **Synthea becomes a platform workload.** A dedicated `synthea-generator` image/Kubernetes Job generates a configurable synthetic population and publishes an immutable Landing batch.
3. **Use small reproducible batches for development.** Start with `population_size=20/50` and a fixed seed. Population size means patient count, not total row count across all CSVs.
4. **Data generation belongs inside the DAG.** The first real DAG starts with `Generate Synthea → Landing → Person → Visit → Reconcile` rather than assuming manually prepared CSV files.
5. **Use two project images first.** `healthcare-data-platform-synthea` and `healthcare-data-platform-runtime`. Continue using the verified Spark runtime initially; build a project-owned Spark image after the orchestration path is proven.
6. **TASK-003 is the reference implementation.** Future Condition, Procedure, Drug, Measurement and Observation work reuses its architecture rather than duplicating its code volume.
7. **Extract a reusable framework starting with Condition.** Canonical publication, Processed publication, stable IDs, materialization, reconciliation and evidence logic should become shared modules.
8. **Runtime evidence outranks plans.** Capabilities move from `PLANNED` to `VERIFIED` only when real execution evidence exists.
9. **Never blindly rerun a frozen batch.** Existing Person/Visit baselines are read-only verification targets. New Airflow testing uses a new batch.
10. **Documentation is an engineering asset.** Maintain bilingual master design, consolidated lessons, step-specific lessons and project skill rules in Git.

---

## 2. Current Platform Topology

| Node | Role | Responsibility | Main components |
|---|---|---|---|
| `master01` | control-plane | Kubernetes management | control plane, kubectl, Helm |
| `worker01` | storage | Data Lake / Landing | SeaweedFS Master/Filer/Volume/S3 |
| `worker02` | platform | Orchestration / Compute | Airflow 3.2.2, Spark Operator 2.5.2, dynamic Driver/Executor Pods |
| `worker03` | relational | OMOP relational serving | PostgreSQL 17, OMOP DB, Airflow metadata DB |
| `runner01` | control / CI runner | development, validation, future CI | Git, kubectl, helper tooling |

Principles:

- no primary data workload on the control plane;
- storage, orchestration/compute and relational serving stay separated;
- Spark runs through ephemeral SparkApplication driver/executor Pods;
- runner01 gradually becomes a control/CI runner instead of the application runtime host.

---

## 3. Storage and Databases

### 3.1 Storage Classes

- `local-path` for general lab components;
- `seaweed-local` for SeaweedFS on worker01;
- `postgres-local` for PostgreSQL on worker03;
- retained PV/PVC cleanup always requires explicit state verification.

### 3.2 SeaweedFS

SeaweedFS is the local S3-compatible Data Lake / Landing Zone.

Logical buckets:

```text
health-landing
health-processing
health-raw
health-processed
health-archive
postgres-backup
```

Layer meaning:

```text
Landing     = immutable source batch + manifest
Processing  = run-scoped workspace / DQ / rejects
Raw         = Canonical Parquet approved by Canonical Gate
Processed   = target/OMOP datasets approved by product gate
Archive     = historical support/archive area
Backup      = PostgreSQL backup
```

### 3.3 PostgreSQL / OMOP

PostgreSQL 17 runs on worker03.

```text
omop
  ├── cdm.*
  └── etl.*

airflow
  └── Airflow metadata
```

OMOP is the standardized healthcare research data model, not the orchestrator or compute engine.

---

## 4. Namespaces and Component Boundaries

| Namespace | Purpose |
|---|---|
| `dw-seaweedfs` | SeaweedFS / S3 |
| `dw-postgre` | PostgreSQL / OMOP |
| `dw-airflow` | Airflow |
| `dw-spark` | Spark Operator / SparkApplication |
| future `data-warehouse` | analytical serving such as ClickHouse |
| future `streaming` | Kafka/streaming only when required |

```text
SeaweedFS = Data Lake / Object Storage
Airflow   = Orchestration
Spark     = Compute / Transformation
Postgres  = Relational Serving
OMOP      = Healthcare Standard Data Model
Mirth     = HL7 Interface Engine (future)
Fabric    = Managed analytics/ML platform (future)
```

---

## 5. Verified Baseline as of 2026-10-10

| Capability | Status |
|---|---|
| Kubernetes multi-node platform | VERIFIED |
| SeaweedFS S3 + authenticated access | VERIFIED |
| PostgreSQL 17 persistence | VERIFIED |
| OMOP CDM 5.4.3 + vocabulary | VERIFIED |
| Airflow 3.2.2 / GitSync / UI / LocalExecutor | VERIFIED |
| Spark Operator 2.5.2 / Spark 3.5.7 lifecycle | VERIFIED |
| TASK-001 whole-batch Landing | VERIFIED |
| TASK-002 Person V2 | VERIFIED (`cdm.person=113`) |
| TASK-003 Encounter → Visit | VERIFIED |
| TASK-003 Processed Visit rows | 5799 |
| Visit stable ID mappings | 5799 |
| Visit ID range | 2..5800 |
| `cdm.visit_occurrence` | 5799 rows |
| Visit sequence | `5800|true` |
| TASK-003 implementation checkpoint | `373439c323c82388f559538204b1ba6348916fa0` |
| Full healthcare Batch DAG | PLANNED / NEXT |
| Synthea Generator Kubernetes Job | PLANNED / NEXT |
| Project runtime image | PLANNED / NEXT |
| Condition/Procedure/Drug/Measurement/Observation | PLANNED |
| Azure/Fabric/ML | PLANNED |
| Mirth/FHIR/HL7 | PLANNED |

TASK-003 established the first complete reference lifecycle:

```text
source
  ↓
canonical
  ↓
Raw
  ↓
Processed
  ↓
stable surrogate IDs
  ↓
OMOP CDM
  ↓
independent verification
```

---

## 6. Synthea Batch Scope and Remaining Core OMOP Tables

One Synthea export is one batch, not 18 unrelated batches.

| Source | Canonical | OMOP target | Status |
|---|---|---|---|
| `patients.csv` | patient | `person` | VERIFIED |
| `encounters.csv` | encounter | `visit_occurrence` | VERIFIED |
| `conditions.csv` | condition | `condition_occurrence` | NEXT |
| `procedures.csv` | procedure | `procedure_occurrence` | PLANNED |
| `medications.csv` | medication | `drug_exposure` | PLANNED |
| `observations.csv` | observation | `measurement` + `observation` | PLANNED |

Remaining core scope: **4 source domains and 5 OMOP target tables**.

Other Synthea files must still be represented and validated in the batch manifest, but may remain explicitly `DEFERRED` during the current MVP.

---

## 7. V4 Runtime Direction: Synthea as a Kubernetes Workload

### 7.1 Goal

Bring source generation inside the platform:

```text
Airflow DAG
    |
    v
Synthea Generator Job
    |
    v
Generated Synthea CSV batch
    |
    v
Landing Publisher
    |
    v
SeaweedFS health-landing
    |
    v
Batch Intake Gate
    |
    v
Person → Visit → Reconcile
```

### 7.2 Synthea Generator Image

Recommended image:

```text
healthcare-data-platform-synthea:<git-sha>
```

Initial parameters:

```text
population_size=20|50
seed=<fixed debug seed>
state=Georgia
city=Atlanta
source_version=v3.3.0
export_csv=true
```

`population_size=50` means 50 synthetic patients. Related encounter/condition/procedure/medication/observation row counts are produced by the longitudinal simulation and are not expected to equal 50.

Start with a fixed seed for deterministic debugging. Add random population size/seed, scenario configuration and FHIR export only after the path is stable.

### 7.3 Landing Publication Contract

The generation/publication workload must:

1. generate CSV files;
2. verify the expected file set;
3. verify non-empty files and headers;
4. compute SHA256;
5. allocate a batch identity;
6. upload `payload/csv/*`;
7. publish the manifest **last**;
8. expose `batch_id` and `manifest_uri` to Airflow.

Expected task output:

```text
SYNTHEA_GENERATION=PASS
POPULATION_SIZE=50
LANDING_PUBLICATION=PASS
BATCH_ID=...
MANIFEST_URI=s3://...
```

---

## 8. Batch Identity vs Pipeline Run Identity

```text
batch_id
= identity of the immutable source data

pipeline_run_id
= identity of one processing attempt/run
```

A batch may have multiple validation or processing runs.

Example:

```text
batch_id=synthea-20261010-pop50-seed10001
pipeline_run_id=synthea-omop-20261010T210000Z-<suffix>
```

Frozen historical batches are not used for blind write retries. Demonstration/replay uses read-only verification or a newly generated batch.

---

## 9. Container Image Strategy

### 9.1 First Two Project Images

#### A. `healthcare-data-platform-synthea`

Contains:

- Java/Synthea runtime;
- parameterized synthetic population generation;
- batch output preparation;
- optionally Landing publication logic.

#### B. `healthcare-data-platform-runtime`

Contains:

- Python utilities;
- contracts;
- batch/manifest validation;
- DQ;
- control and mapping utilities;
- ID reconciliation/allocation;
- database loading/materialization utilities;
- final reconciliation;
- evidence/hash helpers.

### 9.2 Spark Image

Short term: continue using the already proven Spark 3.5.7 runtime and current code-distribution method.

Medium term:

```text
healthcare-data-platform-spark:<git-sha>
```

The image should contain stable Spark/Python runtime, `spark/apps/*`, shared libraries and required JDBC/S3A/JAR dependencies.

Production-like deployments should prefer immutable image digests.

### 9.3 What Never Goes Into Images

Do not bake:

- S3 credentials;
- PostgreSQL passwords;
- GitHub tokens;
- Azure credentials;
- kubeconfig;
- batch IDs / run IDs;
- environment-specific endpoints.

Use Kubernetes Secrets, Config and runtime parameters.

---

## 10. First Runnable Airflow DAG

MVP:

```text
Generate Synthea Batch
        |
        v
Publish / Verify Landing
        |
        v
Process Person
        |
        v
Verify Person
        |
        v
Process Encounter / Visit
        |
        v
Verify Visit
        |
        v
Batch Reconcile
        |
        v
CORE_PARTIAL_COMPLETE
```

The first objective is not to finish every remaining OMOP table. It is to prove that:

- Airflow submits real Kubernetes workloads;
- source generation happens in-cluster;
- a new batch reaches Landing automatically;
- Person and Visit process the new batch;
- every task has observable PASS/FAIL state;
- final reconciliation closes the DAG.

Future topology:

```text
                         ┌─ Condition ──────────┐
                         |
Generate → Person → Visit ┼─ Procedure ──────────┼→ Reconcile
                         |
                         ├─ Drug ───────────────┤
                         |
                         └─ Measurement/Obs ────┘
```

---

## 11. Airflow Parameters and Dependency Rules

Recommended DAG parameters:

```text
population_size
seed
state
city
source_version
batch_id (optional if generate_new_batch=true)
pipeline_run_id
canonical_version
product_version=5.4.3
generate_new_batch=true|false
```

Rules:

- never hard-code historical counts such as 113/5799 into generic DAG logic;
- pass lightweight identities/URIs/status between tasks, not large files;
- parallelize Raw processing only when dependencies allow it;
- OMOP dependency order is `person → visit → clinical facts`;
- a failed core task blocks final COMPLETE;
- preserve successful immutable artifacts for recovery;
- retain CLI runners as debugging/regression interfaces.

---

## 12. Development Strategy After TASK-003

TASK-003 is a reference implementation, not a template for copying thousands of lines per entity.

### 12.1 Condition

Condition has two goals:

1. deliver `condition_occurrence`;
2. extract reusable framework from TASK-003.

Entity-specific logic should be limited to:

```text
source contract
business key
concept mapping
target columns
FK rules
DQ rules
```

Generic mechanics should move into shared components:

```text
canonical publish
processed planning/publication
reservation/write intent/permit
evidence/hash
ID reconciliation/allocation
CDM staging/materialization
post-commit reconciliation
```

### 12.2 Procedure

By Procedure, implementation should become configuration-driven. If another large independent shell stack is required, the abstraction is insufficient.

### 12.3 Drug and Observation

- `drug_exposure`: medication vocabulary/domain mapping is the main challenge;
- `observations.csv`: requires semantic routing to `measurement` vs `observation` and careful handling of value/type/unit/concept/domain.

---

## 13. Data Layers and Publish Boundaries

### Landing

Immutable source batch:

```text
s3://health-landing/source=synthea/source_version=<v>/ingest_date=<UTC>/batch_id=<B>/
  manifest.json
  payload/csv/*.csv
```

Manifest is published last.

### Processing

Run-scoped workspace:

```text
s3://health-processing/source=synthea/batch_id=<B>/run_id=<R>/...
```

Not a downstream consumption layer.

### Canonical Raw

```text
s3://health-raw/canonical_version=v1/entity=<entity>/source=synthea/.../run_id=<R>/
  data/
  dq/result.json
  manifest.json
```

Only data referenced by an APPROVED manifest is consumable downstream.

### Processed

Organized by target dataset with immutable runs and exact lineage.

### CDM

Final relational authority.

---

## 14. DQ, Idempotency and Reconciliation Standard

Every persisted dataset should expose:

- row count;
- unique business-key count;
- contract version;
- source lineage;
- SHA256/fingerprint;
- required-field violations;
- FK violations;
- domain/concept checks.

High-risk mutation lifecycle:

```text
read-only preflight
  ↓
mutation contract
  ↓
rehearsal where practical
  ↓
one controlled execution
  ↓
independent reconciliation
  ↓
canonical freeze
```

If commit state is uncertain: **no blind retry**. Open a new read-only session and reconcile persistent state.

Stable IDs do not need to be gapless. Sequence gaps are legal; automatic sequence rewind is forbidden.

---

## 15. Runtime vs Git Boundary

Git contains:

```text
canonical source
contracts
tests
manifests
docs
SQL
permanent scripts
```

Normally excluded:

```text
runtime/
raw healthcare files
Parquet outputs
credentials
kubeconfig
temp_shell/
local.env
```

> Git explains how the system works; runtime explains what happened in a specific run.

---

## 16. Git / CI / Delivery Roadmap

Short term:

```text
local development
→ tests
→ Git checkpoint
→ Airflow GitSync / manifests
```

Next:

```text
Git commit
  ↓
unit + contract tests
  ↓
build image
  ↓
security scan
  ↓
push GHCR
  ↓
record immutable digest
  ↓
Airflow/Kubernetes execute
```

Argo CD/GitOps comes later and must not block the runtime MVP.

---

## 17. Azure / Fabric / ML Phase II

Phase II must not block the local Batch MVP.

Goals:

1. validate S3 + Azure Blob/ADLS Gen2 dual-target landing;
2. keep PostgreSQL OMOP as the local CDM authority;
3. export selected OMOP tables incrementally to Azure/OneLake Delta;
4. build Fabric Lakehouse/Notebook flows;
5. create dbt-fabric Gold models;
6. expose SQL through Fabric Warehouse;
7. add MLflow batch feature/scoring lifecycle.

Azure/Fabric features remain `PLANNED` until real execution evidence exists.

---

## 18. FHIR / HL7 / Mirth Phase

After the Synthea CSV batch path is stable:

```text
HL7 v2 / MLLP
  ↓
Mirth Connect
  ↓
Landing
  ↓
Airflow
  ↓
Spark
  ↓
Canonical / OMOP
```

FHIR R4:

```text
FHIR Patient/Encounter/Condition/Observation
  ↓
source-specific adapter
  ↓
shared Canonical / OMOP path
```

Keeping Source Adapters separate from OMOP Mappers allows multiple source protocols to share the downstream transformation framework.

---

## 19. Documentation Governance

### 19.1 Master Design

Maintain bilingual authoritative design:

```text
docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md
docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md
```

Keep V3/V2.1 historical documents for traceability.

### 19.2 Development Lessons

Consolidated document:

```text
docs/runbooks/development-lessons.md
```

Step-specific source records:

```text
docs/runbooks/development-lessons-taskNNN-stepXX.md
```

Periodically promote general lessons into `development-lessons.md`, while preserving step-specific files.

### 19.3 Project Skill

```text
docs/skill/SKILL.md
```

Continuously records validated project development rules, shell delivery methods, PASS/freeze rules, mutation/recovery rules, Git/documentation rules and lessons-maintenance policy.

---

## 20. Current Priority Roadmap

### Phase A — Documentation & Git Baseline

- V4 bilingual master design;
- consolidated lessons;
- normalized step lesson naming;
- updated project skill;
- Git checkpoint.

### Phase B — Synthea Runtime

- build `healthcare-data-platform-synthea` image;
- parameterized Kubernetes Job generating 20/50 patients;
- immutable Landing publication;
- manifest/checksum verification.

### Phase C — Runtime Image

- build `healthcare-data-platform-runtime`;
- package validation/DQ/ID/materialization/reconciliation utilities;
- keep CLI debugging interfaces.

### Phase D — Airflow Person + Visit MVP

- orchestrate Synthea generation;
- Landing intake;
- Person pipeline;
- Visit pipeline;
- final reconciliation;
- verify with a **new batch**.

### Phase E — Clinical Facts

```text
Condition
→ Procedure
→ Drug
→ Measurement / Observation
```

Extract shared framework during Condition.

### Phase F — Hybrid / Healthcare Integration

- Azure/Fabric/ML;
- Mirth/HL7;
- FHIR;
- CI/CD/GitOps;
- ATLAS/WebAPI / dbt / research workflows.

---

## 21. Final Architecture Goal

The goal is not the number of installed products. It is an explainable, testable, replayable and extensible healthcare data engineering path:

```text
Synthetic / Healthcare Sources
        ↓
Kubernetes Source Jobs / Interfaces
        ↓
Immutable Landing Batch
        ↓
Airflow Orchestration
        ↓
Spark / Runtime Jobs
        ↓
Canonical Raw
        ↓
OMOP Processed
        ↓
Stable IDs + Transactional CDM
        ↓
Reconciliation / Evidence
        ↓
Analytics / Fabric / Research / ML
```

**The short-term V4 success criterion is not to finish every table first; it is to make this pipeline actually run.**
