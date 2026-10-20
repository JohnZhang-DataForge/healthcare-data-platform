terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.60.0"
    }
  }

  # Initial Bootstrap State MUST NOT depend on the Storage being created.
  backend "local" {}
}
