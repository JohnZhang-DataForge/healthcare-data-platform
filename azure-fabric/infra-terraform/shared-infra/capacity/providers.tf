provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
  storage_use_azuread = true
}
provider "fabric" {
  use_oidc = true
}
