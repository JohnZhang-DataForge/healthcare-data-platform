# New-environment Azure Blob connection only. No Storage, RBAC, or existing
# Connection is created/adopted. The external approval flags are NOT live checks.
resource "fabric_connection" "azure_blob" {
  display_name                        = var.connection_name
  connectivity_type                   = "ShareableCloud"
  privacy_level                       = "Organizational"
  allow_usage_in_user_controlled_code = var.user_controlled_code_approved

  connection_details = {
    type            = "AzureBlobs"
    creation_method = "AzureBlobs"
    parameters = [
      { name = "account", value = var.storage_account_name },
      { name = "domain", value = var.blob_domain },
    ]
  }

  # Fabric provider OIDC is the deployment identity, NOT the Blob reader.
  # For ServicePrincipal the secret remains in an existing Key Vault, reached
  # through an existing, separately inventoried Fabric Key Vault connection.
  # WorkspaceIdentity contains no secret and requires its own RBAC verification.
  credential_details = {
    credential_type     = var.reader_credential_type
    single_sign_on_type = "None"
    skip_test_connection = false
    service_principal_credentials = var.reader_credential_type == "ServicePrincipal" ? {
      client_id = var.blob_reader_client_id
      tenant_id = var.blob_reader_tenant_id
      service_principal_secret_reference = {
        connection_id = var.key_vault_connection_id
        secret_name   = var.key_vault_secret_name
        version       = var.key_vault_secret_version
      }
    } : null
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition = (
        var.connection_creation_approved &&
        var.connection_inventory_verified &&
        var.connector_metadata_verified &&
        var.blob_domain_verified &&
        var.reader_access_verified &&
        var.backend_operator_client_id != var.fabric_deployer_client_id &&
        var.connection_name == "HDP-${var.environment}-azureblobs" &&
        var.storage_account_name == "johnzhang"
      )
      error_message = "Connection creation requires independent inventory, approved AzureBlobs metadata/domain, Blob Reader access and HDP naming."
    }
    precondition {
      condition = var.reader_credential_type == "WorkspaceIdentity" ? (
        var.workspace_identity_verified
      ) : (
        var.key_vault_reference_verified &&
        var.blob_reader_client_id != null &&
        var.blob_reader_tenant_id == var.backend_tenant_id &&
        var.blob_reader_client_id != var.backend_operator_client_id &&
        var.blob_reader_client_id != var.fabric_deployer_client_id &&
        var.key_vault_connection_id != null &&
        var.key_vault_secret_name != null
      )
      error_message = "Reader credentials must be separately approved: existing Key Vault reference plus distinct Tenant-A reader, or verified Workspace Identity."
    }
  }
}
