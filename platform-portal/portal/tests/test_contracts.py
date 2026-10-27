"""Offline contract and fixture tests. Never contact cloud or shared runtime."""
import copy
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts"
FIXTURES = ROOT / "fixtures"
CASES = {
    "snapshot-v1": "snapshot.mock.json",
    "trigger-request-v1": "trigger-request.mock.json",
    "trigger-response-v1": "trigger-response.mock.json",
    "run-status-v1": "run-status.mock.json",
    "api-error-v1": "api-error.mock.json",
}

def load(name, folder):
    return json.loads((folder / name).read_text(encoding="utf-8"))

def validate(contract, payload):
    schema = load(contract + ".schema.json", SCHEMAS)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)

class PortalContractsTest(unittest.TestCase):
    def test_all_examples_match_versioned_schemas(self):
        for contract, filename in CASES.items():
            with self.subTest(contract=contract):
                validate(contract, load(filename, FIXTURES))

    def test_mock_lineage_graph_has_no_dangling_refs(self):
        snap = load("snapshot.mock.json", FIXTURES)
        nodes = {d["dataset_ref"]: d for d in snap["datasets"]}
        runs = {r["run_ref"] for r in snap["runs"]}
        self.assertEqual(len(nodes), len(snap["datasets"]))
        self.assertEqual(len(runs), len(snap["runs"]))
        self.assertEqual(len(snap["hospitals"]), snap["summary"]["hospital_count"])
        for kind in ("table_edges", "column_edges"):
            for edge in snap["lineage"][kind]:
                self.assertIn(edge["source_dataset_ref"], nodes)
                self.assertIn(edge["target_dataset_ref"], nodes)
                self.assertIn(edge["run_ref"], runs)
                if kind == "column_edges":
                    self.assertIn(edge["source_column"], nodes[edge["source_dataset_ref"]]["columns"])
                    self.assertIn(edge["target_column"], nodes[edge["target_dataset_ref"]]["columns"])

    def test_mock_cannot_claim_verified_export(self):
        snap = load("snapshot.mock.json", FIXTURES)
        snap["data_origin"] = "VERIFIED_EXPORT"
        with self.assertRaises(ValidationError):
            validate("snapshot-v1", snap)

    def test_trigger_rejects_arbitrary_execution_parameters(self):
        req = load("trigger-request.mock.json", FIXTURES)
        req["workflow"] = "arbitrary-shell"
        with self.assertRaises(ValidationError):
            validate("trigger-request-v1", req)

    def test_complete_status_requires_published_snapshot(self):
        status = load("run-status.mock.json", FIXTURES)
        status["phase"] = "COMPLETE"
        with self.assertRaises(ValidationError):
            validate("run-status-v1", status)

    def test_snapshot_rejects_private_runtime_fields(self):
        snap = load("snapshot.mock.json", FIXTURES)
        snap["marquez_private_api"] = "http://internal:5000/api/v1"
        with self.assertRaises(ValidationError):
            validate("snapshot-v1", snap)

    def test_error_contract_rejects_unexpected_internal_details(self):
        err = load("api-error.mock.json", FIXTURES)
        err["stack_trace"] = "hidden implementation"
        with self.assertRaises(ValidationError):
            validate("api-error-v1", err)

    def test_public_mock_has_no_identifying_payload(self):
        snap = load("snapshot.mock.json", FIXTURES)
        serialized = json.dumps(snap).lower()
        for disallowed in ("patient_name", "first_name", "last_name", "social_security", "birth_address", "password", "client_secret", "access_token", "s3://", "abfss://", "10.0."):
            with self.subTest(disallowed=disallowed):
                self.assertNotIn(disallowed, serialized)
        self.assertEqual(snap["data_origin"], "MOCK")
        self.assertIn("MOCK ONLY", snap["mock_notice"])

if __name__ == "__main__":
    unittest.main()
