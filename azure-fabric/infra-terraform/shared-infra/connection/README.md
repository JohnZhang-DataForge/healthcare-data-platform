# Shared Fabric Azure Blob Connection

Standalone, optional Terraform Root reusing `../../modules/connection`. Backend base key `shared-infra/connection.tfstate`, **default Terraform CLI Workspace**; no Workspace/OneLake/Capacity ownership.

The committed `terraform.tfvars` remains `connection = null` by design. Before any separate authorized Connection Plan/Apply, verify tenant-supported AzureBlobs connection metadata and supported user-controlled-code credentials, compare actual Storage and Fabric tenants, inventory existing matching connections, and approve a real Blob Reader principal. **Workspace identity does not support cross-tenant connections**, and connection creation alone never proves Notebook access. ServicePrincipal requires an existing Fabric Key Vault secret reference. Never commit or print secrets, tokens, or account keys. Existing connection ownership requires an explicit import decision; `prevent_destroy` remains active.

`connection_readiness.py` provides **read-only** live OIDC inspection of Azure subscription tenant, existing Storage account, account-scope IAM inventory, Fabric-supported AzureBlobs methods/credentials, and existing account connections. This does not write Azure/Fabric resources or Terraform State, grant permissions, or prove a Notebook read. The Self-Runner workflow must use an exact Healthcare source SHA and an inspect-only gate. The optional Root output `connection_id` stays null while disabled.

See [OpenSpec](../../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md).
