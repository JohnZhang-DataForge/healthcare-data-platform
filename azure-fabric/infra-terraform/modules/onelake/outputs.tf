output "lakehouse_id" { value = fabric_lakehouse.current.id }
output "onelake_files_path" { value = fabric_lakehouse.current.properties.onelake_files_path }
output "onelake_tables_path" { value = fabric_lakehouse.current.properties.onelake_tables_path }
output "data_access_role_ids" {
  value = { for name, role in fabric_onelake_data_access_security.roles : name => role.id }
}
