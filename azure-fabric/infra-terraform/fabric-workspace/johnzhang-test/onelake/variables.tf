variable "lakehouse_name" {
  description = "Lakehouse display name in the parent Fabric Workspace."
  type        = string
}

variable "backend_storage_account_name" {
  description = "AzureRM state Storage Account; must match the Workspace Root backend."
  type        = string
}

variable "backend_container_name" {
  description = "AzureRM state container; must match the Workspace Root backend."
  type        = string
}
