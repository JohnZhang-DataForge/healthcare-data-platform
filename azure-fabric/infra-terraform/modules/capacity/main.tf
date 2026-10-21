# Reusable paid Fabric Capacity model. This provisions a billable Azure resource.
variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "sku_name" { type = string }
variable "administration_members" { type = list(string) }

data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}

resource "azurerm_fabric_capacity" "current" {
  name                   = var.name
  resource_group_name    = data.azurerm_resource_group.existing.name
  location               = var.location
  administration_members = var.administration_members

  sku {
    name = var.sku_name
    tier = "Fabric"
  }
}
