# Root outputs form the contract for downstream independent Terraform states.
output "fabric_workspace_id" {
  description = "Real Fabric Workspace ID from the reusable module."
  value       = module.workspace.workspace_id

  precondition {
    condition     = terraform.workspace != "default" && terraform.workspace == local.workspace_name
    error_message = "Select the non-default Terraform CLI workspace matching the Fabric workspace parent directory."
  }
}

output "fabric_workspace_name" {
  description = "Fabric display name derived directly from the Git parent directory."
  value       = local.workspace_name

  precondition {
    condition     = terraform.workspace != "default" && terraform.workspace == local.workspace_name
    error_message = "Terraform CLI workspace must match the Fabric workspace directory name."
  }
}

output "workspace_identity_principal_id" {
  description = "The Workspace Identity Entra Object ID for Azure Blob Data Reader; null until it exists."
  value       = module.workspace.workspace_identity_principal_id

  precondition {
    condition     = terraform.workspace != "default" && terraform.workspace == local.workspace_name
    error_message = "Terraform CLI workspace must match the Fabric workspace directory name."
  }
}
