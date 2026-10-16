variable "workspace_id" { type = string }
variable "pipeline_name" { type = string }
variable "notebook_id" {
  description = "Existing Fabric Notebook GUID. Empty keeps pipeline fail-closed."
  type        = string
  default     = ""
}
