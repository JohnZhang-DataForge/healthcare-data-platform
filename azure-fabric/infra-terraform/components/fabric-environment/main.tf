# Local Terraform state guard only; does not create or alter any Fabric object.
resource "terraform_data" "workspace_selection" {
  input = terraform.workspace

  lifecycle {
    precondition {
      condition     = terraform.workspace != "default"
      error_message = "Select a named Terraform CLI Workspace; 'default' must not deploy Fabric."
    }
    precondition {
      condition     = terraform.workspace != "healthcare-omop" || var.existing_workspace_imported
      error_message = "Existing healthcare-omop must be inventoried and imported into this ROOT and CLI Workspace state before planning."
    }
  }
}

module "workspace" {
  source = "../../modules/workspace"

  workspace_name   = terraform.workspace
  description      = var.description
  capacity_id      = var.capacity_id
  role_assignments = var.role_assignments

  depends_on = [terraform_data.workspace_selection]
}

module "onelake" {
  source = "../../modules/onelake"

  workspace_id      = module.workspace.workspace_id
  lakehouse_name    = var.lakehouse_name
  data_access_roles = var.data_access_roles
}

# A Fabric Connection is tenant-scoped, not nested inside a Fabric Workspace.
# Use a workspace-specific display name and unique Terraform State ownership.
module "connection" {
  count  = var.connection == null ? 0 : 1
  source = "../../modules/connection"

  connection_name                   = var.connection.name
  storage_account_name             = var.connection.storage_account_name
  blob_domain                      = var.connection.blob_domain
  reader_credential_type           = var.connection.reader_type
  reader_client_id                 = try(var.connection.service_principal.client_id, null)
  reader_tenant_id                 = try(var.connection.service_principal.tenant_id, null)
  key_vault_connection_id         = try(var.connection.service_principal.key_vault_connection_id, null)
  key_vault_secret_name           = try(var.connection.service_principal.key_vault_secret_name, null)
  key_vault_secret_version        = try(var.connection.service_principal.key_vault_secret_version, null)
  allow_usage_in_user_controlled_code = var.connection.allow_user_code

  depends_on = [terraform_data.workspace_selection]
}
