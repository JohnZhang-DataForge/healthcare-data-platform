variable "capacity_name" {
  type = string
  validation {
    condition = can(regex("^[a-z][a-z0-9]{2,62}$",var.capacity_name))
    error_message = "Only lowercase alphanumeric Fabric Capacity names are accepted."
  }
}
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "sku_name" {
  type = string
  validation {
    condition = var.sku_name == "F2"
    error_message = "This bounded test Root only permits the minimal F2 paid SKU."
  }
}
variable "additional_admins" {
  type = list(string)
  default = []
}
