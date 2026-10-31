"""Synthetic FHIR R4 inputs and unchanged Local v1 Contract tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from healthcare_data_engine import (
    BatchContext, SourceObject, parse_fhir_resources, normalize_fhir_patient,
    normalize_fhir_encounter, load_pinned_contract, PublicationRecord, decide_replay, reconcile_patient_encounter)
from healthcare_data_engine.canonical.validation import validate_row

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures/fhir_r4/patient_encounters_bundle.json"
PATIENT = ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json"
ENCOUNTER = ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json"


def context(hospital="hospital-a", manifest=None):
    return BatchContext(
        hospital_id=hospital, feed_id="fhir-r4", source_system="synthetic-fhir",
        request_id="request-fixture-001",
        manifest_sha256=manifest or hashlib.sha256(b"synthetic manifest v1").hexdigest(),
        processing_version="fhir0.1.0:canonical-v1:shaA",
        processing_run_id="offline-run-001", source_version="R4",
        source_ingest_date=date(2026, 10, 31),
        processed_at=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc))


def bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def source(data, **kwargs):
    return SourceObject.from_bytes("synthetic-bundle.json",
                                   json.dumps(data, sort_keys=True).encode("utf-8"), **kwargs)


def contracts():
    return (load_pinned_contract(PATIENT.read_bytes(), "patient"),
            load_pinned_contract(ENCOUNTER.read_bytes(), "encounter"))


def outcomes(data=None, ctx=None):
    ctx = ctx or context()
    parsed = parse_fhir_resources((source(data or bundle()),), ctx)
    patient_contract, encounter_contract = contracts()
    return (parsed, normalize_fhir_patient(parsed, patient_contract, ctx),
            normalize_fhir_encounter(parsed, encounter_contract, ctx))


class FhirCanonicalContractTest(unittest.TestCase):
    def test_good_bundle_urn_uuid_relative_reference_and_local_contract(self):
        parsed, patients, encounters = outcomes()
        self.assertEqual(parsed.metrics, {"accepted": 3, "rejected": 0})
        self.assertEqual(patients.metrics["accepted"], 1)
        self.assertEqual(encounters.metrics["accepted"], 2)
        p = patients.accepted[0]
        self.assertEqual(p["source_system"], "synthetic-fhir:hospital-a:fhir-r4")
        self.assertEqual(p["source_record_id"], "patient-1")
        self.assertEqual(p["birth_date"], date(1992, 1, 5))
        self.assertEqual(p["race_code"], "2106-3")
        self.assertEqual(p["ethnicity_code"], "2186-5")
        self.assertEqual({x["source_person_id"] for x in encounters.accepted}, {"patient-1"})
        self.assertEqual(validate_row(p, contracts()[0]), ())
        self.assertEqual(validate_row(encounters.accepted[0], contracts()[1]), ())

    def test_patient_missing_dob_gender_race_ethnicity_is_quarantined_not_fabricated(self):
        for key in ("birthDate", "gender", "extension"):
            with self.subTest(key=key):
                data = bundle()
                data["entry"][0]["resource"].pop(key)
                _, p, e = outcomes(data)
                self.assertFalse(p.accepted)
                self.assertEqual(p.quarantined[0].reason, "PATIENT_CANONICAL_V1_INCOMPATIBLE")
                # Encounter FK resolution is syntactic, not approval: caller must
                # reconcile accepted Patient keys before Silver writes.
                self.assertEqual(len(e.accepted), 2)

    def test_reconciliation_rejects_fk_to_quarantined_patient(self):
        data = bundle()
        data["entry"][0]["resource"].pop("birthDate")
        _, p, e = outcomes(data)
        result = reconcile_patient_encounter(p, e, context())
        self.assertEqual(result.metrics["patient_accepted"], 0)
        self.assertEqual(result.metrics["encounter_accepted"], 0)
        self.assertEqual(result.metrics["encounter_rejected"], 2)
        self.assertEqual({x.reason for x in result.encounter.rejected},
                         {"ENCOUNTER_PATIENT_NOT_ACCEPTED"})

    def test_reconciliation_rejects_cross_namespace_and_duplicate_pk(self):
        _, p, e = outcomes()
        ctx = context()
        changed = dict(p.accepted[0], source_system="synthetic-fhir:hospital-other:fhir-r4")
        from healthcare_data_engine.quality.result import TransformResult
        invalid_p = TransformResult((changed,), (), ())
        result = reconcile_patient_encounter(invalid_p, e, ctx)
        self.assertEqual(result.patient.rejected[0].reason, "PATIENT_SOURCE_NAMESPACE_CONFLICT")
        self.assertEqual(result.metrics["encounter_accepted"], 0)
        duplicated = TransformResult((p.accepted[0], p.accepted[0]), (), ())
        duplicate = reconcile_patient_encounter(duplicated, e, ctx)
        self.assertEqual(sum(x.reason == "PATIENT_DUPLICATE_PRIMARY_KEY"
                             for x in duplicate.patient.rejected), 2)

    def test_encounter_missing_end_is_quarantined_not_fabricated(self):
        data = bundle()
        data["entry"][1]["resource"]["period"].pop("end")
        _, p, e = outcomes(data)
        self.assertEqual(len(p.accepted), 1)
        self.assertEqual(len(e.accepted), 1)
        self.assertEqual(e.quarantined[0].reason, "ENCOUNTER_CANONICAL_V1_INCOMPATIBLE")
        self.assertIn("FHIR_PERIOD_START_END_REQUIRED", e.quarantined[0].detail)

    def test_encounter_invalid_type_and_class_quarantined(self):
        for field in ("type", "class"):
            data = bundle()
            data["entry"][1]["resource"][field] = 1
            _, _, e = outcomes(data)
            self.assertEqual(len(e.quarantined), 1)

    def test_unresolved_reference_rejected(self):
        data = bundle()
        data["entry"][1]["resource"]["subject"]["reference"] = "Patient/absent"
        _, _, e = outcomes(data)
        self.assertEqual(len(e.accepted), 1)
        self.assertEqual(e.rejected[0].reason, "UNRESOLVED_PATIENT_REFERENCE")

    def test_duplicate_resource_id_all_duplicates_rejected(self):
        data = bundle()
        data["entry"].append(deepcopy(data["entry"][0]))
        parsed, p, e = outcomes(data)
        self.assertEqual(len(p.accepted), 0)
        self.assertEqual(sum(x.reason == "DUPLICATE_RESOURCE_ID" for x in parsed.rejected), 2)
        self.assertEqual(len(e.rejected), 2)

    def test_cross_hospital_object_and_meta_tag_are_rejected(self):
        ctx = context()
        wrong = source(bundle(), hospital_id="hospital-b")
        result = parse_fhir_resources((wrong,), ctx)
        self.assertEqual(result.rejected[0].reason, "CROSS_HOSPITAL_SOURCE_CONFLICT")
        data = bundle()
        data["entry"][0]["resource"]["meta"] = {
            "tag": [{"system": "urn:healthcare:hospital-id", "code": "hospital-b"}]}
        parsed, p, _ = outcomes(data, ctx)
        self.assertEqual(len(p.accepted), 0)
        self.assertIn("CROSS_HOSPITAL_RESOURCE_CONFLICT", {x.reason for x in parsed.rejected})

    def test_same_fhir_id_in_different_hospitals_never_merges(self):
        _, p1, _ = outcomes(ctx=context("hospital-a"))
        _, p2, _ = outcomes(ctx=context("hospital-b"))
        self.assertNotEqual(p1.accepted[0]["source_system"],
                            p2.accepted[0]["source_system"])
        self.assertNotEqual(p1.accepted[0]["source_batch_id"],
                            p2.accepted[0]["source_batch_id"])

    def test_invalid_sha_json_resource_type_and_id_rejected(self):
        obj = source(bundle())
        wrong = SourceObject(obj.source_file, obj.payload, "0" * 64, obj.size_bytes)
        self.assertEqual(parse_fhir_resources((wrong,), context()).rejected[0].reason,
                         "SOURCE_SHA256_MISMATCH")
        invalid_json = SourceObject.from_bytes("synthetic.json", b"{not valid")
        self.assertEqual(parse_fhir_resources((invalid_json,), context()).rejected[0].reason,
                         "INVALID_FHIR_JSON")
        data = bundle()
        data["entry"][0]["resource"]["id"] = 42
        self.assertIn("INVALID_RESOURCE_ID_TYPE",
                      {x.reason for x in parse_fhir_resources((source(data),), context()).rejected})

    def test_exact_local_contract_sha256_and_schema_drift_blocked(self):
        p, e = contracts()
        self.assertEqual(len(p["fields"]), 18)
        self.assertEqual(len(e["fields"]), 27)
        modified = PATIENT.read_bytes().replace(b'"nullable": false', b'"nullable": true', 1)
        with self.assertRaisesRegex(ValueError, "CONTRACT_SHA256_MISMATCH"):
            load_pinned_contract(modified, "patient")
        with self.assertRaisesRegex(ValueError, "CONTRACT_SHA256_MISMATCH"):
            load_pinned_contract(ENCOUNTER.read_bytes(), "patient")

    def test_replay_identities_conflict_version_drift_and_unknown_ack(self):
        ctx = context()
        self.assertEqual(decide_replay(ctx, []), "NEW")
        record = PublicationRecord(ctx.hospital_id, ctx.feed_id, ctx.source_system,
                                   ctx.request_id, ctx.manifest_sha256,
                                   ctx.processing_version, "pub-001", True)
        self.assertEqual(decide_replay(ctx, [record]), "SKIP")
        self.assertEqual(decide_replay(ctx, [record], unknown_ack=True), "VERIFY_READONLY")
        diff_manifest = context(manifest="a" * 64)
        self.assertEqual(decide_replay(diff_manifest, [record]), "HOLD_CONFLICT")
        different_version = PublicationRecord(
            record.hospital_id, record.feed_id, record.source_system, record.request_id,
            record.manifest_sha256, "different-map-version", record.publication_id, True)
        self.assertEqual(decide_replay(ctx, [different_version]), "HOLD_VERSION")
        self.assertNotEqual(ctx.source_batch_id, diff_manifest.source_batch_id)
        self.assertNotEqual(ctx.source_batch_id, record.publication_id)


if __name__ == "__main__":
    unittest.main()
