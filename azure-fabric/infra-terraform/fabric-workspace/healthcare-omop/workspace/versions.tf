terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.13.0"
    }
  }

  # Storage account/container/OIDC supplied by the deploying workflow.
  # CLI named workspaces isolate individual Fabric Workspaces.
  backend "azurerm" {
    key = "fabric-workspace/workspace.tfstate"
  }
}
