"""Offline contracts for a Lakehouse Root dependent on Workspace remote State."""

from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[3]
INFRA = REPO / "azure-fabric" / "infra-terraform"
PARENT = INFRA / "fabric-workspace" / "healthcare-omop"
ONELAKE = PARENT / "onelake"


class FabricOnelakeRootTest(unittest.TestCase):
    def source(self, filename):
        return (ONELAKE / filename).read_text(encoding="utf-8")

    def test_expected_resource_root_and_shared_module(self):
        self.assertEqual(ONELAKE.parent.name, "healthcare-omop")
        self.assertEqual(
            {p.name for p in ONELAKE.iterdir() if p.is_file()
             and (p.suffix == ".tf" or p.name == "terraform.tfvars")},
            {"main.tf", "iam.tf", "variables.tf", "outputs.tf",
             "providers.tf", "versions.tf", "terraform.tfvars"},
        )
        self.assertTrue((ONELAKE / "../../../modules/onelake").resolve().is_dir())
        self.assertIn('source = "../../../modules/onelake"', self.source("main.tf"))

    def test_separate_backend_key_and_named_workspace(self):
        version = self.source("versions.tf")
        main = self.source("main.tf")
        self.assertIn('key = "fabric-workspace/onelake.tfstate"', version)
        self.assertIn('workspace = terraform.workspace', main)
        self.assertNotIn('key = "fabric-workspace/onelake.tfstate"', main)
        self.assertIn("basename(dirname(abspath(path.root)))", main)
        self.assertIn('terraform.workspace != "default" && terraform.workspace == local.workspace_name',
                      self.source("outputs.tf"))

    def test_remote_workspace_state_required_without_fallback(self):
        main = self.source("main.tf")
        self.assertIn('data "terraform_remote_state" "workspace"', main)
        self.assertIn('backend   = "azurerm"', main)
        self.assertIn('key                  = "fabric-workspace/workspace.tfstate"', main)
        self.assertIn('use_oidc             = true', main)
        self.assertIn('use_azuread_auth     = true', main)
        self.assertIn('workspace_id      = data.terraform_remote_state.workspace.outputs.fabric_workspace_id', main)
        self.assertNotIn("try(", main)
        self.assertNotIn("coalesce(", main)
        self.assertNotIn('variable "workspace_id"', self.source("variables.tf"))
        self.assertNotIn("FABRIC_WORKSPACE_ID", main)

    def test_no_workspace_creation_or_other_item_ownership(self):
        source = "\n".join(self.source(p.name) for p in ONELAKE.glob("*.tf"))
        for forbidden in ('resource "fabric_workspace"', 'resource "fabric_notebook"',
                          'resource "fabric_data_pipeline"'):
            self.assertNotIn(forbidden, source)
        self.assertIn("value       = module.onelake.lakehouse_id", self.source("outputs.tf"))
        self.assertIn("value       = module.onelake.onelake_tables_path", self.source("outputs.tf").replace("value = ", "value       = "))

    def test_non_secret_backend_configuration_and_no_implicit_permissions(self):
        tfvars = self.source("terraform.tfvars")
        self.assertIn('backend_storage_account_name = "johnzhang"', tfvars)
        self.assertIn('backend_container_name       = "tfstate"', tfvars)
        self.assertIn('data_access_roles            = {}', tfvars)
        self.assertNotIn("workspace_id", tfvars)
        self.assertNotIn("capacity_id", tfvars)
        self.assertIn("default = {}", self.source("iam.tf"))
        self.assertIn("preview  = true", self.source("providers.tf"))


if __name__ == "__main__":
    unittest.main()
