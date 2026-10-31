---
status: adopted-final-development-design
decision_date: 2026-10-31
implementation_status: not-started
---

# ADR 2026-10-31 — Fabric-native Notebook, Pipeline, Environment and Shared Engine

**Final and authoritative source/execution design** for Healthcare Fabric. This supersedes all earlier standalone `azure-fabric/ingestion/`, `runtime/`, `libraries/healthcare-fabric-io/`, and second `healthcare_fabric` wheel proposals. The [2026-10-30 Medallion ADR](FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) remains authoritative for Bronze/Silver/Gold semantics, clinical contracts and batch publication. No actual Fabric resource or application source has been created by this design decision.

## Required owners and execution responsibilities

| Component | Role | Source / Item |
| --- | --- | --- |
| **Fabric Pipeline — mandatory** | cross-job dependencies, schedule, parameters, retry/failure branch; replaces Airflow's orchestration role | native `pl_fhir_ingest.DataPipeline` Item |
| **Fabric Notebook — mandatory** | real **visible** PySpark ETL: source verification, read, DataFrame transformation, DQ, Delta persistence, independent readback, evidence and output status | native `nb_fhir_ingest.Notebook` Item |
| **Shared Data Engine — only new Python package** | FHIR/CSV/HL7 adapters as approved, Canonical, OMOP Mapper, identity-plan, DQ, reconciliation | `shared-data-engine/src/healthcare_data_engine/` |
| **Fabric Environment** | install **version-pinned Shared Wheel** and runtime dependencies; explicit Publish and effective-version verification | native `env_healthcare.Environment` Item |
| Fabric native I/O | Pipeline Copy, OneLake Shortcut, Notebook `spark.read`/DataFrame Delta writes | Fabric platform APIs, **not a new I/O framework** |
| Existing infrastructure | workspace/lakehouse/connection/permissions | existing `azure-fabric/infra-terraform/`; preserve state |
| Existing Local DP | Airflow, Spark, S3/SeaweedFS, PG and Contract authority | existing `local-data-platform/`; leave paths unchanged |

**Important**: Pipeline handles *workflow orchestration*; Notebook performs the *single Spark application's ETL*. Shared handles *platform-neutral domain algorithms*. A generic Fabric I/O wrapper class or second wheel is **not** an initial prerequisite. Manifest SHA256, quarantine, replay/approval, PK/FK and two-table independent readback are still required correctness behaviors and do not disappear merely because the platform uses native reads/writes.

## Chosen Git source and Fabric Workspace mapping

~~~text
healthcare-data-platform/
├── shared-data-engine/
│   ├── AGENTS.md                              # existing
│   ├── pyproject.toml                         # planned single shared wheel
│   ├── src/healthcare_data_engine/            # adapters, canonical, omop, DQ, identity
│   └── tests/                                 # synthetic and cross-runtime tests
├── local-data-platform/                       # existing; no mass migration
└── azure-fabric/
    ├── workspaces/
    │   ├── healthcare-omop/                   # intended Fabric Git Folder root
    │   │   ├── notebooks/                    # our chosen Fabric UI folder
    │   │   │   └── ingestion/
    │   │   │       └── nb_fhir_ingest.Notebook/
    │   │   │           ├── .platform
    │   │   │           └── notebook-content.py
    │   │   ├── pipelines/
    │   │   │   └── pl_fhir_ingest.DataPipeline/
    │   │   │       ├── .platform
    │   │   │       └── pipeline-content.json
    │   │   └── environments/
    │   │       └── env_healthcare.Environment/  # files from actual Fabric export
    │   └── johnzhang-test/                    # existing smoke, untouched
    ├── infra-terraform/                       # existing modules/state, untouched
    ├── deployment/                            # existing scoped publishing tools
    └── openlineage/                           # existing integration
~~~

**All business Native Items above are FUTURE items.** Current `healthcare-omop` source tree only contains placeholders. Fabric Git Integration must use `azure-fabric/workspaces/healthcare-omop/` as the selected repository folder and verify actual workspace branch, UI folders and current item inventory *before* sync. `notebooks/`, `pipelines/`, `environments/` are our **chosen taxonomy**, not a Microsoft-mandated type hierarchy. They correspond to real Workspace UI folders, while `*.Notebook/`, `*.DataPipeline/`, `*.Environment/` are Fabric native Item definitions. Use real, exported `.platform` IDs, never copy Smoke logicalIds. Ordinary `.py` files do **not** become Notebook Items by being in Git. Lakehouse Files/Tables data is separate from Git.

## Notebook and Pipeline implementation contract

Notebook must visibly execute these distinct phases (one Notebook for initial Patient/Encounter batch; split later only at demonstrated recovery boundaries):

1. Receive Pipeline parameters; verify frozen manifest/source identity and SHA256; reject mismatched bytes or conflicting request versions.
2. Access verified raw FHIR via approved Shortcut/Copy and Spark native reader; preserve Bronze source receipt.
3. Import **published version** of `healthcare_data_engine`; run FHIR R4 Patient/Encounter normalization, Canonical contract and DQ; quarantine invalid resource rows.
4. Stage/write Silver Canonical Delta using native Spark/Delta. Enforce NEW_ONLY replay semantics; never blind append duplicate versions.
5. Independently read back both Patient and Encounter, verify PK/FK/counts/versions, then publish Silver APPROVED evidence; return explicit result to Pipeline.

Pipeline handles activity dependencies, retries, scheduling, alerts; Pipeline SUCCESS is not Silver APPROVED. Gold COMMITTED remains subject to separate Warehouse/Delta transaction POC and independent readback. Shared Python owns mappings, not platform I/O or orchestration; Notebook must not copy 900-line Mapper sources.

## Shared Wheel and Environment are different things

~~~text
shared-data-engine/ (editable Python source)
   → CI tests and build one healthcare-data-engine wheel
   → immutable wheel version + SHA256
   → controlled Environment custom-library update
   → explicit Environment Publish and effective-version readback
   → Notebook imports healthcare_data_engine
~~~

**Never map Shared source directly into the Environment Git Item.** Fabric Environment represents configured binary dependencies/runtime settings. It may track a reviewed custom-wheel release via native Git Item, or use controlled API upload of a pinned CI artifact with Git-state reconciliation; the first accepted rollout must select **one** update writer and validate actual Fabric export/Git sync to avoid drift. Do not commit every transient wheel; don't rely on Notebook `%pip install` for reproducible runs. Local and Fabric independently pin versions after cross-runtime testing.

## Gates and ownership

- Existing Local Canonical/OMOP Contracts at `local-data-platform/spark/contracts/` remain the only manually maintained authority until separate approved migration.
- Native Notebook/Pipeline/Environment Item definitions use Fabric Git/fabric-cicd; existing Terraform owns Workspace/Lakehouse/Connection, **not simultaneously the same Item**. Current Trial publisher remains trial-only.
- P0: latest Main/PR check, extend Shared/Native Item CODE-map and forbidden-import negative tests. P1: one Shared Wheel and synthetic FHIR/Contract offline tests. P2: real native Item export, Environment publish and build/readback verification, authorized separately. P3: verified Fabric Bronze/Silver small then 100-synthetic-batch end-to-end. P4: Gold controlled transaction POC.
- Document merge authorizes **developer guidance only**, not Terraform apply, actual Fabric sync/publish, paid capacity, Blob/K8s/PG writes or production batch replay.

Microsoft capability documentation: [Fabric Git integration](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/intro-to-git-integration), [Git item formats](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format), [Notebook source control](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment), [Environment Git/pipelines](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline), [Environment libraries](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-manage-library).
