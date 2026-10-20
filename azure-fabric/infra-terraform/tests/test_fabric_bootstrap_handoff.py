"""Handoff fail-closed matrix; all test IDs/ARM paths are synthetic."""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_bootstrap_handoff import handoff, main
from fabric_bootstrap_profile import InvalidBootstrapProfile

A = "899a04e8-8d3d-486c-88a1-7bdeb22d5f1a"
B = "cb50fc2d-f9be-449a-9ae7-276884d0de55"
SUB = "6c0cc7f1-6912-4b25-805f-732be3882da8"
SUB_B = "7cb66f5d-4c20-4c31-9bc1-0547e25b745f"
CAP = "18da26c5-dc71-43d2-b6fa-1ed15e24e7cb"
CLIENTS = ("35174fe8-88a8-4d12-b97c-c395f64fd1eb",
           "76fc48a8-6a93-46be-a33b-3e41de8d8ae5",
           "639629c1-89c3-4a11-98dc-d8506aa5203e")


def fixtures(cross=False, fresh=False, paid=False):
    p = {
        "schema_version": 1,
        "environment": "lab-b",
        "bootstrap_mode": "fresh-bootstrap" if fresh else "reuse-existing",
        "tenants": {"backend_tenant_id": A, "fabric_tenant_id": B if cross else A},
        "github_oidc": {"repository": "JohnZhang-DataForge/Self-Runner",
                        "ref": "refs/heads/main"},
        "storage": {
            "account": "hdplabbstorage" if fresh else "johnzhang",
            "subscription_id": SUB,
            "resource_group": "rg-hdp-lab-b" if fresh else "existing-rg",
            "landing_container": "landing", "state_container": "tfstate",
            "state_prefix": "fabric/lab-b",
        },
        "bootstrap_state": {"strategy": "isolated-local",
                            "custody_reference": "CUSTODY-OFFLINE-PLAN-01"},
        "capacity": {"mode": "reuse-existing", "capacity_id": CAP},
    }
    if paid:
        p["capacity"] = {
            "mode": "create-new", "sku": "F2", "region": "eastus2",
            "subscription_id": SUB_B, "estimated_monthly_usd": 300,
            "monthly_budget_usd": 500, "billing_owner": "billing-owner",
            "cost_review_reference": "COST-REVIEW-20261019",
        }
    ids = {role: {"tenant_id": B if cross and role == "fabric_deployer" else A,
                  "client_id": cid}
           for role, cid in zip(("backend_operator", "fabric_deployer", "blob_reader"),
                                CLIENTS)}
    account_id = (f"/subscriptions/{SUB}/resourceGroups/"
                  f"{p['storage']['resource_group']}/providers/Microsoft.Storage/"
                  f"storageAccounts/{p['storage']['account']}")
    s = {
        "bootstrap_mode": p["bootstrap_mode"],
        "backend_tenant_id": A, "storage_subscription_id": SUB,
        "storage_account_id": None if fresh else account_id,
        "storage_account_name": p["storage"]["account"],
        "landing_container": "landing", "backend_container": "tfstate",
        "backend_state_prefix": "fabric/lab-b",
        "backend_operator_scope": None, "blob_reader_scope": None,
        "resource_ownership_status": "NOT_VERIFIED", "remote_state_checked": False,
        "initial_state_custody_checked": False, "cloud_access_verified": False,
    }
    c = {
        "capacity_mode": p["capacity"]["mode"],
        "capacity_origin": p["capacity"]["mode"],
        "fabric_tenant_id": B if cross else A,
        "capacity_subscription_id": SUB_B if paid else SUB,
        "reused_fabric_uuid": None if paid else CAP,
        "created_azure_arm_id": None, "created_fabric_uuid": None,
        "resource_ownership": "NOT_VERIFIED",
        "capacity_id_verified": False, "paid_approval_verified": False,
        "external_inventory_read": False,
    }
    return p, ids, s, c


