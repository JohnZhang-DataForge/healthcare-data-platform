variable "workspace_name" { type = string }
variable "description" { type = string }
variable "capacity_id" { type = string }
variable "role_assignments" {
  type = map(object({
    principal_id   = string
    principal_type = string
    role           = string
  }))
  default = {}
}
