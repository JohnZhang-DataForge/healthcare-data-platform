variable "environment" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production"], var.environment)
    error_message = "Only distinct new-environment names are allowed."
  }
}

variable "workspace_name" {
  type = string
  validation {
    condition     = startswith(var.workspace_name, "HDP-") && var.workspace_name != "healthcare-omop"
    error_message = "A new HDP-prefixed Workspace name is required."
  }
}

variable "capacity_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.capacity_id)) && var.capacity_id != "00000000-0000-0000-0000-000000000000"
    error_message = "An existing, nonzero Fabric Capacity UUID must be supplied."
  }
}

# Fail closed; requires independently reviewed inventory and explicit approval.
# This boolean is an acknowledgement, not proof that remote Workspace is absent.
variable "workspace_creation_approved" {
  type    = bool
  default = false
}
