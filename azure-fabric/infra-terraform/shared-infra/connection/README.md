# Shared Fabric Azure Blob Connection

Standalone, optional Terraform Root reusing `../../modules/connection`. Backend base key: `shared-infra/connection.tfstate`, **default Terraform CLI Workspace**; unrelated to the named `johnzhang-test` workspace/onelake states. No paid Capacity or Workspace resources.

The checked-in `terraform.tfvars` is `connection=null` intentionally. Before a separate reviewed Plan/Apply: verify live AzureBlobs supported Connection metadata, exact Fabric tenant and an existing Connection inventory; choose an approved WorkspaceIdentity with real Azure Blob RBAC, or a ServicePrincipal backed **only** by an existing Fabric Key Vault secret reference. Never commit passwords, secret values or tokens. Confirm `allow_user_code` policy for Notebook access. Root output is `connection_id` (null when disabled). The existing module has `prevent_destroy`; do not silently import, delete or recreate connections.

This first stage is **source/static validation only**. Do not trigger Terraform Apply or assume a connection exists. See [OpenSpec](../../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md).
