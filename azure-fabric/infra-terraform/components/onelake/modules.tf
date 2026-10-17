module "onelake" {
  source            = "../../modules/onelake"
  workspace_id      = var.workspace_id
  lakehouse_name    = var.lakehouse_name
  data_access_roles = var.data_access_roles
}
