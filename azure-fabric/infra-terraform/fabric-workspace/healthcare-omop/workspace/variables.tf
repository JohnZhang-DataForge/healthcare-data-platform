variable "description" {
  description = "Fabric Workspace description."
  type        = string
  default     = "Healthcare OMOP analytical workspace"
}

variable "capacity_id" {
  description = "Existing Fabric Capacity GUID. Set in this Workspace Root terraform.tfvars; runner does not inject it. Never creates a Capacity."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", var.capacity_id))
    error_message = "capacity_id must be the GUID of an existing Fabric Capacity."
  }
}

# Opt-in on this workspace only; module defaults to disabled for other workspaces.
variable "enable_workspace_identity" {
  description = "Enable the existing Fabric Workspace system-assigned identity for same-tenant Azure Blob access."
  type        = bool
  default     = false
}
