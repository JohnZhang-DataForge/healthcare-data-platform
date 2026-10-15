workspace_id   = ""
lakehouse_name = "lh_omop_analytics"

# OneLake role definitions/members are PREVIEW and disabled until explicit review.
# Example (not enabled):
# data_access_roles = {
#   analyst_person_read = {
#     paths = ["/Tables/person"]
#     actions = ["Read"]
#     entra_members = [{ object_id = "<USER_OR_GROUP_OBJECT_ID>", object_type = "Group" }]
#   }
# }
data_access_roles = {}
