# A Fabric Connection is account/tenant scoped, not a Workspace child.
# The default configuration intentionally creates no resources.
module "azure_blob_connection" {
  count  = var.connection == null ? 0 : 1
  source = "../../modules/connection"

  connection_name                     = var.connection.name
  storage_account_name                = var.connection.storage_account_name
  blob_domain                         = var.connection.blob_domain
  reader_credential_type              = var.connection.reader_type
  reader_client_id                    = try(var.connection.service_principal.client_id, null)
  reader_tenant_id                    = try(var.connection.service_principal.tenant_id, null)
  key_vault_connection_id             = try(var.connection.service_principal.key_vault_connection_id, null)
  key_vault_secret_name               = try(var.connection.service_principal.key_vault_secret_name, null)
  key_vault_secret_version            = try(var.connection.service_principal.key_vault_secret_version, null)
  allow_usage_in_user_controlled_code = var.connection.allow_user_code
}
