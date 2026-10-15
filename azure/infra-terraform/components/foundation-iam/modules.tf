module "foundation_iam" {
  source                = "../../modules/foundation-iam"
  resource_group_name   = var.resource_group_name
  shared_role_bindings  = var.shared_role_bindings
}
