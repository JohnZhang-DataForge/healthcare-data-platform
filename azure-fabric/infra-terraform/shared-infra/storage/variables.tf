variable "resource_group_name" {
  type        = string
  description = "Existing Azure Resource Group."
}

variable "storage_account_name" {
  type        = string
  description = "Existing Azure Storage Account."
}

variable "landing_container_name" {
  type        = string
  description = "Existing Blob Landing container name."
}
