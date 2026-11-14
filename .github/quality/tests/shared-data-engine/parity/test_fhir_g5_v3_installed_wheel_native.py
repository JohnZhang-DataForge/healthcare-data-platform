"""0.1.13 source and *installed* Wheel ↔ existing FHIR Native v3 parity.

Synthetic-only, no Fabric network, no environment publish, no Delta/SQL writes.
The CI calls this once with source PYTHONPATH and again after installing the
actual freshly built SHA-pinned 0.1.13 Wheel in an isolated venv.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock

import healthcare_data_engine as engine
from healthcare_data_engine.mapping.omop.candidate_publication import (
    FrozenCandidateScope,
)
from healthcare_data_engine.security.provider_attestation import (
    TrustedTechnicalScope,
)

ROOT = Path(__file__).resolve().parents[5]
NATIVE = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "nb_fhir_ingest.Notebook/notebook-content.py")


def synthetic_scopes():
    scope = FrozenCandidateScope(
        hospital_id="atlanta-hospital-a",
        feed_id="atlanta-hospital-a-fhir-r4",
        source_system="synthea-fhir:atlanta-hospital-a:atlanta-hospital-a-fhir-r4",
        request_id="atlanta-fhir-gh-20261111001",
        source_batch_id="a" * 64,
        manifest_sha256="b" * 64,
        silver_processing_version="fhir-silver-canonical-v1:engine-0.1.1",
        silver_publication_id="f" * 64,
        mapping_sha256="c" * 64,
        identity_snapshot_fingerprint="d" * 64,
        patient_count=6,
        encounter_count=21,
        provisional_person_count=6,
        provisional_visit_count=21,
    )
    technical = TrustedTechnicalScope(
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
    technical.validate()
    return scope, technical


class FhirNativeWheelV3Parity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = runpy.run_path(
            str(NATIVE), run_name="_g5_0113_wheel_native_pure_parity")

    def test_runtime_013_and_native_halt_fence(self):
        self.assertEqual(engine.__version__, "0.1.13")
        self.assertEqual(self.native["engine_version"], "0.1.13")
        self.assertEqual(self.native["run_mode"], "HALT")
        self.assertIs(self.native["write_authorized"], False)
        self.assertIs(self.native["retention_preflight_verified"], False)

    def test_actual_typed_v3_scope_wires_to_native_fhir_planner(self):
        source, trusted = synthetic_scopes()
        paths = self.native["_plan_fhir_candidate_paths_from_trusted_scope"](
            source, trusted_scope=trusted)
        self.assertEqual(set(paths), {"person", "visit", "approval"})
        self.assertIn(source.request_id, paths["person"])
        self.assertIn(source.source_batch_id, paths["person"])
        self.assertIn(trusted.stage_scope_version, paths["person"])
        self.assertIn(source.mapping_sha256, paths["approval"])
        self.assertTrue(paths["approval"].endswith("/candidate_approval"))
        self.assertNotIn("Files/silver/", str(paths))

    def test_tampered_source_format_stage_f2_and_manifest_fail_closed(self):
        source, trusted = synthetic_scopes()
        fn = self.native["_plan_fhir_candidate_paths_from_trusted_scope"]
        invalids = (
            replace(trusted, source_format="HL7_V2"),
            replace(trusted, stage="GOLD_COMMITTED"),
            replace(trusted, f2_identity_snapshot_fingerprint="4" * 64),
            replace(trusted, manifest_sha256="5" * 64),
        )
        for altered in invalids:
            with self.subTest(altered=altered):
                with self.assertRaisesRegex(
                    RuntimeError, "STAGE_BATCH_OR_EVIDENCE_DRIFT"
                ):
                    fn(source, trusted_scope=altered)

    def test_dynamic_readback_bad_date_fails_before_spark_io(self):
        source, trusted = synthetic_scopes()
        spark = Mock()
        fn = self.native["verify_fhir_g5_dynamic_silver_source_readonly"]
        with self.assertRaisesRegex(
            RuntimeError, "G4_SOURCE_VERSION_OR_DATE"
        ):
            fn(spark, scope=source, trusted_scope=trusted,
               source_ingest_date="2026-11-11",
               patient_contract_json="synthetic-patient",
               encounter_contract_json="synthetic-encounter")
        spark.read.format.assert_not_called()

    def test_legacy_g4_write_and_readback_still_hold_under_013(self):
        # In-place replacement of GA 0.1.7 would break historic G4 reads.
        # This explicitly forces isolated runtime/Environment commissioning.
        spark = Mock()
        fn = self.native["verify_fhir_g4_silver"]
        with self.assertRaisesRegex(
            RuntimeError, "HOLD_G4_ENGINE_OR_MANIFEST_PIN"
        ):
            fn(
                spark, request="atlanta-fhir-gh-41552666929",
                manifest_sha="b" * 64, mode="SILVER_READBACK_ONLY",
                allow_write=False, retention_ok=False,
                strategy="DELTA_RAW_SNAPSHOT_V1",
                manifest_override="", source_override="", target_override="",
                patient_contract_json="synthetic-patient",
                encounter_contract_json="synthetic-encounter",
            )
        spark.read.format.assert_not_called()


if __name__ == "__main__":
    unittest.main()
