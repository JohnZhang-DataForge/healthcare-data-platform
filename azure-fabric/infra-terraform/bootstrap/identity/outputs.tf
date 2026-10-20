output "identity_targets" {
  description = "Non-secret ID targets only; not a cloud validation."
  value = {
    backend_tenant_id = var.backend_tenant_id
    fabric_tenant_id  = var.fabric_tenant_id
    backend_client_id = try(azuread_application_registration.backend_operator[0].client_id, null)
    fabric_client_id  = try(azuread_application_registration.fabric_deployer[0].client_id, null)
    reader_client_id  = try(azuread_application_registration.blob_reader[0].client_id, null)
    backend_sp_id     = try(azuread_service_principal.backend_operator[0].object_id, null)
    fabric_sp_id      = try(azuread_service_principal.fabric_deployer[0].object_id, null)
    reader_sp_id      = try(azuread_service_principal.blob_reader[0].object_id, null)
    verified          = false
  }
}
