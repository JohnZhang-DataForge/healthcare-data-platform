# Existing, separately authorized Seed Operator obtains credentials outside source.
provider "azuread" {
  alias     = "backend"
  tenant_id = var.backend_tenant_id
}
provider "azuread" {
  alias     = "fabric"
  tenant_id = var.fabric_tenant_id
}
