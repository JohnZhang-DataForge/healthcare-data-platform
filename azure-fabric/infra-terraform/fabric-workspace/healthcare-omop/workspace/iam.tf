# Only explicit additional Workspace membership grants are managed.
# The reusable module owns fabric_workspace_role_assignment resources.
variable "role_assignments" {
  description = "Entra object IDs and roles to grant; empty means no added grants."
  type = map(object({
    principal_id   = string
    principal_type = string
    role           = string
  }))
  default = {}
}
