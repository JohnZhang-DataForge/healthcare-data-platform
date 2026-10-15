output "account_id" { value = data.azurerm_storage_account.current.id }
output "landing_scope" {
  value = "${data.azurerm_storage_account.current.id}/blobServices/default/containers/${var.landing_container_name}"
}
