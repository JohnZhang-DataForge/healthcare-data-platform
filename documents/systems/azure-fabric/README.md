---
status: staging
scope: azure-fabric-system-overview
last_verified: 2026-10-16
source_sha: 48d24b1467efc6db28d9864ff20905cd193f5d96
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
| Infrastructure | [Current Terraform source](../../../azure/infra-terraform/README.md) — seven roots and matching modules | Existing code; source directory rename not yet performed |
| Exporter | `azure-fabric/exporter/` — consistent PG export, Parquet / manifest and Blob publication | Reserved directory; **not built** |
| Spark | `azure-fabric/spark-notebooks/{notebooks,src}/` — Notebook entry plus reusable read/validation/Delta logic | Reserved directories; **not built** |
| Data Factory | `azure-fabric/data-factory/` — business Pipeline definitions | Reserved directory; **not built** |
| Tests | `azure-fabric/tests/` — local tests and, later, independent reconciliation | Reserved directory; **not built** |

The `azure-fabric/infra-terraform/` directory is a **non-executable placeholder**. The original Terraform roots remain at `azure/infra-terraform/` so the existing Self-Runner workflow is not broken during cross-repository migration.

**Source of truth:** [CODE map](CODE.md) for tracked files, [Project Status](../../engineering/status/PROJECT-STATUS.md) for accepted work and outstanding tasks, [Data Flow](../../architecture/DATA-FLOW.md) for system boundaries. The [previous Azure component brief](../../components/azure-fabric/README.md) remains available during the documentation cutover, including historical Plan run links.

No Terraform Plan/Apply, pipeline run, export, or cloud deployment was performed by this directory preparation.
