# Azure / Microsoft Fabric subsystem

This directory is the **planned source home** for the Azure/Fabric OMOP analytical replica. The local PostgreSQL OMOP database remains authoritative; the target flow is a read-only export to existing Azure Blob Storage, then a Fabric Data Pipeline orchestrating a PySpark Notebook that loads a OneLake Lakehouse.

## Directory responsibilities

| Directory | Responsibility | Status |
| --- | --- | --- |
| `infra-terraform/` | Azure/Fabric resources, IAM and remote Terraform State | **Placeholder only in this path**; current runnable source remains at [`azure/infra-terraform/`](../azure/infra-terraform/README.md) |
| `exporter/` | PostgreSQL snapshot export and immutable Blob publication | Planned; no implementation |
| `spark-notebooks/notebooks/` | Fabric Notebook entry points | Planned; current Terraform bootstrap is intentionally fail-closed |
| `spark-notebooks/src/` | Reusable Spark readers, validation and Delta writer | Planned; no implementation |
| `data-factory/` | Business Pipeline definitions and orchestration | Planned; current Terraform Pipeline definition is a fail-closed/bootstrap shell |
| `tests/` | Unit, contract, integration and independent readback/reconciliation tests | Planned; no implementation |

**Important:** This folder does **not** contain a second runnable Terraform stack. Do not initialize, plan or apply Terraform from `azure-fabric/infra-terraform/` until the existing source is migrated together with the [Self-Runner workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml). The current workflow still selects `healthcare/azure/infra-terraform/components/$COMPONENT`. Its `operation` input supports `plan` (default) or explicitly selected `apply`; this directory preparation does not authorize either.

For the real source-file inventory see the [Azure/Fabric CODE map](../documents/systems/azure-fabric/CODE.md). For system context see the [Azure/Fabric overview](../documents/systems/azure-fabric/README.md). Warehouse is an optional future component, not the OneLake-first MVP target.
