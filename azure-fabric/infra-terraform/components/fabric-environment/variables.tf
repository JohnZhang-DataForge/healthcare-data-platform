variable "description" {
  type    = string
  default = "Healthcare OMOP analytical platform"
}

variable "capacity_id" {
  type        = string
  description = "Existing Fabric Capacity ID; an empty string leaves it unset."
  default     = ""
}

variable "role_assignments" {
  type = map(object({
    principal_id   = string
    principal_type = string
    role           = string
  }))
  default = {}
}

variable "lakehouse_name" {
  type    = string
  default = "lh_omop_analytics"
}

variable "data_access_roles" {
  type = map(object({
    paths   = list(string)
    actions = list(string)
    entra_members = list(object({
      object_id   = string
      object_type = string
      tenant_id   = optional(string)
    }))
  }))
  default = {}
}

# No connection is created until the existing data Reader is explicitly configured.
# All values in this object are nonsecret identifiers/metadata, not credentials.
variable "connection" {
  type = object({
    name                 = string
    storage_account_name = string
    blob_domain          = string
    reader_type          = string
    service_principal = optional(object({
      client_id               = string
      tenant_id               = string
      key_vault_connection_id = string
      key_vault_secret_name   = string
      key_vault_secret_version = optional(string)
    }))
    allow_user_code = optional(bool, false)
  })
  default = null

  validation {
    condition = var.connection == null ? true : (
      contains(["WorkspaceIdentity", "ServicePrincipal"], var.connection.reader_type) &&
      (var.connection.reader_type != "ServicePrincipal" || var.connection.service_principal != null) &&
      (var.connection.reader_type != "WorkspaceIdentity" || var.connection.service_principal == null)
    )
    error_message = "Select a supported Reader type; ServicePrincipal requires a Key Vault secret reference and WorkspaceIdentity must not include one."
  }
}

# The existing healthcare-omop must first be independently inventoried and
# explicitly imported into this ROOT + CLI Workspace; this is not an import action.
variable "existing_workspace_imported" {
  type    = bool
  default = false
}
