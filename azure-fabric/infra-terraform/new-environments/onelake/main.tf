# New-environment Lakehouse only. Workspace must have been independently
# approved and its ID obtained from the intended environment, not legacy dev.
resource "fabric_lakehouse" "current" {
  display_name = var.lakehouse_name
  description  = "Isolated OMOP analytics Lakehouse"
  workspace_id = var.workspace_id

  configuration = {
    enable_schemas = true
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.lakehouse_creation_approved && var.workspace_id_verified && var.lakehouse_name == "HDP-${var.environment}-omop"
      error_message = "Explicit Lakehouse approval and verified new-environment Workspace ID are required."
    }
  }
}
