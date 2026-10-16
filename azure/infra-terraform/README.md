# Azure Infrastructure Terraform — Component-owned IAM (v2, 2026-10-15)

**Development mode (2026-10-15):** `Azure-Infra-TF` supports an explicit `operation` choice: `plan` (default) or `apply`. No automatic apply or destroy.

Source of truth: `healthcare-data-platform/azure/infra-terraform`.
Executor: `Self-Runner/.github/workflows/azure-infra.yaml` (**Azure-Infra-TF**).
The GitHub OIDC federated credential belongs to **Self-Runner/main**, not this source repo.

## Directory organization

```text
components/
  storage/          # Existing johnzhang / landing + optional NEW landing RBAC
  workspace/        # Fabric Workspace + workspace membership
  onelake/          # Fabric Lakehouse + OPTIONAL OneLake data roles (preview)
  data-factory/     # Fabric Data Pipeline item; workspace permissions
  notebook/         # Fabric Notebook item; workspace permissions
  warehouse/        # Fabric Warehouse item; SQL GRANT remains separate
  foundation-iam/   # SHARED RG-level identities/grants ONLY
modules/
  storage/{main.tf,iam.tf,outputs.tf}
  workspace/{main.tf,iam.tf,outputs.tf}
  onelake/{main.tf,iam.tf,outputs.tf}
  data-factory/{main.tf,iam.tf,outputs.tf}
  notebook/{main.tf,iam.tf,outputs.tf}
  warehouse/{main.tf,iam.tf,outputs.tf}
  foundation-iam/{main.tf,iam.tf,outputs.tf}
```

Each `components/<selector>` is a **Terraform root module** (`versions.tf`, `providers.tf`, `modules.tf`, `variables.tf`, `outputs.tf`, `iam.tf`, `environments/dev.tfvars`). It selects the child module, passes environment-specific IAM/configuration values, and has its own remote state. Actual resource and supported IAM implementation lives in its `modules/<selector>`. Thus: **Modules define HOW; components define WHAT and WHO; tfvars define environment values.**

## Archived, independent Azure smoke roots

Earlier, before `azure/infra-terraform/components/` became the canonical Azure/Fabric IaC project, two **one-off, independent** Terraform smoke roots were created at the top-level `infra/azure/`. They have now been **relocated without changing resource definitions or remote Terraform state keys**:

- [`smoke/terraform-oidc-smoke/`](smoke/terraform-oidc-smoke/README.md): ARM control-plane OIDC/backend/create/read/destroy probe.
- [`smoke/landing-blob-smoke/`](smoke/landing-blob-smoke/README.md): AzureAD data-plane write check targeting an existing landing Blob container.

These are **NOT** deployable Fabric components; do not select them as `Azure-Infra-TF` `component`, and do not merge their remote state into `dev/<component>.tfstate`. Their separate `smoke/*.tfstate` backend keys are intentionally unchanged. Both contain actual Azure **apply-capable** code; the presence of these files authorizes **no execution**. Refer to [smoke safety and workflow compatibility](smoke/README.md) before any future run.

**Canonical Azure IaC root remains** `azure/infra-terraform/components/`; all new Azure experiments should stay under this `azure/` tree, never a second top-level `infra/`.

## IAM ownership and permission boundaries

| Component | Module IAM definition | dev.tfvars | Notes |
|---|---|---|---|
| storage | `modules/storage/iam.tf` — Azure Blob container RBAC | `blob_role_assignments = {}` | Existing Portal Bootstrap grant stays unmanaged; import before adoption |
| workspace | `modules/workspace/iam.tf` — Fabric workspace role assignment | `role_assignments = {}` | Supported Fabric roles: Admin / Member / Contributor / Viewer |
| onelake | `modules/onelake/iam.tf` — OneLake data-access role, **PREVIEW** | `data_access_roles = {}` | Supports Lakehouse table/folder path and member rules; no grants by default |
| data-factory / notebook | Module `iam.tf` records ownership/boundary | No fabricated grants | Workspace membership / independently reviewed Fabric item permissions |
| warehouse | Module `iam.tf` records ownership/boundary | No fabricated grants | Workspace IAM plus SQL GRANT/REVOKE managed in SQL deployment |
| foundation-iam | `modules/foundation-iam/iam.tf` — shared Resource Group RBAC only | `shared_role_bindings = {}` | NOT component-level Blob/OneLake IAM; no bootstrap self-management |

**Important: RBAC does NOT define new Azure roles** in this code. It binds existing role names to Entra **object IDs** (not Application/client IDs). Existing `OMOP`, `johnzhang`, `landing`, `tfstate` are not managed resources. Bootstrap SP's RG Contributor / Blob Data Contributor were Portal-created and must not be recreated or destroyed. Assigning NEW Azure roles requires `Microsoft.Authorization/roleAssignments/write`, which normal RG Contributor lacks.

**OneLake security is not Azure RBAC.** The Fabric `fabric_onelake_data_access_security` provider resource is preview and requires `provider.fabric.preview = true`, explicitly enabled in `components/onelake/providers.tf`; `data_access_roles = {}` means zero role resources. Fabric workspace access and permissions are separate from Azure RG rights. Avoid confusing Fabric Lakehouse/OneLake with a new Azure Storage Account.

## Terraform root / state isolation

