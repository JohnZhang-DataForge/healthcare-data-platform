variable "resource_group_name" { type = string }

# Truly SHARED Resource Group grants, never component-owned Blob/Lakehouse roles.
variable "shared_role_bindings" {
  description = "New project-wide RG-level grants; existing bootstrap privileges remain outside Terraform."
  type = map(object({
    principal_id = string # Object ID, not Client ID
    role         = string
  }))
  default = {}
}
