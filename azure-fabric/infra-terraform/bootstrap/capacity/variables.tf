variable "environment" {
  description = "Unique HDP environment; never existing healthcare-omop."
  type        = string
  validation {
    condition     = length(var.environment) <= 40 && can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production", "healthcare-omop"], var.environment)
    error_message = "Safe distinct lowercase environment required."
  }
}
variable "capacity_mode" {
  description = "Default: reuse an existing Capacity. Never auto-fallback to creation."
  type        = string
  default     = "reuse-existing"
  validation {
    condition     = contains(["reuse-existing", "create-new"], var.capacity_mode)
    error_message = "Capacity mode must be reuse-existing or create-new."
  }
}
variable "existing_capacity_id" {
  description = "Unverified existing Fabric Capacity UUID used only in reuse mode."
  type        = string
  default     = null
  validation {
    condition     = var.existing_capacity_id == null ? true : (can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.existing_capacity_id)) && lower(var.existing_capacity_id) != "00000000-0000-0000-0000-000000000000")
    error_message = "Existing Capacity ID must be a nonzero UUID."
  }
}
variable "fabric_tenant_id" {
  description = "Tenant B. May equal Tenant A, but explicit and independent."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.fabric_tenant_id)) && lower(var.fabric_tenant_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Fabric Tenant must be a nonzero UUID."
  }
}
variable "capacity_subscription_id" {
  description = "Independent Tenant B Azure subscription; not implicitly the Storage subscription."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.capacity_subscription_id)) && lower(var.capacity_subscription_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Capacity subscription must be a nonzero UUID."
  }
}
variable "capacity_resource_group_id" {
  description = "Externally verified Tenant B RG ARM ID; this Root will never create/adopt it."
  type        = string
  default     = null
  validation {
    condition     = var.capacity_resource_group_id == null ? true : can(regex("^/subscriptions/[0-9a-fA-F-]+/resourceGroups/rg-hdp-[a-z0-9-]+$", var.capacity_resource_group_id))
    error_message = "Capacity RG must be an explicit isolated rg-hdp-* ARM ID."
  }
}
variable "capacity_region" {
  description = "Region explicitly reviewed for SKU availability and costs."
  type        = string
  default     = null
  validation {
    condition     = var.capacity_region == null ? true : can(regex("^[a-z][a-z0-9]{1,30}$", var.capacity_region))
    error_message = "Region must be a lowercase Azure location token."
  }
}
variable "capacity_sku" {
  description = "F SKU only, availability and price require independent quote."
  type        = string
  default     = null
  validation {
    condition     = var.capacity_sku == null ? true : contains(["F2", "F4", "F8", "F16", "F32", "F64", "F128", "F256", "F512", "F1024", "F2048"], var.capacity_sku)
    error_message = "Unsupported paid Fabric F SKU."
  }
}
variable "capacity_administrators" {
  description = "Explicit independently reviewed Capacity admin user identities."
  type        = list(string)
  default     = []
  validation {
    condition     = alltrue([for admin in var.capacity_administrators : can(regex("^[A-Za-z0-9._@-]{3,128}$", admin))]) && length(var.capacity_administrators) <= 10
    error_message = "Capacity admins must be a small list of nonempty non-secret identity values."
  }
}
variable "estimated_monthly_usd" {
  description = "Estimate, not an actual Azure price quote."
  type        = number
  default     = 0
  validation {
    condition     = var.estimated_monthly_usd >= 0 && var.estimated_monthly_usd <= 1000000
    error_message = "Monthly cost estimate outside bounds."
  }
}
variable "monthly_budget_usd" {
  description = "Manually reviewed upper bound, not a deployed Azure Budget."
  type        = number
  default     = 0
  validation {
    condition     = var.monthly_budget_usd >= 0 && var.monthly_budget_usd <= 1000000
    error_message = "Monthly budget outside bounds."
  }
}
variable "approved_cost_review_reference" {
  description = "Non-secret external review reference; NEVER sufficient evidence."
  type        = string
  default     = null
  validation {
    condition     = var.approved_cost_review_reference == null ? true : can(regex("^COST-REVIEW-[A-Z0-9-]{5,64}$", var.approved_cost_review_reference))
    error_message = "Cost review reference must be traceable and non-secret."
  }
}
variable "reviewed_source_sha" {
  description = "Exact 40-digit approved source SHA; enforce match in trusted workflow."
  type        = string
  default     = null
  validation {
    condition     = var.reviewed_source_sha == null ? true : can(regex("^[0-9a-f]{40}$", var.reviewed_source_sha))
    error_message = "Review must be pinned to a full Git commit SHA."
  }
}
variable "capacity_creation_approved" {
  type    = bool
  default = false
}
variable "independent_billing_approval_verified" {
  type    = bool
  default = false
}
variable "protected_environment_approval_verified" {
  type    = bool
  default = false
}
variable "subscription_and_rg_inventory_verified" {
  type    = bool
  default = false
}
variable "name_and_sku_quota_verified" {
  type    = bool
  default = false
}
variable "seed_operator_authorized" {
  type    = bool
  default = false
}
