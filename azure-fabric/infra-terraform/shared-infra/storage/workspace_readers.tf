# Explicitly selected Fabric Workspace Identities may read the existing landing
# container. Resolve the Entra service principal OBJECT ID from Terraform output.
# Do not copy generated Object IDs into this shared infrastructure source.
variable "workspace_identity_readers" {
  description = "Map of approved reader labels to existing Fabric Terraform CLI workspaces."
  type        = map(string)
  default     = {}
  validation {
    condition     = alltrue([for workspace in values(var.workspace_identity_readers) : can(regex("^[a-z][a-z0-9-]+$", workspace)) && workspace != "default"])
    error_message = "Reader workspace names must be explicitly named non-default Terraform CLI workspaces."
  }
}

variable "workspace_state_backend" {
  description = "Existing AzureRM State account/container holding named Fabric Workspace states."
  type = object({
    storage_account_name = string
    container_name       = string
  })
  default = null
}

data "terraform_remote_state" "fabric_workspace" {
  for_each  = var.workspace_identity_readers
  backend   = "azurerm"
  workspace = each.value

  config = {
    storage_account_name = var.workspace_state_backend.storage_account_name
    container_name       = var.workspace_state_backend.container_name
    key                  = "fabric-workspace/workspace.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}

locals {
  workspace_identity_role_assignments = {
    for label, state in data.terraform_remote_state.fabric_workspace :
    label => {
      principal_id = state.outputs.workspace_identity_principal_id
      role         = "Storage Blob Data Reader"
    }
  }
}
