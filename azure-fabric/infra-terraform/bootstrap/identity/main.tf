# NO management or adoption of the existing github-terraform application.
# Default count=0: no apps, SPNs, groups or OIDC credentials are created.
# Manual inventory, protected environment and Seed consent are separate gates.

resource "azuread_application_registration" "backend_operator" {
  provider     = azuread.backend
  count        = var.identity_creation_approved ? 1 : 0
  display_name = "hdp-${var.environment}-backend-operator"
  lifecycle {
    prevent_destroy = true
  }
}
resource "azuread_service_principal" "backend_operator" {
  provider  = azuread.backend
  count     = var.identity_creation_approved ? 1 : 0
  client_id = azuread_application_registration.backend_operator[0].client_id
  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_application_registration" "blob_reader" {
  provider     = azuread.backend
  count        = var.identity_creation_approved ? 1 : 0
  display_name = "hdp-${var.environment}-blob-reader"
  lifecycle {
    prevent_destroy = true
  }
}
resource "azuread_service_principal" "blob_reader" {
  provider  = azuread.backend
  count     = var.identity_creation_approved ? 1 : 0
  client_id = azuread_application_registration.blob_reader[0].client_id
  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_application_registration" "fabric_deployer" {
  provider     = azuread.fabric
  count        = var.identity_creation_approved ? 1 : 0
  display_name = "hdp-${var.environment}-fabric-deployer"
  lifecycle {
    prevent_destroy = true
  }
}
resource "azuread_service_principal" "fabric_deployer" {
  provider  = azuread.fabric
  count     = var.identity_creation_approved ? 1 : 0
  client_id = azuread_application_registration.fabric_deployer[0].client_id
  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_group" "backend_operators" {
  provider         = azuread.backend
  count            = var.identity_creation_approved ? 1 : 0
  display_name     = "hdp-${var.environment}-backend-operators"
  security_enabled = true
  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_group" "fabric_deployers" {
  provider         = azuread.fabric
  count            = var.identity_creation_approved ? 1 : 0
  display_name     = "hdp-${var.environment}-fabric-deployers"
  security_enabled = true
  lifecycle {
    prevent_destroy = true
  }
}

# GitHub Environment must separately restrict deployment branches to main.
resource "azuread_application_federated_identity_credential" "backend_operator" {
  provider       = azuread.backend
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.backend_operator[0].id
  display_name   = "hdp-${var.environment}-backend-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge/healthcare-data-platform:environment:fabric-${var.environment}-backend"
  lifecycle {
    prevent_destroy = true
  }
}

# GitHub Environment must separately restrict deployment branches to main.
resource "azuread_application_federated_identity_credential" "fabric_deployer" {
  provider       = azuread.fabric
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.fabric_deployer[0].id
  display_name   = "hdp-${var.environment}-fabric-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge/healthcare-data-platform:environment:fabric-${var.environment}-deployer"
  lifecycle {
    prevent_destroy = true
  }
}
