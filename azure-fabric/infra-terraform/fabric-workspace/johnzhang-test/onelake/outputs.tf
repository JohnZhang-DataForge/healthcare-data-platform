output "fabric_workspace_id" {
  description = "Read directly from the upstream Workspace Root remote state."
  value       = data.terraform_remote_state.workspace.outputs.fabric_workspace_id

  precondition {
    condition     = terraform.workspace != "default" && terraform.workspace == local.workspace_name
    error_message = "Select the Terraform CLI workspace matching the Fabric workspace parent directory."
  }
}

output "lakehouse_id" {
  description = "Created Lakehouse ID."
  value       = module.onelake.lakehouse_id

  precondition {
    condition     = terraform.workspace != "default" && terraform.workspace == local.workspace_name
    error_message = "Terraform CLI Workspace must match the parent directory."
  }
}

output "onelake_files_path" {
  value = module.onelake.onelake_files_path
}

output "onelake_tables_path" {
  value = module.onelake.onelake_tables_path
}

output "data_access_role_ids" {
  value = module.onelake.data_access_role_ids
}
