variable "connection_name" {
  type = string
  validation {
    condition     = length(trimspace(var.connection_name)) > 0 && length(var.connection_name) <= 123
    error_message = "Connection name must be nonempty and at most 123 characters."
  }
}

variable "storage_account_name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "A valid existing Azure Storage account name is required."
  }
}

variable "blob_domain" {
  type = string
  validation {
    condition     = length(trimspace(var.blob_domain)) > 0
    error_message = "The existing Azure Blob domain is required."
  }
}

variable "reader_credential_type" {
  type = string
  validation {
    condition     = contains(["WorkspaceIdentity", "ServicePrincipal"], var.reader_credential_type)
    error_message = "Only WorkspaceIdentity or ServicePrincipal is supported."
  }
}

variable "reader_client_id" {
  type    = string
  default = null
}
variable "reader_tenant_id" {
  type    = string
  default = null
}
variable "key_vault_connection_id" {
  type    = string
  default = null
}
variable "key_vault_secret_name" {
  type    = string
  default = null
}
variable "key_vault_secret_version" {
  type    = string
  default = null
}

variable "allow_usage_in_user_controlled_code" {
  type    = bool
  default = false
}
