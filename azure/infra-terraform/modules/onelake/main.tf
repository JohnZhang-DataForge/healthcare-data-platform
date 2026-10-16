# OneLake is provided by Fabric Lakehouse, NOT a new Azure Storage Account.
# Schema-enabled Lakehouse supports OMOP 'cdm' tables in a later data-loading step.
variable "workspace_id" { type = string }
variable "lakehouse_name" { type = string }
variable "data_access_roles" {
  type = map(object({
    paths   = list(string)
    actions = list(string)
    entra_members = list(object({
      object_id   = string
      object_type = string
      tenant_id   = optional(string)
    }))
  }))
  default = {}
}
resource "fabric_lakehouse" "current" {
  display_name = var.lakehouse_name
  description  = "OneLake analytics replica of local OMOP PostgreSQL snapshots"
  workspace_id = var.workspace_id

  # Creation-time setting. Changing after an Apply would force replacement.
  configuration = {
    enable_schemas = true
  }
}
