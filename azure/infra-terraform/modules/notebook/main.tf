# Fabric Notebook SHELL; Python/PySpark definition is future work.
variable "workspace_id" { type = string }
variable "notebook_name" { type = string }
resource "fabric_notebook" "current" {
  display_name = var.notebook_name
  workspace_id = var.workspace_id
}
