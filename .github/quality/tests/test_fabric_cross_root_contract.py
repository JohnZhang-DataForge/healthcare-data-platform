"""Offline cross-Root ownership and State contracts; no Azure calls."""

from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parents[3]
TF = REPO / "azure-fabric" / "infra-terraform"
FABRIC = TF / "fabric-workspace" / "healthcare-omop"
STORAGE = TF / "shared-infra" / "storage"
WORKSPACE = FABRIC / "workspace"
ONELAKE = FABRIC / "onelake"


class FabricCrossRootContract(unittest.TestCase):
    def source(self, root, name):
        return (root / name).read_text(encoding="utf-8")

    def test_all_new_roots_are_separate_and_reuse_modules(self):
        for root, module in ((WORKSPACE, "workspace"), (ONELAKE, "onelake"),
                             (STORAGE, "storage")):
            self.assertTrue(root.is_dir())
            self.assertTrue((TF / "modules" / module).is_dir())
        self.assertIn('source = "../../modules/storage"', self.source(STORAGE, "main.tf"))
        self.assertFalse(list(FABRIC.glob("*.tf")))
        self.assertFalse(list((TF / "shared-infra").glob("*.tf")))

    def test_all_three_backend_keys_are_unique_and_not_legacy(self):
        keys = []
        for root in (WORKSPACE, ONELAKE, STORAGE):
            versions = self.source(root, "versions.tf")
            match = re.search(r'(?m)^\s*key\s*=\s*"([^"]+)"', versions)
            self.assertIsNotNone(match)
            keys.append(match.group(1))
        self.assertEqual(keys, [
            "fabric-workspace/workspace.tfstate",
            "fabric-workspace/onelake.tfstate",
            "shared-infra/storage.tfstate",
        ])
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(not key.startswith("dev/") and
                            not key.startswith("fabric/platform") for key in keys))
        self.assertNotIn("healthcare-omop", " ".join(keys))

    def test_named_workspace_outputs_and_onelake_fail_closed(self):
        workspace = self.source(WORKSPACE, "outputs.tf")
        onelake = self.source(ONELAKE, "main.tf")
        self.assertIn('output "fabric_workspace_id"', workspace)
        self.assertIn("module.workspace.workspace_id", workspace)
        self.assertIn('workspace = terraform.workspace', onelake)
        self.assertIn('key                  = "fabric-workspace/workspace.tfstate"', onelake)
        self.assertIn('data.terraform_remote_state.workspace.outputs.fabric_workspace_id', onelake)
        for bad in ('try(', 'coalesce(', 'FABRIC_WORKSPACE_ID'):
            self.assertNotIn(bad, onelake)
        for root in (WORKSPACE, ONELAKE):
            self.assertIn('terraform.workspace != "default"',
                          self.source(root, "outputs.tf"))
            self.assertIn('terraform.workspace == local.workspace_name',
                          self.source(root, "outputs.tf"))

    def test_storage_is_shared_not_fabric_workspace_specific(self):
        main = self.source(STORAGE, "main.tf")
        tfvars = self.source(STORAGE, "terraform.tfvars")
        self.assertNotIn("terraform.workspace", main)
        self.assertNotIn("workspace_id", main)
        self.assertNotIn("capacity_id", main)
        self.assertIn("module \"storage\"", main)
        self.assertIn("blob_role_assignments  = var.blob_role_assignments", main)
        self.assertIn("blob_role_assignments  = {}", tfvars)
        self.assertIn('storage_account_name   = "johnzhang"', tfvars)
        self.assertIn("default = {}", self.source(STORAGE, "iam.tf"))
        for filename in ("main.tf", "iam.tf", "variables.tf", "outputs.tf"):
            self.assertNotRegex(self.source(STORAGE, filename),
                                r'resource\s+"(azurerm_storage_account|fabric_capacity)"')

    def test_no_fabric_item_owned_by_new_terraform_tree(self):
        roots = (WORKSPACE, ONELAKE, STORAGE)
        combined = "\n".join(
            p.read_text() for root in roots for p in root.glob("*.tf")
        )
        for bad in ("fabric_notebook", "fabric_data_pipeline", "fabric_capacity"):
            self.assertNotIn(bad, combined)
        self.assertNotIn('backend "local"', combined)


if __name__ == "__main__":
    unittest.main()
