terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.13.0"
    }
  }

  # Account-level connection has a separate backend from Workspace/OneLake.
  # Always use the default Terraform CLI Workspace for shared-infra.
  backend "azurerm" {
    key = "shared-infra/connection.tfstate"
  }
}
