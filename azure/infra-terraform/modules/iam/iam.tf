# Do not re-create existing Portal assignments: role assignments are empty by default.
# Azure RBAC writes require roleAssignments/write beyond standard RG Contributor.
resource "azurerm_role_assignment" "landing" {
  for_each             = var.role_assignments
  scope                = local.landing_scope
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
}
