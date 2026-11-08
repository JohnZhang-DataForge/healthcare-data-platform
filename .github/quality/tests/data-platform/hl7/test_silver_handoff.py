"""Synthetic-only HL7 Candidate -> reused Shared Canonical v1 DQ handoff."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "shared-data-engine/src"))
sys.path.insert(0, str(ROOT / "local-data-platform/spark/apps/hl7"))

from healthcare_data_engine.canonical.validation import load_pinned_contract, validate_row
from healthcare_data_engine.models.batch_context import BatchContext
from silver_handoff import HL7HandoffHold, prepare_hl7_canonical_handoff


RAW_PATIENT = (ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes()
RAW_ENCOUNTER = (ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes()
PATIENT = load_pinned_contract(RAW_PATIENT, "patient")
ENCOUNTER = load_pinned_contract(RAW_ENCOUNTER, "encounter")
UTC = timezone.utc


def context():
    return BatchContext(
        hospital_id="johns-creek-hospital-b",
        feed_id="johns-creek-hospital-b-hl7-v2",
        source_system="johns-creek-hl7",
        request_id="johnscreek-hl7-gh-12345678901",
        manifest_sha256="a" * 64,
        processing_version="hl7-canonical-v1-synthetic-test",
        processing_run_id="synthetic-v2-001",
        source_version="HL7v2.5.1",
        source_ingest_date=date(2026, 11, 7),
        processed_at=datetime(2026, 11, 7, 13, 0, 0, tzinfo=UTC),
        adapter_version="1.3.5",
    )


def rows(ctx=None):
    ctx = ctx or context()
    def base(entity, event):
        fields = PATIENT["fields"] if entity == "patient" else ENCOUNTER["fields"]
        result = {f["name"]: None for f in fields}
        result.update({
            "source_system": "johns-creek-hl7",
            "source_version": "HL7v2.5.1",
            "source_batch_id": ctx.request_id,
            "source_ingest_date": ctx.source_ingest_date,
            "source_file": (
                f"clinical/v1/{ctx.hospital_id}/{ctx.feed_id}/{ctx.request_id}"
                f"/HL7_V2/hl7/visit-1-{event}.hl7"
            ),
            "source_file_sha256": "b" * 64,
            "source_file_size_bytes": 405,
            "adapter_name": "hl7apy",
            "adapter_version": "1.3.5",
            "canonical_version": "v1",
            "processing_run_id": ctx.processing_run_id,
            "processed_at": ctx.processed_at,
        })
        return result
    p = base("patient", "A01")
    p.update(source_record_id="patient-1", birth_date=date(1981, 2, 3),
             gender_code="female", race_code="2028-9", ethnicity_code="2135-2")
    e = base("encounter", "A03")
    e.update(source_encounter_id="visit-1", source_person_id="patient-1",
             start_datetime=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
             end_datetime=datetime(2026, 11, 3, 12, 0, tzinfo=UTC),
             encounter_class="inpatient", source_code="IMP")
    return p, e


def plan(patients=None, encounters=None, ctx=None, **kwargs):
    c = ctx or context()
    p, e = rows(c)
    return prepare_hl7_canonical_handoff(
        [p] if patients is None else patients,
        [e] if encounters is None else encounters,
        context=c, patient_contract_bytes=RAW_PATIENT,
        encounter_contract_bytes=RAW_ENCOUNTER, **kwargs)


class HL7SilverDQHandoffTests(unittest.TestCase):
    def test_positive_uses_shared_namespaced_batch_identity_and_contract(self):
        ctx = context()
        raw_p, raw_e = rows(ctx)
        result = plan(ctx=ctx, patients=[raw_p], encounters=[raw_e])
        self.assertEqual(result.status, "CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED")
        self.assertEqual(result.metrics["patient_accepted"], 1)
        self.assertEqual(result.metrics["encounter_accepted"], 1)
        self.assertEqual(result.metrics["patient_quarantined"], 0)
        self.assertEqual(result.patient.accepted[0]["source_system"], ctx.namespaced_source_system)
        self.assertEqual(result.encounter.accepted[0]["source_batch_id"], ctx.source_batch_id)
        self.assertNotEqual(ctx.source_batch_id, ctx.request_id)
        self.assertEqual(validate_row(result.patient.accepted[0], PATIENT), ())
        self.assertEqual(validate_row(result.encounter.accepted[0], ENCOUNTER), ())
        self.assertEqual(raw_p["source_system"], "johns-creek-hl7")
        self.assertEqual(raw_e["source_batch_id"], ctx.request_id)

    def test_same_source_deterministic_and_explicitly_no_publication(self):
        a, b = plan(), plan()
        self.assertEqual(a, b)
        self.assertNotIn("SILVER_APPROVED", a.status)
        self.assertFalse(hasattr(a, "publish"))
        self.assertFalse(hasattr(a, "publication_id"))

    def test_quarantine_incompatible_patient_birth_date_and_hold_all(self):
        p, e = rows()
        p["birth_date"] = None
        result = plan(patients=[p], encounters=[e])
        self.assertEqual(result.status, "HOLD_DQ_NO_SILVER_APPROVAL")
        self.assertEqual(result.metrics["patient_quarantined"], 1)
        self.assertEqual(result.metrics["encounter_rejected"], 1)

    def test_quarantine_encounter_end_before_start(self):
        p, e = rows()
        e["end_datetime"] = e["start_datetime"].replace(day=1)
        e["start_datetime"] = e["start_datetime"].replace(day=3)
        result = plan(patients=[p], encounters=[e])
        self.assertEqual(result.status, "HOLD_DQ_NO_SILVER_APPROVAL")
        self.assertEqual(result.metrics["encounter_quarantined"], 1)

    def test_quarantine_unknown_class_and_missing_required_field(self):
        p, e = rows()
        e["encounter_class"] = "UNMAPPED"
        a = plan(patients=[p], encounters=[e])
        self.assertEqual(a.status, "HOLD_DQ_NO_SILVER_APPROVAL")
        p["gender_code"] = None
        b = plan(patients=[p], encounters=[e])
        self.assertEqual(b.metrics["patient_quarantined"], 1)

    def test_reject_duplicate_patient_primary_key(self):
        p, e = rows()
        result = plan(patients=[p, dict(p)], encounters=[e])
        self.assertEqual(result.status, "HOLD_DQ_NO_SILVER_APPROVAL")
        self.assertEqual(result.metrics["patient_rejected"], 2)
        self.assertEqual(result.metrics["encounter_rejected"], 1)

    def test_reject_orphan_encounter(self):
        p, e = rows()
        e["source_person_id"] = "foreign-person"
        result = plan(patients=[p], encounters=[e])
        self.assertEqual(result.status, "HOLD_DQ_NO_SILVER_APPROVAL")
        self.assertEqual(result.metrics["encounter_rejected"], 1)

    def test_empty_or_partial_batch_holds(self):
        self.assertEqual(plan(patients=[]).status, "HOLD_DQ_NO_SILVER_APPROVAL")
        self.assertEqual(plan(encounters=[]).status, "HOLD_DQ_NO_SILVER_APPROVAL")

    def test_wrong_request_hospital_version_or_origin_holds(self):
        p, e = rows()
        for k,v in (
            ("source_batch_id", "other"), ("source_system", "foreign-source"),
            ("adapter_version", "99.0"), ("processing_run_id", "wrong"),
            ("source_file", "clinical/v1/foreign/unsafe.hl7"),
            ("source_file_sha256", "bad"),
        ):
            with self.subTest(k=k), self.assertRaises(HL7HandoffHold):
                plan(patients=[dict(p, **{k:v})], encounters=[e])
        wrong_context = context()
        from dataclasses import replace
        with self.assertRaises(HL7HandoffHold):
            plan(ctx=replace(wrong_context, hospital_id="foreign-hospital"))

    def test_pinned_contract_bytes_reject_tamper(self):
        c = context()
        p, e = rows(c)
        with self.assertRaisesRegex(ValueError, "CONTRACT_SHA256_MISMATCH"):
            prepare_hl7_canonical_handoff(
                [p], [e], context=c, patient_contract_bytes=RAW_PATIENT+b" ",
                encounter_contract_bytes=RAW_ENCOUNTER)

    def test_naive_spark_timestamp_requires_explicit_verified_utc(self):
        p, e = rows()
        p["processed_at"] = p["processed_at"].replace(tzinfo=None)
        e["processed_at"] = e["processed_at"].replace(tzinfo=None)
        e["start_datetime"] = e["start_datetime"].replace(tzinfo=None)
        e["end_datetime"] = e["end_datetime"].replace(tzinfo=None)
        with self.assertRaises(HL7HandoffHold):
            plan(patients=[p], encounters=[e])
        result = plan(patients=[p], encounters=[e], spark_timestamp_timezone="UTC")
        self.assertEqual(result.status, "CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED")
        self.assertEqual(result.encounter.accepted[0]["start_datetime"].tzinfo, UTC)

    def test_changed_processing_time_and_invalid_provenance_hold(self):
        p, e = rows()
        p["processed_at"] = p["processed_at"].replace(hour=12)
        with self.assertRaises(HL7HandoffHold):
            plan(patients=[p], encounters=[e])

    def test_synthetic_row_no_persistent_or_cloud_side_effect_api(self):
        import ast
        src = (ROOT / "local-data-platform/spark/apps/hl7/silver_handoff.py").read_text()
        tree=ast.parse(src)
        banned = {"open","remove","unlink","mkdir","delete","write","saveAsTable",
                  "upload_blob","download_blob","SparkSession","getOrCreate","sql"}
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        attrs = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse((calls|attrs)&banned)


if __name__ == "__main__":
    unittest.main()
