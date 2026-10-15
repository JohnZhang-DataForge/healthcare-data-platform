# Resource-based Terraform Architecture

Status: IaC scaffolding only. **NO APPLY**.

```text
Healthcare Repo azure/infra-terraform/
   components/<selector>/ -> modules.tf -> modules/<selector>/main.tf
         |                                      |
         |                              iam.tf (optional authorization)
         +---- non-secret environments/dev.tfvars
         +---- independent dev/<selector>.tfstate in johnzhang/tfstate
                     ^
               GitHub OIDC
                     |
Self-Runner/.github/workflows/azure-infra.yaml  (Azure-Infra-TF)
```

## Stages and ownership
1. Existing Azure: `OMOP`, `johnzhang`, `landing`, `tfstate` are manually bootstrapped. `storage` reads them; `iam` has empty default RBAC changes. No Terraform apply required to inspect.
2. Fabric Workspace: use existing Fabric Trial workspace GUID via env or explicitly reconcile/import previously created Workspace. Do not create a second one by mistake.
3. OneLake is Fabric-managed; a Lakehouse is optional and not required by the direct Blob → Notebook → Warehouse path. The `onelake` root is available on-demand.
4. Fabric Data Factory Pipeline, Notebook, Warehouse items are declared as empty shells only. Actual ETL/notebook definition and SQL promotion are separate, later code delivery.
5. Azure Blob Exporter: not Terraform; Python Azure SDK via Self-Runner's OIDC and existing landing Blob Contributor.
6. Capacity not managed in v1 (Trial unsupported by Fabric Terraform provider). Monitor charges and keep Fabric permissions separate.

## Deploy gate to add later only with separate approval
Future CI apply would require a reviewed SHA, approval/environment protection, allowlist, serialized state lock, cost/delete gates and explicit management authorization. The current workflow intentionally does not contain an apply path. No secrets in tfvars, code, plan artifacts, or state logs.
