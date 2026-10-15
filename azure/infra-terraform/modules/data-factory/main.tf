# Fabric Data Factory Pipeline SHELL, not Azure Data Factory; definition is future work.
variable "workspace_id" { type = string }
variable "pipeline_name" { type = string }
resource "fabric_data_pipeline" "current" {
  display_name = var.pipeline_name
  workspace_id = var.workspace_id
}
