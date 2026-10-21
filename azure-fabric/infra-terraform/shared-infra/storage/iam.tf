# Existing landing access remains externally owned. New grants require
# explicit review: no implicit role assignments in this Root.
variable "blob_role_assignments" {
  description = "Optional *new* Landing RBAC assignments (not existing Portal-managed permissions)."
  type = map(object({
    principal_id = string
    role         = string
  }))
  default = {}
}
