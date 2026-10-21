# Lakehouse/OneLake is an independent Terraform Root and State.
# Its Fabric Workspace must already exist in the separate workspace Root State.
locals {
  workspace_name = basename(dirname(abspath(path.root)))
}

data "terraform_remote_state" "workspace" {
  backend   = "azurerm"
  workspace = terraform.workspace

  config = {
    storage_account_name = var.backend_storage_account_name
    container_name       = var.backend_container_name
    key                  = "fabric-workspace/workspace.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}

module "onelake" {
  source = "../../../modules/onelake"

  workspace_id      = data.terraform_remote_state.workspace.outputs.fabric_workspace_id
  lakehouse_name    = var.lakehouse_name
  data_access_roles = var.data_access_roles
}
