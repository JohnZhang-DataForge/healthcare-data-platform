# Dedicated Fabric Tenant B OIDC identity; never reuse Backend ARM_*.
# Preview is required by the existing optional OneLake access module.
provider "fabric" {
  use_oidc = true
  preview  = true
}
