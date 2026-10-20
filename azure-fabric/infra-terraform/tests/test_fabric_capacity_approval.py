"""Paid Capacity evidence fail-closed tests; no cloud or Terraform involved."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_bootstrap_profile import InvalidBootstrapProfile
from fabric_capacity_approval import check_capacity_evidence

A = "899a04e8-8d3d-486c-88a1-7bdeb22d5f1a"
B = "cb50fc2d-f9be-449a-9ae7-276884d0de55"
SUB = "6c0cc7f1-6912-4b25-805f-732be3882da8"
CAP = "18da26c5-dc71-43d2-b6fa-1ed15e24e7cb"


def profile(create=True):
    return {
        "schema_version": 1, "environment": "lab-b",
        "bootstrap_mode": "fresh-bootstrap",
        "tenants": {"backend_tenant_id": A, "fabric_tenant_id": B},
        "github_oidc": {"repository": "JohnZhang-DataForge/Self-Runner",
                        "ref": "refs/heads/main"},
        "storage": {"account": "hdplabbstorage", "subscription_id": SUB,
                    "resource_group": "rg-hdp-lab-b", "landing_container": "landing",
                    "state_container": "tfstate", "state_prefix": "fabric/lab-b"},
        "bootstrap_state": {"strategy": "isolated-local",
                            "custody_reference": "CUSTODY-OFFLINE-PLAN-01"},
        "capacity": ({
            "mode": "create-new", "sku": "F2", "region": "eastus2",
            "subscription_id": SUB, "estimated_monthly_usd": 300,
            "monthly_budget_usd": 500, "billing_owner": "owner",
            "cost_review_reference": "COST-REVIEW-20261019",
        } if create else {"mode": "reuse-existing", "capacity_id": CAP}),
    }


def evidence():
    return {
        "schema_version": 1,
        "request": {"environment": "lab-b", "fabric_tenant_id": B,
                    "subscription_id": SUB, "sku": "F2", "region": "eastus2",
                    "estimated_monthly_usd": 300, "monthly_budget_usd": 500,
                    "source_sha": "a" * 40},
        "review": {"reference": "COST-REVIEW-20261019", "reviewer": "independent-reviewer",
                   "approved_on_utc": "2026-10-19T12:00:00Z",
                   "expires_on_utc": "2026-10-20T12:00:00Z",
                   "record_uri": "https://billing.invalid.local/reviews/2026/10/19"},
    }


class CostEvidenceTests(unittest.TestCase):
    def reject(self, p, e):
        with self.assertRaises(InvalidBootstrapProfile):
            check_capacity_evidence(p, e)

    def test_default_reuse_is_reference_only(self):
        out = check_capacity_evidence(profile(False))
        self.assertEqual(out["capacity_id"], CAP)
        self.assertFalse(out["paid_creation_authorized"])
        self.assertFalse(out["verified"])

    def test_absent_evidence_holds(self):
        out = check_capacity_evidence(profile())
        self.assertEqual(out["status"], "HOLD_PAID_CAPACITY_EXTERNAL_APPROVAL")
        self.assertFalse(out["cost_evidence_shape_valid"])
        self.assertFalse(out["paid_creation_authorized"])

    def test_complete_claim_is_still_hold_not_approval(self):
        result = check_capacity_evidence(profile(), evidence())
        self.assertTrue(result["cost_evidence_shape_valid"])
        self.assertFalse(result["cost_review_verified"])
        self.assertFalse(result["paid_creation_authorized"])
        self.assertFalse(result["terraform_executed"])
        self.assertEqual(result, check_capacity_evidence(profile(), deepcopy(evidence())))

    def test_reuse_with_paid_approval_is_disallowed(self):
        self.reject(profile(False), evidence())

    def test_wrong_environment_tenant_subscription_sku_cost_and_sha(self):
        for field, invalid in (
            ("environment", "dev"),
            ("fabric_tenant_id", A),
            ("subscription_id", A),
            ("sku", "F64"),
            ("region", "westus"),
            ("estimated_monthly_usd", 200),
            ("monthly_budget_usd", 600),
            ("source_sha", "short"),
        ):
            with self.subTest(field=field):
                e = evidence()
                e["request"][field] = invalid
                self.reject(profile(), e)

    def test_untrusted_review_and_missing_fields_rejected(self):
        for field, value in (
            ("reference", "COST-REVIEW-OTHER"),
            ("reviewer", "owner"),
            ("reviewer", ""),
            ("approved_on_utc", "tomorrow"),
            ("expires_on_utc", "2026-10-18T12:00:00Z"),
            ("record_uri", "http://bad.com/x"),
            ("record_uri", "https://example.com/review"),
        ):
            with self.subTest(field=field):
                e = evidence()
                e["review"][field] = value
                self.reject(profile(), e)
        for target, field in (("request", "secret"), ("review", "token")):
            e = evidence()
            e[target][field] = "never-put-me-in-state"
            self.reject(profile(), e)
        e = evidence()
        del e["review"]["record_uri"]
        self.reject(profile(), e)


if __name__ == "__main__":
    unittest.main()
