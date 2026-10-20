variable "environment" {
  description = "Isolated environment; never an existing deployment."
  type        = string
  validation {
    condition     = length(var.environment) <= 40 && can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production", "healthcare-omop"], var.environment)
    error_message = "Expected safe, distinct lowercase kebab-case environment."
  }
}
variable "backend_tenant_id" {
  description = "Tenant A, Backend Operator and Blob Reader identity."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.backend_tenant_id)) && lower(var.backend_tenant_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Expected nonzero Tenant A UUID."
  }
}
variable "fabric_tenant_id" {
  description = "Tenant B (may equal A), independent Fabric Deployer identity."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.fabric_tenant_id)) && lower(var.fabric_tenant_id) != "00000000-0000-0000-0000-000000000000"
    error_message = "Expected nonzero Tenant B UUID."
  }
}
variable "identity_creation_approved" {
  description = "Default deny. True is never an independent Seed/Graph/Apply authorization."
  type        = bool
  default     = false
}
