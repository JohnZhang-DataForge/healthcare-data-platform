variable "environment" {
  description = "New HDP environment, not a legacy dev/workspace."
  type        = string

  validation {
    condition     = length(var.environment) <= 40 && can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production", "healthcare-omop"], var.environment)
    error_message = "Environment must use unique lowercase kebab-case, not a legacy name."
  }
}

variable "bootstrap_mode" {
  description = "Explicit, fail-closed Storage ownership; never auto-switch."
  type        = string
  default     = "reuse-existing"

  validation {
    condition     = contains(["reuse-existing", "fresh-bootstrap"], var.bootstrap_mode)
    error_message = "Choose explicitly reuse-existing or fresh-bootstrap."
  }
}

variable "backend_tenant_id" {
  description = "Tenant A where Backend Operator and Blob Reader identities reside."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.backend_tenant_id)) && lower(var.backend_tenant_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Tenant A must be a nonzero UUID."
  }
}

variable "storage_subscription_id" {
  description = "Tenant A subscription for new Storage; must be externally inventoried."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.storage_subscription_id)) && lower(var.storage_subscription_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Storage subscription must be a nonzero UUID."
  }
}

variable "storage_region" {
  description = "Explicit Azure region; planned only, not availability verified."
  type        = string
  default     = null

  validation {
    condition     = var.storage_region == null ? true : can(regex("^[a-z][a-z0-9]{1,30}$", var.storage_region))
    error_message = "Region must be a lowercase Azure location token."
  }
}

variable "fresh_storage_account_name" {
  description = "Fresh HDP-only account; never johnzhang or an existing resource."
  type        = string
  default     = null

  validation {
    condition     = var.fresh_storage_account_name == null ? true : (can(regex("^hdp[a-z0-9]{0,21}$", var.fresh_storage_account_name)) && length(var.fresh_storage_account_name) >= 3 && length(var.fresh_storage_account_name) <= 24 && var.fresh_storage_account_name != "johnzhang")
    error_message = "Fresh storage name must start hdp, be 3-24 chars, and not name a legacy account."
  }
}

variable "reuse_existing_storage_account_id" {
  description = "An external, previously verified legacy account ARM ID; never imported or queried here."
  type        = string
  default     = null

  validation {
    condition     = var.reuse_existing_storage_account_id == null ? true : can(regex("^/subscriptions/[0-9a-fA-F-]+/resourceGroups/[A-Za-z0-9_.()-]+/providers/Microsoft[.]Storage/storageAccounts/johnzhang$", var.reuse_existing_storage_account_id))
    error_message = "Reuse mode permits only an explicitly inventoried johnzhang ARM account ID."
  }
}

variable "fresh_storage_creation_approved" {
  description = "Default DENY, insufficient without separate inventory, Seed and State custody approvals."
  type        = bool
  default     = false
}

variable "new_resource_inventory_verified" {
  description = "Default false. Claim is never an external proof of name/subscription vacancy."
  type        = bool
  default     = false
}

variable "seed_operator_authorized" {
  description = "Default false. Does NOT grant Seed Operator permission or Graph/Azure roles."
  type        = bool
  default     = false
}

variable "initial_state_custody_verified" {
  description = "Default false. Protected local/bootstrap State, backup and recovery reviewed out of band."
  type        = bool
  default     = false
}

variable "private_connectivity_verified" {
  description = "Default false. Backend/Reader must be able to reach private Storage; not supplied by this root."
  type        = bool
  default     = false
}

variable "rbac_creation_approved" {
  description = "Default DENY; independent approval for container-scope RBAC."
  type        = bool
  default     = false
}

variable "identity_provenance_verified" {
  description = "Default false; identity root outputs are not automatically live verified."
  type        = bool
  default     = false
}

variable "backend_operator_object_id" {
  description = "Tenant A Backend Operator SERVICE PRINCIPAL object ID, not client/application ID."
  type        = string
  default     = null

  validation {
    condition     = var.backend_operator_object_id == null ? true : (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.backend_operator_object_id)) && lower(var.backend_operator_object_id) != "00000000-0000-0000-0000-000000000000")
    error_message = "Backend Operator SP object ID must be nonzero canonical UUID."
  }
}

variable "blob_reader_object_id" {
  description = "Tenant A Blob Reader SERVICE PRINCIPAL object ID, never the Fabric Deployer ID."
  type        = string
  default     = null

  validation {
    condition     = var.blob_reader_object_id == null ? true : (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.blob_reader_object_id)) && lower(var.blob_reader_object_id) != "00000000-0000-0000-0000-000000000000")
    error_message = "Blob Reader SP object ID must be nonzero canonical UUID."
  }
}
