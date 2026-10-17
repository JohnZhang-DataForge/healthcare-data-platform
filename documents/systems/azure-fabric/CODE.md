---
status: staging
scope: azure-fabric-source-map
last_verified: 2026-10-16
source_sha: 48d24b1467efc6db28d9864ff20905cd193f5d96
---

# Azure / Microsoft Fabric — CODE / Source Map

> **Source-map preparation only.** This page links the **actual files currently on Main**, not planned implementations. The existing runnable Terraform source is `azure/infra-terraform/`, **not yet** `azure-fabric/infra-terraform/`. Azure/Fabric has not been wired into the component CODE-map sync gate yet. See the [system README](README.md), [Developer Naming Rules](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md) and [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md).

## Terraform — the active infrastructure source

[Terraform README](../../../azure/infra-terraform/README.md) · [IAM and remote State architecture](../../../azure/infra-terraform/docs/ARCHITECTURE.md) · [ignore rules](../../../azure/infra-terraform/.gitignore)

Each `components/<component>/` is an **independent Terraform root**; `modules/<component>/` holds its resource and IAM implementation. Root-to-child sources remain relative `../../modules/<component>`. Existing OIDC Azure Blob remote State keys are `dev/<component>.tfstate` and must remain unchanged during the future move.

| Component | Root / environment source | Implementation source | Current ownership / boundary |
| --- | --- | --- | --- |
| Storage | [root](../../../azure/infra-terraform/components/storage/modules.tf) · [dev vars](../../../azure/infra-terraform/components/storage/environments/dev.tfvars) | [resource](../../../azure/infra-terraform/modules/storage/main.tf) · [IAM](../../../azure/infra-terraform/modules/storage/iam.tf) | Existing Blob landing; resource-specific Azure RBAC is optional |
| Workspace | [root](../../../azure/infra-terraform/components/workspace/modules.tf) · [dev vars](../../../azure/infra-terraform/components/workspace/environments/dev.tfvars) | [resource](../../../azure/infra-terraform/modules/workspace/main.tf) · [IAM](../../../azure/infra-terraform/modules/workspace/iam.tf) | Existing manually created Workspace **must be imported** before Terraform can manage it |
| OneLake | [root](../../../azure/infra-terraform/components/onelake/modules.tf) · [dev vars](../../../azure/infra-terraform/components/onelake/environments/dev.tfvars) | [Lakehouse](../../../azure/infra-terraform/modules/onelake/main.tf) · [IAM preview](../../../azure/infra-terraform/modules/onelake/iam.tf) | MVP Lakehouse definition; Plan evidence, no Apply |
| Notebook | [root](../../../azure/infra-terraform/components/notebook/modules.tf) · [dev vars](../../../azure/infra-terraform/components/notebook/environments/dev.tfvars) | [Notebook item](../../../azure/infra-terraform/modules/notebook/main.tf) · [bootstrap](../../../azure/infra-terraform/modules/notebook/definitions/notebook-content.py) | Item scaffold only; bootstrap **raises RuntimeError**, no ETL |
| Data Factory | [root](../../../azure/infra-terraform/components/data-factory/modules.tf) · [dev vars](../../../azure/infra-terraform/components/data-factory/environments/dev.tfvars) | [Data Pipeline item](../../../azure/infra-terraform/modules/data-factory/main.tf) | Orchestration item, **not** `azurerm_data_factory`; no real pipeline execution |
| Warehouse | [root](../../../azure/infra-terraform/components/warehouse/modules.tf) · [dev vars](../../../azure/infra-terraform/components/warehouse/environments/dev.tfvars) | [resource](../../../azure/infra-terraform/modules/warehouse/main.tf) · [IAM boundary](../../../azure/infra-terraform/modules/warehouse/iam.tf) | Future optional component; **not required by OneLake MVP** |
| Foundation IAM | [root](../../../azure/infra-terraform/components/foundation-iam/modules.tf) · [dev vars](../../../azure/infra-terraform/components/foundation-iam/environments/dev.tfvars) | [shared IAM](../../../azure/infra-terraform/modules/foundation-iam/iam.tf) | Separate shared Azure RG-level grants; not the owner of per-component permissions |

