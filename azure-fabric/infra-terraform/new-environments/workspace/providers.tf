# Fabric provider uses the independent Tenant B identity supplied by
# FABRIC_CLIENT_ID / FABRIC_TENANT_ID / FABRIC_USE_OIDC, never ARM_*.
provider "fabric" {
  use_oidc = true
}
