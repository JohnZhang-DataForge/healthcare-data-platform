---
status: staging
scope: azure-fabric-source-map
last_verified: 2026-10-16
source_sha: 93b397026a07a16baed4460c6c03e39d72d2bb12
---

# Azure / Microsoft Fabric — CODE / Source Map

> **Source-map preparation only.** This page links the **actual files currently on Main**, not planned implementations. The active Terraform source has been copied to `azure-fabric/infra-terraform/`; the original `azure/infra-terraform/` remains unchanged. Execution-path cutover is coordinated with Self-Runner. Azure/Fabric has not been wired into the component CODE-map sync gate yet. See the [system README](README.md), [Developer Naming Rules](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md) and [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md).

## Terraform — the active infrastructure source

[Terraform README](../../../azure-fabric/infra-terraform/README.md) · [IAM and remote State architecture](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md) · [ignore rules](../../../azure-fabric/infra-terraform/.gitignore)

Each `components/<component>/` is an **independent Terraform root**; `modules/<component>/` holds its resource and IAM implementation. Root-to-child sources remain relative `../../modules/<component>`. Existing OIDC Azure Blob remote State keys are still `dev/<component>.tfstate`. Resource definitions are copied unchanged; the original `azure/infra-terraform/` is retained for reference and rollback, not for parallel execution.

