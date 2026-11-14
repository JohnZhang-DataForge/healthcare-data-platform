"""Positive/negative tests for semantic, project-phase-free source naming."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "scripts" / "check_semantic_naming.py"
spec = importlib.util.spec_from_file_location("semantic_naming", FILE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class SemanticNamingTests(unittest.TestCase):
    def test_reject_new_phase_named_source_paths(self):
        for path in (
            "azure-fabric/warehouse/g5_candidate.py",
            ".github/workflows/fabric-g5-stage.yml",
            "shared-data-engine/src/healthcare_data_engine/f2_identity.py",
            "local-data-platform/spark/p2_writer.py",
            ".github/quality/tests/fabric/test_g4_silver.py",
            "src/ci/fabric_blob_b4_release.py",
            "scripts/ci/task005-prepare.sh",
        ):
            with self.subTest(path=path):
                self.assertTrue(guard.path_violation(path))

    def test_reject_new_phase_declarations_in_existing_file(self):
        path = "azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py"
        for line in (
            "def _g5_candidate_paths(scope):",
            "class G5CandidateWriter:",
            "_G5_APPROVED_REQUEST = 'x'",
            "f2_identity_snapshot_fingerprint: str",
            "STATUS = 'G5_RELEASE_APPROVED'",
            "SCHEMA = 'fabric-g5-technical-transport-v4'",
            "raise RuntimeError('HOLD_G5_CANDIDATE_MISMATCH')",
        ):
            with self.subTest(line=line):
                self.assertTrue(guard.line_violations(path, line))

    def test_reject_yaml_semantic_name_with_project_stage(self):
        path = ".github/workflows/omop-publication.yml"
        self.assertTrue(guard.line_violations(path, "name: G5 Candidate Publish"))
        self.assertTrue(guard.line_violations(path, "  job_name: fabric-p2-controller"))

    def test_reject_new_but_preserve_old_references(self):
        path = "shared-data-engine/src/healthcare_data_engine/identity/handoff.py"
        self.assertEqual(guard.evaluate([], {path: [
            'if source.status == "G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED":',
            '    return legacy_f2_scope',
        ]}), [])
        self.assertTrue(guard.evaluate([], {path: ["def verify_f2_identity():"]}))

    def test_accept_real_standards_versions_and_component_names(self):
        for name in (
            "shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/bundle.py",
            "azure-fabric/warehouse/omop-cdm-5.4/warehouse_schema.py",
            "local-data-platform/spark/apps/hl7_v2/reader.py",
            ".github/workflows/technical-admission.yml",
            "src/ci/omop_p100_batch_readonly.py",
        ):
            self.assertFalse(guard.path_violation(name))
        path = "shared-data-engine/src/healthcare_data_engine/schema.py"
        self.assertEqual(guard.evaluate([], {path: [
            "def plan_candidate_publication(scope):",
            'SCHEMA = "omop-technical-admission-v1"',
            'STATUS = "TECHNICAL_ADMISSION_HOLD"',
            'FHIR_VERSION = "R4"',
            'HL7_VERSION = "v2"',
        ]}), [])

    def test_reject_suffixed_public_schema_constant(self):
        path = "shared-data-engine/src/healthcare_data_engine/security/provider.py"
        self.assertTrue(guard.line_violations(
            path, 'DYNAMIC_TECHNICAL_SCHEMA = "fabric-g5-technical-evidence-transport-v3"'))
        self.assertTrue(guard.line_violations(
            path, 'ADMISSION_STATUS = "G5_STAGE_SOURCE_ONLY"'))

    def test_multilanguage_and_embedded_camelcase_identifiers(self):
        cases = (
            ("platform-portal/portal/web/controller.ts", "export const G5Candidate = 1;"),
            ("platform-portal/portal/web/controller.ts", "function verifyP2Stage() {}"),
            ("local-data-platform/sql/omop/schema.sql", "CREATE TABLE etl.g5_candidate (id int);"),
            ("local-data-platform/scripts/omop/release.sh", "export FABRIC_B4_RELEASE=1"),
            ("azure-fabric/deployment/contract.json", '  "schema_version": "fabric-g5-transport-v3",'),
            ("shared-data-engine/src/healthcare_data_engine/mapping/omop/candidates.py",
             'return {"status": "G5_NEW_RELEASE_UNVERIFIED"}'),
        )
        for path, line in cases:
            with self.subTest(path=path, line=line):
                self.assertTrue(guard.line_violations(path, line))

    def test_python_ast_rejects_new_functions_classes_and_ambiguous_names(self):
        path = "shared-data-engine/src/healthcare_data_engine/identity/preview.py"
        old = "\n".join([
            "def old_g5_preview():",
            "    return None",
        ])
        new = "\n".join([
            "def old_g5_preview():",
            "    return None",
            "class CandidateG5Publisher:",
            "    async def process_f2_rows(self):",
            "        return None",
            "    def do_stuff(self):",
            "        return None",
            "def process_data2():",
            "    return None",
            "def validate_candidate_batch():",
            "    return None",
        ])
        errors = guard.python_ast_violations(path, old, new)
        self.assertTrue(any("CandidateG5Publisher" in x for x in errors))
        self.assertTrue(any("process_f2_rows" in x for x in errors))
        self.assertTrue(any("do_stuff" in x for x in errors))
        self.assertTrue(any("process_data2" in x for x in errors))
        self.assertFalse(any("old_g5_preview" in x for x in errors))
        self.assertFalse(any("validate_candidate_batch" in x for x in errors))

    def test_python_ast_catches_multiline_public_contract_and_dict(self):
        path = "shared-data-engine/src/healthcare_data_engine/security/evidence.py"
        old = "\n".join(['SCHEMA = "technical-admission-v1"', "data = {}"])
        new = "\n".join([
            "SCHEMA = (",
            '    "fabric-g5-"',
            '    "evidence-v3"',
            ")",
            "data = {",
            '    "status": (',
            '        "G5_CANDIDATE_RELEASED"',
            "    ),",
            "}",
        ])
        errors = guard.python_ast_violations(path, old, new)
        self.assertTrue(any("public-contract:SCHEMA" in x for x in errors))
        self.assertTrue(any("public-dict:status" in x for x in errors))

    def test_python_ast_retains_unchanged_legacy_contracts(self):
        path = "shared-data-engine/src/healthcare_data_engine/security/evidence.py"
        old = "\n".join([
            "def f1_lookup():",
            "    return None",
            'SCHEMA = "fabric-g5-transport-v3"',
            'state = {"status": "G5_CANDIDATE_PENDING"}',
        ])
        new = old + "\n" + "\n".join([
            "def validate_identity_snapshot():",
            "    return True",
            'VERSION = "FHIR_R4"',
        ])
        self.assertEqual(guard.python_ast_violations(path, old, new), [])

    def test_python_ast_fail_closed_on_invalid_source(self):
        path = "shared-data-engine/src/healthcare_data_engine/security/evidence.py"
        self.assertTrue(guard.python_ast_violations(path, "", "def invalid(:"))
        self.assertEqual(
            guard.python_ast_violations("documents/naming-example.py", "",
                                        "def g5_bad(:"),
            [],
        )

    def test_legacy_paths_unchanged_are_not_blocked(self):
        self.assertEqual(guard.evaluate([], {}), [])
        self.assertEqual(guard.evaluate(
            [], {"documents/engineering/development/README.md": [
                "The old g5 stage was a planning label."
            ]}
        ), [])


if __name__ == "__main__":
    unittest.main()
