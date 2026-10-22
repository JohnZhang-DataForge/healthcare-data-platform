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
               "path": "johnzhang;blob.core.windows.net"}},
            {"displayName": "unrelated",
             "connectionDetails": {"type": "AzureBlobs",
               "path": "other;blob.core.windows.net"}},
            {"displayName": "not-a-blob",
             "connectionDetails": {"type": "SQL",
               "path": "johnzhang;blob.core.windows.net"}}
        ]
        self.assertEqual(module.storage_connection_names(entries, "johnzhang"), ["landing-omop"])

    def test_workspace_identity_inspect_reads_only_metadata_and_explicit_roles(self):
        workspace_id = "745ce03b-15b6-4870-b0e5-8c5750aa18dc"
        def fake_json(url, *, bearer=None, form=None):
            self.assertEqual(bearer, "test-bearer")
            if url.endswith("/" + workspace_id):
                return {"id": workspace_id, "capacityId": "existing-capacity",
                        "workspaceIdentity": None}
            if url.endswith("/roleAssignments"):
                return {"value": [
                    {"role": "Admin", "principal": {"type": "ServicePrincipal",
                        "servicePrincipalDetails": {"aadAppId": "runner-app"}}},
                    {"role": "Viewer", "principal": {"type": "User", "id": "other"}}]}
            if url.endswith("/workspaces"):
                return {"value": [{"id": workspace_id,
                                   "displayName": "healthcare-omop"}]}
            self.fail("Unexpected endpoint: " + url)
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with patch.object(module, "json_request", side_effect=fake_json), redirect_stdout(output):
            module.inspect_workspace_identity("healthcare-omop", "test-bearer", "runner-app")
        self.assertIn("WORKSPACE_IDENTITY_IN_FABRIC_API=ABSENT", output.getvalue())
        self.assertIn('RUNNER_SERVICE_PRINCIPAL_EXPLICIT_WORKSPACE_ROLES=["Admin"]',
                      output.getvalue())
        self.assertIn("WORKSPACE_IDENTITY_CLOUD_WRITES=NO", output.getvalue())

    def test_workspace_identity_inspect_requires_unique_workspace(self):
        with patch.object(module, "pages", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "exactly one"):
                module.inspect_workspace_identity("healthcare-omop", "fake", "app")

    def test_role_assignment_summary_reads_only_principal_role_and_scope(self):
        source = [{"properties": {
            "principalId": "1AE64649-A7C3-497E-9FE3-69B37D27C453",
            "roleDefinitionId": "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
            "scope": "/subscriptions/sub/resourceGroups/OMOP/providers/Microsoft.Storage/storageAccounts/johnzhang/blobServices/default/containers/landing",
        }, "irrelevantJwt": "NEVER-PRINT"}]
        result = module.summarize_scope_role_assignments(source)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["principal_id"], "1ae64649-a7c3-497e-9fe3-69b37d27c453")
        self.assertEqual(result[0]["role_definition_id"], "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1")
        self.assertEqual(set(result[0]), {"principal_id", "role_definition_id", "scope"})
        with self.assertRaisesRegex(RuntimeError, "missing required metadata"):
            module.summarize_scope_role_assignments([{"properties": {}}])

    def test_exact_connection_get_proves_account_id_and_type_not_runtime_access(self):
        from contextlib import redirect_stdout
        from io import StringIO
        connection_id = "92d67d9c-7a9d-4619-bcf3-2b48b5b93788"
        source = {"id": connection_id, "displayName": "healthcare-omop-landing-blob",
                  "connectionDetails": {"type": "AzureBlobs",
                      "path": "johnzhang;blob.core.windows.net"},
                  "credentialDetails": {"secret": "DO-NOT-PRINT"}}
        output = StringIO()
        with patch.object(module, "json_request", return_value=source) as get, redirect_stdout(output):
            module.verify_exact_connection(connection_id, "johnzhang", "token")
        self.assertEqual(get.call_count, 1)
        self.assertIn("EXACT_FABRIC_CONNECTION_GET=PASS", output.getvalue())
        self.assertIn("ACTUAL_BLOB_READ=NOT_TESTED", output.getvalue())
        self.assertNotIn("DO-NOT-PRINT", output.getvalue())
        with patch.object(module, "json_request", return_value=source):
            with self.assertRaisesRegex(RuntimeError, "path did not match"):
                module.verify_exact_connection(connection_id, "other", "token")

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
