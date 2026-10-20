# This Root is intentionally non-deployable from defaults.
# No data sources/automatic inventory: reuse is a UUID reference ONLY.
# Creation needs independent external approval; passing flags is not proof.
locals {
  capacity_name = "hdp${replace(var.environment, "-", "")}capacity"

  paid_creation_gate = (
    var.capacity_mode == "create-new"
    && var.capacity_creation_approved
    && var.independent_billing_approval_verified
    && var.protected_environment_approval_verified
    && var.subscription_and_rg_inventory_verified
    && var.name_and_sku_quota_verified
    && var.seed_operator_authorized
    && var.capacity_resource_group_id != null
    && (var.capacity_resource_group_id == null ? false : lower(var.capacity_resource_group_id) == "/subscriptions/${lower(var.capacity_subscription_id)}/resourcegroups/rg-hdp-${var.environment}")
    && var.capacity_region != null
    && var.capacity_sku != null
    && length(var.capacity_administrators) > 0
    && var.estimated_monthly_usd > 0
    && var.monthly_budget_usd >= var.estimated_monthly_usd
    && var.approved_cost_review_reference != null
    && var.reviewed_source_sha != null
  )
}

# Explicit ARM 2023-11-01: body.sku belongs inside body, not top level.
# Resource ID is an ARM path; downstream Fabric Capacity UUID requires readback.
resource "azapi_resource" "paid_capacity" {
  count     = local.paid_creation_gate ? 1 : 0
  type      = "Microsoft.Fabric/capacities@2023-11-01"
  name      = local.capacity_name
  parent_id = var.capacity_resource_group_id
  location  = var.capacity_region

  body = {
    properties = {
      administration = {
        members = var.capacity_administrators
      }
    }
    sku = {
      name = var.capacity_sku
      tier = "Fabric"
    }
  }

  tags = {
    owner_environment = var.environment
    owner_change      = "bootstrap-fabric-infrastructure"
  }

  lifecycle {
    prevent_destroy = true
  }
}
