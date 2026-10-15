# OneLake is Fabric-managed via Lakehouse, NOT a second Azure Storage Account.
variable "workspace_id" { type = string }
variable "lakehouse_name" { type = string }
resource "fabric_lakehouse" "current" {
  display_name = var.lakehouse_name
  workspace_id = var.workspace_id
}
