# Healthcare Data Platform

A clinical data engineering project built with Kubernetes, PySpark, Apache Airflow, PostgreSQL, and Microsoft Fabric.

The project starts with a straightforward problem: clinical data arrives in different formats, while analysts need consistent, traceable records they can query. I built a working local pipeline that takes synthetic patient and encounter data from source files to **OMOP CDM 5.4** tables. I am extending it with FHIR/HL7 source integration and an Azure/Microsoft Fabric analytics layer.

This is an independent engineering project using **synthetic data only**. It is not connected to a hospital or a production EHR, and it does not contain patient information.

## The platform at a glance

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Source and ingestion | Synthea, CSV; FHIR R4 and HL7 v2 adapters in development | Generate or receive clinical records; preserve source identity and batch metadata |
| Landing | SeaweedFS (S3-compatible); Azure Blob for cloud integration | Keep source batches and manifests separate from transformed data |
| Orchestration | Apache Airflow | Select approved batches, coordinate Spark jobs, handle retries and checkpoints |
| Processing | Apache Spark / PySpark, Python, SQL | Validate, normalize, map Patient/Encounter records to OMOP, and reconcile results |
| Clinical data store | PostgreSQL 17, OMOP CDM 5.4 | Persist standardized Person and Visit Occurrence records through a guarded writer |
| Lineage | OpenLineage, Marquez, PostgreSQL 14 | Track DAG runs, Spark jobs, datasets, and column mappings |
| Cloud analytics | Azure Blob, Microsoft Fabric, OneLake Lakehouse | Provisioned foundation; end-to-end analytical ingestion is still in development |
| Delivery | Kubernetes, Terraform, GitHub Actions, GHCR | Build images, provision infrastructure, run checks, and keep changes reproducible |

### Data flow

The solid path is the local pipeline that has been exercised end to end. Dashed paths show work that is not yet accepted as a complete data flow.

```mermaid
flowchart LR
    S["Synthea<br/>synthetic CSV"] --> L["SeaweedFS / S3<br/>batch + manifest"]
    L --> A["Airflow<br/>batch selection"]
    A --> P["PySpark<br/>validation and OMOP mapping"]
    P --> R["Reconciliation<br/>and guarded writer"]
    R --> D[("PostgreSQL<br/>OMOP CDM 5.4")]

    A -. "run metadata" .-> M["OpenLineage / Marquez"]
    P -. "dataset and column lineage" .-> M

    F["FHIR R4 producer<br/>component work"] --> B["Azure Blob<br/>publisher tested separately"]
    H["HL7 v2 / OIE<br/>in development"] -.-> B
    D -. "consistent export planned" .-> C[("Fabric OneLake<br/>Lakehouse")]
    B -. "Fabric pipeline/notebook planned" .-> C
```

The local components run on a multi-node Kubernetes cluster. The producer and consumer are separate: generating a file does not automatically authorize a database write. A batch is identified by its manifest and checksum, and the consumer processes an approved snapshot rather than whatever happens to be newest in storage.

## What is working

**A real Person/Visit pipeline.** Synthea publishes synthetic source batches to S3-compatible storage. Airflow runs PySpark transformations for Patient and Encounter records, maps them to OMOP **Person** and **Visit Occurrence**, checks the resulting data, and hands it to a controlled PostgreSQL writer. Source IDs and batch IDs remain available for traceability.

**Retry-safe database writes.** The pipeline checks batch identity and prior completion before committing. Reconciliation and database readback are separate from orchestration status: a successful Airflow task does not, by itself, prove the data was committed. Running an already-completed batch follows a skip path rather than inserting the same records again.

**Run and data lineage.** Airflow and Spark emit OpenLineage metadata to Marquez. On the internal network, the Marquez UI has displayed real Patient/Encounter processing datasets and field-level mappings. The remaining Spark RDD action lifecycle gap is documented rather than hidden.

