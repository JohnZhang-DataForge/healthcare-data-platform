# Only a newly owned connection's ID; no credentials or remote State output.
output "connection_id" {
  description = "New AzureBlobs connection ID after separately authorized deployment."
  value       = fabric_connection.azure_blob.id
}
