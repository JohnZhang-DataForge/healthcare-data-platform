"""Offline regression: G5 technical admission must not require two human signatures.

Historical v1 replay may retain its exact versioned schema. This test makes
no Fabric calls and grants no Candidate/Gold release.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
PROVIDER = ROOT / "shared-data-engine/src/healthcare_data_engine/security/provider_attestation.py"
NOTEBOOK = ROOT / "azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py"
HUMAN = {"clinical_review_sha256", "license_review_sha256",
         "clinically_reviewed", "license_reviewed"}


class G5NoHumanQuorumRegression(unittest.TestCase):
    def test_v3_technical_contract_excludes_human_review_fields(self):
        source = PROVIDER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        values[target.id] = node.value
        self.assertIn("DYNAMIC_TECHNICAL_SCHEMA", values)
        self.assertIn("TECHNICAL_PAYLOAD_FIELDS", values)
        technical = ast.get_source_segment(source, values["TECHNICAL_PAYLOAD_FIELDS"])
        self.assertIn("clinical_review_sha256", technical)
        self.assertIn("license_review_sha256", technical)
        self.assertIn("-", technical, "Technical schema must subtract legacy fields")
        self.assertIn("technical_evidence_sha256", technical)

    def test_candidate_technical_branch_does_not_require_human_quorum(self):
        source = NOTEBOOK.read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        writer = functions["plan_and_write_g5_candidate_delta"]
        text = ast.get_source_segment(source, writer)
        self.assertIn("technical_evidence_sha256 is not None", text)
        self.assertIn("trusted_technical_release_gate", text)
        self.assertIn("HOLD_G5_TECHNICAL_STAGE_RELEASE_UNTRUSTED", text)
        self.assertIn("HOLD_G5_LEGACY_SIGNED_RELEASE_INCOMPLETE", text)
        self.assertIn("elif not (clinically_reviewed and license_reviewed)", text)
        # Structural check: the legacy quorum is *only* the else branch
        # of the technical gate; substring checks falsely match "elif".
        legacy_condition = "not (clinically_reviewed and license_reviewed)"
        legacy_if_nodes = [
            n for n in ast.walk(writer)
            if isinstance(n, ast.If)
            and ast.get_source_segment(source, n.test) == legacy_condition
        ]
        self.assertEqual(len(legacy_if_nodes), 1)
        legacy_if = legacy_if_nodes[0]
        parents = [
            n for n in ast.walk(writer)
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.Name) and n.test.id == "technical"
            and n.orelse == [legacy_if]
        ]
        self.assertEqual(len(parents), 1, "Legacy quorum must be technical-only else")
        self.assertIn("trusted_technical_release_gate",
                      ast.get_source_segment(source, parents[0].body[0]))
        self.assertIn("HOLD_G5_TECHNICAL_EVIDENCE_CANNOT_FORGE_REVIEWS", text)

    def test_v3_transport_is_source_only_not_writer_authorization(self):
        source = PROVIDER.read_text(encoding="utf-8")
        self.assertIn("G5_DYNAMIC_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE", source)
        self.assertIn("G5_TRANSPORT_NATIVE_TRUST_OR_LEDGER_NOT_ONBOARDED", source)


if __name__ == "__main__":
    unittest.main()
