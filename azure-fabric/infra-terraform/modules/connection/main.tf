# Reusable Azure Blob connection; existing Storage and Reader permissions are external.
resource "fabric_connection" "current" {
  display_name                        = var.connection_name
  connectivity_type                   = "ShareableCloud"
  privacy_level                       = "Organizational"
  allow_usage_in_user_controlled_code = var.allow_usage_in_user_controlled_code

  connection_details = {
    type            = "AzureBlobs"
    creation_method = "AzureBlobs"
    parameters = [
      { name = "account", value = var.storage_account_name },
      { name = "domain", value = var.blob_domain },
    ]
  }

  # The deployer credential is NOT the data source credential.
  # ServicePrincipal uses an existing Fabric Key Vault connection; no raw secrets.
  credential_details = {
    credential_type     = var.reader_credential_type
    single_sign_on_type = "None"
    # Fabric Provider 1.13.0 rejects skip_test_connection=true for
    # WorkspaceIdentity during Plan. This FALSE is a provider constraint,
    # not a claim that credential health is verifiable by connection status.
    # Verify data access with a real Notebook/Pipeline Blob read.
    skip_test_connection = false
    service_principal_credentials = var.reader_credential_type == "ServicePrincipal" ? {
      client_id = var.reader_client_id
      tenant_id = var.reader_tenant_id
      service_principal_secret_reference = {
        connection_id = var.key_vault_connection_id
        secret_name   = var.key_vault_secret_name
        version       = var.key_vault_secret_version
      }
    } : null
  }

  lifecycle {
    prevent_destroy = true
  }
}
