variable "resource_group_name" { type = string }
variable "shared_role_bindings" {
  type = map(object({
    principal_id = string
    role         = string
  }))
  default = {}
}
data "azurerm_resource_group" "project" {
  name = var.resource_group_name
}
