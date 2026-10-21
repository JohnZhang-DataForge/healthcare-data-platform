terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Shared Infra owns its own independent default-workspace state.
  backend "azurerm" {
    key = "shared-infra/storage.tfstate"
  }
}
