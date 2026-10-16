terraform {
  required_version = ">= 1.8.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Isolated state. The pre-existing backend must NEVER be destroyed.
  backend "azurerm" {
    storage_account_name = "johnzhang"
    container_name       = "tfstate"
    key                  = "smoke/landing-blob-write.tfstate"

    use_oidc         = true
    use_azuread_auth = true
  }
}
