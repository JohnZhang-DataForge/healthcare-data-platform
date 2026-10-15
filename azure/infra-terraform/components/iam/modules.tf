module "iam" {
  source                 = "../../modules/iam"
  resource_group_name    = var.resource_group_name
  storage_account_name   = var.storage_account_name
  landing_container_name = var.landing_container_name
  role_assignments       = var.role_assignments
}
