output "capacity_target" {
  description = "Never treat Terraform ARM ID as a verified Fabric workspace Capacity UUID."
  value = {
    capacity_mode            = var.capacity_mode
    capacity_origin          = var.capacity_mode
    fabric_tenant_id         = var.fabric_tenant_id
    capacity_subscription_id = var.capacity_subscription_id
    reused_fabric_uuid       = var.capacity_mode == "reuse-existing" ? var.existing_capacity_id : null
    created_azure_arm_id     = try(azapi_resource.paid_capacity[0].id, null)
    created_fabric_uuid      = null
    resource_ownership       = "NOT_VERIFIED"
    capacity_id_verified     = false
    paid_approval_verified   = false
    external_inventory_read  = false
  }
}
