variable "resource_group_name" { type = string }
variable "storage_account_name" { type = string }
variable "landing_container_name" { type = string }
variable "role_assignments" {
  type = map(object({
    principal_id = string
    role         = string
  }))
  default = {}
}
