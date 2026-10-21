# Independent paid Capacity Root; never touches existing Trial Capacity.
data "azurerm_client_config" "current" {}

module "capacity" {
  source                 = "../../modules/capacity"
  name                   = var.capacity_name
  resource_group_name    = var.resource_group_name
  location               = var.location
  sku_name               = var.sku_name
  administration_members = distinct(concat([data.azurerm_client_config.current.object_id], var.additional_admins))
}

# Fabric's Capacity GUID is not the Azure Resource Manager resource ID.
# It is needed by the separate Workspace Terraform Root.
data "fabric_capacity" "created" {
  display_name = module.capacity.capacity_name
}
