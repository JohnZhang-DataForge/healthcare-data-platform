"""Synthetic offline HL7 Silver -> existing Candidate/Gold/Replay interface tests.

These assert code contract only. They do not claim any Fabric physical writes.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import copy
import hashlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared-data-engine/src"))
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))

from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.canonical.validation import load_pinned_contract
from healthcare_data_engine.identity.candidate_handoff import (
    CandidatePersonId, CandidateVisitId, PersonVisitCandidateHandoff)
from healthcare_data_engine.mapping.omop.candidate_publication import FrozenCandidateScope
import hl7_commit as subject

PATIENT_CONTRACT = (
    ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes()
ENCOUNTER_CONTRACT = (
    ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes()


def fixture():
    ctx = BatchContext(
        hospital_id=subject.HL7_HOSPITAL,
        feed_id=subject.HL7_FEED,
        source_system=subject.HL7_SOURCE,
        request_id="johnscreek-hl7-gh-12345678901",
        manifest_sha256="a" * 64,
        processing_version="hl7-canonical-source-v1",
        processing_run_id="hl7-run-001",
        source_version=subject.HL7_FORMAT,
        source_ingest_date=date(2026, 11, 7),
        processed_at=datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc),
        adapter_version=subject.HL7_ADAPTER,
    )
    publication = "p" * 64
    identity = "f" * 64
    scope = FrozenCandidateScope(
        hospital_id=ctx.hospital_id, feed_id=ctx.feed_id,
        source_system=ctx.namespaced_source_system,
        request_id=ctx.request_id, source_batch_id=ctx.source_batch_id,
        manifest_sha256=ctx.manifest_sha256,
        silver_processing_version=ctx.processing_version,
        silver_publication_id=publication, mapping_sha256="b" * 64,
        identity_snapshot_fingerprint=identity,
        patient_count=1, encounter_count=1,
        provisional_person_count=1, provisional_visit_count=1,
    )
    person = CandidatePersonId(
        ctx.hospital_id, ctx.namespaced_source_system,
        "patient-1", 1, "PROVISIONAL")
    visit = CandidateVisitId(
        ctx.hospital_id, ctx.namespaced_source_system,
        "visit-1", "patient-1", 1, 1, "PROVISIONAL", "PROVISIONAL")
    handoff = PersonVisitCandidateHandoff(
        person_lookup=(person,), batch_persons=(person,),
        batch_visits=(visit,), hospital_id=ctx.hospital_id,
        source_system=ctx.namespaced_source_system,
        source_batch_id=ctx.source_batch_id,
        manifest_sha256=ctx.manifest_sha256,
        processing_version=ctx.processing_version,
        silver_publication_id=publication,
        snapshot_fingerprint=identity,
    )
    prefix = ("clinical/v1/" + ctx.hospital_id + "/" + ctx.feed_id + "/" +
              ctx.request_id + "/HL7_V2/hl7/")
    common = dict(
        source_system=ctx.namespaced_source_system,
        source_batch_id=ctx.source_batch_id,
        source_version=subject.HL7_FORMAT,
        adapter_name="hl7apy",
        adapter_version=subject.HL7_ADAPTER, canonical_version="v1",
        source_file_sha256="c" * 64,
    )
    base_fields = dict(
        source_ingest_date=ctx.source_ingest_date,
        source_file_size_bytes=405,
        processing_run_id=ctx.processing_run_id,
        processed_at=ctx.processed_at,
    )
    patient = {
        f["name"]: None
        for f in load_pinned_contract(PATIENT_CONTRACT, "patient")["fields"]
    }
    patient.update(common, **base_fields)
    patient.update(
        source_file=prefix + "patient-1-A01.hl7",
        source_record_id="patient-1",
        birth_date=date(1981, 2, 3),
        gender_code="female", race_code="2028-9",
        ethnicity_code="2135-2",
    )
    encounter = {
        f["name"]: None
        for f in load_pinned_contract(ENCOUNTER_CONTRACT, "encounter")["fields"]
    }
    encounter.update(common, **base_fields)
    encounter.update(
        source_file=prefix + "visit-1-A03.hl7",
        source_encounter_id="visit-1", source_person_id="patient-1",
        start_datetime=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
        end_datetime=datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc),
        encounter_class="inpatient", source_code="IMP",
    )
    approval = {
        "source_batch_id": ctx.source_batch_id,
        "manifest_sha256": ctx.manifest_sha256,
        "processing_version": ctx.processing_version,
        "publication_id": publication,
        "patient_count": 1, "encounter_count": 1, "quarantine_count": 0,
        "patient_contract_sha256": hashlib.sha256(PATIENT_CONTRACT).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(ENCOUNTER_CONTRACT).hexdigest(),
        "source_preservation_strategy": subject.SOURCE_PRESERVATION,
        "status": "SILVER_APPROVED",
    }
    physical = {
        "canonical_patient": [patient],
        "canonical_encounter": [encounter],
        "silver_approval": [approval],
    }
    args = dict(
        context=ctx, scope=scope, handoff=handoff,
        patient_contract_bytes=PATIENT_CONTRACT,
        encounter_contract_bytes=ENCOUNTER_CONTRACT,
        read_silver_physical=Mock(side_effect=lambda: copy.deepcopy(physical)),
        connection=object(), independent_connection=lambda: object(),
        single_writer_fence=lambda: True, release_gate=lambda _: True,
        read_candidate_physical=Mock(), read_warehouse_physical=Mock(),
        mapping_version="hl7-vocabulary-reviewed-v1",
        writer_version="existing-warehouse-writer",
        technical_evidence_sha256="e" * 64,
    )
    return args, physical


class HL7GoldHandoffTests(unittest.TestCase):
    def test_canonical_silver_twice_then_existing_gold_writer(self):
        args, _ = fixture()
        with patch.object(subject, "commit_verified_fhir_batch",
                          return_value="GOLD_COMMITTED_AND_INDEPENDENT_READBACK_PASS") as writer:
            result = subject.commit_verified_hl7_batch(**args)
            self.assertEqual(result, "GOLD_COMMITTED_AND_INDEPENDENT_READBACK_PASS")
            self.assertEqual(args["read_silver_physical"].call_count, 2)
            writer.assert_called_once()
            passed = writer.call_args.kwargs
            for field in ("scope", "handoff", "read_candidate_physical",
                          "read_warehouse_physical", "single_writer_fence",
                          "release_gate", "independent_connection"):
                self.assertIs(passed[field], args[field])

    def test_replay_delegates_existing_independent_sql_skip(self):
        args, _ = fixture()
        with patch.object(subject, "commit_verified_fhir_batch",
                          return_value="GOLD_VERIFIED_REPLAY_SKIP") as writer:
            self.assertEqual(subject.commit_verified_hl7_batch(**args),
                             "GOLD_VERIFIED_REPLAY_SKIP")
            writer.assert_called_once()

    def test_source_identity_mismatch_blocks_before_physical_access(self):
        for field, value in (
            ("source_system", "synthea-fhir"),
            ("source_version", "FHIR_R4"),
            ("hospital_id", "foreign-hospital"),
            ("adapter_version", "9.9"),
        ):
            args, _ = fixture()
            args["context"] = replace(args["context"], **{field: value})
            with self.subTest(field=field), patch.object(
                    subject, "commit_verified_fhir_batch") as writer:
                with self.assertRaises(subject.HL7CommitHold):
                    subject.commit_verified_hl7_batch(**args)
                args["read_silver_physical"].assert_not_called()
                writer.assert_not_called()

    def test_changed_silver_processing_scope_holds(self):
        args, _ = fixture()
        args["scope"] = replace(args["scope"],
                                silver_processing_version="wrong")
        with patch.object(subject, "commit_verified_fhir_batch") as writer:
            with self.assertRaisesRegex(
                    subject.HL7CommitHold, "SCOPE_DRIFT"):
                subject.commit_verified_hl7_batch(**args)
            writer.assert_not_called()

    def test_physical_readback_changed_between_two_connections_holds(self):
        args, first = fixture()
        second = copy.deepcopy(first)
        second["canonical_patient"][0]["source_file_sha256"] = "d" * 64
        args["read_silver_physical"] = Mock(
            side_effect=[copy.deepcopy(first), second])
        with patch.object(subject, "commit_verified_fhir_batch") as writer:
            with self.assertRaisesRegex(
                    subject.HL7CommitHold, "TWO_PHYSICAL_READS_DISAGREE"):
                subject.commit_verified_hl7_batch(**args)
            writer.assert_not_called()

    def test_approval_dq_or_silver_source_tamper_holds(self):
        for selector, changed in (
            ("status", "CANDIDATE_ONLY"),
            ("quarantine_count", 1),
            ("source_preservation_strategy", "DELTA_RAW_SNAPSHOT_V1"),
            ("manifest_sha256", "d" * 64),
            ("publication_id", "other"),
        ):
            args, physical = fixture()
            physical["silver_approval"][0][selector] = changed
            args["read_silver_physical"] = Mock(return_value=physical)
            with self.subTest(selector=selector), patch.object(
                    subject, "commit_verified_fhir_batch") as writer:
                with self.assertRaisesRegex(subject.HL7CommitHold,
                                            "APPROVAL_OR_COUNTS_DRIFT"):
                    subject.commit_verified_hl7_batch(**args)
                writer.assert_not_called()

    def test_bad_fk_cross_hospital_and_non_hl7_rows_hold(self):
        for section, field, value in (
            ("canonical_encounter", "source_person_id", "foreign"),
            ("canonical_patient", "source_system", "other:tenant:feed"),
            ("canonical_patient", "source_file", "wrong/visit.hl7"),
            ("canonical_patient", "adapter_name", "fhir_r4"),
            ("canonical_patient", "source_batch_id", "not-this-batch"),
        ):
            args, physical = fixture()
            physical[section][0][field] = value
            args["read_silver_physical"] = Mock(return_value=physical)
            with self.subTest(section=section, field=field), patch.object(
                    subject, "commit_verified_fhir_batch") as writer:
                with self.assertRaises(subject.HL7CommitHold):
                    subject.commit_verified_hl7_batch(**args)
                writer.assert_not_called()

    def test_full_canonical_contract_validation_rejects_missing_fact(self):
        args, physical = fixture()
        physical["canonical_patient"][0]["birth_date"] = None
        args["read_silver_physical"] = Mock(return_value=physical)
        with patch.object(subject, "commit_verified_fhir_batch") as writer:
            with self.assertRaisesRegex(subject.HL7CommitHold,
                                        "CANONICAL_CONTRACT_INVALID"):
                subject.commit_verified_hl7_batch(**args)
            writer.assert_not_called()

    def test_unverifiable_silver_or_contract_holds(self):
        args, _ = fixture()
        args["read_silver_physical"] = Mock(side_effect=RuntimeError("credentials"))
        with patch.object(subject, "commit_verified_fhir_batch") as writer:
            with self.assertRaisesRegex(subject.HL7CommitHold,
                                        "SILVER_PHYSICAL_READ_FAILED"):
                subject.commit_verified_hl7_batch(**args)
            writer.assert_not_called()
        args, _ = fixture()
        args["patient_contract_bytes"] += b" "
        with patch.object(subject, "commit_verified_fhir_batch") as writer:
            with self.assertRaisesRegex(subject.HL7CommitHold,
                                        "PINNED_CANONICAL_CONTRACT_DRIFT"):
                subject.commit_verified_hl7_batch(**args)
            writer.assert_not_called()

    def test_no_caller_supplied_approval_or_write_flags(self):
        args, _ = fixture()
        with self.assertRaises(TypeError):
            subject.commit_verified_hl7_batch(**args, approved=True)
        with self.assertRaises(TypeError):
            subject.commit_verified_hl7_batch(**args, physical_readback_pass=True)


if __name__ == "__main__":
    unittest.main()
