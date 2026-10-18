# Fabric Warehouse SHELL; SQL schema/data loads are future work.
variable "workspace_id" { type = string }
variable "warehouse_name" { type = string }
resource "fabric_warehouse" "current" {
  display_name = var.warehouse_name
  workspace_id = var.workspace_id
}
