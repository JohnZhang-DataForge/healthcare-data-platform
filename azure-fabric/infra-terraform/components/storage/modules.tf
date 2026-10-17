module "storage" {
  source                 = "../../modules/storage"
  resource_group_name    = var.resource_group_name
  storage_account_name   = var.storage_account_name
  landing_container_name = var.landing_container_name
  blob_role_assignments  = var.blob_role_assignments
}
