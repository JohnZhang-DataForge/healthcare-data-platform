"""Offline source-only gates for AzureBlobs Connection Root.

These assertions are NOT a substitute for provider validation, remote inventory,
credential verification or an authorized Terraform plan. Never contact a cloud API.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "new-environments" / "connection"
DENIALS = (
    "connection_creation_approved", "connection_inventory_verified",
    "connector_metadata_verified", "blob_domain_verified",
    "reader_access_verified", "key_vault_reference_verified",
    "workspace_identity_verified", "user_controlled_code_approved",
    "fresh_storage_provenance_verified",
)


def audit_source(main: str, variables: str, outputs: str) -> None:
    """Cheap independent defense against accidentally weakening the source gate."""
    required = (
        'resource "fabric_connection" "azure_blob"',
        'connectivity_type                   = "ShareableCloud"',
        'type            = "AzureBlobs"',
        'creation_method = "AzureBlobs"',
        '{ name = "account", value = var.storage_account_name }',
        '{ name = "domain", value = var.blob_domain }',
        'credential_type      = var.reader_credential_type',
        'var.reader_credential_type == "ServicePrincipal"',
        'service_principal_secret_reference = {',
        'connection_id = var.key_vault_connection_id',
        'secret_name   = var.key_vault_secret_name',
        'var.blob_reader_tenant_id == var.backend_tenant_id',
        'var.backend_operator_client_id != var.fabric_deployer_client_id',
        'var.blob_reader_client_id != var.backend_operator_client_id',
        'var.blob_reader_client_id != var.fabric_deployer_client_id',
        'var.workspace_identity_verified',
        'var.key_vault_reference_verified',
        'var.connection_name == "HDP-${var.environment}-azureblobs"',
        'var.bootstrap_mode == "reuse-existing"',
        'var.bootstrap_mode == "fresh-bootstrap"',
        'var.storage_account_name == "johnzhang"',
        '!var.fresh_storage_provenance_verified',
        'var.storage_account_name != "johnzhang"',
        'var.fresh_storage_provenance_verified',
        'can(regex("^hdp[a-z0-9]{0,21}$", var.storage_account_name))',
        'prevent_destroy = true',
        'skip_test_connection = false',
        'allow_usage_in_user_controlled_code = var.user_controlled_code_approved',
    )
    for clause in required:
        if clause not in main:
            raise ValueError("guard clause missing: " + clause)
    for name in DENIALS:
        match = re.search(
            r'variable "' + re.escape(name) +
            r'"\s*\{[^}]*?\bdefault\s*=\s*(true|false)', variables, re.S
        )
        if match is None or match.group(1) != "false":
            raise ValueError("default-deny approval missing: " + name)
        if "var." + name not in main:
            raise ValueError("approval variable unused: " + name)
    if not all(item in variables for item in (
        'variable "backend_tenant_id"', 'variable "backend_operator_client_id"',
        'variable "fabric_deployer_client_id"', 'variable "blob_reader_tenant_id"',
        'variable "blob_reader_client_id"', 'variable "reader_credential_type"',
        'variable "bootstrap_mode"',
    )):
        raise ValueError("reader and deployment identity inputs must stay separate")
    # Shared precondition must apply BEFORE choosing either credential branch.
    common_gate = main.split('var.reader_credential_type == "WorkspaceIdentity"', 1)[0]
    if 'var.backend_operator_client_id != var.fabric_deployer_client_id' not in common_gate:
        raise ValueError("backend/deployer app identity separation must be common to both modes")
    if 'var.connection_creation_approved' not in common_gate:
        raise ValueError("creation approval must apply to both credential modes")
    if 'contains(["reuse-existing", "fresh-bootstrap"], var.bootstrap_mode)' not in variables:
        raise ValueError("Bootstrap origin must be one of two reviewed modes")
    if not re.search(r'variable "bootstrap_mode"\s*{[^}]+default\s*=\s*"reuse-existing"', variables):
        raise ValueError("Storage origin must default to legacy reuse, never fresh")
    if 'contains(["ServicePrincipal", "WorkspaceIdentity"], var.reader_credential_type)' not in variables:
        raise ValueError("only vetted credential modes are permitted")
    if 'var.blob_domain' not in main or 'variable "blob_domain"' not in variables:
        raise ValueError("required domain must be explicit")
    if 'output "connection_id"' not in outputs or 'fabric_connection.azure_blob.id' not in outputs:
        raise ValueError("connection ownership output missing")
    if len(re.findall(r'(?m)^resource\s+"', main)) != 1:
        raise ValueError("unexpected resource count")
    for source in (main, variables, outputs):
        if re.search(r'(?m)^\s*(data|module|import|removed|moved|provisioner)\s+["{]', source):
            raise ValueError("non-owned Terraform construct found")
        if re.search(r'\b(?:client_secret_wo|client_secret|access_key|sas_token|local-exec)\b', source):
            raise ValueError("secret value, access-key or execution bypass found")
    if re.search(r'(?m)^\s*default\s*=\s*true\s*$', variables):
        raise ValueError("default true must never silently enable creation")


class ConnectionRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / "main.tf").read_text(encoding="utf-8")
        cls.variables = (ROOT / "variables.tf").read_text(encoding="utf-8")
        cls.outputs = (ROOT / "outputs.tf").read_text(encoding="utf-8")

    def test_offline_policy_contract(self):
        audit_source(self.main, self.variables, self.outputs)

    def test_no_literal_secrets_or_environment_credentials(self):
        for path in ROOT.glob("*.tf"):
            body = path.read_text(encoding="utf-8")
            self.assertNotIn("TF_VAR_", body)
            self.assertNotIn("ARM_CLIENT_SECRET", body)
            self.assertNotIn("FABRIC_CLIENT_SECRET", body)
            self.assertNotIn("credential_type = \"Anonymous\"", body)
        self.assertNotIn("skip_test_connection = true", self.main)

    def test_mutating_creation_or_inventory_gates_fails(self):
        for clause in ("var.connection_creation_approved", "var.connection_inventory_verified",
                       "var.reader_access_verified", "prevent_destroy = true"):
            with self.subTest(clause=clause), self.assertRaises(ValueError):
                audit_source(self.main.replace(clause, "false"), self.variables, self.outputs)

    def test_fresh_storage_origin_is_default_deny_and_no_legacy_fallback(self):
        self.assertIn('default = "reuse-existing"', self.variables)
        self.assertRegex(self.variables, r'variable "fresh_storage_provenance_verified"\s*{[^}]+default\s*=\s*false')
        with self.assertRaises(ValueError):
            audit_source(self.main.replace('var.bootstrap_mode == "reuse-existing"',
                                           'true'), self.variables, self.outputs)
        with self.assertRaises(ValueError):
            audit_source(self.main.replace('!var.fresh_storage_provenance_verified',
                                           'true'), self.variables, self.outputs)
        self.assertNotIn('resource "azurerm_storage_account"', self.main)

    def test_secret_value_injection_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_source(self.main + "\nclient_secret_wo = var.secret\n",
                         self.variables, self.outputs)

    def test_enabling_any_approval_by_default_is_rejected(self):
        for name in DENIALS:
            with self.subTest(name=name), self.assertRaises(ValueError):
                text = re.sub(
                    r'(variable "' + re.escape(name) + r'"\s*\{[^}]*?default\s*=\s*)false',
                    r'\g<1>true', self.variables, count=1, flags=re.S
                )
                audit_source(self.main, text, self.outputs)

    def test_identity_or_domain_bypass_fails(self):
        for clause in (
            "var.blob_reader_tenant_id == var.backend_tenant_id",
            "var.blob_reader_client_id != var.fabric_deployer_client_id",
            "var.backend_operator_client_id != var.fabric_deployer_client_id",
            'var.storage_account_name == "johnzhang"',
            'var.storage_account_name != "johnzhang"',
            'var.bootstrap_mode == "fresh-bootstrap"',
            'var.fresh_storage_provenance_verified',
            "var.workspace_identity_verified",
            "var.key_vault_reference_verified",
        ):
            with self.subTest(clause=clause), self.assertRaises(ValueError):
                audit_source(self.main.replace(clause, "true"), self.variables, self.outputs)


if __name__ == "__main__":
    unittest.main()
