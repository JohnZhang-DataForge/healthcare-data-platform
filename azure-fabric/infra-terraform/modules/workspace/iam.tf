# Only explicitly new memberships. Import manually-created memberships before managing them.
resource "fabric_workspace_role_assignment" "additional" {
  for_each     = var.role_assignments
  workspace_id = fabric_workspace.current.id
  principal = {
    id   = each.value.principal_id
    type = each.value.principal_type
  }
  role = each.value.role
}
