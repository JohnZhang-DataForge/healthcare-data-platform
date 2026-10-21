"""Static contract for the single-account, same-name Fabric Terraform root."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
TF = ROOT / "azure-fabric" / "infra-terraform"
ENV = TF / "components" / "fabric-environment"


class FabricEnvironmentStructureTest(unittest.TestCase):
    def test_same_name_workspace_and_module_dependencies(self):
        main = (ENV / "main.tf").read_text()
        self.assertIn('workspace_name   = terraform.workspace', main)
        self.assertIn('workspace_id      = module.workspace.workspace_id', main)
        self.assertIn('source = "../../modules/workspace"', main)
        self.assertIn('source = "../../modules/onelake"', main)
        self.assertIn('source = "../../modules/connection"', main)
        self.assertNotRegex(main, r'(?m)^\\s*resource\\s+"fabric_(workspace|lakehouse|connection)"')

    def test_default_and_existing_workspace_are_blocked_until_adopted(self):
        main = (ENV / "main.tf").read_text()
        self.assertIn('terraform.workspace != "default"', main)
        self.assertIn('terraform.workspace != "healthcare-omop" || var.existing_workspace_imported', main)
        self.assertIn('depends_on = [terraform_data.workspace_selection]', main)
        self.assertIn('default = false', (ENV / "variables.tf").read_text())

    def test_single_backend_key_and_no_account_profile(self):
        versions = (ENV / "versions.tf").read_text()
        self.assertIn('backend "azurerm" {}', versions)
        self.assertNotRegex(versions, r'key\\s*=')
        self.assertNotIn('account_profile', (ENV / "variables.tf").read_text())
        self.assertIn('terraform.workspace', (ENV / "outputs.tf").read_text())

    def test_connection_opt_in_no_secrets_or_anonymous(self):
        variables = (ENV / "variables.tf").read_text()
        conn = (TF / "modules" / "connection" / "main.tf").read_text()
        self.assertIn('default = null', variables)
        self.assertIn('var.connection == null ? 0 : 1', (ENV / "main.tf").read_text())
        self.assertIn('ServicePrincipal', conn)
        self.assertIn('WorkspaceIdentity', (TF / "modules" / "connection" / "variables.tf").read_text())
        self.assertIn('service_principal_secret_reference', conn)
        self.assertNotIn('client_secret_wo', conn)
        self.assertNotIn('credential_type       = "Anonymous"', conn)
        self.assertIn('prevent_destroy = true', conn)


if __name__ == "__main__":
    unittest.main()
