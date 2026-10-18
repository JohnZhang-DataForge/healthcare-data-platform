resource_group_name    = "OMOP"
storage_account_name   = "johnzhang"
landing_container_name = "landing"

# Bootstrap SP already has Portal-created landing permissions.
# Do NOT duplicate it. Declare only NEW principal bindings, or import originals.
blob_role_assignments = {}
