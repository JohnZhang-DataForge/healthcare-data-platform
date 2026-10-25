# Existing Storage resources only. No credentials or service principal secrets.
# Reviewed externally created Publisher SP is granted landing-container write only.
resource_group_name    = "OMOP"
storage_account_name   = "johnzhang"
landing_container_name = "landing"
blob_role_assignments = {
  healthcare_blob_publisher = {
    # Verified from this enterprise service principal's own Storage OAuth token:
    # Self-Runner read-only Run #40204621241; NOT the App Registration Object ID.
    principal_id = "01cd737f-6c86-48bb-ae5c-209246d62ed6"
    role         = "Storage Blob Data Contributor"
  }
}

# The approved reader is resolved from the existing, named Workspace State.
# Fabric Workspace principal IDs are still obtained from their Terraform state.
# The externally registered Publisher principal ID is explicitly pinned above.
workspace_state_backend = {
  storage_account_name = "johnzhang"
  container_name       = "tfstate"
}
workspace_identity_readers = {
  healthcare_omop = "healthcare-omop"
}
