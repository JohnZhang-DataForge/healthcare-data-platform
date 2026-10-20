"""Offline Bootstrap → Self-Runner intake integration and safety matrix."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_execution_readiness import readiness, main
from fabric_bootstrap_profile import InvalidBootstrapProfile
from test_fabric_bootstrap_handoff import fixtures

SHA = "a" * 40
CTRL = "b" * 40


def intake(phase="bootstrap", root="identity"):
    return {
        "status": "FABRIC_CONTROLLED_ENTRY_OFFLINE_INTAKE_HOLD",
        "phase": phase, "root": root, "environment": "lab-b",
        "controller_commit": CTRL,
        "requested_healthcare_commit": SHA,
        "plan_digest_format_checked": phase == "apply",
        "source_sha_live_verified": False,
        "reviewed_plan_artifact_verified": False,
        "protected_environments_verified": False,
        "separate_authorization_verified": False,
        "capacity_billing_authorized": False,
        "remote_state_checked": False,
        "cloud_access_attempted": False,
        "terraform_executed": False,
        "self_runner_used": False,
        "deployment_allowed": False,
    }


class FabricReadinessTests(unittest.TestCase):
    def build(self, *, cross=False, fresh=False, paid=False,
              phase="bootstrap", root="identity"):
        return (*fixtures(cross=cross, fresh=fresh, paid=paid),
                intake(phase, root))

    def reject(self, obj):
        with self.assertRaises((InvalidBootstrapProfile, ValueError)):
            readiness(*obj, expected_healthcare_sha=SHA)

    def test_three_phases_default_holds_and_exact_state_keys(self):
        for phase, root in (("bootstrap", "identity"), ("plan", "workspace"),
                            ("apply", "connection")):
            with self.subTest(phase=phase):
                result = readiness(*self.build(phase=phase, root=root),
                                   expected_healthcare_sha=SHA)
                self.assertEqual(result["status"], "FABRIC_OFFLINE_INTEGRATION_HOLD")
                self.assertEqual(result["reviewed_sha_claim"], SHA)
                self.assertEqual(result["expected_state_keys"]["connection"],
                                 "fabric/lab-b/connection.tfstate")
                self.assertGreaterEqual(len(result["blocking_reasons"]), 8)
                self.assertEqual(result, readiness(*self.build(phase=phase, root=root),
                                                    expected_healthcare_sha=SHA))
                for key in ("source_commit_retrieved_from_github",
                            "signed_plan_verified", "billing_authorization_verified",
                            "cloud_access_attempted", "remote_state_checked",
                            "runner_invoked", "terraform_executed", "deployment_allowed"):
                    self.assertIs(result[key], False)
                if phase == "apply":
                    self.assertIn("REVIEWED_BINARY_PLAN_AND_SAVED_DIGEST_NOT_VERIFIED",
                                  result["blocking_reasons"])

    def test_cross_tenant_fresh_never_promoted_to_deployable(self):
        result = readiness(*self.build(cross=True, fresh=True,
                                       phase="plan", root="onelake"),
                           expected_healthcare_sha=SHA)
        self.assertEqual(result["identity_topology"], "cross-tenant")
        self.assertEqual(result["handoff_status"],
                         "STATIC_HANDOFF_HOLD_FRESH_EXTERNAL_APPROVALS")
        self.assertIn("FRESH_PRIVATE_NETWORK_DNS_AND_STATE_CUSTODY_NOT_VERIFIED",
                      result["blocking_reasons"])
        self.assertFalse(result["deployment_allowed"])

    def test_paid_capacity_never_grants_billing_or_uses_arm_uuid(self):
        result = readiness(*self.build(cross=True, fresh=True, paid=True,
                                       phase="plan", root="capacity"),
                           expected_healthcare_sha=SHA)
        self.assertEqual(result["handoff_status"],
                         "STATIC_HANDOFF_HOLD_PAID_CAPACITY_UUID")
        self.assertIn("PAID_CAPACITY_BILLING_APPROVAL_AND_FABRIC_UUID_ABSENT",
                      result["blocking_reasons"])
        self.assertFalse(result["billing_authorization_verified"])

    def test_forged_approval_and_secret_fields_fail_closed(self):
        base = self.build()
        for field in (
            "deployment_allowed", "source_sha_live_verified",
            "protected_environments_verified", "capacity_billing_authorized",
            "reviewed_plan_artifact_verified", "terraform_executed",
        ):
            obj = deepcopy(base)
            obj[4][field] = True
            with self.subTest(field=field):
                self.reject(obj)
        for field in ("secrets", "OIDC_TOKEN", "plan_binary", "billing_approval"):
            obj = deepcopy(base)
            obj[4][field] = "SENSITIVE_DO_NOT_LOG"
            with self.subTest(field=field):
                self.reject(obj)

    def test_reject_unbound_environment_root_and_phase(self):
        for field, value in (
            ("environment", "lab-other"), ("phase", "destroy"),
            ("root", "../dev"), ("status", "AUTHORIZED"),
            ("controller_commit", "main"),
            ("requested_healthcare_commit", "c" * 40),
            ("plan_digest_format_checked", True),
        ):
            obj = deepcopy(self.build())
            obj[4][field] = value
            with self.subTest(field=field):
                self.reject(obj)
        obj = deepcopy(self.build())
        obj[4]["root"] = "workspace"
        self.reject(obj)
        obj = deepcopy(self.build(phase="apply", root="workspace"))
        obj[4]["plan_digest_format_checked"] = False
        self.reject(obj)
        with self.assertRaises(InvalidBootstrapProfile):
            readiness(*self.build(), expected_healthcare_sha="b" * 40)

    def test_reject_tampered_bootstrap_and_injected_capacity_source(self):
        obj = deepcopy(self.build(cross=True))
        obj[1]["fabric_deployer"]["tenant_id"] = obj[0]["tenants"]["backend_tenant_id"]
        self.reject(obj)
        obj = deepcopy(self.build(fresh=True))
        obj[2]["storage_account_name"] = "johnzhang"
        self.reject(obj)
        obj = deepcopy(self.build(paid=True))
        obj[3]["created_fabric_uuid"] = "18da26c5-dc71-43d2-b6fa-1ed15e24e7cb"
        self.reject(obj)

    def test_cli_rejects_duplicates_or_secrets_without_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"{n}.json" for n in range(5)]
            vals = list(self.build())
            vals[4]["client_secret"] = "NEVER_ECHO_RAW_TOKEN"
            for p, val in zip(paths, vals):
                p.write_text(json.dumps(val), encoding="utf-8")
            args = []
            for name, p in zip(("profile", "resolved-clients", "storage-target",
                                "capacity-target", "controller-intake"), paths):
                args.extend(("--" + name, str(p)))
            args.extend(("--expected-healthcare-sha", SHA))
            captured = StringIO()
            with redirect_stdout(captured):
                result = main(args)
            self.assertEqual(result, 2)
            self.assertNotIn("NEVER_ECHO_RAW_TOKEN", captured.getvalue())
            vals[4].pop("client_secret")
            paths[-1].write_text('{"phase":"plan","phase":"apply"}', encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(args), 2)


if __name__ == "__main__":
    unittest.main()
