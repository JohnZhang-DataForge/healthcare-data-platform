# Only explicit additional Workspace membership grants are managed.
# The reusable module owns fabric_workspace_role_assignment resources.
variable "role_assignments" {
  description = "Entra object IDs and roles to grant; empty means no added grants."
  type = map(object({
    principal_id   = string
    principal_type = string
    role           = string
  }))
  default = {}
}

# This tenant-specific Entra user Object ID is configured per Workspace, not in Self-Runner.
# Until a verified ID is supplied, do NOT create an accidental or fictitious membership.
variable "portal_admin_user_object_id" {
  description = "Verified Entra User Object ID for Workspace Admin (not UPN, tenant ID, client ID or service-principal ID)."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.portal_admin_user_object_id == null || can(regex("^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", var.portal_admin_user_object_id))
    error_message = "portal_admin_user_object_id must be null or a valid Entra user Object ID GUID."
  }
}
