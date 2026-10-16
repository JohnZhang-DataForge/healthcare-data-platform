terraform {
  required_version = ">= 1.8.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Dedicated disposable validation state; never share a state key with production.
  backend "azurerm" {
    storage_account_name = "johnzhang"
    container_name       = "tfstate"
    key                  = "smoke/oidc-connectivity.tfstate"

    use_oidc         = true
    use_azuread_auth = true
  }
}
