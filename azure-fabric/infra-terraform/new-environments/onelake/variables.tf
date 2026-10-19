variable "environment" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", var.environment)) && !contains(["dev", "main", "default", "production"], var.environment)
    error_message = "A distinct new environment name is required."
  }
}

variable "workspace_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.workspace_id)) && var.workspace_id != "00000000-0000-0000-0000-000000000000"
    error_message = "An explicit nonzero Workspace UUID is required."
  }
}

variable "lakehouse_name" {
  type = string
  validation {
    condition     = can(regex("^HDP-[a-z][a-z0-9-]*-omop$", var.lakehouse_name))
    error_message = "New Lakehouse names must use the HDP-<environment>-omop convention."
  }
}

# An independent approved inventory must confirm that workspace_id belongs
# to this exact environment. These flags are acknowledgments, NOT a live lookup.
variable "workspace_id_verified" {
  type    = bool
  default = false
}

variable "lakehouse_creation_approved" {
  type    = bool
  default = false
}
