# Healthcare Azure Infrastructure — Terraform (v1)

**PLAN-ONLY; no apply/destroy is authorized or configured.**

The canonical IaC lives here. Controller: `JohnZhang-DataForge/Self-Runner/.github/workflows/azure-infra.yaml`, display name **Azure-Infra-TF**. GitHub OIDC trust is on Self-Runner/main.

## Select a resource

| Workflow component | Terraform root | Future resource on apply | Dependencies |
|---|---|---|---|
| `storage` | `components/storage` | No new resource; data-only existing OMOP / johnzhang | Azure RG + existing Storage |
| `workspace` | `components/workspace` | Fabric Workspace | Fabric tenant SP permissions; existing workspace import first |
| `onelake` | `components/onelake` | Fabric Lakehouse (optional OneLake item) | Fabric Workspace ID |
| `data-factory` | `components/data-factory` | Fabric Data Pipeline **shell** | Fabric Workspace ID |
| `notebook` | `components/notebook` | Fabric Notebook **shell** | Fabric Workspace ID |
| `warehouse` | `components/warehouse` | Fabric Warehouse **shell** | Fabric Workspace ID |
| `iam` | `components/iam` | Empty by default; only new grants if explicitly configured | Additional Azure roleAssignments/write permission |

Every `components/<name>` is an independent Terraform root, with `versions.tf`, `providers.tf`, `modules.tf`, `variables.tf`, `outputs.tf`, `iam.tf`, and `environments/dev.tfvars`. `modules.tf` delegates to reusable `modules/<name>`, which declares the actual managed resources. Role assignments live in module `iam.tf`. All `tfvars` are safe, non-secret placeholders/names.

Each selected component uses a separate Azure Blob backend state key `dev/<component>.tfstate` in existing `johnzhang/tfstate`. Neither the RG nor the Storage Account nor `landing` nor `tfstate` is a Terraform-managed resource, preventing accidental destroy. Source checkout is from the Healthcare repository; OIDC belongs to the executing Self-Runner workflow.

**OneLake is not a separately deployable Azure Storage Account**: the optional `onelake` component creates a Lakehouse item backed by Fabric-managed OneLake. Fabric's Data Factory here is `fabric_data_pipeline`, NOT a redundant Azure Data Factory service. The originally approved minimal Fabric demo does not require a Lakehouse.

**Fabric requires separate permissions**: Azure RG Contributor + Blob Contributor do not imply Fabric tenant or workspace access. Fabric provider does not provision Fabric Trial Capacity. Grant Fabric SP API authorization and workspace roles separately; configure Self-Runner `FABRIC_WORKSPACE_ID` for existing-workspace components. The Workspace module must import any already-existing Fabric Workspace before a future apply, otherwise it would create a duplicate.

To run: Self-Runner → Actions → **Azure-Infra-TF** → Run workflow → `component` → `dev`. The Workflow executes `terraform fmt -check`, `init`, `validate`, and `plan` ONLY. For Fabric components without a configured workspace ID, the workflow will fail safely before planning; that is an external permission/config gate, not success. No Azure account keys, client secrets or live patient data are stored here.

Provider docs: https://registry.terraform.io/providers/microsoft/fabric/latest/docs
