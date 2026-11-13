"""G5 native Notebook candidate-input physical preflight, offline simulated Delta.

Mocked G4 readback and synthetic in-memory frames are TEST FIXTURES, not an
actual Fabric Job or evidence of real P100/E5918 acceptance.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock, patch

from pyspark.sql import SparkSession

ROOT = Path(__file__).resolve().parents[5]
NB = ROOT / "azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py"
PATIENT = ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json"
ENCOUNTER = ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json"
CODE = runpy.run_path(str(NB), run_name="_g5_synthetic_no_fabric_execution")
CHECK = CODE["verify_fhir_g5_candidate_source_readonly"]
INVENTORY = CODE["verify_fhir_g5_concept_source_inventory_readonly"]
PATHS = CODE["_silver_publication_paths"]("atlanta-fhir-gh-41552666929")
BATCH = "a" * 64
SOURCE = "synthea-fhir:atlanta-hospital-a:atlanta-hospital-a-fhir-r4"
APPROVAL = {
    "status": "SILVER_APPROVED",
    "source_batch_id": BATCH,
    "manifest_sha256": "425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1",
    "processing_version": "fhir-silver-canonical-v1:engine-0.1.1",
    "publication_id": "fixture-publication",
    "patient_count": 100,
    "encounter_count": 5918,
    "quarantine_count": 0,
    "patient_contract_sha256": hashlib.sha256(PATIENT.read_bytes()).hexdigest(),
    "encounter_contract_sha256": hashlib.sha256(ENCOUNTER.read_bytes()).hexdigest(),
    "source_preservation_strategy": "DELTA_RAW_SNAPSHOT_V1",
}


def args():
    return dict(
        request="atlanta-fhir-gh-41552666929",
        manifest_sha=APPROVAL["manifest_sha256"],
        allow_write=False,
        retention_ok=False,
        strategy="DELTA_RAW_SNAPSHOT_V1",
        manifest_override="", source_override="", target_override="",
        patient_contract_json=PATIENT.read_text(encoding="utf-8"),
        encounter_contract_json=ENCOUNTER.read_text(encoding="utf-8"),
    )


def g4_fixture(**overrides):
    values = dict(
        status="SILVER_SKIP_VERIFIED",
        source_batch_id=BATCH,
        processing_version="fhir-silver-canonical-v1:engine-0.1.1",
        publication_id="fixture-publication",
        metrics={"patient": 100, "encounter": 5918, "quarantine_or_reject": 0},
    )
    values.update(overrides)
    return type("G4Fixture", (), values)()


class Reader:
    def __init__(self, frames):
        self.frames = frames

    def format(self, fmt):
        if fmt != "delta":
            raise AssertionError("G5 must physically read only existing Delta")
        return self

    def load(self, path):
        if path not in self.frames:
            raise AssertionError("unexpected unpinned G5 Delta path")
        return self.frames[path]


class OnlyReads:
    def __init__(self, frames):
        self.read = Reader(frames)
        # No createDataFrame, .sql, .write, connect or external network API.


class NegativeBeforeAnySparkRead(unittest.TestCase):
    def test_request_manifest_write_flags_and_overrides_hold_before_g4(self):
        for key, value in (
            ("request", "atlanta-fhir-gh-41570668110"),  # rejected Q26
            ("request", "../../other-hospital"),
            ("manifest_sha", "f" * 64),
            ("allow_write", True),
            ("allow_write", "false"),
            ("retention_ok", True),
            ("strategy", "HALT"),
            ("manifest_override", "{}"),
            ("source_override", "Files/another"),
            ("target_override", "Files/omop_candidate"),
        ):
            with self.subTest(key=key, value=value):
                g4 = Mock(side_effect=AssertionError("must not call G4"))
                with patch.dict(CHECK.__globals__, {"verify_fhir_g4_silver": g4}):
                    with self.assertRaisesRegex(RuntimeError, "HOLD_G5_SOURCE_PIN"):
                        CHECK(object(), **dict(args(), **{key: value}))
                g4.assert_not_called()

    def test_no_canonical_bytes_or_tampered_raw_pin_holds_before_g4(self):
        for name in ("patient_contract_json", "encounter_contract_json"):
            with self.subTest(name=name):
                case = args()
                case[name] = ""
                with patch.dict(CHECK.__globals__, {
                    "verify_fhir_g4_silver": Mock(side_effect=AssertionError("G4 called"))
                }):
                    with self.assertRaisesRegex(RuntimeError, "HOLD_G5_CANONICAL"):
                        CHECK(object(), **case)
                case[name] = case[name] + "{}"
                with self.assertRaises(ValueError):
                    CHECK(object(), **case)

    def test_unapproved_g4_status_or_counts_never_claims_source_success(self):
        for x in (
            {"status": "HOLD_DQ"},
            {"status": "SILVER_APPROVED"},
            {"processing_version": "fhir-silver-canonical-v1:engine-0.1.3"},
            {"metrics": {"patient": 99, "encounter": 5893, "quarantine_or_reject": 26}},
            {"publication_id": ""},
        ):
            with self.subTest(g4=x):
                stub = Mock(return_value=g4_fixture(**x))
                with patch.dict(CHECK.__globals__, {"verify_fhir_g4_silver": stub}):
                    with self.assertRaisesRegex(RuntimeError, "HOLD_G5_G4_PHYSICAL"):
                        CHECK(object(), **args())
                self.assertEqual(stub.call_count, 1)
                self.assertEqual(stub.call_args.kwargs["mode"], "SILVER_READBACK_ONLY")
                self.assertIs(stub.call_args.kwargs["allow_write"], False)
                self.assertIs(stub.call_args.kwargs["retention_ok"], False)


class SyntheticDeltaFrames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[2]")
                     .appName("g5-candidate-source-readonly-unit").getOrCreate())
        cls.spark.sparkContext.setLogLevel("ERROR")
        patients = [(SOURCE, BATCH, f"p{i:03d}") for i in range(100)]
        encounters = [(SOURCE, BATCH, f"e{i:05d}", f"p{i%100:03d}")
                      for i in range(5918)]
        cls.patient = cls.spark.createDataFrame(
            patients, "source_system string, source_batch_id string, source_record_id string").cache()
        cls.encounter = cls.spark.createDataFrame(
            encounters, "source_system string, source_batch_id string, source_encounter_id string, source_person_id string").cache()
        cls.patient.count()
        cls.encounter.count()

    @classmethod
    def tearDownClass(cls):
        cls.patient.unpersist()
        cls.encounter.unpersist()
        cls.spark.stop()

    def frames(self, **changes):
        approval = dict(APPROVAL)
        approval.update(changes.pop("approval", {}))
        fields = list(APPROVAL)
        row = self.spark.createDataFrame([tuple(approval[k] for k in fields)],
                                         ", ".join(
                                             f"{k} {'long' if k in ('patient_count','encounter_count','quarantine_count') else 'string'}"
                                             for k in fields))
        return {
            PATHS["patient"]: changes.get("patient", self.patient),
            PATHS["encounter"]: changes.get("encounter", self.encounter),
            PATHS["approval"]: changes.get("approval_df", row),
        }

    def invoke(self, frames):
        with patch.dict(CHECK.__globals__, {
            "verify_fhir_g4_silver": Mock(return_value=g4_fixture())
        }):
            return CHECK(OnlyReads(frames), **args())

    def test_synthetic_p100_e5918_source_only_pass(self):
        result = self.invoke(self.frames())
        self.assertEqual(result,
            "FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_APPROVAL_DELTA_PASS_20261104")
        self.assertNotIn("GOLD", result)
        self.assertNotIn("COMMITTED", result)
        self.assertNotIn("OMOP_CANDIDATE_WRITTEN", result)

    def test_tampered_approval_never_passes(self):
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_APPROVAL_FENCE_CHANGED"):
            self.invoke(self.frames(approval={"quarantine_count": 26}))
        duplicate = self.spark.createDataFrame(
            [tuple(APPROVAL[k] for k in APPROVAL)] * 2,
            ", ".join(f"{k} {'long' if k in ('patient_count','encounter_count','quarantine_count') else 'string'}"
                      for k in APPROVAL))
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_APPROVAL_ROW_CARDINALITY"):
            self.invoke(self.frames(approval_df=duplicate))

    def test_missing_patient_encounter_fails_counts(self):
        partial = self.patient.limit(99)
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_SILVER_COUNTS_DRIFT"):
            self.invoke(self.frames(patient=partial))

    def test_cross_hospital_or_orphan_fk_never_passes(self):
        from pyspark.sql import functions as F
        changed = self.encounter.withColumn(
            "source_person_id",
            F.when(F.col("source_encounter_id") == "e00000", "foreign-patient")
             .otherwise(F.col("source_person_id")))
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_ENCOUNTER_PERSON_FK_ORPHAN"):
            self.invoke(self.frames(encounter=changed))

    def test_source_batch_drift_never_passes(self):
        from pyspark.sql import functions as F
        changed = self.patient.withColumn(
            "source_batch_id",
            F.when(F.col("source_record_id") == "p000", "f"*64)
             .otherwise(F.col("source_batch_id")))
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_PATIENT_NAMESPACE_OR_KEY"):
            self.invoke(self.frames(patient=changed))


    def _code_frames(self):
        from pyspark.sql import functions as F
        patient = (self.patient.withColumn("gender_code", F.lit("synthetic-g"))
                   .withColumn("race_code", F.lit("synthetic-r"))
                   .withColumn("ethnicity_code", F.lit("synthetic-e")))
        encounter = (self.encounter.withColumn("encounter_class", F.lit("synthetic-v"))
                     .withColumn("source_code", F.lit("synthetic-source-code")))
        return self.frames(patient=patient, encounter=encounter)

    def _inventory(self, frames, **parameters):
        verified = Mock(return_value=(
            "FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_"
            "APPROVAL_DELTA_PASS_20261104"))
        with patch.dict(INVENTORY.__globals__, {
            "verify_fhir_g5_candidate_source_readonly": verified
        }):
            result = INVENTORY(OnlyReads(frames), **dict(args(), **parameters))
        self.assertEqual(verified.call_count, 1)
        self.assertIs(verified.call_args.kwargs["allow_write"], False)
        self.assertIs(verified.call_args.kwargs["retention_ok"], False)
        return result

    def test_p1_inventory_extracts_real_dataframe_codes_but_no_gold(self):
        result = self._inventory(self._code_frames())
        prefix = "FHIR_G5_CONCEPT_SOURCE_INVENTORY_READONLY_PASS|"
        self.assertTrue(result.startswith(prefix))
        info = json.loads(result[len(prefix):])
        self.assertEqual(info["status"], "P1_G4_CODE_INVENTORY_PHYSICAL_READONLY_ONLY")
        self.assertEqual((info["patient_count"], info["encounter_count"]), (100, 5918))
        self.assertEqual(info["code_counts"]["gender_code"], {"synthetic-g": 100})
        self.assertEqual(info["code_counts"]["encounter_class"], {"synthetic-v": 5918})
        self.assertEqual(info["code_counts"]["source_code"], {"synthetic-source-code": 5918})
        self.assertNotIn("GOLD_COMMITTED", result)
        self.assertNotIn("person_id", result)

    def test_p1_inventory_denies_tampered_approval_and_person_source_width(self):
        from pyspark.sql import functions as F
        with self.assertRaisesRegex(RuntimeError, "HOLD_P1_APPROVAL_CHANGED"):
            self._inventory(self.frames(**{
                **{"patient": self._code_frames()[PATHS["patient"]],
                   "encounter": self._code_frames()[PATHS["encounter"]]},
                "approval": {"manifest_sha256": "0"*64},
            }))
        frames = self._code_frames()
        frames[PATHS["patient"]] = frames[PATHS["patient"]].withColumn(
            "source_record_id",
            F.when(F.col("source_record_id") == "p000", F.lit("p" * 51))
             .otherwise(F.col("source_record_id")))
        with self.assertRaisesRegex(RuntimeError, "HOLD_P1_PERSON_SOURCE_VALUE_TOO_LONG"):
            self._inventory(frames)

    def test_p1_inventory_denies_unmapped_or_casefold_ambiguous_codes(self):
        from pyspark.sql import functions as F
        frames = self._code_frames()
        frames[PATHS["encounter"]] = frames[PATHS["encounter"]].withColumn(
            "encounter_class",
            F.when(F.col("source_encounter_id") == "e00000", F.lit("SYNTHETIC-V"))
             .otherwise(F.col("encounter_class")))
        with self.assertRaisesRegex(RuntimeError, "HOLD_P1_SOURCE_CODE_COLLATION_CONFLICT"):
            self._inventory(frames)


if __name__ == "__main__":
    unittest.main()
