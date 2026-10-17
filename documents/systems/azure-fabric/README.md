---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-10-16
source_sha: 1f393e954f4c0a1e4727774881f036a97dee7770
---

# Azure / Microsoft Fabric — OMOP analytical replica

The Azure/Fabric analytical replica is a **sibling system** of the local data platform. The existing PostgreSQL OMOP database is authoritative; a future read-only exporter will produce an immutable snapshot for the existing Azure Blob landing. A Fabric Data Pipeline then orchestrates a PySpark Notebook into a OneLake Lakehouse. This is a **target design**, not a verified cloud data E2E.

## Source organization

The [Azure/Fabric code root](../../../azure-fabric/README.md) contains exactly two source areas:

| Source area | System component | Implementation status |
| --- | --- | --- |
| [`infra-terraform/`](../../../azure-fabric/infra-terraform/README.md) | Seven Terraform roots, shared IaC and remote State | Existing source, seven new-path Plan-only jobs passed; no Apply inferred |
| [`workspaces/healthcare-omop/notebooks/`](../../../azure-fabric/workspaces/healthcare-omop/notebooks/) | [Notebooks](notebooks/README.md) · [CODE](notebooks/CODE.md) — read snapshots, verify schema/DQ/PK/FK, load Lakehouse Delta | Placeholder only; no native `*.Notebook/` item or business ETL |
| [`workspaces/healthcare-omop/pipelines/`](../../../azure-fabric/workspaces/healthcare-omop/pipelines/) | [Pipelines](pipelines/README.md) · [CODE](pipelines/CODE.md) — run parameters, orchestration, failure gates | Placeholder only; no native `*.DataPipeline/` item or active orchestration |

`healthcare-omop` is the existing **Fabric Workspace name**, not a proposed second Workspace. The `workspaces/` Git tree is a *planned source location*, not an established Fabric Git connection. Fabric native item folders and provider-created Terraform item definitions cannot be treated as interchangeable without an item identity and deployment ownership decision.

### Data-flow and implementation boundaries

```text
Local PostgreSQL OMOP (source of truth)
  → Read-only exporter + immutable manifest [future local development]
  → Existing Azure Blob snapshot landing
  → Fabric Data Pipeline [future business source in workspaces/.../pipelines]
  → Fabric PySpark Notebook [future business source in workspaces/.../notebooks]
  → OneLake Lakehouse / Delta [planned cloud analytics replica]
```

Terraform's [Notebook bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) raises an exception intentionally; the [Pipeline fail definition](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) intentionally fails until an actual Notebook GUID is supplied. Do not copy them into empty workspace source directories or claim Fabric Git Integration / business E2E.

A local exporter and independent cross-platform reconciliation remain **required future capabilities**, but are not Fabric-native workspace items; former empty `azure-fabric/exporter/` and `azure-fabric/tests/` placeholders were removed as part of the two-source-area layout. No exporter logic or tests existed there.

The original `azure/infra-terraform/` remains for transition purposes. Self-Runner now selects `azure-fabric/infra-terraform/` and seven components have successful historical **Plan-only** regressions ([technical evidence](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md#verified-plan-evidence)); no cloud resource creation or data load follows from this source-only work.

**Navigation:** [System CODE map](CODE.md) · [Notebooks](notebooks/README.md) · [Pipelines](pipelines/README.md) · [Data Flow](../../architecture/DATA-FLOW.md) · [Project Status](../../engineering/status/PROJECT-STATUS.md) · [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md).
