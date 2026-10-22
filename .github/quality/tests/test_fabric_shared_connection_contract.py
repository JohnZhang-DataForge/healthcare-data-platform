"""Non-cloud contract for optional, account-scoped Fabric Connection Root."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SHARED = ROOT / "azure-fabric/infra-terraform/shared-infra/connection"
MODULE = ROOT / "azure-fabric/infra-terraform/modules/connection"


class SharedFabricConnectionContract(unittest.TestCase):
    def test_files_and_backend_isolation(self):
        required = {"main.tf", "variables.tf", "versions.tf", "providers.tf",
                    "outputs.tf", "terraform.tfvars", "README.md"}
        self.assertTrue(all((SHARED / x).is_file() for x in required))
        versions = (SHARED / "versions.tf").read_text()
        self.assertIn('key = "shared-infra/connection.tfstate"', versions)
        self.assertNotIn("fabric-workspace/", versions)

    def test_default_is_optional_but_planned_candidate_is_workspace_identity(self):
        source = (SHARED / "main.tf").read_text()
        vars_text = (SHARED / "variables.tf").read_text()
        self.assertIn('source = "../../modules/connection"', source)
        self.assertIn('count  = var.connection == null ? 0 : 1', source)
        self.assertIn('default = null', vars_text)
        self.assertIn('default = null', vars_text)
        candidate = (SHARED / "terraform.tfvars").read_text()
        self.assertIn('name                 = "healthcare-omop-landing-blob"', candidate)
        self.assertIn('storage_account_name = "johnzhang"', candidate)
        self.assertIn('blob_domain          = "blob.core.windows.net"', candidate)
        self.assertIn('reader_type          = "WorkspaceIdentity"', candidate)
        self.assertIn('allow_user_code      = true', candidate)
        self.assertNotIn("service_principal =", candidate)
        self.assertIn('skip_test_connection = var.reader_credential_type == "WorkspaceIdentity"',
                      (MODULE / "main.tf").read_text())

    def test_no_workspace_lakehouse_capacity_or_item_ownership(self):
        source = "\n".join((SHARED / f).read_text() for f in
                           ["main.tf", "providers.tf", "versions.tf"])
        for resource in ["fabric_workspace", "fabric_lakehouse",
                         "azurerm_fabric_capacity", "fabric_notebook",
                         "fabric_data_pipeline"]:
            self.assertNotIn('resource "' + resource + '"', source)
        self.assertIn('resource "fabric_connection"', (MODULE / "main.tf").read_text())

    def test_no_raw_credentials_in_default_config(self):
        tfvars = (SHARED / "terraform.tfvars").read_text()
        for secret_assignment in ["client_secret =", "password =", "secret_value =",
                                  "access_token ="]:
            self.assertNotIn(secret_assignment, tfvars)


if __name__ == "__main__":
    unittest.main()
