# Azure/Fabric OneLake-first infrastructure — PLAN ONLY (2026-10-15)

**Scope:** Terraform *source code only*. The user explicitly forbids Terraform Apply, Destroy, and any remote resource provisioning in this iteration. A successful Plan is not a successful Fabric creation.

## Current target

```text
Local PostgreSQL OMOP (cdm.person + cdm.visit_occurrence)
  -> later read-only consistent exporter
  -> EXISTING Azure Blob landing (no storage changes)
  -> Fabric Data Factory pipeline (orchestration)
  -> Fabric Spark Notebook (later transform, DQ, idempotency)
  -> OneLake Lakehouse (schema-enabled; later Delta cdm tables)
```

This **OneLake-first** design supersedes the older Warehouse-first MVP in `AZURE-FABRIC-MINIMAL-IMPLEMENTATION-PLAN-v1.0.zh-CN.md` for the immediate infrastructure phase. The `warehouse` component remains optional and **must not be included** in the initial plan/apply sequence. Fabric Data Factory here means `fabric_data_pipeline`, not an additional Azure Data Factory account.

## Existing, untouched resources

- Business Storage/landing and Terraform state Blob: **existing**, no Terraform storage changes.
- Fabric Workspace: existing manually-created `healthcare-omop`, ID previously recorded as `56dca14e-5d3c-42de-ae57-d76a916ecbca`. Verify current identity in Fabric before any real deployment. **Do not apply the `workspace` component:** its historical tfvars name is different, and the Workspace must first be imported before it can be Terraform-managed.
- Reuse Self-Runner `Azure-Infra-TF` workflow; no workflow code changes in this PR. `operation=plan` **MUST** be selected. That workflow also exposes `apply`, which is explicitly **NOT AUTHORIZED**.

## What the Terraform code now declares

| Existing root component | Plan-only desired resources | Notes |
|---|---|---|
| `onelake` | `fabric_lakehouse` `lh_omop_analytics`, schema enabled | Exposes Lakehouse ID / OneLake Files+Tables paths; access roles default empty (preview) |
| `notebook` | `fabric_notebook` `nb_omop_snapshot_load`, source-controlled PySpark source | Bootstrap intentionally raises exception; **not an ETL** |
| `data-factory` | `fabric_data_pipeline` `pl_omop_snapshot_to_onelake`, versioned definition | With no Notebook ID, contains an explicit Fail activity; not an empty success pipeline |

**Dependency across state boundaries:** `notebook` and `data-factory` are separate Terraform state roots. Terraform cannot refer to an unapplied Notebook's unknown GUID when planning the pipeline. `notebook_id=""` is a deliberate plan-safe, fail-closed default. After the Notebook really exists **in a future separately-authorized phase**, obtain its item GUID from the Notebook Terraform output and update `components/data-factory/environments/dev.tfvars` to link the Notebook activity. No placeholder/fake GUID is written to a live pipeline. `FABRIC_WORKSPACE_ID` is still injected by the existing Self-Runner workflow.

## Read-only Plan sequence

Run the existing **Azure-Infra-TF** workflow **only** with `environment=dev` and `operation=plan`; run independently for `onelake`, `notebook`, `data-factory`. Each root independently performs `terraform fmt -check`, OIDC backend `init`, `validate`, `plan`. Save workflow run IDs and counts (adds/changes/destroys). **No Apply or Destroy.** Any failure of real Fabric access is a Plan limitation, not permission to relax identity controls.

Expected preliminary plan shape, assuming empty component states and Fabric permissions: **one added Lakehouse, one added Notebook, one added Pipeline** across three independent plans. Actual results may differ if states contain resources or if existing unmanaged Fabric items have name collisions. Never equate this expectation with verified Plan evidence.

## Future gates (not authorized by this PR)

1. Reconcile existing workspace, capacity/license, Fabric tenant Service Principal privileges, and existing items. Import existing items if necessary rather than duplicating.
2. Only on later explicit approval, create Lakehouse + Notebook, review outputs/permissions. Update Pipeline `notebook_id` to real Notebook ID; separately approve Pipeline deployment.
3. Implement exporter, Notebook validation (READY manifest, source counts, PK/FK, hash), Delta write to OneLake and replay checks. The current Notebook intentionally **fails closed**; pipeline with linked Notebook also fails until the code is actually implemented.
4. Check Data Factory Notebook Activity run identity and ADLS credentials; Fabric Workspace permission does not confer Blob RBAC. No Storage Account Key or SAS in the repo.
5. Warehouse optional and not planned. All actual cloud processing and SQL validation are later work.

