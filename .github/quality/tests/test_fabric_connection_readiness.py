"""Pure, offline contracts for read-only Fabric/Azure Blob readiness inventory."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = (Path(__file__).resolve().parents[3] /
        "azure-fabric/infra-terraform/shared-infra/connection/connection_readiness.py")
SPEC = importlib.util.spec_from_file_location("fabric_connection_readiness", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ReadinessTest(unittest.TestCase):
    def test_supported_azure_blob_connector_and_notebook_auth(self):
        items = [{"type": "AzureBlobs", "creationMethods": [{
            "name": "AzureBlobs", "parameters": [
                {"name": "account", "required": True},
                {"name": "domain", "required": True}]}],
            "supportedCredentialTypes": ["WorkspaceIdentity", "ServicePrincipal"],
            "supportedCredentialTypesForUsageInUserControlledCode": ["ServicePrincipal"]}]
        result = module.azure_blobs_metadata(items)
        self.assertEqual(result[0]["required_parameters"], ["account", "domain"])
        self.assertEqual(result[0]["user_code_credentials"], ["ServicePrincipal"])

    def test_unsupported_connector_returns_empty(self):
        self.assertEqual(module.azure_blobs_metadata([{"type": "SQL"}]), [])
        self.assertFalse(module.azure_blobs_metadata([{"type": "AzureBlobs"}])[0]["method"])

    def test_inventory_only_matches_exact_account(self):
        entries = [
            {"displayName": "landing-omop",
             "connectionDetails": {"type": "AzureBlobs",
               "parameters": [{"name": "account", "value": "johnzhang"}]}},
            {"displayName": "unrelated",
             "connectionDetails": {"type": "AzureBlobs",
               "parameters": [{"name": "account", "value": "other"}]}},
            {"displayName": "not-a-blob",
             "connectionDetails": {"type": "SQL",
               "parameters": [{"name": "account", "value": "johnzhang"}]}}
        ]
        self.assertEqual(module.storage_connection_names(entries, "johnzhang"), ["landing-omop"])

    def test_oidc_fail_closed_without_actions_context(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "ACTIONS_ID_TOKEN_REQUEST_URL"):
                module.token_for("tenant", "client", "scope")

    def test_source_does_not_manage_resources_or_secrets(self):
        source = PATH.read_text()
        self.assertNotIn("terraform apply", source)
        self.assertNotIn("terraform destroy", source)
        self.assertNotIn("client_secret", source)
        self.assertNotIn('print(azure_token)', source)
        self.assertNotIn('print(fabric_token)', source)


if __name__ == "__main__":
    unittest.main()
