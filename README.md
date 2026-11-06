# Healthcare Data Platform

**A working vertical slice of a unified data platform — from source-specific ingestion to trusted, traceable data.**

Different systems rarely agree on schemas, identifiers, or delivery formats. The engineering challenge is not just moving their data into one place; it is preserving where it came from, applying consistent rules, detecting bad or incomplete loads, and making the results safe to reuse.

This independent project tackles those problems with synthetic healthcare data. It has a **verified local CSV-to-OMOP pipeline**, working Airflow/Spark lineage, and separately developing FHIR R4, HL7 v2, and Microsoft Fabric integrations. It is an engineering lab, not a hospital integration or a production EHR system.

> **[Explore the live data lineage viewer](https://lineage.johnzhang-dataforge.site)** — Inspect real Spark jobs, upstream/downstream datasets, and Patient field mappings in Marquez. The self-hosted demo may be temporarily unavailable.

## Browse the repository (human-first)

The source tree is organized by **system and function**, not by development task number. [Full directory guide and legacy migration status](documents/engineering/development/REPOSITORY-STRUCTURE-AND-HUMAN-NAVIGATION.md).

| Folder | What you find there | Human-readable map |
| --- | --- | --- |
| [`local-data-platform/`](local-data-platform/) | Existing Local Synthea, Airflow, Spark and OMOP workflows; historical `taskNNN/` paths still have live consumers | [Local components](documents/systems/data-platform/README.md) |
| [`azure-fabric/`](azure-fabric/) | Fabric-native Items, Writer business code, deployment SQL/config and Terraform | [Fabric components](documents/systems/azure-fabric/README.md) |
| [`platform-portal/`](platform-portal/) | Marquez, OpenLineage, public viewer and metadata storage | [Portal components](documents/systems/platform-portal/README.md) |
| [`shared-data-engine/`](shared-data-engine/) | One portable Python library and scoped Agent instructions | [Shared Engine](documents/systems/data-platform/shared-engine/README.md) |
| [`documents/`](documents/) | Canonical architecture, component README/CODE and runbooks | [Docs index](documents/README.md) |
| [`openspec/`](openspec/) | Adopted specs, active changes, archived accepted history | [Change lifecycle](documents/engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md) |
| [`.github/`](.github/) | Workflows and centralized quality/test assets | [Developer CODE map](documents/engineering/development/CODE.md) |

The Local DP task-named directories are **operational compatibility paths**, not preferred new source organization. They are being assessed by function and consumer dependency before any physical migration. New code uses descriptive component names.

## The platform problem

A new source system should not require a completely new pipeline. But a shared ingestion framework also cannot assume that CSV, FHIR, HL7, and future enterprise feeds have the same structure or semantics.

I designed the pipeline around a few practical questions:

| Engineering question | Design response |
| --- | --- |
| **How do we onboard another source?** | Separate format-specific producers/adapters from a common landing, batch identity, validation, and processing contract. |
| **How do different source records become consistent?** | Normalize source records into a canonical clinical representation, then map them to domain-standard OMOP tables while retaining source references. |
| **How do we know a load is trustworthy?** | Require explicit batch selection, validation, reconciliation, and database readback rather than trusting an orchestrator's green status. |
| **What happens after a failed or repeated run?** | Use batch identity, guarded commits, completion tracking, and a tested same-batch skip path to avoid duplicate writes. |
| **Can someone explain a number or field later?** | Capture job, dataset, run, and column lineage with OpenLineage and Marquez. |

The reusable part is **source onboarding, provenance, validation, reconciliation, and observability**. OMOP is the target model for this *clinical* example—not a universal model for HR, finance, student, or research administration data. Other domains would reuse the platform patterns with their own models and business rules.

## Canonical-first shared processing (approved architecture)

The [Medallion Canonical ADR](documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) fixes the long-term design: **source-specific CSV/FHIR/HL7 adapters → one canonical Patient/Encounter contract → one portable OMOP mapping, DQ, identity-planning and reconciliation engine**. Data sources supply independently reviewed code-to-Concept profiles; the Local PostgreSQL and Fabric Warehouse publishers remain platform-specific. The single `healthcare_data_engine` Wheel 0.1.3 has FHIR/Canonical/OMOP Candidate code and passed isolated Fabric import, but the **Local production mapper has not yet been fully migrated to it**. Fabric's synthetic FHIR Approved Silver milestone (100 Patient / 5,918 Encounter) is physically accepted; Fabric clinical Candidate/Gold COMMIT and end-to-end pipeline are not. The separate Local PG→Fabric analytical snapshot route remains a future product. [Current data flow](documents/architecture/DATA-FLOW.md).

## Architecture: different sources, common Canonical contract

```mermaid
flowchart TB
    subgraph LOCAL["Local CSV path — verified PG17 COMMIT"]
        CSV["Synthea CSV"] --> S3["SeaweedFS + immutable manifest"]
        S3 --> AF["Airflow batch gate"] --> LSP["Local Spark adapter / Canonical / legacy OMOP mapping"]
        LSP --> PGW["PG guarded Writer"] --> PG[("PostgreSQL OMOP Person / Visit")]
    end

    subgraph FABRIC["Fabric FHIR R4 path — approved Silver; Gold still open"]
        FHIR["FHIR R4 source"] --> BLOB["Azure Blob manifest / source SHA"]
        BLOB --> NB["Native Fabric Notebook / Shared FHIR adapter"]
        NB --> SILVER[("G4 Canonical Silver Delta — approved / read back")]
        SILVER -. "G5 Concept/Identity/Gold not yet committed" .-> CAND["OMOP Candidate / Warehouse Writer"] 
        CAND -. "not yet accepted" .-> DW[("Fabric OMOP Gold")]
    end

    subgraph SHARED["Shared business architecture — single code owner"]
        CONTRACT["ONE Canonical Patient/Encounter v1 Contract"]
        ENGINE["healthcare_data_engine: post-Canonical Mapper / DQ / Reconciliation"]
        CONTRACT --> ENGINE
    end

    LSP -. "contract compliant; legacy Local implementation" .-> CONTRACT
    NB -. "same frozen contract" .-> CONTRACT
    AF -. "Airflow event metadata" .-> LINEAGE["OpenLineage / Marquez"]
    LSP -. "Spark event metadata" .-> LINEAGE
    HL7["HL7 v2 / OIE — future shared Adapter"] -. "future Canonical integration" .-> CONTRACT
```

**Reading the diagram:** Solid arrows are established local or Fabric Bronze/Silver component flows; dotted arrows identify unaccepted Fabric Gold, future HL7 integration, metadata, or logical contract relationships—not proof of a common deployed runtime. Source-specific adapters converge on a single *contract*, and post-Canonical business logic belongs to the shared code owner. The verified Local path retains its existing mapper until equivalence-tested incremental migration; no second Fabric business engine or cross-database SQL Writer is authorized. For exact stage acceptance see [Data Flow](documents/architecture/DATA-FLOW.md) and [current E2E tasks](openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md).

## What has been demonstrated

| Capability | Verified result |
| --- | --- |
| **End-to-end clinical processing** | Synthea source data through S3-compatible landing, Airflow, PySpark, reconciliation, and OMOP **Person / Visit Occurrence** writes. |
| **Durable data quality checks** | A fresh October 25, 2026 batch committed **100 Person** and **15,742 Visit Occurrence** rows, confirmed by an independent PostgreSQL readback. |
| **Safe retries** | Reprocessing the same completed batch followed the skip path, with no further database changes. |
| **Real lineage** | The public Marquez UI has shown Patient and Encounter table-level paths, plus six real Patient column mappings. |
| **Repeatable infrastructure** | Kubernetes workloads, container builds, GitHub Actions checks, and Terraform-managed Azure/Fabric infrastructure. |

### Inspect a transformation, not a slide

The live viewer shows the actual Synthea → canonical Patient lineage observed in the Spark pipeline. For example:

| Source field | Canonical field |
| --- | --- |
| `BIRTHDATE` | `birth_date` |
| `GENDER` | `gender_code` |
| `RACE` | `race_code` |
| `ETHNICITY` | `ethnicity_code` |
| `Id` | `source_record_id` |
| `DEATHDATE` | `death_date` |

**[Open the interactive lineage viewer](https://lineage.johnzhang-dataforge.site)** to explore the wider job/dataset relationships. It currently uses the native Marquez UI; a separate public-only UI build and fuller public access/security review remain open. These visualizations are evidence of observed business-level lineage, not a claim that every underlying Spark RDD lifecycle event is complete.

## How I would extend this to more sources

The goal is to keep the shared controls stable while allowing each source to have its own adapter and domain mapping.

1. **Define the source contract.** Record the producer/feed identity, format and schema expectations, batch identity, checksums, and source-to-target mapping rules.
2. **Land before transforming.** Keep the source payload and its metadata separate from normalized and curated datasets; detect missing or unexpected inputs before scheduling downstream work.
3. **Reuse the processing pattern.** Adapt FHIR resources or HL7 messages into an approved canonical representation, then apply domain-specific transformations and quality checks. The current end-to-end implementation covers the CSV-based clinical path.
4. **Publish only validated results.** Reconcile what was received and written, preserve source identifiers, and make reruns predictable.
5. **Make every handoff observable.** Carry dataset and run identity through orchestration and Spark, so investigators can trace unexpected output back to inputs and transformations.

This approach is deliberately not tied to one message standard or one processing runtime. It demonstrates a platform *pattern* using healthcare data, while leaving room for other business domains and their distinct models.

## Microsoft Fabric and the next integration milestones

The Azure/Fabric foundation is provisioned with Terraform, including a Fabric workspace and OneLake Lakehouse. Azure Blob publishing has been exercised separately. **A complete FHIR/HL7 → Fabric Notebook/Pipeline → curated OneLake load has not yet passed end-to-end acceptance.**

The next milestones are to complete the vetted FHIR-to-OMOP Concept Mapping Profile, durable Identity/Gold transaction and independently verified Candidate/Gold/Pipeline replay, then gradually migrate Local pure transformations to the same Shared Engine. New CSV/HL7 Fabric adapters and the separate PG snapshot export product are later, individually scoped work. Data quality, lineage, replay behavior, and evidence of durable writes will remain acceptance criteria—not optional reporting features.

The project uses **synthetic records only**. It does not contain real patient data, and it makes no HIPAA certification, institution-wide production-readiness, or always-on availability claim.

## Explore the source code

These links go directly to implementation and build locations.

| Component | Source |
| --- | --- |
| Batch orchestration | [Airflow DAGs](local-data-platform/airflow/dags/) |
| Source onboarding, FHIR, and HL7 producers | [Clinical producer code](local-data-platform/apps/clinical_producers/) |
| Spark normalization and clinical mapping | [PySpark applications](local-data-platform/spark/apps/) |
| Reconciliation and controlled writes | [OMOP writer](local-data-platform/apps/omop_writer/) |
| Input and output contracts | [Data contracts](local-data-platform/contracts/) |
| Kubernetes deployment definitions | [Kubernetes manifests](local-data-platform/kubernetes/manifests/) |
| Marquez integration | [Marquez component](platform-portal/marquez/) |
| Airflow/Spark lineage emitters | [OpenLineage integration](platform-portal/openlineage/) |
| Azure and Microsoft Fabric provisioning | [Terraform modules](azure-fabric/infra-terraform/) |
| Automated builds and checks | [GitHub Actions](.github/workflows/) |

## Copyright and usage restrictions

**Copyright © 2026 JohnZhang-DataForge. All rights reserved.**

This is an independent portfolio and demonstration project, **not an open-source project**. Unless expressly stated otherwise for third-party material, no license or permission is granted to use, copy, modify, distribute, sublicense, or create derivative works from this repository's code, documentation, configurations, or other original materials without the copyright holder's **prior written authorization**.

**Please do not fork, mirror, or copy this repository for reuse or independent development without prior written permission.** GitHub's Terms of Service may permit viewing and platform-native forking of public repositories; those platform permissions do **not** grant additional rights to use, modify, redistribute, or commercially exploit the project.

For permission requests, contact the repository owner.

---

*Independent data engineering project · Synthetic clinical data · Verified local processing, with multi-source and Fabric ingestion under development.*
