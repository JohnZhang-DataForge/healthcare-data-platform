"""Static contracts for the workspace-scoped Fabric Terraform Root."""

from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[3]
INFRA = REPO / "azure-fabric" / "infra-terraform"
PARENT = INFRA / "fabric-workspace" / "healthcare-omop"
WORKSPACE = PARENT / "workspace"


class FabricWorkspaceRootTest(unittest.TestCase):
    def text(self, filename):
        return (WORKSPACE / filename).read_text(encoding="utf-8")

    def test_one_workspace_parent_and_seven_expected_files(self):
        self.assertEqual(WORKSPACE.parent.name, "healthcare-omop")
        self.assertEqual(
            {p.name for p in WORKSPACE.iterdir() if p.is_file() and (p.suffix == ".tf" or p.name == "terraform.tfvars")},
            {
                "main.tf",
                "iam.tf",
                "variables.tf",
                "outputs.tf",
                "versions.tf",
                "providers.tf",
                "terraform.tfvars",
            },
        )
        self.assertFalse(list(PARENT.glob("*.tf")))

    def test_module_source_points_to_existing_workspace_model(self):
        main = self.text("main.tf")
        self.assertIn('source = "../../../modules/workspace"', main)
        self.assertTrue((WORKSPACE / "../../../modules/workspace").resolve().is_dir())
        self.assertIn("basename(dirname(abspath(path.root)))", main)
        self.assertIn("workspace_name   = local.workspace_name", main)
        self.assertIn("role_assignments = merge(var.role_assignments, local.portal_admin_role_assignments)", main)
        self.assertNotRegex(main, r'(?m)^\s*resource\s+"fabric_')

    def test_state_base_key_unique_to_resource_type(self):
        versions = self.text("versions.tf")
        self.assertIn('backend "azurerm"', versions)
        self.assertIn('key = "fabric-workspace/workspace.tfstate"', versions)
        self.assertNotIn("healthcare-omop.tfstate", versions)
        self.assertNotIn("dev/workspace.tfstate", versions)
        self.assertIn('source  = "microsoft/fabric"', versions)

    def test_fabric_and_cli_workspace_names_are_guarded(self):
        outputs = self.text("outputs.tf")
        self.assertIn("value       = module.workspace.workspace_id", outputs)
        self.assertIn('output "fabric_workspace_id"', outputs)
        self.assertIn('output "fabric_workspace_name"', outputs)
        self.assertEqual(
            outputs.count('terraform.workspace != "default" && terraform.workspace == local.workspace_name'),
            2,
        )
        self.assertNotIn('workspace_name = "healthcare-omop"', self.text("main.tf"))

    def test_no_implicit_capacity_or_iam_grants(self):
        variables = self.text("variables.tf")
        iam = self.text("iam.tf")
        tfvars = self.text("terraform.tfvars")
        self.assertIn('variable "capacity_id"', variables)
        self.assertNotRegex(variables, r'(?s)variable "capacity_id"\s*\{[^}]*default\s*=')
        self.assertIn('default = {}', iam)
        self.assertIn('role_assignments = {}', tfvars)
        self.assertIn('capacity_id      = "3914ac8b-3375-498b-b3c0-1180a1902dd6"', tfvars)
        self.assertIn("runner does not inject it", variables)
        self.assertNotIn("client_secret", tfvars)
        self.assertIn("use_oidc = true", self.text("providers.tf"))

    def test_each_workspace_owns_existing_capacity_reference(self):
        for name in ("healthcare-omop", "johnzhang-test"):
            root = INFRA / "fabric-workspace" / name / "workspace"
            tfvars = (root / "terraform.tfvars").read_text(encoding="utf-8")
            variables = (root / "variables.tf").read_text(encoding="utf-8")
            self.assertIn('capacity_id      = "3914ac8b-3375-498b-b3c0-1180a1902dd6"', tfvars)
            self.assertIn('variable "capacity_id"', variables)
            self.assertNotIn("azurerm_fabric_capacity", (root / "main.tf").read_text())

    def test_workspace_admin_is_root_owned_and_fails_closed_until_object_id_is_verified(self):
        module_iam = (INFRA / "modules" / "workspace" / "iam.tf").read_text(encoding="utf-8")
        self.assertIn('resource "fabric_workspace_role_assignment" "additional"', module_iam)
        self.assertIn('workspace_id = fabric_workspace.current.id', module_iam)
        for name in ("healthcare-omop", "johnzhang-test"):
            root = INFRA / "fabric-workspace" / name / "workspace"
            iam = (root / "iam.tf").read_text(encoding="utf-8")
            main = (root / "main.tf").read_text(encoding="utf-8")
            tfvars = (root / "terraform.tfvars").read_text(encoding="utf-8")
            self.assertIn('variable "portal_admin_user_object_id"', iam)
            self.assertIn('default     = null', iam)
            self.assertIn('can(regex(', iam)
            self.assertIn('portal_admin_role_assignments = var.portal_admin_user_object_id == null ? {} : {', main)
            self.assertIn('principal_type = "User"', main)
            self.assertIn('role           = "Admin"', main)
            self.assertIn('role_assignments = merge(var.role_assignments, local.portal_admin_role_assignments)', main)
            self.assertIn('portal_admin_user_object_id = null', tfvars)
            self.assertIn('johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com', tfvars)
            self.assertNotIn("azuread_user", main)
            self.assertNotIn("FABRIC_ADMIN_OBJECT_ID", main)
            self.assertNotIn("azurerm_fabric_capacity", main)

    def test_no_notebook_or_pipeline_terraform_ownership(self):
        source = "\n".join(self.text(p.name) for p in WORKSPACE.glob("*.tf"))
        self.assertNotRegex(source, r'resource\s+"fabric_(notebook|data_pipeline)"')
        self.assertNotRegex(source, r'module\s+"(notebook|data-factory)"')


if __name__ == "__main__":
    unittest.main()
