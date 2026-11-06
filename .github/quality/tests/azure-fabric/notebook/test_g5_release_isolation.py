"""OFFLINE ONLY: 0.1.3 effective Fabric Native Notebook vs 0.1.6 source release boundary.

Tests use the one already-staged Git Native 0.1.3 Wheel; source 0.1.6 is
exercised separately in another CI job / installed environment. These probes
must NEVER try a Fabric git sync, Environment Publish, Notebook execution,
Delta read/write, Warehouse SQL, or ID allocation.
"""
from __future__ import annotations

import hashlib
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
PUBLISHED_VERSION = "0.1.3"
SOURCE_CANDIDATE_VERSION = "0.1.6"
PINNED_WHEEL_SHA256 = (
    "6f5d95a47ab87a553686afcdc405343198ded6c99d244eb57c6ab2907a1fac59")


class G5NativeWheelIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A unique non-__main__ name ensures zero runtime entrypoint actions.
        cls.native = runpy.run_path(
            str(NATIVE), run_name="_g5_013_offline_source_isolation")

    def test_sole_git_native_wheel_and_source_candidate_are_distinct(self):
        self.assertEqual(engine.__version__, PUBLISHED_VERSION)
        self.assertEqual(self.native["engine_version"], PUBLISHED_VERSION)
        self.assertEqual(self.native["run_mode"], "HALT")
        self.assertIs(self.native["write_authorized"], False)
        self.assertIs(self.native["retention_preflight_verified"], False)
        self.assertEqual(
            tomllib.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
            ["project"]["version"], SOURCE_CANDIDATE_VERSION)
        wheel_files = sorted(LIBS.glob("*.whl"))
        self.assertEqual(
            [p.name for p in wheel_files],
            [f"healthcare_data_engine-{PUBLISHED_VERSION}-py3-none-any.whl"])
        self.assertEqual(
            hashlib.sha256(wheel_files[0].read_bytes()).hexdigest(),
            PINNED_WHEEL_SHA256)
        source = NATIVE.read_text(encoding="utf-8")
        self.assertEqual(
            source.count('if engine_version != "0.1.3":'), 3)
        self.assertIn('run_mode = "HALT"', source)
        self.assertIn('fhir-silver-canonical-v1:engine-0.1.1', source)
        self.assertNotIn("write_authorized = True", source)

    def test_old_notebook_rejects_016_even_with_safe_flags_before_data_reads(self):
        # Existing G3/G4 source processing must not silently accept 0.1.6.
        with patch.dict(
            self.native["prepare_batch"].__globals__,
            {"engine_version": SOURCE_CANDIDATE_VERSION},
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
            {"engine_version": SOURCE_CANDIDATE_VERSION,
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
            {"engine_version": SOURCE_CANDIDATE_VERSION},
        ):
            with self.assertRaisesRegex(
                    RuntimeError, "HOLD_RUNTIME_SMOKE_WRONG_ENGINE_VERSION"):
                self.native["validate_read_only_runtime_smoke"](
                    mode="RUNTIME_SMOKE", allow_write=False,
                    retention_ok=False, request="", manifest="",
                    source="", target="")
        self.assertEqual(self.native["engine_version"], PUBLISHED_VERSION)


if __name__ == "__main__":
    unittest.main()
