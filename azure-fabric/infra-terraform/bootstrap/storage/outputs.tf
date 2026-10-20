output "storage_target" {
  description = "Unverified targets only; does not prove Resource/State/permission existence."
  value = {
    bootstrap_mode                = var.bootstrap_mode
    backend_tenant_id             = var.backend_tenant_id
    storage_subscription_id       = var.storage_subscription_id
    storage_account_id            = var.bootstrap_mode == "reuse-existing" ? var.reuse_existing_storage_account_id : try(azurerm_storage_account.fresh[0].id, null)
    storage_account_name          = var.bootstrap_mode == "reuse-existing" ? "johnzhang" : try(azurerm_storage_account.fresh[0].name, null)
    landing_container             = "landing"
    backend_container             = "tfstate"
    backend_state_prefix          = "fabric/${var.environment}"
    backend_operator_scope        = try(azurerm_storage_container.backend[0].resource_manager_id, null)
    blob_reader_scope             = try(azurerm_storage_container.landing[0].resource_manager_id, null)
    resource_ownership_status     = "NOT_VERIFIED"
    remote_state_checked          = false
    initial_state_custody_checked = false
    cloud_access_verified         = false
  }
}
