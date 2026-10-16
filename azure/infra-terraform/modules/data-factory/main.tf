# Fabric Data Factory Data Pipeline (not an azurerm_data_factory resource).
# A Fail activity protects the environment until a real Notebook ID is supplied.
variable "workspace_id" { type = string }
variable "pipeline_name" { type = string }
variable "notebook_id" {
  type        = string
  description = "Existing Notebook item GUID. Empty for fail-closed PLAN-only bootstrap."
  default     = ""

  validation {
    condition     = var.notebook_id == "" || can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.notebook_id))
    error_message = "notebook_id must be empty or a valid Notebook GUID."
  }
}

resource "fabric_data_pipeline" "current" {
  display_name = var.pipeline_name
  description  = "Local OMOP snapshot: Azure Blob landing -> Fabric Notebook -> OneLake"
  workspace_id = var.workspace_id
  format       = "Default"

  definition = {
    "pipeline-content.json" = {
      source = var.notebook_id == "" ? "${path.module}/definitions/pipeline-disabled.json" : "${path.module}/definitions/pipeline-notebook.json"
      tokens = var.notebook_id == "" ? {} : {
        WorkspaceId = var.workspace_id
        NotebookId  = var.notebook_id
      }
    }
  }
}
