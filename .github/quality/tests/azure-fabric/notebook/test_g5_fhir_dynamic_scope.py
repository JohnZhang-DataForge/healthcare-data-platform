"""FHIR G5 dynamic v3 StageScope path planning; OFFLINE and SOURCE_ONLY.

This does not dispatch a Spark job, activate Fabric, or authorize Candidate/Gold.
The active published Wheel remains 0.1.7, so its runtime must fail closed.
"""
from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
NOTEBOOK = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "nb_fhir_ingest.Notebook/notebook-content.py")
TRANSPORT = ROOT / (
    "shared-data-engine/src/healthcare_data_engine/"
    "security/provider_attestation.py")


class DynamicG5SourceOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = runpy.run_path(str(NOTEBOOK), run_name="_g5_fhir_dynamic_offline")
        # Load the 0.1.13 SOURCE contract without replacing the installed,
        # independently verified Fabric GA 0.1.7 runtime Wheel.
        name = "_g5_0113_source_transport_test"
        spec = importlib.util.spec_from_file_location(name, TRANSPORT)
        assert spec and spec.loader
        cls.contract = importlib.util.module_from_spec(spec)
        sys.modules[name] = cls.contract
        spec.loader.exec_module(cls.contract)
        from healthcare_data_engine.mapping.omop.candidate_publication import (
            FrozenCandidateScope,
        )
        cls.FrozenCandidateScope = FrozenCandidateScope

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("_g5_0113_source_transport_test", None)

    def scopes(self):
        scope = self.FrozenCandidateScope(
            hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4",
            source_system=(
                "synthea-fhir:atlanta-hospital-a:atlanta-hospital-a-fhir-r4"),
            request_id="atlanta-fhir-gh-20261111001",
            source_batch_id="a" * 64,
            manifest_sha256="b" * 64,
            silver_processing_version="fhir-silver-canonical-v2:engine-0.1.13",
            silver_publication_id="g4-published-new-batch",
            mapping_sha256="c" * 64,
            identity_snapshot_fingerprint="d" * 64,
            patient_count=6,
            encounter_count=21,
            provisional_person_count=6,
            provisional_visit_count=21,
        )
        trusted = self.contract.TrustedTechnicalScope(
            request_id=scope.request_id,
            source_batch_id=scope.source_batch_id,
            manifest_sha256=scope.manifest_sha256,
            mapping_profile_sha256=scope.mapping_sha256,
            stage_scope_version="1" * 64,
            source_format="FHIR_R4",
            source_system=scope.source_system,
            stage="CANDIDATE_APPROVED",
            f1_release_metadata_sha256="e" * 64,
            f2_identity_snapshot_fingerprint=scope.identity_snapshot_fingerprint,
            technical_evidence_sha256="f" * 64,
        )
        trusted.validate()
        return scope, trusted

    def invoke(self, scope, trusted):
        method = self.nb["_g5_dynamic_fhir_candidate_paths_source_only"]
        with patch.dict(method.__globals__, {"engine_version": "0.1.13"}):
            with patch.dict(sys.modules, {
                "healthcare_data_engine.security.provider_attestation":
                    self.contract
            }):
                return method(scope, trusted_scope=trusted)

    def test_published_017_remains_halt_before_v3_import(self):
        self.assertEqual(self.nb["engine_version"], "0.1.7")
        self.assertEqual(self.nb["run_mode"], "HALT")
        self.assertIs(self.nb["write_authorized"], False)
        method = self.nb["_g5_dynamic_fhir_candidate_paths_source_only"]
        with self.assertRaisesRegex(RuntimeError, "WHEEL_NOT_PUBLISHED"):
            method(object(), trusted_scope=object())

    def test_new_batch_path_is_dynamic_and_stage_isolated(self):
        scope, trusted = self.scopes()
        first = self.invoke(scope, trusted)
        self.assertEqual(set(first), {"person", "visit", "approval"})
        self.assertIn(scope.source_batch_id, first["person"])
        self.assertIn(scope.request_id, first["person"])
        self.assertIn(trusted.stage_scope_version, first["person"])
        self.assertIn(scope.mapping_sha256, first["person"])
        self.assertTrue(first["approval"].endswith("/candidate_approval"))
        second = self.invoke(
            replace(scope, source_batch_id="2" * 64),
            replace(trusted, source_batch_id="2" * 64))
        self.assertNotEqual(first, second)
        third = self.invoke(
            scope, replace(trusted, stage_scope_version="3" * 64))
        self.assertNotEqual(first, third)
        self.assertEqual(first, self.invoke(scope, trusted))

    def test_wrong_batch_manifest_mapping_f2_request_or_namespace_hold(self):
        scope, trusted = self.scopes()
        drifts = [
            ("source_batch_id", "9" * 64),
            ("manifest_sha256", "8" * 64),
            ("mapping_profile_sha256", "7" * 64),
            ("f2_identity_snapshot_fingerprint", "6" * 64),
            ("request_id", "different-fhir-request"),
            ("source_system", "synthea-fhir:other-hospital:other-feed"),
        ]
        for key, value in drifts:
            with self.subTest(field=key):
                with self.assertRaisesRegex(
                    RuntimeError, "STAGE_BATCH_OR_EVIDENCE_DRIFT"
                ):
                    self.invoke(scope, replace(trusted, **{key: value}))

    def test_hl7_gold_forged_scope_and_oversized_batch_all_hold(self):
        scope, trusted = self.scopes()
        for variation in (
            replace(trusted, source_format="HL7_V2"),
            replace(trusted, stage="GOLD_COMMITTED"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "STAGE_BATCH_OR_EVIDENCE_DRIFT"
            ):
                self.invoke(scope, variation)
        with self.assertRaisesRegex(RuntimeError, "TRUSTED_SCOPE_TYPE"):
            self.invoke(scope, object())
        with self.assertRaisesRegex(RuntimeError, "TRUSTED_SCOPE_INVALID"):
            self.invoke(scope, replace(trusted, stage_scope_version="invalid"))
        with self.assertRaisesRegex(RuntimeError, "UNSUPPORTED_LARGE_BATCH"):
            self.invoke(replace(scope, encounter_count=10001), trusted)

    def test_existing_frozen_source_path_and_main_dispatch_unchanged(self):
        # Planning the v3 output path must NEVER rewrite the pre-existing
        # physically accepted P100/E5918 source or make a notebook run live.
        source = NOTEBOOK.read_text(encoding="utf-8")
        self.assertIn('_G5_APPROVED_PATIENTS = 100', source)
        self.assertIn('_G5_APPROVED_ENCOUNTERS = 5918', source)
        self.assertIn('run_mode = "HALT"', source)
        self.assertIn("def verify_fhir_g5_candidate_source_readonly(", source)
        self.assertEqual(self.nb["run_mode"], "HALT")
        self.assertIs(self.nb["write_authorized"], False)


if __name__ == "__main__":
    unittest.main()
