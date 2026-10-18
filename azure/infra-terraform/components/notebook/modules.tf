module "notebook" {
  source        = "../../modules/notebook"
  workspace_id  = var.workspace_id
  notebook_name = var.notebook_name
}
