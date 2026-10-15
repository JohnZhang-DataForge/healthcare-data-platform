# Azure Infrastructure Terraform — Component-owned IAM (v2, 2026-10-15)

**PLAN ONLY** — code refactor, no `apply` or `destroy` authorized.

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

The `Azure-Infra-TF` workflow exposes **storage / workspace / onelake / data-factory / notebook / warehouse / foundation-iam**. It runs only `fmt -check`, `init`, `validate`, `plan` on a selected component, using existing `johnzhang/tfstate` OIDC backend and **independent** `dev/<component>.tfstate` keys. Old `components/iam` and `modules/iam` were replaced with `foundation-iam`; the old `dev/iam.tfstate` has not been migrated or deleted. No old IAM state has been applied in this project; if state ever appears there, inspect and reconcile before adopting. No `-target` is required.

## Fabric planning restrictions

Fabric Provider Service Principal OIDC does NOT automatically gain Fabric tenant permissions or Trial capacity access by virtue of Azure RG Contributor. Existing workspaces must be reconciled/imported before Apply; `FABRIC_WORKSPACE_ID` is required by non-workspace Fabric components. Data Pipeline, Notebook and Warehouse modules are *item shells*, not functional ETL code, SQL or schedules. OneLake Lakehouse is optional to the direct Azure Blob → Notebook → Warehouse MVP. Trial Capacity is not deployed through this Terraform project.

## Tested evidence

- Prior **storage** Plan-only success: [Self-Runner Run 38761100632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632): GitHub OIDC, azurerm Backend, plan of existing OMOP/johnzhang; `APPLY_EXECUTED=NO`.
- This IAM refactor requires a **new regression** of storage and foundation-iam `fmt/validate/plan`. Do not claim all Fabric plans passed before real Fabric permissions/workspace are configured.

Docs: [IAM ownership design](docs/ARCHITECTURE.md), [Azure RBAC](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment), [Fabric workspace RBAC](https://microsoft.github.io/terraform-provider-fabric/resources/workspace_role_assignment/), [OneLake security preview](https://microsoft.github.io/terraform-provider-fabric/resources/onelake_data_access_security/).

## Component-owned IAM refactor acceptance — 2026-10-15

- **Foundation shared RBAC root** — [Azure-Infra-TF Run 38767227655, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655) **SUCCESS**: recursive `terraform fmt -check`, remote OIDC Backend `init`, `validate`, and `plan` passed; `shared_role_bindings = {}` caused no grant changes.
- **Storage component with its own IAM module** — [Azure-Infra-TF Run 38761100632 (re-run)](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632) **SUCCESS**: storage `init/validate/plan` read `OMOP` + `johnzhang`, `blob_role_assignments = {}`; no new RBAC.
- Both tests checked out Healthcare SHA `bdbfe21b2230926adbee82cbfb72b952bf6b5837`, and both logged `APPLY_EXECUTED=NO`, `DESTROY_EXECUTED=NO`.
- Workflow reverted to **manual workflow_dispatch** only; selector `iam` removed and replaced with `foundation-iam`. Fabric-specific `onelake` preview IAM is declared but its real provider validate/plan and permissions remain **NOT VERIFIED**.
