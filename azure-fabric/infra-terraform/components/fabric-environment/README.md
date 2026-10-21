# Fabric Environment — Current Fabric account

This is the **composable Terraform Root**, not a new bootstrap system. It reuses
`modules/workspace`, `modules/onelake` and `modules/connection`.

The first, **already existing** Fabric Workspace is `healthcare-omop`.
For this project the **non-default Terraform CLI Workspace name MUST match the
Fabric Workspace display name exactly**. Do not create a second `healthcare-omop`.

## Existing state handoff (NOT YET VERIFIED)

Before a real Init/Plan/Apply, inspect existing `dev/workspace.tfstate`,
any other legacy Root state and the real Fabric Workspace GUID. Make a
deliberate ownership decision. Only when it is confirmed that no other active
state will manage the object, import the existing GUID to:

`module.workspace.fabric_workspace.current`

under this Root with CLI Workspace `healthcare-omop`. That import is a
separate authenticated operation; **this repository does not import anything
automatically**. The Boolean `existing_workspace_imported` is a safety
acknowledgement, not a live State query. Verify with `terraform state list`
and `terraform state show` before setting it true; do not use it as a bypass.

An authenticated operator can use the following as a sequence **after**
checking ownership and preparing access. These are reference commands, not
commands executed in this PR:

```bash
cd azure-fabric/infra-terraform/components/fabric-environment
cp environments/healthcare-omop.tfvars.example environments/healthcare-omop.tfvars
# Review/edit this local tfvars against the REAL workspace and capacity before deployment.
terraform init -backend-config="storage_account_name=johnzhang" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=fabric/platform.tfstate" \
  -backend-config="use_azuread_auth=true"
terraform workspace select healthcare-omop || terraform workspace new healthcare-omop
# Authorized ONLY after checking old state ownership:
# terraform import -var-file=environments/healthcare-omop.tfvars \
#   'module.workspace.fabric_workspace.current' '<REAL_WORKSPACE_GUID>'
# Verify current State address before changing existing_workspace_imported=true.
terraform plan -var-file=environments/healthcare-omop.tfvars
```

Do not execute the example plan while the example has unverified Capacity,
Reader configuration, or an unimported existing Workspace. In particular,
AzureRM derives a separate blob path for non-default CLI Workspaces; do
not also vary the base Backend Key per Workspace. Secrets never enter Git.

The Connection is optional until a supported, authorized existing Landing
Reader identity is configured. `WorkspaceIdentity` or a `ServicePrincipal`
with an existing Key Vault connection can be used if supported by the actual
tenant and connector. No anonymous connection fallback; no Storage creation.

The sole owners of Notebook/Pipeline business code are `fabric-cicd` and Git.
A Module output is an actual Fabric ID after deployment; it is **not** proof
of a successful connection read or a completed ETL run.
