# Explicit OneLake roles only; provider PREVIEW is retained for the reusable module.
variable "data_access_roles" {
  description = "Optional OneLake access roles scoped to this Lakehouse; empty by default."
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
