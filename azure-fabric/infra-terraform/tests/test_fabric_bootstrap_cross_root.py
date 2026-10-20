"""Offline ownership boundary assertions for SIX independent Fabric Terraform roots.

The tests inspect tracked source only: no Terraform, providers, cloud, secrets or
state. A source-only PASS does not establish absence of remote resources.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "bootstrap"
NEW = ROOT / "new-environments"

EXPECTED = {
    ("bootstrap", "identity"): {
        "azuread_application_registration": 3,
        "azuread_service_principal": 3,
        "azuread_group": 2,
        "azuread_application_federated_identity_credential": 2,
    },
    ("bootstrap", "storage"): {
        "azurerm_resource_group": 1,
        "azurerm_storage_account": 1,
        "azurerm_storage_container": 2,
        "azurerm_role_assignment": 2,
    },
    ("bootstrap", "capacity"): {"azapi_resource": 1},
    ("new-environments", "workspace"): {"fabric_workspace": 1},
    ("new-environments", "onelake"): {"fabric_lakehouse": 1},
    ("new-environments", "connection"): {"fabric_connection": 1},
}

FORBIDDEN_BLOCKS = re.compile(
    r'^\s*(?:data|module|import|moved|removed|provisioner)\s+(?:["{])',
    re.M,
)
RESOURCE = re.compile(r'^resource\s+"([^"]+)"\s+"([^"]+)"\s*{', re.M)


class BootstrapCrossRootStaticTests(unittest.TestCase):
    def test_six_nonoverlapping_terraform_ownership_roots(self):
        addresses = set()
        for (group, name), expected in EXPECTED.items():
            with self.subTest(root=f"{group}/{name}"):
                location = ROOT / group / name
                self.assertTrue(location.is_dir())
                sources = {p.name: p.read_text(encoding="utf-8")
                           for p in location.glob("*.tf")}
                self.assertEqual(
                    set(sources), {"versions.tf", "providers.tf", "variables.tf",
                                   "main.tf", "outputs.tf"}
                )
                full = "\n".join(sources.values())
                self.assertIsNone(FORBIDDEN_BLOCKS.search(full))
                found = RESOURCE.findall(sources["main.tf"])
                counts = {kind: sum(typ == kind for typ, _ in found)
                          for kind, _ in found}
                self.assertEqual(counts, expected)
                for kind, resource_name in found:
                    address = f"{kind}.{resource_name}"
                    self.assertNotIn(address, addresses)
                    addresses.add(address)
                self.assertEqual(full.count("prevent_destroy = true"), len(found))
                self.assertNotRegex(full, r'\b(?:client_secret|storage_account_key|sas_token)\b')
                for command in ("terraform init", "terraform plan", "terraform apply",
                                "terraform destroy", "terraform import"):
                    self.assertNotIn(command, full)

    def test_bootstrap_state_cannot_bootstrap_itself(self):
        for name in ("identity", "storage", "capacity"):
            versions = (BOOTSTRAP / name / "versions.tf").read_text(encoding="utf-8")
            self.assertIn('backend "local" {}', versions)
            self.assertNotIn('backend "azurerm"', versions)
        for name in ("workspace", "onelake", "connection"):
            versions = (NEW / name / "versions.tf").read_text(encoding="utf-8")
            self.assertIn('backend "azurerm" {}', versions)
            self.assertNotIn('backend "local"', versions)

    def test_fresh_storage_does_not_adopt_legacy_or_manage_capacity(self):
        storage = (BOOTSTRAP / "storage" / "main.tf").read_text(encoding="utf-8")
        self.assertIn('var.bootstrap_mode == "fresh-bootstrap"', storage)
        self.assertIn("scope                = azurerm_storage_container.backend[0].resource_manager_id", storage)
        self.assertIn("scope                = azurerm_storage_container.landing[0].resource_manager_id", storage)
        self.assertNotIn('"johnzhang"', storage)
        self.assertNotIn("terraform_remote_state", storage)
        capacity = (BOOTSTRAP / "capacity" / "main.tf").read_text(encoding="utf-8")
        self.assertIn('var.capacity_mode == "create-new"', capacity)
        self.assertIn('count     = local.paid_creation_gate ? 1 : 0', capacity)
        self.assertNotIn("terraform_remote_state", capacity)

    def test_single_owner_of_workspace_and_lakehouse(self):
        workspace = (NEW / "workspace" / "main.tf").read_text(encoding="utf-8")
        lakehouse = (NEW / "onelake" / "main.tf").read_text(encoding="utf-8")
        conn = (NEW / "connection" / "main.tf").read_text(encoding="utf-8")
        self.assertIn("var.workspace_creation_approved", workspace)
        self.assertIn("var.capacity_id", workspace)
        self.assertIn("var.lakehouse_creation_approved", lakehouse)
        self.assertIn("var.workspace_id_verified", lakehouse)
        self.assertIn("var.connection_creation_approved", conn)
        self.assertIn("var.connection_inventory_verified", conn)
        self.assertNotIn('resource "fabric_workspace"', conn + lakehouse)
        self.assertNotIn('resource "fabric_lakehouse"', conn + workspace)

    def test_no_cloud_authenticated_or_stateful_pr_ci(self):
        workflow = (ROOT.parents[1] / ".github/workflows/fabric-environment-preflight.yml").read_text(
            encoding="utf-8")
        for name in ("identity", "storage", "capacity"):
            self.assertIn(f"terraform fmt -check -diff azure-fabric/infra-terraform/bootstrap/{name}", workflow)
        for name in ("workspace", "onelake", "connection"):
            self.assertIn(f"terraform fmt -check -diff azure-fabric/infra-terraform/new-environments/{name}", workflow)
        self.assertIn("test_fabric_bootstrap_cross_root.py", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("id-token: write", workflow)
        for line in workflow.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if re.match(r"terraform\s+(?!fmt\b)", line):
                self.fail("PR CI contains a non-format Terraform command")


if __name__ == "__main__":
    unittest.main()