## Verified Terraform Plans — 2026-10-15 (PLAN ONLY)

All three component plans executed via the existing `Azure-Infra-TF` Workflow, each with `environment=dev`, `operation=plan`, remote Azure Blob state (OIDC), Terraform 1.13.5 and Fabric Provider 1.13.0. All checked out **identical Healthcare source SHA `6acb59353f5d7630f65b6f417c8e8bfbd39cf651`**.

| Component | Run | Planned Fabric resource | Add / Change / Destroy |
|---|---|---|---|
| onelake | [38799966270 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270/attempts/2) | `module.onelake.fabric_lakehouse.current`: `lh_omop_analytics` | **1 / 0 / 0** |
| notebook | [38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550) | `module.notebook.fabric_notebook.current`: `nb_omop_snapshot_load` | **1 / 0 / 0** |
| data-factory | [38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221) | `module.data_factory.fabric_data_pipeline.current`: `pl_omop_snapshot_to_onelake` | **1 / 0 / 0** |
| **Total** | **three completed-success jobs** | **three items proposed** | **3 / 0 / 0** |

Each actual job log confirms `TERRAFORM_PLAN_STATUS=PASS`, `APPLY_EXECUTED=NO`, and `DESTROY_EXECUTED=NO`. The Notebook and Data Factory runs were generated by a narrow plan-only dispatcher ([dispatch run 38832788250](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832788250)) which invoked **the existing** `azure-infra.yaml` with `operation=plan`.

### Observed planning parameters

| Item | Plan observation |
|---|---|
| Existing Workspace | All 3 items point at `56dca14e-5d3c-42de-ae57-d76a916ecbca`. No new workspace or capacity |
| Lakehouse | `lh_omop_analytics`, `configuration.enable_schemas=true`, description `OneLake analytics replica of local OMOP PostgreSQL snapshots` |
| Lakehouse IAM | `data_access_roles={}`, `data_access_role_ids={}`: **no OneLake role creation** |
| Notebook | `nb_omop_snapshot_load`, `format=py`, `definition` source `../../modules/notebook/definitions/notebook-content.py`, SHA-256 `d87a6aff03576cfa56e4b578f064cb24814088fd3aedc9edff6da184e180a338` |
| Data Pipeline | `pl_omop_snapshot_to_onelake`, `format=Default`, `definition` source `../../modules/data-factory/definitions/pipeline-disabled.json`, SHA-256 `f27980f1a3733162481b1f5cb559128de9857cf86b9226b549ed3bb0d9efd431` |
| Pipeline notebook binding | `notebook_id=""`; `NotebookId=""` and `WorkspaceId=56dca14e-5d3c-42de-ae57-d76a916ecbca` definition tokens. **Default Pipeline contains a Fail activity, not Notebook Activity** |
| Pipeline runtime parameters | `export_id`: String default `""`; `manifest_uri`: String default `""`. Both are future runtime inputs |
| Fabric item IDs/paths | Lakehouse ID, Notebook ID, Pipeline ID, OneLake Files/Tables paths are `(known after apply)`; no resources created |
| Terraform state keys | Existing `johnzhang/tfstate` Azure Blob: `dev/onelake.tfstate`, `dev/notebook.tfstate`, `dev/data-factory.tfstate`; each root isolated |

### Guardrails / what has NOT been built

**The current Notebook is an intentionally disabled bootstrap** with `export_id` and `manifest_uri` parameter cells followed by `raise RuntimeError`; there is no ETL, blob access, data quality validation or OneLake Delta write yet. **The current Pipeline definition likewise contains a Fail activity** until a genuine Notebook ID is wired *after separately approved future provisioning and ETL implementation*. The older `warehouse` root is optional and was not planned. Storage, existing Azure landing, Workspace, Terraform State Storage, IAM bootstrap, PostgreSQL, and Fabric capacity were not changed.

Successful `plan` validates the Terraform configuration and what Terraform proposes, **not** the Fabric Create APIs, Notebook runtime, Pipeline execution, capacity assignment, or end-to-end connectivity. Prior to any future authorized Apply, reconcile existing unmanaged Fabric items and workspace permissions/capacity. There was **NO Terraform Apply, NO Destroy, and NO Azure/Fabric resource provisioning** during this verification.