## Real Fabric definition files — Terraform-owned bootstrap only

| Actual source file | Function / current safety boundary |
| --- | --- |
| [`modules/notebook/definitions/notebook-content.py`](../../../azure/infra-terraform/modules/notebook/definitions/notebook-content.py) | Fabric Notebook parameter cells `export_id` and `manifest_uri`; **deliberate fail-closed bootstrap**, not a business Spark job |
| [`modules/data-factory/definitions/pipeline-disabled.json`](../../../azure/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) | Fail activity for missing Notebook GUID; does not claim load success |
| [`modules/data-factory/definitions/pipeline-notebook.json`](../../../azure/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) | Notebook Activity template and `export_id` / `manifest_uri` parameter expressions; not an executed E2E workflow |
| [`modules/data-factory/main.tf`](../../../azure/infra-terraform/modules/data-factory/main.tf) | Chooses disabled or Notebook definition according to `notebook_id`; do not bypass the failure gate |
| [`modules/notebook/main.tf`](../../../azure/infra-terraform/modules/notebook/main.tf) | Provisions Fabric Notebook item from checked-in definition; does not provision missing exporter/DQ code |

**Future source ownership:** `azure-fabric/spark-notebooks/` owns the real Notebook entry and reusable Python modules; `azure-fabric/data-factory/` owns the real business Pipeline; Terraform will reference/package their **single** authoritative definitions when those features are implemented. Do not maintain two divergent copies of Notebook or Pipeline logic. The transition requires an independent packaging/integration review.

## Planned modules — no business source files yet

| Reserved path | Intended responsibility | State |
| --- | --- | --- |
| `azure-fabric/infra-terraform/` | Target of the controlled Git move from `azure/infra-terraform/` | **Placeholder, not runnable** |
| `azure-fabric/exporter/` | Consistent read-only PG snapshot, Parquet, SHA-256 manifest and immutable Azure Blob publication | Not implemented |
| `azure-fabric/spark-notebooks/notebooks/` | Fabric Notebook entry point, pipeline parameters and orchestration | Not implemented |
| `azure-fabric/spark-notebooks/src/` | Reusable Blob reader, schema/PK/FK/DQ validators and idempotent Delta writer | Not implemented |
| `azure-fabric/data-factory/` | Future operational pipeline JSON with parameter propagation and error handling | Not implemented |
| `azure-fabric/tests/` | Unit/contract/integration tests, with independent PG/manifest ↔ OneLake reconciliation later | Not implemented |

No separate `reconciliation/` directory is required for the initial MVP. Internal validation belongs in the Spark library. **Independent** post-load reconciliation should live in tests or become its own component only when a distinct runnable workflow exists.

## Execution ownership and evidence

- [Self-Runner Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml): manually selects one of seven component roots, `environment=dev`, `operation=plan|apply` (**default plan**). Today its checked-out path is `healthcare/azure/infra-terraform/components/$COMPONENT`; switching it requires a coordinated Self-Runner change before moving the source.
- [Existing system brief](../../components/azure-fabric/README.md) records 2026-10-15 Plan-only evidence for Lakehouse, Notebook and Pipeline; those historical runs do **not** establish Apply, Delta data or business E2E.
- [Project status](../../engineering/status/PROJECT-STATUS.md) is the canonical CURRENT/NEXT view. Never treat a CODE map, a successful Plan or a directory scaffold as permission to deploy.

**Maintenance rule:** any later move/add/delete of Azure/Fabric source code must update this CODE map and relevant quality gates in the same PR. The current general naming/code-map checks must be extended to `azure-fabric/` during the coordinated Terraform migration; this staged page is not proof that those checks already enforce Azure ownership.