**Repeatable engineering work.** Components are packaged as containers and deployed on Kubernetes. GitHub Actions builds and tests the images, while Terraform manages the Azure/Fabric infrastructure. Code, contracts, workflow definitions, and operational notes are kept in the repository.

### A batch that can be checked

On October 25, 2026, a new synthetic batch committed **100 Person** and **15,742 Visit Occurrence** rows. An independent PostgreSQL readback confirmed the commit. Running the same batch again skipped the Spark processing and writer, with no further database changes.

- [Original batch execution](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) — the workflow ultimately reported failure in a *post-commit evidence step*, not in the database transaction.
- [Independent PostgreSQL and lineage verification](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539).
- [Same-batch skip and unchanged-data verification](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676).
- [Marquez walkthrough and known lineage limits](documents/systems/platform-portal/marquez/SHOWCASE-RUNBOOK.md).

These are results from specific test runs, not production availability or performance claims. More results and their scope are recorded in the [project status](documents/engineering/status/PROJECT-STATUS.md).

## Design choices

### Standardize the clinical model, not just the file format

CSV, FHIR, and HL7 have different structures and identifiers. The target is a consistent OMOP model that keeps source references and supports SQL-based analysis. The current accepted mappings cover **Person** and **Visit Occurrence**; the remaining OMOP domains and the complete multi-source ingestion path are future work.

### Check data after it lands

Schema checks, manifests, source-to-target reconciliation, and durable readback answer different questions. Keeping those checks separate makes failures easier to isolate and prevents a green scheduler status from masking missing data.

### Preserve history and make retries predictable

Immutable source batches, explicit batch selection, guarded commits, and a completion ledger make a failed or repeated run easier to investigate. A retry should not silently change the identity of its source data or duplicate a prior commit.

### Keep security and governance in the design

This repository uses generated records, not PHI. It explores practices that matter in governed healthcare environments: separate service identities, controlled storage access, source metadata, lineage, and documented data contracts. It does **not** claim HIPAA certification or production security validation.

### Keep Fabric deployment separate from Fabric data ingestion

Terraform has provisioned and verified the Azure/Fabric foundation, including workspace, Lakehouse, identity/access configuration, and a Blob connection. Fabric pipelines/notebooks and the full **OMOP → Azure Blob → OneLake** analytical flow have **not** passed end-to-end acceptance. That work, along with FHIR/HL7 ingestion, is the next stage.

## Where to start in the code

| Interested in | Start here |
| --- | --- |
| System design and pipeline boundaries | [System overview](documents/architecture/SYSTEM-OVERVIEW.md) · [data flow](documents/architecture/DATA-FLOW.md) |
| Ingestion, Airflow, Spark, and OMOP components | [Data platform guide](documents/systems/data-platform/README.md) · [source tree](local-data-platform/) |
| The working batch consumer | [Airflow DAG](local-data-platform/airflow/dags/new_only_omop_consumer.py) |
| Transformations and database writing | [Spark code map](documents/systems/data-platform/spark/CODE.md) · [OMOP code map](documents/systems/data-platform/omop/CODE.md) |
| Lineage and the internal viewer | [Platform Portal](documents/systems/platform-portal/README.md) · [Marquez walkthrough](documents/systems/platform-portal/marquez/SHOWCASE-RUNBOOK.md) |
| Azure and Microsoft Fabric | [Fabric system guide](documents/systems/azure-fabric/README.md) · [Terraform architecture](documents/systems/azure-fabric/infra-terraform/ARCHITECTURE.md) |
| Builds, tests, and ongoing status | [GitHub Actions](.github/workflows/) · [project status](documents/engineering/status/PROJECT-STATUS.md) |

For detailed design decisions, testing evidence, and operations, see the [documentation index](documents/README.md). Contributors and coding agents should begin with [AGENTS.md](AGENTS.md).

---

*Independent project · Synthetic clinical data · Local OMOP processing verified; cross-source and Fabric analytical processing still in progress.*
