output "lakehouse_id" { value = fabric_lakehouse.current.id }
output "data_access_role_ids" {
  value = { for name, role in fabric_onelake_data_access_security.roles : name => role.id }
}
