# Existing AzureBlobs account; no credentials/secrets are committed.
# This is a planned Connection candidate only. Do not Apply before the
# explicit Landing container Reader authorization exists and is read back.
connection = {
  name                 = "healthcare-omop-landing-blob"
  storage_account_name = "johnzhang"
  blob_domain          = "blob.core.windows.net"
  reader_type          = "WorkspaceIdentity"
  allow_user_code      = true
}
