# IAM security resource is a preview feature; no roles are created by default.
provider "fabric" {
  use_oidc = true
  preview  = true
}
