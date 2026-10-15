# Only a small, explicitly named test Blob; existing account/container are unmanaged.
provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
  storage_use_azuread             = true
}

locals {
  probe_content = "Azure Blob Terraform OIDC landing write test\nDate: 2026-10-15\nRepository: JohnZhang-DataForge/healthcare-data-platform\nResult: file created by Terraform through Self-Runner\n"
}

resource "azurerm_storage_blob" "probe" {
  name                   = "terraform-smoke/oidc-landing-20261015.txt"
  storage_account_name   = "johnzhang"
  storage_container_name = "landing"
  type                   = "Block"
  content_type           = "text/plain"
  source_content         = local.probe_content
  content_md5            = md5(local.probe_content)
}

output "blob_url" {
  value = azurerm_storage_blob.probe.url
}

output "content_md5" {
  value = md5(local.probe_content)
}
