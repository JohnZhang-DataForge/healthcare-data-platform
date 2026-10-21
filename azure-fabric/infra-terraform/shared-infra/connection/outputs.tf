output "connection_id" {
  description = "Null when connection is intentionally disabled."
  value       = try(module.azure_blob_connection[0].connection_id, null)
}
