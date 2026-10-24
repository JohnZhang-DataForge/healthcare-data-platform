terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.13.0"
    }
  }

  # Backend values, including the ONE base Key, are supplied at terraform init.
  # Non-default Terraform CLI Workspaces derive their own isolated State blobs.
  backend "azurerm" {}
}
