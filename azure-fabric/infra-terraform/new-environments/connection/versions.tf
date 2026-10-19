# Scaffold only: Fabric Connection schema must be verified separately.
terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.13.0"
    }
  }
  backend "azurerm" {}
}