class HandoffTests(unittest.TestCase):
    def rejected(self, fields):
        with self.assertRaises((InvalidBootstrapProfile, ValueError)):
            handoff(*fields)

    def test_reuse_same_tenant_preview_only(self):
        f = fixtures()
        result = handoff(*f)
        self.assertEqual(result["status"], "STATIC_HANDOFF_HOLD_EXTERNAL_INVENTORY")
        self.assertEqual(result["identity_topology"], "same-tenant")
        self.assertEqual(result["proposed_legacy_compatible_environment"]["fabric"]["capacity_id"], CAP)
        self.assertEqual(result["state_keys"]["workspace"], "fabric/lab-b/workspace.tfstate")
        self.assertEqual(result["proposed_legacy_compatible_backend"]["storage_account_name"], "johnzhang")
        self.assertEqual(result["proposed_connection_storage_variables"], {
            "bootstrap_mode": "reuse-existing", "storage_account_name": "johnzhang",
            "fresh_storage_provenance_verified": False, "connection_creation_approved": False,
        })
        self.assertNotEqual(result["identity_client_ids"]["backend_operator"],
                            result["identity_client_ids"]["fabric_deployer"])
        for flag in ("verified", "external_inventory_verified", "capacity_id_verified",
                     "billing_approved", "backend_state_checked", "github_oidc_verified",
                     "terraform_executed"):
            self.assertIs(result[flag], False)
        self.assertEqual(result, handoff(*(deepcopy(x) for x in f)))

    def test_reuse_cross_tenant_separates_clients(self):
        result = handoff(*fixtures(cross=True))
        self.assertEqual(result["identity_topology"], "cross-tenant")
        self.assertEqual(result["proposed_legacy_compatible_environment"]["backend"]["tenant_id"], A)
        self.assertEqual(result["proposed_legacy_compatible_environment"]["fabric"]["tenant_id"], B)

    def test_fresh_cannot_reuse_legacy_connection_backend_builder(self):
        f = fixtures(cross=True, fresh=True)
        result = handoff(*f)
        self.assertEqual(result["status"], "STATIC_HANDOFF_HOLD_FRESH_EXTERNAL_APPROVALS")
        self.assertIsNone(result["proposed_legacy_compatible_environment"])
        self.assertEqual(result["blocked_roots"], [])
        self.assertEqual(result["proposed_connection_storage_variables"]["bootstrap_mode"], "fresh-bootstrap")
        self.assertEqual(result["proposed_connection_storage_variables"]["storage_account_name"], "hdplabbstorage")
        self.assertIs(result["proposed_connection_storage_variables"]["fresh_storage_provenance_verified"], False)
        self.assertIs(result["proposed_connection_storage_variables"]["connection_creation_approved"], False)
        self.assertEqual(result["proposed_bootstrap_environment"]["schema_version"], 2)
        self.assertEqual(result["proposed_bootstrap_backend"]["storage_account_name"], "hdplabbstorage")
        self.assertEqual(result["storage_account_name"], "hdplabbstorage")
        self.assertFalse(result["external_inventory_verified"])

    def test_paid_capacity_never_uses_arm_id_as_fabric_uuid(self):
        f = fixtures(cross=True, fresh=True, paid=True)
        f[3]["created_azure_arm_id"] = (
            f"/subscriptions/{SUB_B}/resourceGroups/rg-hdp-lab-b/"
            "providers/Microsoft.Fabric/capacities/hdplabbcapacity"
        )
        result = handoff(*f)
        self.assertEqual(result["status"], "STATIC_HANDOFF_HOLD_PAID_CAPACITY_UUID")
        self.assertIsNone(result["reused_fabric_capacity_uuid"])
        self.assertIsNone(result["proposed_legacy_compatible_environment"])
        self.assertEqual(result["created_capacity_arm_id"], f[3]["created_azure_arm_id"])
        self.assertFalse(result["billing_approved"])
        self.assertNotEqual(result["storage_subscription_id"], result["capacity_subscription_id"])

    def test_reject_wrong_owner_namespace_and_cross_tenant(self):
        for position, field, value in [
            (2, "storage_account_name", "johnzhang2"),
            (2, "storage_subscription_id", SUB_B),
            (2, "backend_state_prefix", "dev"),
            (2, "backend_tenant_id", B),
            (2, "storage_account_id", "/subscriptions/" + SUB_B + "/x"),
            (2, "resource_ownership_status", "VERIFIED"),
            (2, "cloud_access_verified", True),
            (3, "capacity_origin", "create-new"),
            (3, "fabric_tenant_id", B),
            (3, "reused_fabric_uuid", A),
            (3, "created_fabric_uuid", CAP),
            (3, "capacity_id_verified", True),
            (3, "paid_approval_verified", True),
        ]:
            with self.subTest(field=field):
                f = list(fixtures())
                f[position][field] = value
                self.rejected(f)

    def test_reject_secret_unknown_fields_or_role_collision(self):
        for pos, field in ((1, "client_secret"), (2, "sas_token"),
                           (3, "access_token"), (0, "password")):
            f = list(fixtures())
            f[pos][field] = "DO_NOT_ECHO_SECRET"
            self.rejected(f)
        f = list(fixtures())
        f[1]["blob_reader"]["client_id"] = f[1]["backend_operator"]["client_id"]
        self.rejected(f)
        f = list(fixtures(cross=True))
        f[1]["fabric_deployer"]["tenant_id"] = A
        self.rejected(f)

    def test_reject_forged_scope_and_capacity_subscription(self):
        f = list(fixtures(fresh=True))
        f[2]["backend_operator_scope"] = (
            f"/subscriptions/{SUB}/resourceGroups/rg-hdp-lab-b/"
            "providers/Microsoft.Storage/storageAccounts/johnzhang/"
            "blobServices/default/containers/tfstate"
        )
        self.rejected(f)
        f = list(fixtures(cross=True, fresh=True, paid=True))
        f[3]["capacity_subscription_id"] = SUB
        self.rejected(f)
        f = list(fixtures())
        f[3]["created_azure_arm_id"] = "/subscriptions/fake"
        self.rejected(f)

    def test_cli_does_not_echo_secret_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            files = [Path(temp) / name for name in ("profile", "clients", "storage", "capacity")]
            f = list(fixtures())
            f[3]["access_token"] = "DONT_ECHO_SECRET_VALUE"
            for file, obj in zip(files, f):
                file.write_text(json.dumps(obj), encoding="utf-8")
            buffer = StringIO()
            with redirect_stdout(buffer):
                status = main([
                    "--profile", str(files[0]), "--resolved-clients", str(files[1]),
                    "--storage-target", str(files[2]), "--capacity-target", str(files[3]),
                ])
            self.assertEqual(status, 2)
            self.assertNotIn("DONT_ECHO_SECRET_VALUE", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
