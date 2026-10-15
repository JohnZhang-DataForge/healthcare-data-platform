# OneLake data-access-security resources are provider PREVIEW.
# The resource is declared but no policies are created unless explicitly
# configured in data_access_roles. Review preview limitations before APPLY.
provider "fabric" {
  use_oidc = true
  preview  = true
}
