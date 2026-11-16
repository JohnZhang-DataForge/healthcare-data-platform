"""Static regression for code-owned semantic API migration.

Frozen signed-wire contract values are tracked separately in the rename map;
no claim is made that historic external signers have been migrated.
"""
from __future__ import annotations

from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[5]
PACKAGE = ROOT / "shared-data-engine/src/healthcare_data_engine"
NOTEBOOK = (ROOT / "azure-fabric/workspaces/healthcare-omop/"
            "nb_fhir_ingest.Notebook/notebook-content.py")
RENAME_MAP = ROOT / "documents/systems/data-platform/shared-engine/semantic-rename-map.tsv"


class SemanticIdentifiersTests(unittest.TestCase):
    @staticmethod
    def _phase_symbol_pattern():
        # Single backslash: Python regex digit class, not a literal '\\d'.
        # Match both snake_case stage tokens and embedded CamelCase stage names.
        return re.compile(
            r"(?:^|_)(?:g[1-9]\d?|f[1-9]\d?|p[1-9]\d?)(?=_|$)"
            r"|[GgFfPp][1-9]\d?(?=[A-Z])",
            re.IGNORECASE,
        )

    def test_phase_identifier_pattern_has_independent_negative_and_positive_controls(self):
        phase = self._phase_symbol_pattern()
        # A working gate must catch regressions before scanning real sources.
        for bad in (
            "execute_g5_person_visit_business",
            "verify_fhir_g3_bronze",
            "bridge_f2_person_visit_allocation",
            "f1_lookup",
            "_P3_CANDIDATE_RELEASE",
            "CandidateG5Publisher",
            "processP2Scope",
        ):
            with self.subTest(should_block=bad):
                self.assertIsNotNone(phase.search(bad))
        for allowed in (
            "execute_person_visit_candidate_publication",
            "identity_snapshot_fingerprint",
            "vocabulary_release_metadata_sha256",
            "fhir_r4_adapter",
            "hl7_v2_parser",
            "s3_bucket",
            "request_id",
        ):
            with self.subTest(should_allow=allowed):
                self.assertIsNone(phase.search(allowed))

    def test_shared_code_owns_no_stage_numbered_candidate_api(self):
        stage_token_pattern = re.compile(r"(?:G5_|P3_|IDENTITY_F2_)")
        old_api = re.compile(
            r"^\s*(?:def|class)\s+\w*(?:g5|p3|f1_lookup|bridge_f2)\w*\s*\(",
            re.MULTILINE | re.IGNORECASE,
        )
        for path in sorted(PACKAGE.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIsNone(stage_token_pattern.search(text))
                self.assertIsNone(old_api.search(text))

    def test_notebook_candidate_functions_are_canonical_without_alias(self):
        text = NOTEBOOK.read_text(encoding="utf-8")
        for name in (
            "verify_fhir_dynamic_silver_source_readonly",
            "plan_and_write_omop_candidate_delta",
            "verify_candidate_transport_source_only",
            "execute_person_visit_candidate_publication",
            "verify_fhir_candidate_source_readonly",
            "verify_fhir_concept_source_inventory_readonly",
        ):
            self.assertIn("def " + name + "(", text)
        for old in (
            "verify_fhir_g5_dynamic_silver_source_readonly",
            "plan_and_write_g5_candidate_delta",
            "execute_g5_candidate_from_trusted_controller",
            "execute_g5_person_visit_business",
            "verify_fhir_g5_candidate_source_readonly",
            "verify_fhir_g5_concept_source_inventory_readonly",
        ):
            self.assertNotIn(old, text)
        self.assertNotIn("HOLD_G5_", text)
        self.assertNotIn("_G5_APPROVED_", text)

    def test_all_shared_and_fhir_notebook_business_symbols_are_stage_free(self):
        """Inspect actual Python symbols, not PR diff or comment-only matches."""
        phase = self._phase_symbol_pattern()
        # No production Python symbol exemptions: frozen legacy names are
        # JSON payload keys only, not classes, function parameters or attributes.
        for path in (*sorted(PACKAGE.rglob("*.py")), NOTEBOOK):
            source = path.read_text(encoding="utf-8")
            syntax = ast.parse(source, filename=str(path))
            found = []
            for node in ast.walk(syntax):
                symbol = None
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbol = node.name
                elif isinstance(node, (ast.Name, ast.Attribute)):
                    symbol = node.id if isinstance(node, ast.Name) else node.attr
                elif isinstance(node, ast.arg):
                    symbol = node.arg
                elif isinstance(node, ast.keyword):
                    symbol = node.arg
                if symbol and phase.search(symbol):
                    found.append((getattr(node, "lineno", None), symbol))
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(found, [])
            if path == NOTEBOOK:
                for prefix in ("HOLD_G3_", "HOLD_G4_", "HOLD_G5_",
                               "HOLD_P1_", "HOLD_P2_", "FHIR_G3_", "FHIR_G4_"):
                    self.assertNotIn(prefix, source)
        # One canonical callable per source boundary: no legacy G3/G4 alias.
        notebook = NOTEBOOK.read_text(encoding="utf-8")
        for fn in ("process_fhir_bronze_snapshot",
                   "process_fhir_silver_publication",
                   "verify_fhir_bronze_negative_readonly",
                   "verify_fhir_silver_dq_negative"):
            self.assertEqual(notebook.count("def " + fn + "("), 1)
        for old in ("verify_fhir_" + "g3_bronze",
                    "verify_fhir_" + "g4_silver",
                    "verify_fhir_" + "g4_dq_negative",
                    "verify_fhir_" + "g3_negative_readonly"):
            self.assertNotIn(old, notebook)

    def test_rename_map_has_unique_old_keys_and_declares_wire_exceptions(self):
        lines = RENAME_MAP.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "kind\told_name\tnew_name\torigin\tstatus")
        rows = [line.split("\t") for line in lines[1:] if line]
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertEqual(len({r[1] for r in rows}), len(rows))
        self.assertTrue(any(r[4] == "DEFERRED_SIGNATURE_PROTOCOL" for r in rows))
        self.assertTrue(any(r[1] == "bridge_f2_person_visit_allocation" for r in rows))


if __name__ == "__main__":
    unittest.main()
