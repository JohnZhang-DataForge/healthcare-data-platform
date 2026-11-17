"""G5 Warehouse Gold technical evidence: no two human reviewers required.

SOURCE/OFFLINE only: never connects to Warehouse or invokes actual SQL DML.
Historical legacy signed-v1 layout remains compatible, but CURRENT G5
technical-only evidence cannot masquerade as two reviewers.
"""
from __future__ import annotations

from dataclasses import replace
import copy
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))

from identity_plan import BatchFence, IdentityKey
from gold_transaction import (
    GoldBatch, GoldHold, _require_batch, _candidate_rows_digest,
    execute_gold_transaction, prepare_gold_batch_from_candidate_readback,
    commit_gold_from_candidate_readback, PERSON_COLS, VISIT_COLS,
)
import gold_transaction as tx

sys.path.insert(0, str(ROOT / "shared-data-engine/src"))
from healthcare_data_engine.identity.candidate_handoff import (
    CandidatePersonId, CandidateVisitId, PersonVisitCandidateHandoff,
)
from healthcare_data_engine.mapping.omop.candidate_publication import (
    FrozenCandidateScope,
)


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


def candidate_to_gold_fixture():
    hospital, feed = "synthetic-hospital", "hl7"
    source = f"hl7:{hospital}:{feed}"
    technical = "e" * 64
    people = tuple(CandidatePersonId(
        hospital, source, f"patient-{i:02d}", 1000 + i, "PROVISIONAL"
    ) for i in range(1, 11))
    visits = tuple(CandidateVisitId(
        hospital, source, f"encounter-{i:02d}", f"patient-{i:02d}",
        2000 + i, 1000 + i, "PROVISIONAL", "PROVISIONAL"
    ) for i in range(1, 8))
    handoff = PersonVisitCandidateHandoff(
        person_lookup=people, batch_persons=people, batch_visits=visits,
        hospital_id=hospital, source_system=source, source_batch_id="hl7-batch-10",
        manifest_sha256="a" * 64, processing_version="canonical-v1",
        silver_publication_id="silver-approval-10",
        snapshot_fingerprint="b" * 64,
    )
    scope = FrozenCandidateScope(
        hospital_id=hospital, feed_id=feed, source_system=source,
        request_id="hl7-request-10", source_batch_id="hl7-batch-10",
        manifest_sha256="a" * 64, silver_processing_version="canonical-v1",
        silver_publication_id="silver-approval-10", mapping_sha256="c" * 64,
        identity_snapshot_fingerprint="b" * 64,
        patient_count=10, encounter_count=7,
        provisional_person_count=10, provisional_visit_count=7,
    )
    person_rows = []
    for person in people:
        row = {name: None for name in PERSON_COLS}
        row.update(person_id=person.person_id,
                   person_source_value=person.source_business_key,
                   gender_concept_id=8507, race_concept_id=8657,
                   ethnicity_concept_id=38003564, year_of_birth=1980,
                   identity_state=person.state)
        person_rows.append(row)
    visit_rows = []
    for visit in visits:
        row = {name: None for name in VISIT_COLS}
        row.update(
            visit_occurrence_id=visit.visit_occurrence_id,
            person_id=visit.person_id,
            visit_concept_id=9201,
            visit_type_concept_id=44818518,
            visit_start_date=date(2026, 11, 1),
            visit_end_date=date(2026, 11, 2),
            source_system=source,
            source_encounter_id=visit.source_encounter_id,
            source_person_id=visit.source_person_id,
            source_batch_id=scope.source_batch_id,
            identity_state=visit.state,
            parent_identity_state=visit.parent_state,
            source_code="ADT",
            source_description="Synthetic admission",
            raw_publish_run_id="synthetic-batch",
        )
        visit_rows.append(row)
    approval = {
        "scope_receipt_key": scope.receipt_key,
        "source_batch_id": scope.source_batch_id,
        "mapping_sha256": scope.mapping_sha256,
        "snapshot_fingerprint": scope.identity_snapshot_fingerprint,
        "evidence_contract": "CANDIDATE_TECHNICAL_VOCABULARY_IDENTITY_V1",
        "technical_evidence_sha256": technical,
        "person_count": 10, "visit_count": 7,
        "person_sha256": _candidate_rows_digest(person_rows, "person_id", 10),
        "visit_sha256": _candidate_rows_digest(visit_rows, "visit_occurrence_id", 7),
        "status": "CANDIDATE_APPROVED",
    }
    return dict(
        scope=scope, handoff=handoff, candidate_approval=approval,
        person_rows=person_rows, visit_rows=visit_rows,
        mapping_version="synthetic-hl7-v1", writer_version="test-writer-1",
        technical_evidence_sha256=technical,
    )


