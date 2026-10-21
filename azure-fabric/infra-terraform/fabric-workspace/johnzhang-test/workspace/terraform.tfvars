# Versioned non-secret settings. Change this ID when switching Fabric tenants/accounts.
# Existing FREE Trial F4 only: references Capacity; Terraform does NOT create Capacity.
description      = "Isolated Terraform end-to-end validation workspace johnzhang-test"
capacity_id      = "3914ac8b-3375-498b-b3c0-1180a1902dd6"
role_assignments = {}

# Fabric Portal account: johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com
# Object ID provided for the above user on 2026-10-21. Verify mapping before live Apply.
# Workspace Admin is granted by modules/workspace/iam.tf, not by Self-Runner.
portal_admin_user_object_id = "670194b1-b1ff-41af-971a-a61438061f39"
