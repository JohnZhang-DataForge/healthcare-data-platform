output "account_id" {
  description = "Existing Storage Account resource ID."
  value       = module.storage.account_id
}

output "landing_scope" {
  description = "Existing Blob Landing RBAC scope."
  value       = module.storage.landing_scope
}

output "new_landing_role_assignment_ids" {
  description = "Only grants explicitly created by this Root."
  value       = module.storage.role_assignment_ids
}
