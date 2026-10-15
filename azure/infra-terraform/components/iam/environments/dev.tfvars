resource_group_name    = "OMOP"
storage_account_name   = "johnzhang"
landing_container_name = "landing"

# RBAC bootstrap was done in Portal. Keep empty; import before managing existing grants.
# Creating NEW assignments requires roleAssignments/write (not held by RG Contributor).
role_assignments = {}
