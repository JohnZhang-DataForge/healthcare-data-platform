# Azure / Fabric Terraform — developer entry

**Canonical runnable source:** `azure-fabric/infra-terraform/`, selected by [Self-Runner / Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml). This directory manages **infrastructure resources and their permissions**, not the PostgreSQL snapshot exporter or complete Fabric Spark/Data Pipeline business logic. See the [Azure/Fabric code-root guide](../README.md) for the rest of the subsystem and [technical Terraform design](docs/ARCHITECTURE.md) for IAM, state, adoption and historical regression evidence.

The legacy `azure/infra-terraform/` copy was removed from `main` after validating identical implementation files and the Self-Runner cutover. Its [pre-retirement snapshot](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/a0891d08eb934ef1c954576c9ca006fe99b1c02b/azure/infra-terraform) is retained in Git history for reference and rollback. `azure-fabric/infra-terraform/` is the only active IaC source. No Terraform Apply/Destroy or cloud data processing was performed by this code-organization change.

## Where Terraform code lives

```text
infra-terraform/
├── .gitignore
├── README.md
├── components/
│   ├── storage/
│   ├── workspace/
│   ├── onelake/
│   ├── data-factory/
│   ├── notebook/
│   ├── warehouse/
│   └── foundation-iam/
├── modules/
│   └── <matching-seven-modules>/
└── docs/ARCHITECTURE.md
```

Each `components/<name>/` is a separate **Terraform root** and independent remote State. Each root contains `versions.tf`, `providers.tf`, `modules.tf`, `variables.tf`, `outputs.tf`, `iam.tf` and `environments/dev.tfvars`. The matching `modules/<name>/` defines the actual resources, data lookups, outputs and supported component-owned IAM. **Modules define HOW; root components select WHAT and WHO; tfvars define environment settings.**

| Root | Resource and responsibilities | Safety / lifecycle |
| --- | --- | --- |
| `storage` | Look up existing Azure Storage/Blob landing; optional container RBAC | Existing storage is **not** provisioned anew by these data lookups |
| `workspace` | Fabric Workspace and workspace memberships | Existing manually created `healthcare-omop` requires verification/import before any adoption or Apply |
| `onelake` | Fabric Lakehouse plus optional preview data-access security | `data_access_roles = {}` by default: no new grants |
| `notebook` | Fabric Notebook item | Source-controlled **fail-closed bootstrap only**, not working ETL |
| `data-factory` | Fabric **Data Pipeline item**, not an Azure Data Factory resource | Fail Activity until a real Notebook ID is configured |
| `warehouse` | Optional Fabric Warehouse item | Future scope, not required for OneLake-first MVP |
| `foundation-iam` | Optional shared Azure Resource Group-level role bindings | Not the owner of per-component Blob/OneLake/Workspace grants |

**IAM is component-owned:** module `iam.tf` files contain resource-specific definitions or explicit no-op/boundary comments. Entra **object IDs** (not client/application IDs) are required for principal bindings. Existing bootstrap/OIDC credentials and Portal-created permissions remain outside Terraform's ownership unless separately reviewed and imported. See [IAM ownership and OneLake preview details](docs/ARCHITECTURE.md#iam-and-existing-resource-boundaries).

## Execution and remote State

- Runner: **Self-Runner**, manual workflow dispatch on its `main` branch; `component` must be one of the seven roots and `environment=dev`.
- Workflow: `operation=plan|apply` with **plan as default**; it does **not** expose `destroy`. The selected operation performs `fmt -check`, Azure OIDC Blob backend `init`, `validate` and a saved `plan`; selected `apply` executes that saved plan only after built-in guards. Workflow capability does **not** authorize Apply.
- Backend: existing Azure Blob Storage Account `johnzhang`, container `tfstate`, independent State keys `dev/<component>.tfstate` with OIDC/Azure AD authentication. Do **not** move State to Kubernetes `local-path`, a local runner directory or Git.
- GitHub OIDC federation is tied to the **Self-Runner identity and ref**, not the Healthcare source repository. Fabric tenant permissions, workspace membership, Azure management-plane RBAC and Blob data-plane RBAC are separate checks.
- Each workflow run checks out Healthcare `main` and prints the actual source SHA; use the logged SHA as verification evidence. An existing manually created Workspace must **not** be duplicated. The workflow blocks a Workspace Apply when the matching Terraform State lacks the existing resource.
- Even a Plan accesses the cloud and remote State and may acquire a lock. This file is a reference, **not** permission to dispatch a run or change any resources.

All seven roots passed fresh **Plan-only** regression on October 16, 2026 against the new `azure-fabric/` path. Historical counts, run IDs and boundaries are retained in [ARCHITECTURE.md](docs/ARCHITECTURE.md#verified-plan-evidence); Plan success is not proof of resource creation, Item runtime execution, Fabric Git synchronization, dataset write or business E2E acceptance.

## Bootstrap is deliberately non-operational

The [Notebook Terraform module](modules/notebook/main.tf) currently reads [`definitions/notebook-content.py`](modules/notebook/definitions/notebook-content.py), which intentionally raises an error. The [Data Pipeline module](modules/data-factory/main.tf) uses [`pipeline-disabled.json`](modules/data-factory/definitions/pipeline-disabled.json) until an actual Notebook GUID is known. The alternate [Notebook activity JSON](modules/data-factory/definitions/pipeline-notebook.json) is **not** proof of a connected or working pipeline.

Business code added later under `azure-fabric/workspaces/healthcare-omop/` must use real Fabric-native Git item metadata and a deliberate, single source-of-truth delivery model. Do not move these historical Terraform Bootstrap files there by renaming alone.

## Developer checklist

1. Choose **one** Terraform root and inspect its `environments/dev.tfvars`, provider requirements, module implementation, IAM and existing State ownership.
2. Distinguish **data lookup vs managed resource**, especially existing `storage` and `workspace`, and preview OneLake IAM.
3. For documentation-only refactors, verify repository links and source paths without any remote command. Runtime Plan/Apply or credentials checks are **separate work**.
4. For authorized infrastructure changes, follow [Safe Operations](../../documents/engineering/operations/SAFE-OPERATIONS.md), verify the source SHA, capture Plan and State evidence and obtain independent authorization before any Apply.

The [complete technical design and validation history](docs/ARCHITECTURE.md) is the maintained source for detailed lifecycle cautions; the [system overview](../../documents/systems/azure-fabric/README.md) is the human-readable business architecture.
