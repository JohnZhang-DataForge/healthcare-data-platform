# Azure CLI (local) is the Fabric provider default.
# Self-Runner can use FABRIC_USE_OIDC/FABRIC_CLIENT_ID/FABRIC_TENANT_ID.
# OneLake Data Access Security is a preview resource, disabled by default.
provider "fabric" {
  preview = true
}
