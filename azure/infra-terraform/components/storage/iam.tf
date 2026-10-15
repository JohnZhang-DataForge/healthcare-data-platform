# Authorization values are supplied in environments/dev.tfvars:
#   blob_role_assignments = { role_name = { principal_id = "OBJECT-ID", role = "..." } }
# The implementation is in ../../modules/storage/iam.tf. IAM is deployed in
# the SAME state as this storage component, not a separate project-wide state.
