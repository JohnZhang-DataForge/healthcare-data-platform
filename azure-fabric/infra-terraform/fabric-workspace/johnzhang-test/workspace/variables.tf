variable "description" {
  description = "Fabric Workspace description."
  type        = string
  default     = "Healthcare OMOP analytical workspace"
}

variable "capacity_id" {
  description = "Existing Fabric Capacity GUID. Supply at runtime with TF_VAR_capacity_id or -var; never creates a Capacity."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", var.capacity_id))
    error_message = "capacity_id must be the GUID of an existing Fabric Capacity."
  }
}
