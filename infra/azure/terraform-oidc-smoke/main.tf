# Executed from JohnZhang-DataForge/Self-Runner main via GitHub OIDC.
# Do not manage the existing OMOP resource group or backend storage as resources.
provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

data "azurerm_resource_group" "omop" {
  name = "OMOP"
}

# Azure Managed Identities have no additional direct charge.
# Temporary smoke-only resource: the workflow always attempts to destroy it.
resource "azurerm_user_assigned_identity" "probe" {
  name                = "id-hdp-tf-oidc-probe"
  resource_group_name = data.azurerm_resource_group.omop.name
  location            = data.azurerm_resource_group.omop.location

  tags = {
    project = "healthcare-data-platform"
    purpose = "terraform-oidc-temporary-smoke"
  }
}

output "probe_resource_id" {
  value = azurerm_user_assigned_identity.probe.id
}
