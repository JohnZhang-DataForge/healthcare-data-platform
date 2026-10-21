"""Offline contract for the sole Fabric Terraform Root and current account."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
TF = ROOT / "azure-fabric" / "infra-terraform"
ENV = TF / "components" / "fabric-environment"


class FabricEnvironmentStructureTest(unittest.TestCase):
    def test_only_one_root_and_three_modules(self):
        roots = sorted(p.name for p in (TF / "components").iterdir() if p.is_dir())
        modules = sorted(p.name for p in (TF / "modules").iterdir() if p.is_dir())
        self.assertEqual(roots, ["fabric-environment"])
        self.assertEqual(modules, ["connection", "onelake", "workspace"])
        self.assertFalse((ENV / "environments" / "healthcare-omop.tfvars.example").exists())

    def test_workspace_name_matches_terraform_cli_workspace(self):
        main = (ENV / "main.tf").read_text()
        for marker in (
            'workspace_name   = terraform.workspace',
            'workspace_id      = module.workspace.workspace_id',
            'source = "../../modules/workspace"',
            'source = "../../modules/onelake"',
            'source = "../../modules/connection"',
        ):
            self.assertIn(marker, main)
        self.assertNotRegex(
            main, r'(?m)^\s*resource\s+"fabric_(workspace|lakehouse|connection)"'
        )

    def test_existing_workspace_import_guard_and_new_workspace_support(self):
        main = (ENV / "main.tf").read_text()
        self.assertIn('terraform.workspace != "default"', main)
        self.assertIn(
            'terraform.workspace != "healthcare-omop" || var.existing_workspace_imported',
            main,
        )
        self.assertIn('default = false', (ENV / "variables.tf").read_text())
        self.assertTrue((ENV / "environments" / "healthcare-omop.tfvars").exists())

    def test_state_and_connection(self):
        versions = (ENV / "versions.tf").read_text()
        self.assertIn('backend "azurerm" {}', versions)
        self.assertNotRegex(versions, r'(?m)^\s*key\s*=')
        self.assertIn('terraform.workspace', (ENV / "outputs.tf").read_text())
        self.assertIn('default = null', (ENV / "variables.tf").read_text())
        self.assertIn('var.connection == null ? 0 : 1', (ENV / "main.tf").read_text())
        connection = (TF / "modules" / "connection" / "main.tf").read_text()
        self.assertIn('service_principal_secret_reference', connection)
        self.assertIn('prevent_destroy = true', connection)


if __name__ == "__main__":
    unittest.main()
