variable "workspace_id" { type = string }
variable "lakehouse_name" { type = string }

variable "data_access_roles" {
  description = "OneLake data access roles for THIS Lakehouse only; empty by default. Preview provider feature."
  type = map(object({
    paths   = list(string) # Example: ["/Tables/person"] or ["*"]
    actions = list(string) # Provider-supported OneLake actions, e.g. ["Read"]
    entra_members = list(object({
      object_id   = string
      object_type = string
      tenant_id   = optional(string)
    }))
  }))
  default = {}
}
