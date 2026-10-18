output "assignment_ids" {
  value = { for key, assignment in azurerm_role_assignment.shared : key => assignment.id }
}
