# Existing resources only. No credentials, service principal secrets or grants.
resource_group_name    = "OMOP"
storage_account_name   = "johnzhang"
landing_container_name = "landing"
blob_role_assignments  = {}

# The approved reader is resolved from the existing, named Workspace State.
# No generated Entra Object ID is hardcoded in these shared infra files.
workspace_state_backend = {
  storage_account_name = "johnzhang"
  container_name       = "tfstate"
}
workspace_identity_readers = {
  healthcare_omop = "healthcare-omop"
}
