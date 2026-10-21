# Non-secret, versioned configuration for the EXISTING healthcare-omop workspace.
# The exact Fabric Workspace name comes from terraform.workspace, not this file.
# Before apply: import/check its real GUID and set FABRIC_CAPACITY_ID in the
# existing Self-Runner repository variables to the CURRENT assigned Capacity ID.
# Leaving capacity_id out is deliberate: the runner must supply a verified value.
# No Workspace/Capacity/Storage is automatically purchased or re-created here.

description      = "Healthcare OMOP analytical platform"
lakehouse_name   = "lh_omop_analytics"
role_assignments = {}
data_access_roles = {}

# Landing connection is opt-in because Reader auth has not been verified.
# For deployment, supply the nonsecret connection object in the GitHub Actions
# variable FABRIC_LANDING_CONNECTION_CONFIG. Never store secrets in tfvars.
