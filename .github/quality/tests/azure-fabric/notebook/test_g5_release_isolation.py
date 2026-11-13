"""OFFLINE ONLY: pinned Published 0.1.7 Native Notebook, historical 0.1.6 runtime HOLD.

Tests load the sole effective 0.1.7 GA Wheel while current source is 0.1.13; simulate prior
0.1.6 runtime mismatch, without executing any cloud job. These probes
must NEVER try a Fabric git sync, Environment Publish, Notebook execution,
Delta read/write, Warehouse SQL, or ID allocation.
"""
from __future__ import annotations

import hashlib
import sys
from types import ModuleType
from pathlib import Path
import runpy
import tomllib
import unittest
from unittest.mock import Mock, patch

import healthcare_data_engine as engine

ROOT = Path(__file__).resolve().parents[5]
NATIVE = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "nb_fhir_ingest.Notebook/notebook-content.py")
LIBS = ROOT / (
    "azure-fabric/workspaces/healthcare-omop/"
    "env_healthcare.Environment/Libraries/CustomLibraries")
SOURCE_METADATA = ROOT / "shared-data-engine/pyproject.toml"
PUBLISHED_VERSION = "0.1.7"
LEGACY_VERSION = "0.1.6"
SOURCE_CANDIDATE_VERSION = "0.1.13"
PINNED_WHEEL_SHA256 = (
    "0ae651aab21ce52592ac7462e365554dfc4a8cb0e65d44dd5ba9a39cb448c301")
PINNED_REVIEW_ONLY_017_SHA256 = (
    "0ae651aab21ce52592ac7462e365554dfc4a8cb0e65d44dd5ba9a39cb448c301")
REVIEW_ONLY_VERSION = "0.1.7"


