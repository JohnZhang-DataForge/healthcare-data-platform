# Provider source declarations are required in EVERY child module.
# Without this, Terraform assumes the nonexistent hashicorp/fabric provider.
terraform {
  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.13.0"
    }
  }
}