| Component | Root / environment source | Implementation source | Current ownership / boundary |
| --- | --- | --- | --- |
| Storage | [root](../../../azure-fabric/infra-terraform/components/storage/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/storage/environments/dev.tfvars) | [resource](../../../azure-fabric/infra-terraform/modules/storage/main.tf) · [IAM](../../../azure-fabric/infra-terraform/modules/storage/iam.tf) | Existing Blob landing; resource-specific Azure RBAC is optional |
| Workspace | [root](../../../azure-fabric/infra-terraform/components/workspace/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/workspace/environments/dev.tfvars) | [resource](../../../azure-fabric/infra-terraform/modules/workspace/main.tf) · [IAM](../../../azure-fabric/infra-terraform/modules/workspace/iam.tf) | Existing manually created Workspace **must be imported** before Terraform can manage it |
| OneLake | [root](../../../azure-fabric/infra-terraform/components/onelake/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/onelake/environments/dev.tfvars) | [Lakehouse](../../../azure-fabric/infra-terraform/modules/onelake/main.tf) · [IAM preview](../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) | MVP Lakehouse definition; Plan evidence, no Apply |
| Notebook | [root](../../../azure-fabric/infra-terraform/components/notebook/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/notebook/environments/dev.tfvars) | [Notebook item](../../../azure-fabric/infra-terraform/modules/notebook/main.tf) · [bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | Item scaffold only; bootstrap **raises RuntimeError**, no ETL |
| Data Factory | [root](../../../azure-fabric/infra-terraform/components/data-factory/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/data-factory/environments/dev.tfvars) | [Data Pipeline item](../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | Orchestration item, **not** `azurerm_data_factory`; no real pipeline execution |
| Warehouse | [root](../../../azure-fabric/infra-terraform/components/warehouse/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/warehouse/environments/dev.tfvars) | [resource](../../../azure-fabric/infra-terraform/modules/warehouse/main.tf) · [IAM boundary](../../../azure-fabric/infra-terraform/modules/warehouse/iam.tf) | Future optional component; **not required by OneLake MVP** |
| Foundation IAM | [root](../../../azure-fabric/infra-terraform/components/foundation-iam/modules.tf) · [dev vars](../../../azure-fabric/infra-terraform/components/foundation-iam/environments/dev.tfvars) | [shared IAM](../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf) | Separate shared Azure RG-level grants; not the owner of per-component permissions |

## Real Fabric definition files — Terraform-owned bootstrap only

| Actual source file | Function / current safety boundary |
| --- | --- |
| [`modules/notebook/definitions/notebook-content.py`](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | Fabric Notebook parameter cells `export_id` and `manifest_uri`; **deliberate fail-closed bootstrap**, not a business Spark job |
| [`modules/data-factory/definitions/pipeline-disabled.json`](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) | Fail activity for missing Notebook GUID; does not claim load success |
| [`modules/data-factory/definitions/pipeline-notebook.json`](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) | Notebook Activity template and `export_id` / `manifest_uri` parameter expressions; not an executed E2E workflow |
| [`modules/data-factory/main.tf`](../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | Chooses disabled or Notebook definition according to `notebook_id`; do not bypass the failure gate |
| [`modules/notebook/main.tf`](../../../azure-fabric/infra-terraform/modules/notebook/main.tf) | Provisions Fabric Notebook item from checked-in definition; does not provision missing exporter/DQ code |

**Future source ownership:** `azure-fabric/workspace/healthcare-omop/notebooks/` and `pipelines/` are reserved for Fabric Git-integrated **native item definitions** within the `healthcare-omop` Workspace; initial Notebook work is grouped under `notebooks/ingestion/`. Reusable standalone Python libraries, if needed, belong outside the Git-synced item tree and will be placed when implemented. Terraform definitions now also exist at `azure-fabric/infra-terraform/` as a copy, with `azure/infra-terraform/` retained unchanged; deployment/IaC must reference a **single authoritative** Notebook/Pipeline definition, not generate a divergent copy. Git connection, bootstrap migration and packaging require separate review.

## Planned modules — no business source files yet

| Reserved path | Intended responsibility | State |
| --- | --- | --- |
| `azure-fabric/infra-terraform/` | Active source copied from `azure/infra-terraform/` | **Full copy; post-cutover Plan validation pending** |
| `azure-fabric/exporter/` | Consistent read-only PG snapshot, Parquet, SHA-256 manifest and immutable Azure Blob publication | Not implemented |
| `azure-fabric/workspace/healthcare-omop/notebooks/ingestion/` | Future native Fabric Notebook items for OMOP ingestion / Delta load | Placeholder only; no `.Notebook` item yet |
| `azure-fabric/workspace/healthcare-omop/pipelines/` | Future native Fabric Data Pipeline items for orchestration and parameters | Placeholder only; no `.DataPipeline` item yet |
| `azure-fabric/tests/` | Unit/contract/integration tests, with independent PG/manifest ↔ OneLake reconciliation later | Not implemented |

**Git Integration:** connect the existing `healthcare-omop` Workspace to the repository folder `azure-fabric/workspace/healthcare-omop/` only when native Fabric item definitions are ready. `.gitkeep` files are temporary repository placeholders, **not** deployable Fabric items; Fabric does not synchronize empty workspace folders. The directory name does not create or rename a workspace.

No separate `reconciliation/` directory is required for the initial MVP. Internal validation belongs in the Spark library. **Independent** post-load reconciliation should live in tests or become its own component only when a distinct runnable workflow exists.

## Execution ownership and evidence

- [Self-Runner Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml): manually selects one of seven component roots, `environment=dev`, `operation=plan|apply` (**default plan**). The intended execution path after coordinated Self-Runner change is `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`; keep the original tree read-only.
- [Existing system brief](../../components/azure-fabric/README.md) records 2026-10-15 Plan-only evidence for Lakehouse, Notebook and Pipeline; those historical runs do **not** establish Apply, Delta data or business E2E.
- [Project status](../../engineering/status/PROJECT-STATUS.md) is the canonical CURRENT/NEXT view. Never treat a CODE map, a successful Plan or a directory scaffold as permission to deploy.

**Maintenance rule:** any later move/add/delete of Azure/Fabric source code must update this CODE map and relevant quality gates in the same PR. Code-map checks may be extended to `azure-fabric/` in a later follow-up; this source map does not claim that CI currently enforces Azure ownership.
