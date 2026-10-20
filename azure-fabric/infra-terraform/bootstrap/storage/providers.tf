# Seed Operator identity is authorized externally; no token or secret variables.
provider "azurerm" {
  tenant_id       = var.backend_tenant_id
  subscription_id = var.storage_subscription_id

  features {}
}
