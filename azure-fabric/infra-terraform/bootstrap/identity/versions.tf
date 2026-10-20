terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "= 3.8.0"
    }
  }
  # No new remote Storage is needed to initialize this state.
  backend "local" {}
}