class SharedCandidateToGoldBusinessTests(unittest.TestCase):
    def test_ten_patient_seven_visit_candidate_builds_one_existing_gold_batch(self):
        args = candidate_to_gold_fixture()
        batch = prepare_gold_batch_from_candidate_readback(**args)
        self.assertEqual((batch.fence.person_count, batch.fence.visit_count), (10, 7))
        self.assertEqual(len(batch.identities), 17)
        self.assertEqual(len(batch.persons), 10)
        self.assertEqual(len(batch.visits), 7)
        self.assertEqual({v["person_id"] for v in batch.visits},
                         {1000 + i for i in range(1, 8)})
        self.assertTrue(all(p["identity_state"] == "PROVISIONAL"
                            for p in batch.persons))
        self.assertEqual(batch.technical_evidence_sha256, "e" * 64)
        self.assertIsNone(batch.clinical_review_sha256)
        self.assertIsNone(batch.license_review_sha256)
        _require_batch(batch)

    def test_candidate_digest_is_order_independent_but_full_row_bound(self):
        args = candidate_to_gold_fixture()
        self.assertEqual(
            _candidate_rows_digest(args["visit_rows"], "visit_occurrence_id", 7),
            _candidate_rows_digest(list(reversed(args["visit_rows"])),
                                   "visit_occurrence_id", 7))
        changed = copy.deepcopy(args)
        changed["visit_rows"][0]["source_description"] = "Tampered"
        self.assertRaisesRegex(
            GoldHold, "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT",
            prepare_gold_batch_from_candidate_readback, **changed)
        duplicate = copy.deepcopy(args)
        duplicate["person_rows"][1]["person_id"] = duplicate["person_rows"][0]["person_id"]
        self.assertRaisesRegex(
            GoldHold, "IDS_INVALID_OR_DUPLICATE",
            prepare_gold_batch_from_candidate_readback, **duplicate)

    def test_physical_candidate_approval_or_identity_drift_blocks_transaction(self):
        baseline = candidate_to_gold_fixture()
        for mutate, error in (
            (lambda a: a["candidate_approval"].update(status="HOLD"),
             "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT"),
            (lambda a: a["candidate_approval"].update(
                technical_evidence_sha256="f" * 64), "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT"),
            (lambda a: a["candidate_approval"].update(
                clinical_review_sha256="f" * 64), "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT"),
            (lambda a: a["person_rows"][0].update(
                person_source_value="other-patient"), "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT"),
            (lambda a: a["visit_rows"][0].update(
                source_batch_id="foreign-batch"), "APPROVAL_OR_PHYSICAL_DIGEST_DRIFT"),
        ):
            with self.subTest(error=error):
                bad = copy.deepcopy(baseline)
                mutate(bad)
                self.assertRaisesRegex(
                    GoldHold, error, prepare_gold_batch_from_candidate_readback,
                    **bad)
        foreign_source = copy.deepcopy(baseline)
        foreign_source["visit_rows"][0]["source_system"] = "hl7:other:feed"
        foreign_source["candidate_approval"]["visit_sha256"] = _candidate_rows_digest(
            foreign_source["visit_rows"], "visit_occurrence_id", 7)
        self.assertRaisesRegex(
            GoldHold, "IDENTITY_OR_SOURCE_DRIFT",
            prepare_gold_batch_from_candidate_readback, **foreign_source)
        bad_concept = copy.deepcopy(baseline)
        bad_concept["person_rows"][0]["race_concept_id"] = 0
        bad_concept["candidate_approval"]["person_sha256"] = _candidate_rows_digest(
            bad_concept["person_rows"], "person_id", 10)
        self.assertRaisesRegex(
            GoldHold, "PERSON_MAP_OR_PROFILE",
            prepare_gold_batch_from_candidate_readback, **bad_concept)

    def test_replay_skip_first_commit_and_uncertain_ack_are_separate(self):
        args = candidate_to_gold_fixture()
        conn = Mock()
        new_connection = Mock()
        fence = lambda: True
        release = lambda b: True
        with (patch.object(tx, "independent_gold_readback", return_value=True) as read,
              patch.object(tx, "execute_gold_transaction") as execute):
            self.assertEqual(commit_gold_from_candidate_readback(
                conn, new_connection, single_writer_fence=fence,
                release_gate=release, **args), "GOLD_VERIFIED_REPLAY_SKIP")
            execute.assert_not_called()
            read.assert_called_once()
        with (patch.object(tx, "independent_gold_readback",
                           side_effect=[False, True]) as read,
              patch.object(tx, "execute_gold_transaction",
                           return_value="GOLD_COMMIT_ACK_VERIFY_INDEPENDENT_SQL_NOT_ACCEPTED") as execute):
            self.assertEqual(commit_gold_from_candidate_readback(
                conn, new_connection, single_writer_fence=fence,
                release_gate=release, **args),
                "GOLD_COMMITTED_AND_INDEPENDENT_READBACK_PASS")
            execute.assert_called_once()
            self.assertEqual(read.call_count, 2)
        with (patch.object(tx, "independent_gold_readback",
                           side_effect=RuntimeError("SQL unavailable")),
              patch.object(tx, "execute_gold_transaction") as execute):
            self.assertEqual(commit_gold_from_candidate_readback(
                conn, new_connection, single_writer_fence=fence,
                release_gate=release, **args), "GOLD_INITIAL_READBACK_UNAVAILABLE_NO_WRITE")
            execute.assert_not_called()
        with (patch.object(tx, "independent_gold_readback", return_value=False),
              patch.object(tx, "execute_gold_transaction",
                           return_value="GOLD_UNKNOWN_COMMIT_ACK_VERIFY_READONLY")):
            self.assertEqual(commit_gold_from_candidate_readback(
                conn, new_connection, single_writer_fence=fence,
                release_gate=release, **args),
                "GOLD_UNKNOWN_COMMIT_ACK_VERIFY_READONLY")
        with (patch.object(tx, "independent_gold_readback", return_value=False),
              patch.object(tx, "execute_gold_transaction",
                           return_value="GOLD_COMMIT_ACK_VERIFY_INDEPENDENT_SQL_NOT_ACCEPTED")):
            self.assertEqual(commit_gold_from_candidate_readback(
                conn, new_connection, single_writer_fence=fence,
                release_gate=release, **args),
                "GOLD_COMMIT_ACK_UNVERIFIED_READONLY_RECONCILE")

    def test_untrusted_release_and_fence_never_touch_sql(self):
        args = candidate_to_gold_fixture()
        conn = Mock()
        with patch.object(tx, "independent_gold_readback") as reader:
            for fence, release in ((lambda: False, lambda _: True),
                                   (lambda: True, lambda _: False)):
                self.assertRaisesRegex(
                    GoldHold, "RELEASE_OR_SINGLE_WRITER_HOLD",
                    commit_gold_from_candidate_readback,
                    conn, Mock(), single_writer_fence=fence,
                    release_gate=release, **args)
            reader.assert_not_called()
        conn.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
