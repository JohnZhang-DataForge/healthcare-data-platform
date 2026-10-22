# Shared Fabric Azure Blob Connection

Standalone, optional Terraform Root reusing `../../modules/connection`. Backend base key `shared-infra/connection.tfstate`, **default Terraform CLI Workspace**; no Workspace/OneLake/Capacity ownership.

The committed instance `terraform.tfvars` now stages a single `healthcare-omop-landing-blob` AzureBlobs WorkspaceIdentity Connection candidate, while the reusable Terraform variable still defaults to `null` when no instance is configured. **Staging source does not mean cloud deployment.** Before any separate authorized Connection Plan/Apply, verify tenant-supported AzureBlobs connection metadata and supported user-controlled-code credentials, compare actual Storage and Fabric tenants, inventory existing matching connections, and approve a real Blob Reader principal. **Workspace identity does not support cross-tenant connections**, and connection creation alone never proves Notebook access. ServicePrincipal requires an existing Fabric Key Vault secret reference. Never commit or print secrets, tokens, or account keys. Existing connection ownership requires an explicit import decision; `prevent_destroy` remains active.

`connection_readiness.py` provides **read-only** live OIDC inspection of Azure subscription tenant, existing Storage account, account-scope IAM inventory, Fabric-supported AzureBlobs methods/credentials, and existing account connections. This does not write Azure/Fabric resources or Terraform State, grant permissions, or prove a Notebook read. The Self-Runner workflow must use an exact Healthcare source SHA and an inspect-only gate. The Root output `connection_id` becomes known only after a separately authorized Apply; source and Plan do not prove the Connection exists. The live Reader RBAC Apply is currently **blocked by Azure `Microsoft.Authorization/roleAssignments/write` 403** for the Runner principal, and this Connection MUST NOT be applied until Reader authorization is present/read back.

See [OpenSpec](../../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md).

### Provider 1.13.0 Workspace Identity skip-test caveat

Live [Self-Runner Plan #39710912279](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710912279) rejects `credential_details.skip_test_connection=true` at Plan with `Unsupported skip test connection`. For this provider version use `false`; this does **not** make Fabric Workspace Identity Connection status health-check reliable. Actual Blob reads are the acceptance criterion. No Connection created by that failed Plan.
