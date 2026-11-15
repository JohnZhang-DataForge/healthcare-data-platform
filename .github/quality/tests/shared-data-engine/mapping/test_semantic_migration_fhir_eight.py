"""Fresh eight-resource synthetic FHIR regression for semantic API migration.

Source-only / no Fabric / no clinical data / no writes. The same logical
source request is replay-stable; new request IDs produce separate batch IDs.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from healthcare_data_engine import (
    BatchContext, SourceObject, parse_fhir_resources,
    normalize_fhir_patient, normalize_fhir_encounter,
    load_pinned_contract, reconcile_patient_encounter,
    PublicationRecord, decide_replay,
)

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
FHIR = ROOT / ".github/quality/fixtures/fhir_r4/semantic-migration-20261115-eight-resources.json"
PATIENT_CONTRACT = ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json"
ENCOUNTER_CONTRACT = ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json"


def fixture_bytes() -> bytes:
    return FHIR.read_bytes()


def source_context(request: str = "semantic-migration-20261115-batch-a") -> BatchContext:
    return BatchContext(
        hospital_id="hospital-a", feed_id="fhir-r4",
        source_system="synthetic-fhir", request_id=request,
        manifest_sha256=hashlib.sha256(fixture_bytes()).hexdigest(),
        processing_version="semantic-migration-canonical-v1",
        processing_run_id="synthetic-readonly-run-20261115",
        source_version="R4",
        source_ingest_date=date(2026, 11, 15),
        processed_at=datetime(2026, 11, 15, 13, 0, tzinfo=timezone.utc),
    )


def canonicalize(context: BatchContext):
    source = SourceObject.from_bytes("semantic-migration-eight.json", fixture_bytes())
    parsed = parse_fhir_resources((source,), context)
    patient = normalize_fhir_patient(
        parsed, load_pinned_contract(PATIENT_CONTRACT.read_bytes(), "patient"),
        context,
    )
    encounter = normalize_fhir_encounter(
        parsed, load_pinned_contract(ENCOUNTER_CONTRACT.read_bytes(), "encounter"),
        context,
    )
    return parsed, reconcile_patient_encounter(patient, encounter, context)


class NewSyntheticFhirMigrationTests(unittest.TestCase):
    def test_new_four_patients_four_encounters_canonical_fk(self):
        ctx = source_context()
        raw = json.loads(fixture_bytes())
        self.assertEqual(raw["resourceType"], "Bundle")
        self.assertEqual(len(raw["entry"]), 8)
        parsed, result = canonicalize(ctx)
        self.assertEqual(parsed.metrics, {"accepted": 8, "rejected": 0})
        self.assertEqual(result.metrics, {
            "patient_accepted": 4, "encounter_accepted": 4,
            "patient_rejected": 0, "encounter_rejected": 0,
            "patient_quarantined": 0, "encounter_quarantined": 0,
        })
        keys = {p["source_record_id"] for p in result.patient.accepted}
        self.assertEqual(len(keys), 4)
        self.assertEqual(
            {e["source_person_id"] for e in result.encounter.accepted}, keys)
        self.assertEqual(
            {x["source_batch_id"] for x in (
                *result.patient.accepted, *result.encounter.accepted)},
            {ctx.source_batch_id},
        )

    def test_same_batch_is_replay_stable_new_request_is_independent(self):
        ctx = source_context()
        _, original = canonicalize(ctx)
        _, repeated = canonicalize(source_context())
        self.assertEqual(original.patient.accepted, repeated.patient.accepted)
        self.assertEqual(original.encounter.accepted, repeated.encounter.accepted)
        receipt = PublicationRecord(
            ctx.hospital_id, ctx.feed_id, ctx.source_system,
            ctx.request_id, ctx.manifest_sha256, ctx.processing_version,
            "synthetic-test-publication", True,
        )
        self.assertEqual(decide_replay(ctx, [receipt]), "SKIP")
        self.assertEqual(decide_replay(ctx, [receipt], unknown_ack=True),
                         "VERIFY_READONLY")
        separate = source_context("semantic-migration-20261115-batch-b")
        self.assertNotEqual(ctx.source_batch_id, separate.source_batch_id)
        _, other = canonicalize(separate)
        self.assertNotEqual(original.patient.accepted, other.patient.accepted)

    def test_bad_reference_stays_rejected_and_never_fabricated(self):
        data = json.loads(fixture_bytes())
        data["entry"][-1]["resource"]["subject"]["reference"] = "Patient/missing"
        ctx = source_context()
        raw = json.dumps(data, separators=(",", ":")).encode()
        parsed = parse_fhir_resources((
            SourceObject.from_bytes("synthetic-bad-reference.json", raw),
        ), ctx)
        patients = normalize_fhir_patient(
            parsed, load_pinned_contract(PATIENT_CONTRACT.read_bytes(), "patient"), ctx)
        encounters = normalize_fhir_encounter(
            parsed, load_pinned_contract(ENCOUNTER_CONTRACT.read_bytes(), "encounter"), ctx)
        result = reconcile_patient_encounter(patients, encounters, ctx)
        self.assertEqual(result.metrics["patient_accepted"], 4)
        self.assertEqual(result.metrics["encounter_accepted"], 3)
        self.assertEqual(result.metrics["encounter_rejected"], 1)


if __name__ == "__main__":
    unittest.main()
