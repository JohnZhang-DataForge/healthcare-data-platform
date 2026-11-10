"""G5 Warehouse Gold technical evidence: no two human reviewers required.

SOURCE/OFFLINE only: never connects to Warehouse or invokes actual SQL DML.
Historical legacy signed-v1 layout remains compatible, but CURRENT G5
technical-only evidence cannot masquerade as two reviewers.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))

from identity_plan import BatchFence, IdentityKey
from gold_transaction import GoldBatch, GoldHold, _require_batch, execute_gold_transaction


def technical_batch():
    hospital, source = "synthetic-hospital", "synthetic-fhir-source"
    fence = BatchFence(
        hospital, source, "synthetic-batch",
        "a" * 64, "b" * 64, "1.0", 1, 1)
    patient = IdentityKey("PERSON", hospital, source, "patient-one")
    encounter = IdentityKey(
        "VISIT_OCCURRENCE", hospital, source, "encounter-one")
    return GoldBatch(
        fence=fence, identities=((patient, 1), (encounter, 1)),
        persons=({
            "person_id": 1, "person_source_value": "patient-one",
            "gender_concept_id": 8507, "race_concept_id": 8657,
            "ethnicity_concept_id": 38003564, "year_of_birth": 1980,
            "identity_state": "PROVISIONAL",
        },),
        visits=({
            "visit_occurrence_id": 1, "person_id": 1,
            "source_system": source, "source_encounter_id": "encounter-one",
            "source_person_id": "patient-one",
            "visit_concept_id": 9201, "visit_type_concept_id": 44818518,
            "visit_start_date": date(2026, 1, 1),
            "visit_end_date": date(2026, 1, 2),
            "identity_state": "PROVISIONAL",
            "parent_identity_state": "PROVISIONAL",
        },),
        mapping_version="synthetic-v1",
        technical_evidence_sha256="d" * 64,
        candidate_approval_sha256="e" * 64,
    )


class GoldTechnicalEvidenceTests(unittest.TestCase):
    def test_technical_only_batch_valid_without_reviewers(self):
        batch = technical_batch()
        _require_batch(batch)
        self.assertIsNone(batch.clinical_review_sha256)
        self.assertIsNone(batch.license_review_sha256)
        self.assertEqual(batch.technical_evidence_sha256, "d" * 64)

    def test_no_evidence_or_fake_human_mixing_rejected(self):
        batch = technical_batch()
        with self.assertRaisesRegex(GoldHold, "EVIDENCE_NOT_PRESENT"):
            _require_batch(replace(batch, technical_evidence_sha256=None))
        for patch in (
            {"clinical_review_sha256": "c" * 64},
            {"license_review_sha256": "c" * 64},
            {"technical_evidence_sha256": "fake"},
        ):
            with self.subTest(patch=patch):
                with self.assertRaisesRegex(GoldHold, "FAKE_REVIEW|EVIDENCE"):
                    _require_batch(replace(batch, **patch))

    def test_legacy_v1_contract_remains_optional(self):
        batch = replace(
            technical_batch(), technical_evidence_sha256=None,
            clinical_review_sha256="c" * 64,
            license_review_sha256="d" * 64)
        _require_batch(batch)

    def test_actual_source_concept_and_fk_validation_still_required(self):
        batch = technical_batch()
        wrong = dict(batch.persons[0], race_concept_id=0)
        with self.assertRaisesRegex(GoldHold, "PERSON_MAP_OR_PROFILE"):
            _require_batch(replace(batch, persons=(wrong,)))
        bad_visit = dict(batch.visits[0], person_id=999)
        with self.assertRaisesRegex(GoldHold, "VISIT_MAP_FK"):
            _require_batch(replace(batch, visits=(bad_visit,)))

    def test_gold_write_stays_halted_without_trusted_technical_release(self):
        batch = technical_batch()
        conn = Mock()
        with self.assertRaisesRegex(GoldHold, "RELEASE_OR_SINGLE_WRITER"):
            execute_gold_transaction(
                conn, batch, single_writer_fence=lambda: True,
                release_gate=lambda _batch: False)
        conn.cursor.assert_not_called()
        with self.assertRaisesRegex(GoldHold, "RELEASE_OR_SINGLE_WRITER"):
            execute_gold_transaction(
                conn, batch, single_writer_fence=lambda: False,
                release_gate=lambda _batch: True)
        conn.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
