# Executed via Self-Runner/main with GitHub OIDC. NO new RG or paid resources.
provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

data "azurerm_resource_group" "omop" {
  name = "OMOP"
}

# An empty INCREMENTAL ARM deployment proves actual Azure management-plane
# write access without requiring a new resource provider registration or paid
# resources. Never use Complete mode on the existing OMOP Resource Group.
resource "azurerm_resource_group_template_deployment" "probe" {
  name                = "hdp-tf-oidc-probe"
  resource_group_name = data.azurerm_resource_group.omop.name
  deployment_mode     = "Incremental"

  template_content = jsonencode({
    "$schema"      = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
    contentVersion = "1.0.0.0"
    resources      = []
    outputs        = {
      connectivity = {
        type  = "string"
        value = "azure-terraform-oidc-ok"
      }
    }
  })
}

output "probe_resource_id" {
  value = azurerm_resource_group_template_deployment.probe.id
}

output "probe_result" {
  value = jsondecode(azurerm_resource_group_template_deployment.probe.output_content).connectivity.value
}
