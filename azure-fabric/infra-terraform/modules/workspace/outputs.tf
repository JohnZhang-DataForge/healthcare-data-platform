output "workspace_id" { value = fabric_workspace.current.id }

# Entra service principal OBJECT ID for Storage Blob Data Reader; not the application/client ID.
output "workspace_identity_principal_id" {
  value = try(fabric_workspace.current.identity.service_principal_id, null)
}
