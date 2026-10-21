# Versioned non-secret settings. Change this ID when switching Fabric tenants/accounts.
# Existing FREE Trial F4 only: references Capacity; Terraform does NOT create Capacity.
description      = "Healthcare OMOP analytical workspace"
capacity_id      = "3914ac8b-3375-498b-b3c0-1180a1902dd6"
role_assignments = {}

# Fabric Portal account: johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com
# User-provided Entra User Object ID for this Fabric Portal admin.
# Grant uses the Workspace IAM module; the runner never injects account-specific IDs.
# Verify user/object mapping and existing members before the first cloud Apply.
portal_admin_user_object_id = "670194b1-b1ff-41af-971a-a61438061f39"
