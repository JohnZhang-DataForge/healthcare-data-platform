# Versioned non-secret settings. Change this ID when switching Fabric tenants/accounts.
# Existing FREE Trial F4 only: references Capacity; Terraform does NOT create Capacity.
description      = "Isolated Terraform end-to-end validation workspace johnzhang-test"
capacity_id      = "3914ac8b-3375-498b-b3c0-1180a1902dd6"
role_assignments = {}

# Fabric Portal account: johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com
# Replace null with this *user's verified Entra Object ID* to grant Workspace Admin.
# Entra admin center > Identity > Users > All users > selected user > Object ID.
# Null intentionally causes NO grant until identity is verified; never guess a GUID.
portal_admin_user_object_id = null
