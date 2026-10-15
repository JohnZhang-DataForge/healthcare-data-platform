output "assignment_ids" {
  value = { for name, role in azurerm_role_assignment.landing : name => role.id }
}
