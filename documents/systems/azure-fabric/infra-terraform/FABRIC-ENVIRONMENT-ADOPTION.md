---
status: active
scope: azure-fabric-terraform-environment-adoption
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由原源码路径 `azure-fabric/infra-terraform/components/fabric-environment/README.md` 原文迁入。保留历史证据和安全边界；本文是文档/源码合同，不代表本次执行云端读取或 Terraform Apply。最新真实状态以 [系统 CODE Map](../CODE.md)、[Terraform CODE Map](CODE.md) 和对应 Run 为准。

# Fabric Environment — Current Fabric account

This records the **existing composable Terraform Root** and its historical adoption requirements; it is not an instruction to recreate resources or automatically adopt existing State. Refer to the current [Terraform CODE map](CODE.md) and [Architecture](ARCHITECTURE.md) for later verified deployment changes. It reuses
`modules/workspace`, `modules/onelake` and `modules/connection`.

The first, **already existing** Fabric Workspace is `healthcare-omop`.
For this project the **non-default Terraform CLI Workspace name MUST match the
Fabric Workspace display name exactly**. Do not create a second `healthcare-omop`.

## Existing state handoff (operator verification required; historical guidance)

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
# Review the versioned nonsecret healthcare-omop.tfvars against actual cloud values.
# Supply the existing Workspace Capacity ID before Plan/Apply.
terraform init -backend-config="storage_account_name=johnzhang" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=fabric/platform.tfstate" \
  -backend-config="use_azuread_auth=true"
terraform workspace select healthcare-omop || terraform workspace new healthcare-omop
# Authorized ONLY after checking old state ownership:
# terraform import -var-file=environments/healthcare-omop.tfvars \
#   -var=existing_workspace_imported=true \
#   'module.workspace.fabric_workspace.current' '<REAL_WORKSPACE_GUID>'
# Verify current State address before changing existing_workspace_imported=true.
terraform plan -var-file=environments/healthcare-omop.tfvars
```

Do not execute the example plan while the example has unverified Capacity,
Reader configuration, or an unimported existing Workspace. In particular,
AzureRM derives a separate blob path for non-default CLI Workspaces; do
not also vary the base Backend Key per Workspace. Secrets never enter Git.

The Self-Runner workflow reads the versioned `environments/healthcare-omop.tfvars`
(not `.tfvars.example`), obtains the actual Capacity ID from `FABRIC_CAPACITY_ID`,
and optionally accepts a nonsecret `FABRIC_LANDING_CONNECTION_CONFIG` JSON
object. It must verify expected Workspace GUID from `FABRIC_WORKSPACE_ID` before
Plan/Apply. `inspect` is read-only; `adopt` is an explicit State mutation and\nrequires separate review of legacy State ownership. No auto-adoption occurs\nfrom a normal `plan` or `apply`. These repository variables are not verified
by code review, so runtime readiness remains pending.\n\nThe Connection is optional until a supported, authorized existing Landing
Reader identity is configured. `WorkspaceIdentity` or a `ServicePrincipal`
with an existing Key Vault connection can be used if supported by the actual
tenant and connector. No anonymous connection fallback; no Storage creation.

The sole owners of Notebook/Pipeline business code are `fabric-cicd` and Git.
A Module output is an actual Fabric ID after deployment; it is **not** proof
of a successful connection read or a completed ETL run.
