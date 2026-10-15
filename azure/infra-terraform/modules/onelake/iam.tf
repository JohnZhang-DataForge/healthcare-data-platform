# The Fabric OneLake Data Access Security resource is PREVIEW. Provider preview
# mode must be explicitly enabled. This component owns its own Lakehouse roles.
# No role resources are planned unless data_access_roles is nonempty.
resource "fabric_onelake_data_access_security" "roles" {
  for_each     = var.data_access_roles
  workspace_id = var.workspace_id
  item_id      = fabric_lakehouse.current.id
  role_name    = each.key
  decision_rules = [
    {
      effect = "Permit"
      permission = [
        {
          attribute_name              = "Path"
          attribute_value_included_in = each.value.paths
        },
        {
          attribute_name              = "Action"
          attribute_value_included_in = each.value.actions
        }
      ]
    }
  ]
  members = {
    microsoft_entra_members = [
      for principal in each.value.entra_members : {
        object_id   = principal.object_id
        object_type = principal.object_type
        tenant_id   = principal.tenant_id
      }
    ]
  }
}
