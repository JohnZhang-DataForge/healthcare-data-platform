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
            self.assertIn(
                'portal_admin_user_object_id = "670194b1-b1ff-41af-971a-a61438061f39"',
                tfvars,
            )
            self.assertIn('johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com', tfvars)
            self.assertNotIn("azuread_user", main)
            self.assertNotIn("FABRIC_ADMIN_OBJECT_ID", main)
            self.assertNotIn("azurerm_fabric_capacity", main)

    def test_each_workspace_explicitly_configures_same_portal_admin(self):
        johnzhang = (INFRA / "fabric-workspace/johnzhang-test/workspace/terraform.tfvars").read_text()
        omop = (INFRA / "fabric-workspace/healthcare-omop/workspace/terraform.tfvars").read_text()
        self.assertIn(
            'portal_admin_user_object_id = "670194b1-b1ff-41af-971a-a61438061f39"',
            johnzhang,
        )
        self.assertIn('portal_admin_user_object_id = "670194b1-b1ff-41af-971a-a61438061f39"', omop)
        self.assertIn('role_assignments = {}', johnzhang)
        self.assertNotIn('service_principal', johnzhang)
        self.assertNotIn('client_secret', johnzhang)

    def test_healthcare_omop_workspace_onelake_first_apply_contract(self):
        root = INFRA / "fabric-workspace" / "healthcare-omop"
        ws = root / "workspace"
        lake = root / "onelake"
        ws_main = (ws / "main.tf").read_text()
        lake_main = (lake / "main.tf").read_text()
        lake_vars = (lake / "terraform.tfvars").read_text()
        self.assertIn("basename(dirname(abspath(path.root)))", ws_main)
        self.assertIn('source = "../../../modules/workspace"', ws_main)
        self.assertIn('source = "../../../modules/onelake"', lake_main)
        self.assertIn('workspace = terraform.workspace', lake_main)
        self.assertIn("data.terraform_remote_state.workspace.outputs.fabric_workspace_id", lake_main)
        self.assertIn('key = "fabric-workspace/workspace.tfstate"', (ws / "versions.tf").read_text())
        self.assertIn('key = "fabric-workspace/onelake.tfstate"', (lake / "versions.tf").read_text())
        self.assertIn('key                  = "fabric-workspace/workspace.tfstate"', lake_main)
        self.assertIn('lakehouse_name               = "lh_omop_analytics"', lake_vars)
        self.assertIn('backend_storage_account_name = "johnzhang"', lake_vars)
        self.assertIn('backend_container_name       = "tfstate"', lake_vars)
        self.assertIn("enable_schemas = true", (INFRA / "modules/onelake/main.tf").read_text())
        self.assertNotIn("azurerm_fabric_capacity", ws_main)
        self.assertNotIn("azurerm_fabric_capacity", lake_main)

    def test_no_notebook_or_pipeline_terraform_ownership(self):
        source = "\n".join(self.text(p.name) for p in WORKSPACE.glob("*.tf"))
        self.assertNotRegex(source, r'resource\s+"fabric_(notebook|data_pipeline)"')
        self.assertNotRegex(source, r'module\s+"(notebook|data-factory)"')

    def test_workspace_identity_is_opt_in_and_omop_only(self):
        module = INFRA / "modules/workspace"
        module_main = (module / "main.tf").read_text(encoding="utf-8")
        module_outputs = (module / "outputs.tf").read_text(encoding="utf-8")
        self.assertIn('variable "enable_workspace_identity"', module_main)
        self.assertIn("default = false", module_main)
        self.assertIn('identity     = var.enable_workspace_identity ? { type = "SystemAssigned" } : null', module_main)
        self.assertIn('fabric_workspace.current.identity.service_principal_id', module_outputs)
        self.assertNotIn('resource "azurerm_fabric_capacity"', module_main)
        for name in ("healthcare-omop", "johnzhang-test"):
            root = INFRA / "fabric-workspace" / name / "workspace"
            config = (root / "terraform.tfvars").read_text(encoding="utf-8")
            main = (root / "main.tf").read_text(encoding="utf-8")
            if name == "healthcare-omop":
                self.assertIn("enable_workspace_identity = true", config)
                self.assertIn("enable_workspace_identity = var.enable_workspace_identity", main)
                self.assertIn('output "workspace_identity_principal_id"', (root / "outputs.tf").read_text())
                self.assertIn("terraform.workspace != \"default\"", (root / "outputs.tf").read_text())
            else:
                self.assertNotIn("enable_workspace_identity = true", config)
                self.assertNotIn("enable_workspace_identity = var.enable_workspace_identity", main)


if __name__ == "__main__":
    unittest.main()
