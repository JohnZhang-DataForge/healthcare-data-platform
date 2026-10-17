---
status: staging
scope: azure-fabric-system-overview
last_verified: 2026-10-16
source_sha: 93b397026a07a16baed4460c6c03e39d72d2bb12
---

# Azure / Microsoft Fabric — OMOP analytical replica

This page is the **human-readable system overview**. See [CODE.md](CODE.md) for actual source files and [System Overview](../../architecture/SYSTEM-OVERVIEW.md) for the cross-platform architecture.

## OneLake-first target flow

```text
Local PostgreSQL OMOP (authoritative Person/Visit)
  → Read-only snapshot Exporter (not built)
  → Existing Azure Blob snapshot landing
  → Fabric Data Factory Data Pipeline (orchestration)
  → Fabric PySpark Notebook (validation and Delta load; not built)
  → OneLake Lakehouse (analytics copy; not deployed by these plans)
```

The existing Blob account and manually provisioned Fabric Workspace are **not** new resources created by this migration. Historical Terraform Plans for the Lakehouse, Notebook and Data Pipeline passed on 2026-10-15, each proposing one item; **a passed Plan is not an Apply or data E2E acceptance**. The Notebook bootstrap deliberately raises an error, and the Pipeline defaults to a Fail activity if no Notebook ID is configured. Warehouse is optional and outside the MVP's required data path.

## Source organization

| Area | Source location and purpose | Implementation |
| --- | --- | --- |
| Infrastructure | [Active Terraform source](../../../azure-fabric/infra-terraform/README.md) — seven roots and matching modules | Full source copy, old `azure/` preserved |
| Exporter | `azure-fabric/exporter/` — consistent PG export, Parquet / manifest and Blob publication | Reserved directory; **not built** |
| Fabric notebooks | `azure-fabric/workspace/healthcare-omop/notebooks/ingestion/` — Fabric-native Notebook items | Reserved directory; **not built** |
| Fabric pipelines | `azure-fabric/workspace/healthcare-omop/pipelines/` — Fabric-native Data Pipeline items | Reserved directory; **not built** |
| Tests | `azure-fabric/tests/` — local tests and, later, independent reconciliation | Reserved directory; **not built** |

The `azure-fabric/workspace/healthcare-omop/` directory mirrors a **planned Git integration folder**, not a new Fabric Workspace resource. The existing `healthcare-omop` Workspace must be connected explicitly; temporary `.gitkeep` markers do not represent Notebook/Pipeline items and will be retired when real Fabric items are added. Reusable non-Fabric Python code can be kept outside this folder later to avoid contaminating native item definitions.

`azure-fabric/infra-terraform/` now contains the copied Terraform roots and modules; resource configuration and remote State keys are unchanged. The original `azure/infra-terraform/` is still intact. Self-Runner must be switched to the new directory before Plan validation; copying IaC alone does not deploy resources.

**Source of truth:** [CODE map](CODE.md) for tracked files, [Project Status](../../engineering/status/PROJECT-STATUS.md) for accepted work and outstanding tasks, [Data Flow](../../architecture/DATA-FLOW.md) for system boundaries. The [previous Azure component brief](../../components/azure-fabric/README.md) remains available during the documentation cutover, including historical Plan run links.

No Terraform Plan/Apply, pipeline run, export, or cloud deployment was performed by this directory preparation.
