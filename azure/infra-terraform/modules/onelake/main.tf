# OneLake storage is provided by Fabric Lakehouse, NOT a new Azure Storage Account.
variable "workspace_id" { type = string }
variable "lakehouse_name" { type = string }
variable "data_access_roles" {
  type = map(object({
    paths   = list(string)
    actions = list(string)
    entra_members = list(object({
      object_id   = string
      object_type = string
      tenant_id   = optional(string)
    }))
  }))
  default = {}
}
resource "fabric_lakehouse" "current" {
  display_name = var.lakehouse_name
  workspace_id = var.workspace_id
}
