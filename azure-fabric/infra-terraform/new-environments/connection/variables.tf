# Reserved old environment names are forbidden.
variable "environment" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production"], var.environment)
    error_message = "Invalid environment; use only independently verified, non-secret values."
  }
}

# Must equal HDP-<environment>-azureblobs.
variable "connection_name" {
  type = string
  validation {
    condition     = can(regex("^HDP-[a-z][a-z0-9-]*-azureblobs$", var.connection_name)) && length(var.connection_name) <= 123
    error_message = "Invalid connection_name; use only independently verified, non-secret values."
  }
}

# Existing landing account, never provisioned by this Root.
variable "storage_account_name" {
  type = string
  validation {
    condition     = var.storage_account_name == "johnzhang"
    error_message = "Invalid storage_account_name; use only independently verified, non-secret values."
  }
}

# AzureBlobs domain is mandatory and tenant-verified; no guessed default.
variable "blob_domain" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9]+(?:[.-][a-z0-9]+)*$", var.blob_domain)) && length(var.blob_domain) <= 253
    error_message = "Invalid blob_domain; use only independently verified, non-secret values."
  }
}

# Provider 1.13 supports two reviewed, credential-safe modes.
variable "reader_credential_type" {
  type = string
  validation {
    condition     = contains(["ServicePrincipal", "WorkspaceIdentity"], var.reader_credential_type)
    error_message = "Invalid reader_credential_type; use only independently verified, non-secret values."
  }
}

# Tenant A, the Blob Storage owner.
variable "backend_tenant_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.backend_tenant_id)) && var.backend_tenant_id != "00000000-0000-0000-0000-000000000000"
    error_message = "Invalid backend_tenant_id; use only independently verified, non-secret values."
  }
}

# Independently authenticated backend Operator application.
variable "backend_operator_client_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.backend_operator_client_id)) && var.backend_operator_client_id != "00000000-0000-0000-0000-000000000000"
    error_message = "Invalid backend_operator_client_id; use only independently verified, non-secret values."
  }
}

# Independently authenticated Fabric provider application.
variable "fabric_deployer_client_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.fabric_deployer_client_id)) && var.fabric_deployer_client_id != "00000000-0000-0000-0000-000000000000"
    error_message = "Invalid fabric_deployer_client_id; use only independently verified, non-secret values."
  }
}

# Tenant A identity owning data access; SP only.
variable "blob_reader_tenant_id" {
  type = string
  default = null
  validation {
    condition     = var.blob_reader_tenant_id == null || (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.blob_reader_tenant_id)) && var.blob_reader_tenant_id != "00000000-0000-0000-0000-000000000000")
    error_message = "Invalid blob_reader_tenant_id; use only independently verified, non-secret values."
  }
}

# Third application identity with read-only Blob access; SP only.
variable "blob_reader_client_id" {
  type = string
  default = null
  validation {
    condition     = var.blob_reader_client_id == null || (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.blob_reader_client_id)) && var.blob_reader_client_id != "00000000-0000-0000-0000-000000000000")
    error_message = "Invalid blob_reader_client_id; use only independently verified, non-secret values."
  }
}

# ID of pre-existing, authorized Fabric Key Vault connection; SP only.
variable "key_vault_connection_id" {
  type = string
  default = null
  validation {
    condition     = var.key_vault_connection_id == null || (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.key_vault_connection_id)) && var.key_vault_connection_id != "00000000-0000-0000-0000-000000000000")
    error_message = "Invalid key_vault_connection_id; use only independently verified, non-secret values."
  }
}

# Secret NAME only. Never accept or store the secret VALUE.
variable "key_vault_secret_name" {
  type = string
  default = null
  validation {
    condition     = var.key_vault_secret_name == null || can(regex("^[A-Za-z0-9-]{1,127}$", var.key_vault_secret_name))
    error_message = "Invalid key_vault_secret_name; use only independently verified, non-secret values."
  }
}

# Optional Key Vault secret version; no secret value.
variable "key_vault_secret_version" {
  type = string
  default = null
  validation {
    condition     = var.key_vault_secret_version == null || can(regex("^[0-9a-fA-F]{32}$", var.key_vault_secret_version))
    error_message = "Invalid key_vault_secret_version; use only independently verified, non-secret values."
  }
}

# Explicit external approval acknowledgement, never live inventory.
variable "connection_creation_approved" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "connection_inventory_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "connector_metadata_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "blob_domain_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "reader_access_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "key_vault_reference_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "workspace_identity_verified" {
  type = bool
  default = false
}

# Explicit external approval acknowledgement, never live inventory.
variable "user_controlled_code_approved" {
  type = bool
  default = false
}
