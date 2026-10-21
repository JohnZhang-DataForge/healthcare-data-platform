# Only an existing, reviewed data source may be configured.
# Account selection belongs in the instance terraform.tfvars, not this reusable Root.
variable "connection" {
  description = "Optional approved AzureBlobs connection. Null disables creation. Never put secrets here."
  type = object({
    name                 = string
    storage_account_name = string
    blob_domain          = string
    reader_type          = string
    allow_user_code      = optional(bool, false)
    service_principal = optional(object({
      client_id                = string
      tenant_id                = string
      key_vault_connection_id  = string
      key_vault_secret_name    = string
      key_vault_secret_version = optional(string)
    }))
  })
  default = null

  validation {
    condition = var.connection == null ? true : (
      var.connection.reader_type == "WorkspaceIdentity" ?
      var.connection.service_principal == null :
      var.connection.reader_type == "ServicePrincipal" && var.connection.service_principal != null
    )
    error_message = "WorkspaceIdentity MUST omit service_principal; ServicePrincipal MUST supply Key Vault secret reference metadata."
  }

  validation {
    condition = var.connection == null ? true : (
      can(regex("^[a-z0-9]{3,24}$", var.connection.storage_account_name)) &&
      length(trimspace(var.connection.name)) > 0 &&
      length(trimspace(var.connection.blob_domain)) > 0
    )
    error_message = "A valid existing Storage account name, Connection name and Blob domain are required."
  }
}
