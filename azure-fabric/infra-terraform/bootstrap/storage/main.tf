# This Root owns ONLY newly created fresh-bootstrap resources.
# In reuse-existing mode: zero resources, zero data-source lookups, zero RBAC.
# Guard booleans require external signed approvals: they are NOT authorization.
locals {
  fresh_gate = (
    var.bootstrap_mode == "fresh-bootstrap"
    && var.fresh_storage_creation_approved
    && var.new_resource_inventory_verified
    && var.seed_operator_authorized
    && var.initial_state_custody_verified
    && var.private_connectivity_verified
    && var.storage_region != null
    && var.fresh_storage_account_name != null
  )

  rbac_gate = (
    local.fresh_gate
    && var.rbac_creation_approved
    && var.identity_provenance_verified
    && var.backend_operator_object_id != null
    && var.blob_reader_object_id != null
    && var.backend_operator_object_id != var.blob_reader_object_id
  )
}

resource "azurerm_resource_group" "fresh" {
  count    = local.fresh_gate ? 1 : 0
  name     = "rg-hdp-${var.environment}"
  location = var.storage_region

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_account" "fresh" {
  count                    = local.fresh_gate ? 1 : 0
  name                     = var.fresh_storage_account_name
  resource_group_name      = azurerm_resource_group.fresh[0].name
  location                 = azurerm_resource_group.fresh[0].location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  public_network_access_enabled  = false

  tags = {
    owner_environment = var.environment
    owner_change      = "bootstrap-fabric-infrastructure"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "landing" {
  count                 = local.fresh_gate ? 1 : 0
  name                  = "landing"
  storage_account_id    = azurerm_storage_account.fresh[0].id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "backend" {
  count                 = local.fresh_gate ? 1 : 0
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.fresh[0].id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

# Microsoft documents container Resource Manager IDs as the correct RBAC scope.
# These grants cannot exist in reuse mode, or point to existing containers.
resource "azurerm_role_assignment" "backend_operator" {
  count                = local.rbac_gate ? 1 : 0
  scope                = azurerm_storage_container.backend[0].resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.backend_operator_object_id
  principal_type       = "ServicePrincipal"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_role_assignment" "blob_reader" {
  count                = local.rbac_gate ? 1 : 0
  scope                = azurerm_storage_container.landing[0].resource_manager_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.blob_reader_object_id
  principal_type       = "ServicePrincipal"

  lifecycle {
    prevent_destroy = true
  }
}
