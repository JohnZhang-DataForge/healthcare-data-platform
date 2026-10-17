variable "resource_group_name" { type = string }
variable "storage_account_name" { type = string }
variable "landing_container_name" { type = string }
variable "blob_role_assignments" {
  type = map(object({
    principal_id = string
    role         = string
  }))
  default = {}
}

# Data sources only. Existing OMOP / johnzhang / landing are NOT managed.
data "azurerm_resource_group" "omop" { name = var.resource_group_name }
data "azurerm_storage_account" "current" {
  name                = var.storage_account_name
  resource_group_name = data.azurerm_resource_group.omop.name
}
