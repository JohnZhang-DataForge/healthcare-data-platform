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

# Exactly one protected Self-Runner Environment per role/phase.
# Environments MUST restrict main and require independent deployment review.
resource "azuread_application_federated_identity_credential" "backend_operator_plan" {
  provider       = azuread.backend
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.backend_operator[0].id
  display_name   = "hdp-${var.environment}-backend-plan-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-${var.environment}-plan-backend"
  lifecycle {
    prevent_destroy = true
  }
}

# Exactly one protected Self-Runner Environment per role/phase.
# Environments MUST restrict main and require independent deployment review.
resource "azuread_application_federated_identity_credential" "backend_operator_apply" {
  provider       = azuread.backend
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.backend_operator[0].id
  display_name   = "hdp-${var.environment}-backend-apply-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-${var.environment}-apply-backend"
  lifecycle {
    prevent_destroy = true
  }
}

# Exactly one protected Self-Runner Environment per role/phase.
# Environments MUST restrict main and require independent deployment review.
resource "azuread_application_federated_identity_credential" "fabric_deployer_plan" {
  provider       = azuread.fabric
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.fabric_deployer[0].id
  display_name   = "hdp-${var.environment}-fabric-plan-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-${var.environment}-plan-deployer"
  lifecycle {
    prevent_destroy = true
  }
}

# Exactly one protected Self-Runner Environment per role/phase.
# Environments MUST restrict main and require independent deployment review.
resource "azuread_application_federated_identity_credential" "fabric_deployer_apply" {
  provider       = azuread.fabric
  count          = var.identity_creation_approved ? 1 : 0
  application_id = azuread_application_registration.fabric_deployer[0].id
  display_name   = "hdp-${var.environment}-fabric-apply-github"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-${var.environment}-apply-deployer"
  lifecycle {
    prevent_destroy = true
  }
}
