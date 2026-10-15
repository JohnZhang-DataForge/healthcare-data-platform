variable "resource_group_name" { type = string }
variable "storage_account_name" { type = string }
variable "landing_container_name" { type = string }
variable "role_assignments" {
  type = map(object({
    principal_id = string
    role         = string
  }))
}
data "azurerm_storage_account" "current" {
  name                = var.storage_account_name
  resource_group_name = var.resource_group_name
}
locals {
  landing_scope = "${data.azurerm_storage_account.current.id}/blobServices/default/containers/${var.landing_container_name}"
}
