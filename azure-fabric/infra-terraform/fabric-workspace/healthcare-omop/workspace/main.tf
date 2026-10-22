# One real Fabric Workspace per same-named Git parent directory.
# The Terraform CLI workspace is validated in outputs.tf before apply.
locals {
  workspace_name            = basename(dirname(abspath(path.root)))
  # Only Terraform-reviewed, explicitly resolved Entra user IDs receive Workspace Admin.
  portal_admin_role_assignments = var.portal_admin_user_object_id == null ? {} : {
    portal_admin = {
      principal_id   = var.portal_admin_user_object_id
      principal_type = "User"
      role           = "Admin"
    }
  }
}

module "workspace" {
  source = "../../../modules/workspace"

  workspace_name            = local.workspace_name
  description               = var.description
  capacity_id               = var.capacity_id
  enable_workspace_identity = var.enable_workspace_identity
  role_assignments          = merge(var.role_assignments, local.portal_admin_role_assignments)
}
