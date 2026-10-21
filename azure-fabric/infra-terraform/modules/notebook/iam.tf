# Fabric Notebook IAM ownership
# There is currently no blanket per-item IAM resource in the pinned Fabric
# provider for this item type. The parent Fabric Workspace authorization is
# managed in modules/workspace/iam.tf (component workspace).
# Do NOT create duplicate or fictitious azurerm_role_assignment for Fabric
# items. Any separately supported item-share API can be added here later.
# Resource-specific IAM is not enabled until a real supported mechanism is vetted.
