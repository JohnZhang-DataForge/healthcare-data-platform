module "warehouse" {
  source         = "../../modules/warehouse"
  workspace_id   = var.workspace_id
  warehouse_name = var.warehouse_name
}
