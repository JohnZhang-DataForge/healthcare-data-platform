"""FHIR G5 dynamic v3 StageScope path planning; OFFLINE and SOURCE_ONLY.

This does not dispatch a Spark job, activate Fabric, or authorize Candidate/Gold.
The active published Wheel remains 0.1.7, so its runtime must fail closed.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
from types import SimpleNamespace
import importlib.util
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import Mock, patch

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
        method = self.nb["_plan_fhir_candidate_paths_from_trusted_scope"]
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
        method = self.nb["_plan_fhir_candidate_paths_from_trusted_scope"]
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


    def physical_fixture(self):
        """Exact same scopes as current FHIR adapter, synthetic NEW batch."""
        scope, trusted = self.scopes()
        raw = b'{"synthetic-fhir-manifest-only":true}'
        manifest_sha = hashlib.sha256(raw).hexdigest()
        context = self.nb["BatchContext"](
            hospital_id=scope.hospital_id, feed_id=scope.feed_id,
            source_system="synthea-fhir", request_id=scope.request_id,
            manifest_sha256=manifest_sha,
            processing_version=self.nb["_G4_PROCESSING"],
            processing_run_id="g4:" + scope.request_id,
            source_version="FHIR_R4", source_ingest_date=date(2026, 11, 11),
            processed_at=datetime.now(timezone.utc),
        )
        scope = replace(
            scope, manifest_sha256=manifest_sha,
            source_batch_id=context.source_batch_id,
            silver_processing_version=self.nb["_G4_PROCESSING"],
            silver_publication_id="e" * 64,
        )
        trusted = replace(
            trusted, manifest_sha256=manifest_sha,
            source_batch_id=context.source_batch_id,
        )
        candidate = SimpleNamespace(
            findings=(), patient_count=scope.patient_count,
            encounter_count=scope.encounter_count,
            source_batch_id=scope.source_batch_id,
            processing_version=scope.silver_processing_version,
            manifest_sha256=scope.manifest_sha256,
            publication_id=scope.silver_publication_id,
            patient_df=object(), encounter_df=object())
        approval = {"status": "SILVER_APPROVED",
                    "manifest_sha256": scope.manifest_sha256}
        loaded = []
        reader = Mock()
        mock_manifest = Mock()
        mock_manifest.select.return_value.collect.return_value = [
            SimpleNamespace(content=raw)]
        mock_approval = Mock()
        mock_approval.collect.return_value = [
            Mock(asDict=lambda recursive: approval)]
        def load(path):
            loaded.append(path)
            if path.endswith("/landing-manifest.json"):
                return mock_manifest
            if path.endswith("/silver_approval"):
                return mock_approval
            return Mock()
        reader.format.return_value.load.side_effect = load
        spark = SimpleNamespace(read=reader)
        functions = {
            "engine_version": "0.1.13",
            "run_mode": "HALT", "write_authorized": False,
            "load_pinned_contract": Mock(return_value=object()),
            "_manifest_objects": Mock(return_value=({"path": "fhir/one.json"},)),
            "_expected_bronze_source_receipts": Mock(return_value=[{"source_path": "x"}]),
            "_delta_snapshot_exists": Mock(
                side_effect=lambda spark, path: not path.endswith("/quarantine")),
            "_snapshot_silver_source_objects": Mock(return_value=(object(),)),
            "prepare_batch": Mock(return_value=candidate),
            "validate_silver_readback": Mock(),
            "_validate_silver_delta_contents": Mock(),
            "_silver_approval_row": Mock(return_value=approval),
        }
        return spark, scope, trusted, functions, loaded

    def invoke_physical(self, spark, scope, trusted, functions, *,
                        ingest_date=date(2026, 11, 11)):
        method = self.nb["verify_fhir_g5_dynamic_silver_source_readonly"]
        with patch.dict(method.__globals__, functions):
            with patch.dict(sys.modules, {
                "healthcare_data_engine.security.provider_attestation":
                    self.contract
            }):
                return method(
                    spark, scope=scope, trusted_scope=trusted,
                    source_ingest_date=ingest_date,
                    patient_contract_json="patient-contract",
                    encounter_contract_json="encounter-contract")

    def test_dynamic_silver_published_017_halts_before_any_spark_read(self):
        method = self.nb["verify_fhir_g5_dynamic_silver_source_readonly"]
        spark = Mock()
        with self.assertRaisesRegex(RuntimeError, "WHEEL_NOT_PUBLISHED"):
            method(spark, scope=None, trusted_scope=None,
                   source_ingest_date=None, patient_contract_json="",
                   encounter_contract_json="")
        spark.read.format.assert_not_called()

    def test_dynamic_silver_real_readback_orchestration_source_only(self):
        spark, scope, trusted, fns, paths = self.physical_fixture()
        result = self.invoke_physical(spark, scope, trusted, fns)
        self.assertEqual(
            result,
            "G5_DYNAMIC_FHIR_SILVER_PHYSICAL_RECOMPUTE_PASS_SOURCE_ONLY_NO_RELEASE")
        self.assertEqual(len(paths), 4)
        self.assertTrue(paths[0].endswith("/landing-manifest.json"))
        self.assertTrue(paths[1].endswith("/canonical_patient"))
        self.assertTrue(paths[2].endswith("/canonical_encounter"))
        self.assertTrue(paths[3].endswith("/silver_approval"))
        self.assertEqual(fns["prepare_batch"].call_count, 1)
        self.assertEqual(fns["validate_silver_readback"].call_count, 1)
        self.assertEqual(fns["_validate_silver_delta_contents"].call_count, 2)
        self.assertEqual(fns["_delta_snapshot_exists"].call_count, 5)
        self.assertEqual(fns["_snapshot_silver_source_objects"].call_count, 1)
        self.assertNotIn("candidate", " ".join(paths))
        self.assertNotIn("gold", " ".join(paths))

    def test_dynamic_silver_nonhalt_and_wrong_source_date_pre_io(self):
        for changes, date_value, code in (
            ({"run_mode": "G5_CANDIDATE_WRITE"}, date(2026, 11, 11),
             "NONHALT_OR_WRITE"),
            ({"write_authorized": True}, date(2026, 11, 11),
             "NONHALT_OR_WRITE"),
            ({}, "2026-11-11", "SOURCE_VERSION_OR_DATE"),
        ):
            spark, scope, trusted, fns, paths = self.physical_fixture()
            fns.update(changes)
            with self.subTest(code=code):
                with self.assertRaisesRegex(RuntimeError, code):
                    self.invoke_physical(
                        spark, scope, trusted, fns, ingest_date=date_value)
                self.assertEqual(paths, [])

    def test_dynamic_silver_wrong_batch_quarantine_or_approval_holds(self):
        cases = ("batch", "processing", "quarantine", "lost_approval",
                 "dq", "approval")
        for what in cases:
            spark, scope, trusted, fns, paths = self.physical_fixture()
            if what == "batch":
                scope = replace(scope, source_batch_id="9" * 64)
                trusted = replace(trusted, source_batch_id="9" * 64)
                reason = "DERIVED_BATCH_SHA_DRIFT"
            elif what == "processing":
                scope = replace(scope, silver_processing_version="wrong")
                reason = "SOURCE_VERSION_OR_DATE"
            elif what == "quarantine":
                fns["_delta_snapshot_exists"].side_effect = lambda *_: True
                reason = "PARTIAL_OR_QUARANTINED"
            elif what == "lost_approval":
                fns["_delta_snapshot_exists"].side_effect = (
                    lambda spark, path: not path.endswith(
                        ("/quarantine", "/silver_approval")))
                reason = "PARTIAL_OR_QUARANTINED"
            elif what == "dq":
                original = fns["prepare_batch"].return_value
                fns["prepare_batch"].return_value = SimpleNamespace(
                    **(vars(original) | {"patient_count": 777}))
                reason = "RECOMPUTED_DQ_OR_PUBLICATION"
            else:
                fns["_silver_approval_row"].return_value = {"status": "OTHER"}
                reason = "APPROVAL_LAST_FENCE_DRIFT"
            with self.subTest(case=what):
                with self.assertRaisesRegex(RuntimeError, reason):
                    self.invoke_physical(spark, scope, trusted, fns)

    def test_dynamic_shared_recompute_gate_requires_exact_wheel(self):
        method = self.nb["prepare_batch"]
        # A newly published 0.1.13 can enter the ORIGINAL Shared converter
        # without copying any FHIR transformation or OMOP mapper.
        sentinel = ValueError("REACHED_SINGLE_SHARED_CONVERTER")
        with patch.dict(method.__globals__, {
            "engine_version": "0.1.13",
            "verify_source_objects": Mock(side_effect=sentinel),
        }):
            with self.assertRaisesRegex(ValueError, "REACHED_SINGLE_SHARED"):
                method(object(), context=object(), manifest_bytes=b"",
                       source_objects=(),
                       patient_contract_bytes=b"", encounter_contract_bytes=b"")
        with patch.dict(method.__globals__, {"engine_version": "0.1.6"}):
            with self.assertRaisesRegex(
                ValueError, "SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH"
            ):
                method(object(), context=object(), manifest_bytes=b"",
                       source_objects=(),
                       patient_contract_bytes=b"", encounter_contract_bytes=b"")


if __name__ == "__main__":
    unittest.main()
