# One real Fabric Workspace per same-named Git parent directory.
# The Terraform CLI workspace is validated in outputs.tf before apply.
locals {
  workspace_name = basename(dirname(abspath(path.root)))
}

module "workspace" {
  source = "../../../modules/workspace"

  workspace_name   = local.workspace_name
  description      = var.description
  capacity_id      = var.capacity_id
  role_assignments = var.role_assignments
}