class G5NativeWheelIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A unique non-__main__ name ensures zero runtime entrypoint actions.
        cls.native = runpy.run_path(
            str(NATIVE), run_name="_g5_017_native_business_source_isolation")

    def test_semantic_public_names_preserve_legacy_identity_and_halt(self):
        aliases = {
            "process_fhir_bronze_snapshot": "verify_fhir_g3_bronze",
            "process_fhir_silver_publication": "verify_fhir_g4_silver",
            "verify_fhir_dynamic_silver_source_readonly":
                "verify_fhir_g5_dynamic_silver_source_readonly",
            "plan_and_write_omop_candidate_delta": "plan_and_write_g5_candidate_delta",
            "verify_candidate_transport_source_only":
                "execute_g5_candidate_from_trusted_controller",
            "execute_person_visit_candidate_publication":
                "execute_g5_person_visit_business",
            "verify_fhir_candidate_source_readonly":
                "verify_fhir_g5_candidate_source_readonly",
            "verify_fhir_concept_source_inventory_readonly":
                "verify_fhir_g5_concept_source_inventory_readonly",
            "verify_fhir_bronze_negative_readonly":
                "verify_fhir_g3_negative_readonly",
        }
        for semantic, legacy in aliases.items():
            with self.subTest(semantic=semantic):
                self.assertIs(self.native[semantic], self.native[legacy])
                self.assertTrue(callable(self.native[semantic]))
        self.assertEqual(self.native["run_mode"], "HALT")
        self.assertIs(self.native["write_authorized"], False)
        self.assertIs(self.native["retention_preflight_verified"], False)
        main = NATIVE.read_text(encoding="utf-8").split(
            'if __name__ == "__main__":', 1)[1]
        # The legacy Bronze/Silver main dispatch retains frozen HOLD_G3/G4
        # error string compatibility until the Tier C protocol migration.
        for semantic in (
            "verify_fhir_candidate_source_readonly",
            "verify_fhir_concept_source_inventory_readonly",
            "verify_fhir_bronze_negative_readonly",
        ):
            self.assertIn(semantic + "(", main)
            self.assertNotIn(aliases[semantic] + "(", main)

    def test_fhir_storage_constant_names_keep_frozen_values(self):
        fixed = {
            "_FHIR_SOURCE_LANDING_ROOT": "Files/fhir_landing",
            "_FHIR_BRONZE_SNAPSHOT_ROOT": "Files/bronze/fhir_r4",
            "_FHIR_SOURCE_HOSPITAL_ID": "atlanta-hospital-a",
            "_FHIR_SOURCE_FEED_ID": "atlanta-hospital-a-fhir-r4",
            "_FHIR_BRONZE_PROCESSING_VERSION":
                "fhir-bronze-raw-snapshot-v1:engine-0.1.1",
            "_FHIR_SILVER_PUBLICATION_ROOT": "Files/silver/fhir_r4",
        }
        historical_names = (
            "_G3_SOURCE_ROOT", "_G3_BRONZE_ROOT",
            "_G3_HOSPITAL", "_G3_FEED", "_G3_PROCESSING",
            "_G4_SILVER_ROOT",
        )
        for name, value in fixed.items():
            with self.subTest(name=name):
                self.assertEqual(self.native[name], value)
        for name in historical_names:
            with self.subTest(name=name):
                self.assertNotIn(name, self.native)
        self.assertEqual(self.native["run_mode"], "HALT")
        self.assertIs(self.native["write_authorized"], False)
        self.assertIs(self.native["retention_preflight_verified"], False)

    def test_sole_git_native_wheel_matches_published_017_and_halt(self):
        self.assertEqual(engine.__version__, PUBLISHED_VERSION)
        self.assertEqual(self.native["engine_version"], PUBLISHED_VERSION)
        self.assertEqual(self.native["run_mode"], "HALT")
        self.assertIs(self.native["write_authorized"], False)
        self.assertIs(self.native["retention_preflight_verified"], False)
        self.assertEqual(
            tomllib.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
            ["project"]["version"], SOURCE_CANDIDATE_VERSION)
        wheel_files = sorted(LIBS.glob("*.whl"))
        # GA 0.1.7 is now effectively Published in the real Fabric
        # Environment, not merely a review-only Git staging artifact.
        self.assertEqual(
            [x.name for x in wheel_files],
            ["healthcare_data_engine-0.1.7-py3-none-any.whl"])
        self.assertEqual(
            hashlib.sha256(wheel_files[0].read_bytes()).hexdigest(),
            PINNED_WHEEL_SHA256)
        source = NATIVE.read_text(encoding="utf-8")
        self.assertEqual(
            source.count('if engine_version != "0.1.7":'), 2)
        self.assertIn('if engine_version not in ("0.1.7", "0.1.13"):', source)
        self.assertIn('run_mode = "HALT"', source)
        self.assertIn('fhir-silver-canonical-v1:engine-0.1.1', source)
        self.assertNotIn("write_authorized = True", source)

    def test_017_notebook_rejects_016_even_with_safe_flags_before_data_reads(self):
        # G3/G4 historical processing stays unchanged; wrong runtime 0.1.3 MUST HOLD.
        with patch.dict(
            self.native["prepare_batch"].__globals__,
            {"engine_version": LEGACY_VERSION},
        ):
            with self.assertRaisesRegex(
                    ValueError, "SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH"):
                self.native["prepare_batch"](
                    object(), context=object(), manifest_bytes=b"",
                    source_objects=(), patient_contract_bytes=b"",
                    encounter_contract_bytes=b"")

        g4_guard = Mock(side_effect=AssertionError("NO_G4_SPARK_READ_ALLOWED"))
        with patch.dict(
            self.native["verify_fhir_g5_candidate_source_readonly"].__globals__,
            {"engine_version": LEGACY_VERSION,
             "verify_fhir_g4_silver": g4_guard},
        ):
            with self.assertRaisesRegex(RuntimeError, "HOLD_G5_SOURCE_PIN"):
                self.native["verify_fhir_g5_candidate_source_readonly"](
                    object(),
                    request=self.native["_G5_APPROVED_REQUEST"],
                    manifest_sha=self.native["_G5_APPROVED_MANIFEST_SHA"],
                    allow_write=False, retention_ok=False,
                    strategy="DELTA_RAW_SNAPSHOT_V1",
                    manifest_override="", source_override="",
                    target_override="", patient_contract_json="",
                    encounter_contract_json="")
        g4_guard.assert_not_called()

        with patch.dict(
            self.native["validate_read_only_runtime_smoke"].__globals__,
            {"engine_version": LEGACY_VERSION},
        ):
            with self.assertRaisesRegex(
                    RuntimeError, "HOLD_RUNTIME_SMOKE_WRONG_ENGINE_VERSION"):
                self.native["validate_read_only_runtime_smoke"](
                    mode="RUNTIME_SMOKE", allow_write=False,
                    retention_ok=False, request="", manifest="",
                    source="", target="")
        self.assertEqual(self.native["engine_version"], PUBLISHED_VERSION)


    def test_g5_native_legacy_provider_write_denied_before_any_callback(self):
        # The old duck-typed provider was never a trust boundary. Even a
        # convincing fake approval/SQL connection cannot enter a write path.
        method = self.native["execute_g5_candidate_from_trusted_controller"]
        malicious = Mock()
        malicious.load_pinned_inputs.return_value = {
            "status": "SIGNED_CLINICAL_APPROVED",
            "f2": "INDEPENDENT_SIX_TABLE_SQL_PASS",
        }
        spark = Mock()
        for mode in ("G5_CANDIDATE_WRITE", "SILVER_WRITE", "G5_GOLD_COMMIT"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(
                        RuntimeError,
                        "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
                    method(spark, provider=malicious, mode=mode,
                           attestation_bytes=b"fake")
        malicious.load_pinned_inputs.assert_not_called()
        malicious.verify_signed_clinical_review.assert_not_called()
        malicious.verify_license_rights.assert_not_called()
        malicious.capture_full_warehouse_snapshot.assert_not_called()
        malicious.read_verified_warehouse_concepts.assert_not_called()
        spark.read.format.assert_not_called()
        spark.sql.assert_not_called()

    def test_g5_native_readback_rejects_fake_provider_and_spark(self):
        method = self.native["execute_g5_candidate_from_trusted_controller"]
        poisoned_provider = Mock()
        spark = Mock()
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_NATIVE_CALLER_PROVIDER_OR_SPARK_UNTRUSTED"):
            method(spark, provider=poisoned_provider,
                   mode="G5_CANDIDATE_READBACK_ONLY",
                   attestation_bytes=b"forged")
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_NATIVE_CALLER_PROVIDER_OR_SPARK_UNTRUSTED"):
            method(None, provider=poisoned_provider,
                   mode="G5_CANDIDATE_READBACK_ONLY",
                   attestation_bytes=b"forged")
        poisoned_provider.load_pinned_inputs.assert_not_called()
        spark.sql.assert_not_called()

    def test_g5_native_transport_cannot_bypass_effective_wheel_halt(self):
        method = self.native["execute_g5_candidate_from_trusted_controller"]
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_NATIVE_0113_TRANSPORT_WHEEL_NOT_PUBLISHED"):
            method(None, provider=None, mode="G5_CANDIDATE_READBACK_ONLY",
                   attestation_bytes=b"forged")
        with patch.dict(method.__globals__, {"run_mode": "G5_CANDIDATE_WRITE"}):
            with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_RUN_MODE"):
                method(None, provider=None, mode="G5_CANDIDATE_READBACK_ONLY",
                       attestation_bytes=b"forged")
        with patch.dict(method.__globals__, {"write_authorized": True}):
            with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_RUN_MODE"):
                method(None, provider=None, mode="G5_CANDIDATE_READBACK_ONLY",
                       attestation_bytes=b"forged")
        # Hypothetical source-only version must still require actual signed
        # bytes before importing the future verifier or calling the provider.
        with patch.dict(method.__globals__, {"engine_version": "0.1.13"}):
            for bad in (None, "", b"", b"a" * 8193):
                with self.subTest(bad=type(bad).__name__):
                    with self.assertRaisesRegex(
                            RuntimeError,
                            "HOLD_G5_NATIVE_SIGNED_ATTESTATION_BYTES_MISSING"):
                        method(None, provider=None,
                               mode="G5_CANDIDATE_READBACK_ONLY",
                               attestation_bytes=bad)
        source = NATIVE.read_text(encoding="utf-8")
        body = source.split(
            "def execute_g5_candidate_from_trusted_controller(", 1)[1].split(
            "\ndef execute_g5_person_visit_business(", 1)[0]
        self.assertNotIn("provider.verify_signed_clinical_review(", body)
        self.assertNotIn("provider.verify_license_rights(", body)
        self.assertNotIn("provider.capture_full_warehouse_snapshot(", body)
        self.assertNotIn("execute_g5_person_visit_business(", body)
        self.assertIn("G5_NATIVE_ATTESTATION_SOURCE_ONLY_VERIFIED_NOT_DISPATCHED", body)



    def test_dynamic_fhir_hl7_v3_transport_is_source_only_never_release(self):
        """Future verified 0.1.13 can inspect v3, never dispatch a Writer.

        The synthetic module stands in only for the import contract. It is NOT
        a real signature, identity proof, physical Silver or release receipt.
        """
        method = self.native["execute_g5_candidate_from_trusted_controller"]
        class LegacyVerified:
            pass

        class TechnicalVerified:
            def __init__(self, *, status, source_format,
                         candidate_write_authorized=False,
                         gold_committed=False, provisional_ids_persisted=False):
                self.status = status
                self.source_format = source_format
                self.candidate_write_authorized = candidate_write_authorized
                self.gold_committed = gold_committed
                self.provisional_ids_persisted = provisional_ids_persisted

        class SyntheticTransportHold(Exception):
            pass

        security = ModuleType("healthcare_data_engine.security")
        security.__path__ = []
        transport = ModuleType(
            "healthcare_data_engine.security.provider_attestation")
        transport.TransportHold = SyntheticTransportHold
        transport.VerifiedTransport = LegacyVerified
        transport.VerifiedTechnicalTransport = TechnicalVerified
        marker = (
            "G5_DYNAMIC_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE")
        cases = (
            ("FHIR_R4", TechnicalVerified(
                status=marker, source_format="FHIR_R4")),
            ("HL7_V2", TechnicalVerified(
                status=marker, source_format="HL7_V2")),
        )
        for source_format, receipt in cases:
            with self.subTest(source_format=source_format):
                verifier = Mock(return_value=receipt)
                transport.verify_native_handoff_source_only = verifier
                with patch.dict(sys.modules, {
                        "healthcare_data_engine.security": security,
                        "healthcare_data_engine.security.provider_attestation":
                            transport}), patch.dict(method.__globals__, {
                        "engine_version": "0.1.13"}):
                    result = method(
                        None, provider=None, mode="G5_CANDIDATE_READBACK_ONLY",
                        attestation_bytes=b"synthetic-envelope-only")
                self.assertEqual(
                    result, "G5_NATIVE_ATTESTATION_SOURCE_ONLY_VERIFIED_NOT_DISPATCHED")
                verifier.assert_called_once_with(b"synthetic-envelope-only")

                # Even a signer returning forged release or persisted-ID flags
                # cannot elevate the transport-only Notebook preflight.
                for flags in (
                    {"candidate_write_authorized": True},
                    {"gold_committed": True},
                    {"provisional_ids_persisted": True},
                ):
                    with self.subTest(source_format=source_format, flags=flags):
                        transport.verify_native_handoff_source_only = Mock(
                            return_value=TechnicalVerified(
                                status=marker, source_format=source_format,
                                **flags))
                        with patch.dict(sys.modules, {
                                "healthcare_data_engine.security": security,
                                "healthcare_data_engine.security.provider_attestation":
                                    transport}), patch.dict(method.__globals__, {
                                "engine_version": "0.1.13"}):
                            with self.assertRaisesRegex(
                                    RuntimeError,
                                    "HOLD_G5_NATIVE_NON_SOURCE_ONLY_ATTESTATION"):
                                method(None, provider=None,
                                       mode="G5_CANDIDATE_READBACK_ONLY",
                                       attestation_bytes=b"synthetic-envelope-only")

        # The actual 0.1.7 remains a strict HOLD, regardless of fake bytes.
        self.assertEqual(self.native["engine_version"], "0.1.7")



    @staticmethod
    def _g5_synthetic_technical_fixture():
        """GA 0.1.7 typed scope; no fake reviewer/signature or Fabric IO."""
        from healthcare_data_engine.identity.candidate_handoff import (
            CandidatePersonId, CandidateVisitId, PersonVisitCandidateHandoff)
        from healthcare_data_engine.mapping.omop.candidates import OmopCandidates
        from healthcare_data_engine.mapping.omop.candidate_publication import (
            freeze_candidate_scope)
        hospital, feed = "atlanta-hospital-a", "atlanta-hospital-a-fhir-r4"
        source = "synthea-fhir:" + hospital + ":" + feed
        person = CandidatePersonId(
            hospital, source, "patient-000", 1, "PROVISIONAL")
        visit = CandidateVisitId(
            hospital, source, "encounter-000", "patient-000",
            1, 1, "PROVISIONAL", "PROVISIONAL")
        handoff = PersonVisitCandidateHandoff(
            person_lookup=(person,), batch_persons=(person,),
            batch_visits=(visit,), hospital_id=hospital,
            source_system=source,
            source_batch_id="2e110eb1971fcfa3ebb4dda6782c49a7608955855a2de45a3d77ada47fea8adb",
            manifest_sha256="a" * 64,
            processing_version="fhir-silver-canonical-v1:engine-0.1.1",
            silver_publication_id="synthetic-silver-001",
            snapshot_fingerprint="b" * 64)
        mapper = OmopCandidates(object(), object(), "c" * 64, 1, 1)
        scope = freeze_candidate_scope(
            handoff, mapper, feed_id=feed,
            request_id="atlanta-fhir-gh-41552666929")
        return scope, handoff, mapper

    def _candidate_technical_args(self):
        scope, handoff, mapper = self._g5_synthetic_technical_fixture()
        return {
            "scope": scope, "handoff": handoff, "mapper_result": mapper,
            "person_candidate": object(), "visit_candidate": object(),
            "mode": "G5_CANDIDATE_WRITE", "write_authorized": True,
            "warehouse_snapshot_verified": True,
            "warehouse_snapshot_sha256": scope.identity_snapshot_fingerprint,
            "patient_contract_json": "SYNTHETIC",
            "encounter_contract_json": "SYNTHETIC",
            "technical_evidence_sha256": "d" * 64,
        }

    def test_g5_technical_stage_proof_reaches_real_silver_fence_no_humans(self):
        method = self.native["plan_and_write_g5_candidate_delta"]
        arguments = self._candidate_technical_args()
        release = Mock(return_value=True)
        arguments["trusted_technical_release_gate"] = release
        physical = Mock(side_effect=RuntimeError("REACHED_PHYSICAL_SILVER_FENCE"))
        # The real frozen-G4 allowlist is tested elsewhere using P100/E5918.
        # Isolate Stage release ordering here with a synthetic scoped path.
        with patch.dict(method.__globals__, {
            "_g5_candidate_paths": lambda _scope: {
                "person": "synthetic-person", "visit": "synthetic-visit",
                "approval": "synthetic-approval",
            },
            "verify_fhir_g5_candidate_source_readonly": physical,
        }):
            with self.assertRaisesRegex(RuntimeError, "REACHED_PHYSICAL_SILVER_FENCE"):
                method(None, **arguments)
        release.assert_called_once_with(
            arguments["scope"], arguments["technical_evidence_sha256"])
        physical.assert_called_once()
        self.assertIs(self.native["write_authorized"], False)
        self.assertEqual(self.native["run_mode"], "HALT")

    def test_g5_technical_release_rejects_missing_or_untrusted_owner(self):
        method = self.native["plan_and_write_g5_candidate_delta"]
        arguments = self._candidate_technical_args()
        with self.assertRaisesRegex(RuntimeError, "STAGE_RELEASE_UNTRUSTED"):
            method(None, **arguments)
        release = Mock(return_value=False)
        arguments["trusted_technical_release_gate"] = release
        with self.assertRaisesRegex(RuntimeError, "STAGE_RELEASE_UNTRUSTED"):
            method(None, **arguments)
        release.assert_called_once()

    def test_g5_technical_bad_f2_and_fake_review_hold_before_callback(self):
        method = self.native["plan_and_write_g5_candidate_delta"]
        arguments = self._candidate_technical_args()
        release = Mock(side_effect=AssertionError("UNTRUSTED_CALLBACK"))
        arguments["trusted_technical_release_gate"] = release
        bad = dict(arguments, technical_evidence_sha256="BAD")
        with self.assertRaisesRegex(RuntimeError, "EVIDENCE_SHA_NOT_PINNED"):
            method(None, **bad)
        bad = dict(arguments, clinical_review_sha256="e" * 64)
        with self.assertRaisesRegex(RuntimeError, "CANNOT_FORGE_REVIEWS"):
            method(None, **bad)
        bad = dict(arguments, warehouse_snapshot_sha256="a" * 64)
        # Physical F2 fingerprint mismatch MUST fail closed (it must never
        # result in a verified Stage release).
        with self.assertRaises(RuntimeError):
            method(None, **bad)
        release.assert_not_called()

    def test_g5_business_accepts_technical_evidence_shape_without_reviewer(self):
        method = self.native["execute_g5_person_visit_business"]
        args = self._candidate_technical_args()
        arguments = {
            "scope": args["scope"], "handoff": args["handoff"],
            "concepts_from_verified_warehouse": object(),
            "mapping_profile_bytes": b"NOT_REACHED",
            "raw_publish_run_id": "synthetic-run",
            "patient_contract_json": "SYNTHETIC",
            "encounter_contract_json": "SYNTHETIC",
            "mode": "G5_CANDIDATE_WRITE",
            "write_authorized": True,
            "warehouse_snapshot_verified": True,
            "warehouse_snapshot_sha256": args["warehouse_snapshot_sha256"],
            "technical_evidence_sha256": args["technical_evidence_sha256"],
        }
        with self.assertRaisesRegex(RuntimeError, "TECHNICAL_STAGE_RELEASE_MISSING"):
            method(None, **arguments)
        arguments["trusted_technical_release_gate"] = Mock(return_value=False)
        # This path proceeds to validate immutable Profile before any Spark.
        with self.assertRaisesRegex(RuntimeError, "MAPPING_PROFILE_BYTES"):
            method(None, **arguments)
        arguments["technical_evidence_sha256"] = "bad sha"
        with self.assertRaisesRegex(RuntimeError, "TECHNICAL_EVIDENCE_SHA_INVALID"):
            method(None, **arguments)



if __name__ == "__main__":
    unittest.main()
