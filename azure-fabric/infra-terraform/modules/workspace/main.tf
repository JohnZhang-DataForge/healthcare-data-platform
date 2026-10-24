variable "workspace_name" { type = string }
variable "description" { type = string }
variable "capacity_id" { type = string }
# Workspace Identity is opt-in per workspace Root, never tenant-global.
variable "enable_workspace_identity" {
  type    = bool
  default = false
}
variable "role_assignments" {
  type = map(object({
    principal_id   = string
    principal_type = string
    role           = string
  }))
}
resource "fabric_workspace" "current" {
  display_name = var.workspace_name
  description  = var.description
  capacity_id  = var.capacity_id == "" ? null : var.capacity_id
  identity     = var.enable_workspace_identity ? { type = "SystemAssigned" } : null
}
