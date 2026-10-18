variable "resource_group_name" { type = string }
variable "storage_account_name" { type = string }
variable "landing_container_name" { type = string }

# Component defines WHO and WHICH ROLE; the child module defines HOW.
variable "blob_role_assignments" {
  description = "New landing-container assignments only. Import any existing Portal bindings before managing."
  type = map(object({
    principal_id = string # Entra service principal OBJECT ID (not application/client ID)
    role         = string # Example: Storage Blob Data Reader / Contributor
  }))
  default = {}
}
