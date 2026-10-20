# Only a separately authorized, short-lived Seed Operator may use this provider.
# No credentials, client secrets, OIDC tokens or GitHub writable permissions here.
provider "azapi" {
  tenant_id       = var.fabric_tenant_id
  subscription_id = var.capacity_subscription_id
}
