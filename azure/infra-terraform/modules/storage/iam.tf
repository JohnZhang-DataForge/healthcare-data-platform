# Scope OWNED by storage. No grant is created when var.blob_role_assignments = {}.
# Requires roleAssignments/write; RG Contributor ALONE cannot assign Azure RBAC.
# DO NOT duplicate Portal-created Bootstrap RBAC; import before adopting.
resource "azurerm_role_assignment" "landing" {
  for_each             = var.blob_role_assignments
  scope                = "${data.azurerm_storage_account.current.id}/blobServices/default/containers/${var.landing_container_name}"
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
}
