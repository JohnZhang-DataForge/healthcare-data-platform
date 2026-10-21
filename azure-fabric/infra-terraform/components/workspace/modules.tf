module "workspace" {
  source           = "../../modules/workspace"
  workspace_name   = var.workspace_name
  description      = var.description
  capacity_id      = var.capacity_id
  role_assignments = var.role_assignments
}
