# Fabric PySpark Notebook ITEM with a source-controlled, fail-closed bootstrap.
# ETL implementation and data writes are NOT part of Terraform provisioning.
variable "workspace_id" { type = string }
variable "notebook_name" { type = string }

resource "fabric_notebook" "current" {
  display_name = var.notebook_name
  description  = "Azure Blob landing to OneLake OMOP snapshot loader (bootstrap only)"
  workspace_id = var.workspace_id
  format       = "py"

  definition = {
    "notebook-content.py" = {
      source = "${path.module}/definitions/notebook-content.py"
    }
  }
}
