module "data_factory" {
  source        = "../../modules/data-factory"
  workspace_id  = var.workspace_id
  pipeline_name = var.pipeline_name
}
