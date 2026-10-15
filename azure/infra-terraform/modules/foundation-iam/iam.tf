# Cross-component shared identity access at RG level; empty by default.
# Azure role assignment write needs User Access Administrator / RBAC Administrator
# or a suitably limited custom role, NOT an ordinary Contributor.
resource "azurerm_role_assignment" "shared" {
  for_each             = var.shared_role_bindings
  scope                = data.azurerm_resource_group.project.id
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
}
