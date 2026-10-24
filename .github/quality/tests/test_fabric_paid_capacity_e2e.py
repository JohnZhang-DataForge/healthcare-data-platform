"""Offline contract tests for the isolated paid F2 test Capacity / Workspace / Lakehouse."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3] / "azure-fabric/infra-terraform"
TEST = ROOT / "fabric-workspace/johnzhang-test"
CAP = ROOT / "shared-infra/capacity"


class FabricPaidE2ETest(unittest.TestCase):
    def test_named_workspace_and_lakehouse_own_independent_root(self):
        for kind in ("workspace", "onelake"):
            root = TEST / kind
            self.assertTrue(root.is_dir())
            self.assertIn('terraform.workspace == local.workspace_name',(root/"outputs.tf").read_text())
            self.assertIn(f'key = "fabric-workspace/{kind}.tfstate"', (root/"versions.tf").read_text())
        self.assertIn('lakehouse_name               = "lh_johnzhang_test"',
                      (TEST/"onelake/terraform.tfvars").read_text())
        self.assertIn("data.terraform_remote_state.workspace.outputs.fabric_workspace_id",
                      (TEST/"onelake/main.tf").read_text())
        self.assertFalse(list(TEST.glob("*.tf")))

    def test_minimal_paid_capacity_only_and_no_trial_mutation(self):
        vars = (CAP / "terraform.tfvars").read_text()
        self.assertRegex(vars, r'sku_name\s*=\s*"F2"', vars)
        self.assertRegex(vars, r'capacity_name\s*=\s*"fcjohnzhangtest"', vars)
        self.assertRegex(vars, r'location\s*=\s*"eastus"', vars)
        self.assertRegex(vars, r'resource_group_name\s*=\s*"OMOP"', vars)
        module = (ROOT / "modules/capacity/main.tf").read_text()
        self.assertIn('resource "azurerm_fabric_capacity" "current"',module)
        self.assertNotIn('resource "fabric_workspace"',module)
        self.assertNotIn('resource "azurerm_resource_group"',module)
        self.assertIn('display_name = module.capacity.capacity_name',(CAP/"main.tf").read_text())
        self.assertIn('depends_on = [module.capacity]',(CAP/"main.tf").read_text())
        self.assertIn('data.fabric_capacity.created.id',(CAP/"outputs.tf").read_text())
        self.assertIn('key = "shared-infra/capacity.tfstate"',(CAP/"versions.tf").read_text())
        self.assertFalse(list(TEST.rglob("capacity*.tf")))
        self.assertNotIn("3914ac8b", "\n".join(p.read_text() for p in CAP.glob("*.tf*")))

    def test_workspace_capacity_reference_remains_terraform_only(self):
        workspace=(TEST/"workspace/main.tf").read_text()
        self.assertIn('source = "../../../modules/workspace"',workspace)
        self.assertIn('capacity_id      = var.capacity_id',workspace)
        self.assertNotIn("azurerm_fabric_capacity",workspace)
        self.assertNotIn("REST",workspace)
        for kind in ("workspace","onelake"):
            self.assertNotIn("terraform destroy",(TEST/kind/"main.tf").read_text())


if __name__ == "__main__":
    unittest.main()
