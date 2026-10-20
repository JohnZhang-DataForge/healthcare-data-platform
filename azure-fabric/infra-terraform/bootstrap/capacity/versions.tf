terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.8.0"
    }
  }

  # Initial Bootstrap State remains separate from any new Azure Storage.
  backend "local" {}
}