The `Azure-Infra-TF` workflow exposes **storage / workspace / onelake / data-factory / notebook / warehouse / foundation-iam**. It runs `fmt -check`, `init`, `validate`, `plan`, followed by `apply` of the exact saved plan **only when operation=apply**, using existing `johnzhang/tfstate` OIDC backend and **independent** `dev/<component>.tfstate` keys. Old `components/iam` and `modules/iam` were replaced with `foundation-iam`; the old `dev/iam.tfstate` has not been migrated or deleted. No old IAM state has been applied in this project; if state ever appears there, inspect and reconcile before adopting. No `-target` is required.

## Development plan / apply workflow (2026-10-15)

- Workflow: [Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/azure-infra.yaml), manually triggered on `main`.
- Inputs: `component`, `environment=dev`, `operation=plan|apply`. Default operation `plan`; no other environments or `destroy` option.
- Both operations run recursive `terraform fmt -check`, `init` with existing OIDC Azure Blob Backend, `validate`, then `plan -out` into the ephemeral Runner directory. Only selected `apply` reuses that **exact saved plan**. Apply is intentionally easy for a temporary dev lab and does not require a separate approval stage. A plan that would delete or replace an existing tracked resource is blocked.
- Existing `healthcare-omop` Fabric Workspace was created manually. The `workspace` component refuses `apply` until it has been imported into that component's remote Terraform State. This prevents a second Workspace being created accidentally.
- IAM defaults to empty mappings; Bootstrap `OMOP` / `johnzhang` / `tfstate` remain outside lifecycle. Azure data operations may incur ordinary Azure charges even during Fabric Trial.

### Actual Fabric onelake regression

[Azure-Infra-TF Run 38797932758, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38797932758): SUCCESS after correcting missing `required_providers { fabric = { source = "microsoft/fabric" } }` in **all Fabric child modules**. Provider installed `microsoft/fabric v1.13.0`, `terraform validate` passed, and Plan showed `+ fabric_lakehouse.current`, name `lh_omop_analytics` in Workspace `56dca14e-5d3c-42de-ae57-d76a916ecbca`. **Plan: 1 add / 0 change / 0 destroy**; no Apply executed. Actual Fabric API Create/permissions remain to be tested by an explicit `onelake + dev + apply` run.

## Fabric planning restrictions

Fabric Provider Service Principal OIDC does NOT automatically gain Fabric tenant permissions or Trial capacity access by virtue of Azure RG Contributor. Existing workspaces must be reconciled/imported before Apply; `FABRIC_WORKSPACE_ID` is required by non-workspace Fabric components. Data Pipeline, Notebook and Warehouse modules are *item shells*, not functional ETL code, SQL or schedules. **Current OneLake-first MVP** is local PostgreSQL OMOP → existing Azure Blob → Fabric Data Factory Data Pipeline → Fabric PySpark Notebook → OneLake Lakehouse/Delta. Warehouse is optional future scope, not the active MVP. Trial Capacity is not deployed through this Terraform project.

## Tested evidence

- Prior **storage** Plan-only success: [Self-Runner Run 38761100632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632): GitHub OIDC, azurerm Backend, plan of existing OMOP/johnzhang; `APPLY_EXECUTED=NO`.
- This IAM refactor requires a **new regression** of storage and foundation-iam `fmt/validate/plan`. Do not claim all Fabric plans passed before real Fabric permissions/workspace are configured.

Docs: [IAM ownership design](docs/ARCHITECTURE.md), [Azure RBAC](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment), [Fabric workspace RBAC](https://microsoft.github.io/terraform-provider-fabric/resources/workspace_role_assignment/), [OneLake security preview](https://microsoft.github.io/terraform-provider-fabric/resources/onelake_data_access_security/).

## Component-owned IAM refactor acceptance — 2026-10-15

- **Foundation shared RBAC root** — [Azure-Infra-TF Run 38767227655, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655) **SUCCESS**: recursive `terraform fmt -check`, remote OIDC Backend `init`, `validate`, and `plan` passed; `shared_role_bindings = {}` caused no grant changes.
- **Storage component with its own IAM module** — [Azure-Infra-TF Run 38761100632 (re-run)](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632) **SUCCESS**: storage `init/validate/plan` read `OMOP` + `johnzhang`, `blob_role_assignments = {}`; no new RBAC.
- Both tests checked out Healthcare SHA `bdbfe21b2230926adbee82cbfb72b952bf6b5837`, and both logged `APPLY_EXECUTED=NO`, `DESTROY_EXECUTED=NO`.
- Workflow reverted to **manual workflow_dispatch** only; selector `iam` removed and replaced with `foundation-iam`. Fabric-specific `onelake` preview IAM is declared but its real provider validate/plan and permissions remain **NOT VERIFIED**.

## 2026-10-15 OneLake-first resource definitions (PLAN ONLY)

See [Azure/Fabric OneLake infrastructure handoff](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md). Storage and manually-created Workspace are intentionally untouched. The `onelake` root creates a schema-enabled Lakehouse; `notebook` carries a source-controlled fail-closed PySpark bootstrap; `data-factory` carries a fail-closed Pipeline definition and optionally links a **real** Notebook GUID supplied later. Warehouse is no longer required in the first infrastructure deployment. **No Apply or Destroy has been authorized or executed for this change.**
