# Azure / Microsoft Fabric subsystem

This directory is the **planned source home** for the Azure/Fabric OMOP analytical replica. The authoritative local PostgreSQL OMOP database will be exported read-only to the existing Azure Blob landing. A Fabric Data Pipeline will then orchestrate a PySpark Notebook loading a OneLake Lakehouse.

## Directory responsibilities

| Directory | Responsibility | Current status |
| --- | --- | --- |
| `infra-terraform/` | Reserved destination for Azure/Fabric infrastructure as code | **Placeholder only**; live Terraform source remains at [`azure/infra-terraform/`](../azure/infra-terraform/README.md) |
| `exporter/` | Local PostgreSQL snapshot export and immutable Blob publication | Placeholder; no implementation |
| `workspace/healthcare-omop/` | Planned Git integration root for the existing Fabric Workspace `healthcare-omop` | Directory layout only; not connected or deployed by this change |
| `workspace/healthcare-omop/notebooks/ingestion/` | Fabric-native Notebook item definitions for ingestion / Delta loading | Placeholder; no `.Notebook` item yet |
| `workspace/healthcare-omop/pipelines/` | Fabric-native Data Pipeline item definitions for orchestration | Placeholder; no `.DataPipeline` item yet |
| `tests/` | Future unit, contract, integration and independent reconciliation tests | Placeholder; no implementation |

The `workspace/` tree is organized **by Fabric Workspace, then by item type, then by function**. Each real Notebook or Pipeline added later should use Fabric's native Git item-directory format. The current `.gitkeep` markers exist solely to make the empty directories visible in Git; they are not Fabric resources. Fabric Git integration does **not** synchronize empty workspace folders. Remove the placeholders as real items are introduced.

**Important:** This is only a repository layout change. It does not create a Workspace, Notebook, Pipeline or Lakehouse, configure Git Integration, or authorize a Terraform Plan/Apply. There is **no second executable Terraform stack** under this directory. The current [Self-Runner Azure-Infra-TF workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) still points to `healthcare/azure/infra-terraform/components/$COMPONENT`. Moving that code would require a coordinated workflow migration, which is **not** part of this change.

For tracked code and existing Terraform bootstrap details, see the [Azure/Fabric CODE map](../documents/systems/azure-fabric/CODE.md). For the system overview, see [Azure/Fabric overview](../documents/systems/azure-fabric/README.md). Warehouse remains optional, outside the OneLake-first MVP target.
