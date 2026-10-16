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

## Evidence note

Earlier OneLake Terraform Plan succeeded on [Self-Runner run 38797932758 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38797932758) for an **older** Lakehouse-only declaration. This new schema-enabled + definition-bearing revision **needs fresh Plans**. No current-run Terraform Plan has been executed as part of this source-only commit, unless a later run ID is documented explicitly.
