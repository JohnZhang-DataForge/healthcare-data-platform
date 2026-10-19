# Dedicated new-environment Workspace only; never import/adopt legacy resources implicitly.
resource "fabric_workspace" "current" {
  display_name = var.workspace_name
  description  = "New isolated Healthcare Fabric environment"
  capacity_id  = var.capacity_id

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.workspace_creation_approved && var.workspace_name == "HDP-${var.environment}"
      error_message = "Explicit new Workspace approval and HDP environment naming are required."
    }
  }
}
