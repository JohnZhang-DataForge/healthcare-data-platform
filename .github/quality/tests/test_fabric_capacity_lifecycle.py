"""No-cloud contract tests for Trial-readonly and paid Capacity lifecycle OIDC controller."""
import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/capacity-api"
spec = importlib.util.spec_from_file_location("capacity_lifecycle", API / "capacity_lifecycle.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TRIAL_ID = "3914ac8b-3375-498b-b3c0-1180a1902dd6"
SUB = "56107520-5920-4e96-9833-5441ded0a90c"
PAID_ID = f"/subscriptions/{SUB}/resourceGroups/test/providers/Microsoft.Fabric/capacities/fabricdev"
CONFIG = json.loads((API / "capacity.json").read_text())


class CapacityLifecycleTests(unittest.TestCase):
    def test_trial_readonly_success_and_no_post(self):
        requests = []
        def http(url, method="GET", **kwargs):
            requests.append((url, method))
            return 200, {"id": TRIAL_ID, "sku": "F4", "state": "Active"}, {}
        result = module.execute("trial", "inspect", CONFIG,
                                env={"FABRIC_TENANT_ID": TRIAL_ID, "FABRIC_CLIENT_ID": TRIAL_ID},
                                request=http, token_provider=lambda *a: "mock")
        self.assertEqual(result["outcome"], "OBSERVED")
        self.assertEqual(requests, [(f"https://api.fabric.microsoft.com/v1/capacities/{TRIAL_ID}", "GET")])

    def test_trial_suspend_resume_refused_before_auth(self):
        for operation in ("suspend", "resume"):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(module.CapacityError, "never supports"):
                    module.execute("trial", operation, CONFIG, token_provider=lambda *a: self.fail("auth called"))

    def test_paid_subscription_and_arm_path_fail_closed(self):
        for arm_id in ("", TRIAL_ID, "https://management.azure.com/"+PAID_ID,
                       "/subscriptions/"+SUB+"/resourceGroups/test/providers/Microsoft.Fabric/capacities/fabricdev/suspend"):
            with self.subTest(arm_id=arm_id):
                with self.assertRaises(module.CapacityError):
                    module.target("paid", {}, arm_id, SUB)
        with self.assertRaisesRegex(module.CapacityError, "subscription"):
            module.target("paid", {}, PAID_ID, TRIAL_ID)

    def test_paid_mutation_requires_explicit_flag_and_confirmation(self):
        for env in ({}, {"ENABLE_PAID_CAPACITY_OPERATIONS": "true"},
                    {"ENABLE_PAID_CAPACITY_OPERATIONS": "true", "CAPACITY_ACTION_CONFIRM": "RESUME"}):
            with self.subTest(env=env):
                with self.assertRaises(module.CapacityError):
                    module.execute("paid", "suspend", {}, paid_arm_id=PAID_ID,
                                   subscription_id=SUB, env=env,
                                   token_provider=lambda *a: self.fail("auth called"))

    def test_paid_state_readback_and_suspension(self):
        calls = []
        states = iter(["Active", "Suspending", "Suspended"])
        def req(url, method="GET", **kwargs):
            calls.append((method, url))
            if method == "POST":
                return 202, {}, {}
            state = next(states)
            return 200, {"id": PAID_ID, "type": "Microsoft.Fabric/capacities",
                         "sku": {"name": "F2"}, "properties": {"state": state}}, {}
        env = {"ENABLE_PAID_CAPACITY_OPERATIONS": "true", "CAPACITY_ACTION_CONFIRM": "SUSPEND",
               "ARM_TENANT_ID": TRIAL_ID, "ARM_CLIENT_ID": TRIAL_ID}
        result = module.execute("paid", "suspend", {}, paid_arm_id=PAID_ID, subscription_id=SUB,
                                env=env, request=req, token_provider=lambda *a: "mock", sleep=lambda _: None)
        self.assertEqual(result["outcome"], "CONFIRMED")
        self.assertEqual(sum(m == "POST" for m, _ in calls), 1)
        self.assertTrue(calls[1][1].endswith("/suspend?api-version=2023-11-01"))

    def test_paid_resume_and_noop(self):
        for operation, first_state, last_state in (("resume", "Suspended", "Active"),
                                                    ("suspend", "Suspended", "Suspended")):
            with self.subTest(operation=operation):
                states = [first_state, last_state]
                calls = []
                def req(url, method="GET", **kwargs):
                    calls.append(method)
                    if method == "POST":
                        return 200, {}, {}
                    return 200, {"id": PAID_ID, "type": "Microsoft.Fabric/capacities",
                                 "sku": {"name": "F4"}, "properties": {"state": states.pop(0)}}, {}
                env = {"ENABLE_PAID_CAPACITY_OPERATIONS": "true",
                       "CAPACITY_ACTION_CONFIRM": operation.upper(), "ARM_TENANT_ID": TRIAL_ID,
                       "ARM_CLIENT_ID": TRIAL_ID}
                result = module.execute("paid", operation, {}, paid_arm_id=PAID_ID,
                                        subscription_id=SUB, env=env, request=req,
                                        token_provider=lambda *a: "mock", sleep=lambda _: None)
                self.assertEqual(result["outcome"], "CONFIRMED" if operation == "resume" else "ALREADY_AT_TARGET")
                self.assertEqual(calls.count("POST"), 1 if operation == "resume" else 0)

    def test_wrong_resource_type_and_trial_uuid_never_treated_as_paid(self):
        with self.assertRaisesRegex(module.CapacityError, "not Microsoft.Fabric"):
            module.summarize("paid", PAID_ID, {"id": PAID_ID, "type": "Microsoft.Storage/storageAccounts",
                                               "sku": {"name": "F4"}, "properties": {"state": "Active"}})
        with self.assertRaisesRegex(module.CapacityError, "not a supported paid"):
            module.summarize("paid", PAID_ID, {"id": PAID_ID, "type": "Microsoft.Fabric/capacities",
                                               "sku": {"name": "A1"}, "properties": {"state": "Active"}})
        with self.assertRaisesRegex(module.CapacityError, "mismatch"):
            module.summarize("trial", TRIAL_ID, {"id": SUB, "state": "Active"})

    def test_no_workspace_mutation_api_in_source(self):
        s = (API / "capacity_lifecycle.py").read_text()
        self.assertNotIn("/v1/workspaces", s)
        self.assertNotIn("assignToCapacity", s)
        self.assertNotIn("terraform", s)
        self.assertNotIn("client_secret", s)
        self.assertIn("/oauth2/v2.0/token", s)


if __name__ == "__main__":
    unittest.main()
