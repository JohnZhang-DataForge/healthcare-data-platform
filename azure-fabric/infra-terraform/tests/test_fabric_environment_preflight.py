"""Pure-stdlib tests for fail-closed Fabric environment selection."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_environment_preflight import InvalidEnvironment, load, validate  # noqa: E402


def good() -> dict:
    return {
        "schema_version": 1,
        "environment": "lab-b",
        "backend": {
            "storage_account": "johnzhang",
            "container": "tfstate",
            "tenant_id": "11111111-1111-4111-8111-111111111111",
            "state_prefix": "fabric/lab-b",
        },
        "landing": {"storage_account": "johnzhang", "container": "landing"},
        "fabric": {
            "tenant_id": "22222222-2222-4222-8222-222222222222",
            "capacity_id": "33333333-3333-4333-8333-333333333333",
            "workspace_name": "HDP-lab-b",
        },
    }


class FabricEnvironmentPreflightTests(unittest.TestCase):
    def test_valid_cross_tenant_and_deterministic_state_keys(self):
        expected = validate(good())
        self.assertEqual(expected["status"], "STATIC_PREFLIGHT_PASS")
        self.assertEqual(expected["state_keys"]["workspace"], "fabric/lab-b/workspace.tfstate")
        self.assertEqual(expected["state_keys"]["onelake"], "fabric/lab-b/onelake.tfstate")
        self.assertEqual(expected["state_keys"]["connection"], "fabric/lab-b/connection.tfstate")
        self.assertFalse(expected["external_access_verified"])
        self.assertFalse(expected["terraform_executed"])
        self.assertEqual(expected, validate(good()))

    def test_same_tenant_is_allowed(self):
        candidate = good()
        candidate["fabric"]["tenant_id"] = candidate["backend"]["tenant_id"]
        self.assertEqual(validate(candidate)["status"], "STATIC_PREFLIGHT_PASS")

    def test_unknown_fields_and_credential_keys_fail_closed(self):
        candidate = good()
        candidate["fabric"]["client_secret"] = "must-never-print-this"
        with self.assertRaisesRegex(InvalidEnvironment, "unexpected fields"):
            validate(candidate)

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
            with self.assertRaisesRegex(InvalidEnvironment, "duplicate JSON key"):
                load(path)

    def test_reject_legacy_state_target(self):
        for unsafe in ("dev", "../dev", "fabric/dev", "fabric/lab-a", "fabric/lab-b/workspace.tfstate"):
            with self.subTest(prefix=unsafe):
                candidate = good()
                candidate["backend"]["state_prefix"] = unsafe
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)

    def test_reject_unsafe_environment_names(self):
        for unsafe in ("dev", "../lab-b", "lab/b", "LAB-B", "lab--b", "", "main"):
            with self.subTest(environment=unsafe):
                candidate = good()
                candidate["environment"] = unsafe
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)

    def test_workspace_name_must_be_isolated(self):
        for old_name in ("healthcare-omop", "HDP-Analytics-Dev", "HDP-lab-a"):
            with self.subTest(name=old_name):
                candidate = good()
                candidate["fabric"]["workspace_name"] = old_name
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)

    def test_uuid_must_be_present_and_nonzero(self):
        for key, invalid in (
            ("tenant_id", "REPLACE_WITH_NEW_TENANT"),
            ("capacity_id", "00000000-0000-0000-0000-000000000000"),
            ("capacity_id", None),
        ):
            with self.subTest(key=key, invalid=invalid):
                candidate = good()
                candidate["fabric"][key] = invalid
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)

    def test_backend_tenant_must_be_valid(self):
        candidate = good()
        candidate["backend"]["tenant_id"] = "wrong"
        with self.assertRaises(InvalidEnvironment):
            validate(candidate)

    def test_fixed_storage_and_landing(self):
        for section, key, bad in (
            ("backend", "storage_account", "unknown"),
            ("backend", "container", "landing"),
            ("landing", "storage_account", "different"),
            ("landing", "container", "tfstate"),
        ):
            with self.subTest(section=section, key=key):
                candidate = good()
                candidate[section][key] = bad
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)

    def test_missing_fields_fail(self):
        candidate = deepcopy(good())
        del candidate["fabric"]["capacity_id"]
        with self.assertRaisesRegex(InvalidEnvironment, "missing fields"):
            validate(candidate)

    def test_schema_version_must_be_integer_one(self):
        for invalid in (True, "1", 2, 0):
            with self.subTest(schema=invalid):
                candidate = good()
                candidate["schema_version"] = invalid
                with self.assertRaises(InvalidEnvironment):
                    validate(candidate)


if __name__ == "__main__":
    unittest.main()
