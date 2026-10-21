output "fabric_workspace_name" {
  value = terraform.workspace
}

output "fabric_workspace_id" {
  value = module.workspace.workspace_id
}

output "lakehouse_id" {
  value = module.onelake.lakehouse_id
}

output "onelake_files_path" {
  value = module.onelake.onelake_files_path
}

output "onelake_tables_path" {
  value = module.onelake.onelake_tables_path
}

output "connection_id" {
  value = var.connection == null ? null : module.connection[0].connection_id
}
