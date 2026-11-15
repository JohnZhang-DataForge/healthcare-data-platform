"""Static regression for code-owned semantic API migration.

Frozen signed-wire contract values are tracked separately in the rename map;
no claim is made that historic external signers have been migrated.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "shared-data-engine/src/healthcare_data_engine"
NOTEBOOK = (ROOT / "azure-fabric/workspaces/healthcare-omop/"
            "nb_fhir_ingest.Notebook/notebook-content.py")
RENAME_MAP = ROOT / "docs/development/shared-notebook-semantic-rename-map.tsv"


class SemanticIdentifiersTests(unittest.TestCase):
    def test_shared_code_owns_no_stage_numbered_g5_p3_error_or_identity_api(self):
        stage_status = re.compile(r"(?:G5_|P3_|IDENTITY_F2_)")
        old_api = re.compile(
            r"^\s*(?:def|class)\s+\w*(?:g5|p3|f1_lookup|bridge_f2)\w*\s*\(",
            re.MULTILINE | re.IGNORECASE,
        )
        for path in sorted(PACKAGE.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIsNone(stage_status.search(text))
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
