"""Offline contracts for physical FHIR Candidate -> existing Gold writer.

Mocks verify fail-closed orchestration only. These tests NEVER claim that
Fabric, OneLake, SQL COMMIT or replay ran in a live environment.
"""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))
import fhir_commit as subject
import gold_transaction as gold
from silver_identity import F2SnapshotBridge


def snapshot(fingerprint="f" * 64, physical="a" * 64):
    return F2SnapshotBridge(
        snapshot=SimpleNamespace(fingerprint=fingerprint),
        physical_snapshot_sha256=physical,
        table_sha256=(("identity_map", "b" * 64),),
    )


def params():
    candidate = {
        "person_rows": [{"person_id": 7, "person_source_value": "synthetic"}],
        "visit_rows": [{"visit_occurrence_id": 9, "person_id": 7}],
        "candidate_approval": {"status": "CANDIDATE_APPROVED"},
    }
    return dict(
        connection=object(), independent_connection=lambda: object(),
        single_writer_fence=Mock(return_value=True),
        release_gate=Mock(return_value=True),
        scope=SimpleNamespace(patient_count=1, encounter_count=1,
                              identity_snapshot_fingerprint="f" * 64),
        handoff=object(), read_candidate_physical=Mock(return_value=candidate),
        read_warehouse_physical=Mock(return_value=snapshot()),
        mapping_version="1", writer_version="1",
        technical_evidence_sha256="e" * 64,
    )


class FhirCommitTests(unittest.TestCase):
    def test_two_physical_reads_precede_new_write(self):
        args = params()
        with patch.object(subject, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            subject, "independent_gold_readback", return_value=False), patch.object(
            subject, "commit_gold_from_candidate_readback",
            return_value=subject.COMMITTED) as writer:
            self.assertEqual(subject.commit_verified_fhir_batch(**args),
                             subject.COMMITTED)
            self.assertEqual(args["read_candidate_physical"].call_count, 2)
            self.assertEqual(args["read_warehouse_physical"].call_count, 2)
            writer.assert_called_once()

    def test_caller_boolean_flags_cannot_grant_commit(self):
        with self.assertRaises(TypeError):
            subject.commit_verified_fhir_batch(
                **params(), physical_candidate_verified=True)

    def test_candidate_reopened_rows_must_match(self):
        args = params()
        first = args["read_candidate_physical"]()
        drift = dict(first)
        drift["person_rows"] = [{"person_id": 8}]
        args["read_candidate_physical"] = Mock(side_effect=[first, drift])
        with patch.object(subject, "commit_gold_from_candidate_readback") as writer:
            with self.assertRaises(subject.FhirCommitHold):
                subject.commit_verified_fhir_batch(**args)
            writer.assert_not_called()

    def test_candidate_read_failure_never_writes(self):
        args = params()
        args["read_candidate_physical"] = Mock(
            side_effect=RuntimeError("no candidate storage"))
        with patch.object(subject, "commit_gold_from_candidate_readback") as writer:
            with self.assertRaisesRegex(subject.FhirCommitHold, "READBACK_FAILED"):
                subject.commit_verified_fhir_batch(**args)
            writer.assert_not_called()

    def test_warehouse_two_snapshots_must_match_before_write(self):
        args = params()
        args["read_warehouse_physical"] = Mock(
            side_effect=[snapshot(), snapshot(physical="c" * 64)])
        with patch.object(subject, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            subject, "independent_gold_readback", return_value=False), patch.object(
            subject, "commit_gold_from_candidate_readback") as writer:
            with self.assertRaisesRegex(subject.FhirCommitHold,
                                        "TWO_SQL_SNAPSHOTS_DISAGREE"):
                subject.commit_verified_fhir_batch(**args)
            writer.assert_not_called()

    def test_sql_snapshot_fingerprint_must_match_handoff(self):
        args = params()
        args["read_warehouse_physical"] = Mock(
            return_value=snapshot(fingerprint="c" * 64))
        with patch.object(subject, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            subject, "independent_gold_readback", return_value=False), patch.object(
            subject, "commit_gold_from_candidate_readback") as writer:
            with self.assertRaisesRegex(subject.FhirCommitHold, "SNAPSHOT_DRIFT"):
                subject.commit_verified_fhir_batch(**args)
            writer.assert_not_called()

    def test_verified_replay_does_not_require_stale_precommit_snapshot(self):
        args = params()
        with patch.object(subject, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            subject, "independent_gold_readback", return_value=True), patch.object(
            subject, "commit_gold_from_candidate_readback") as writer:
            self.assertEqual(subject.commit_verified_fhir_batch(**args),
                             subject.REPLAYED)
            args["read_warehouse_physical"].assert_not_called()
            writer.assert_not_called()

    def test_unknown_ack_never_becomes_success(self):
        args = params()
        with patch.object(subject, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            subject, "independent_gold_readback", return_value=False), patch.object(
            subject, "commit_gold_from_candidate_readback",
            return_value="GOLD_UNKNOWN_COMMIT_ACK_VERIFY_READONLY") as writer:
            with self.assertRaisesRegex(subject.FhirCommitHold,
                                        "NOT_VERIFIED"):
                subject.commit_verified_fhir_batch(**args)
            writer.assert_called_once()

    def test_existing_gold_writer_retains_trusted_release_before_sql(self):
        with patch.object(gold, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            gold, "independent_gold_readback", return_value=True) as read, patch.object(
            gold, "execute_gold_transaction") as transaction:
            with self.assertRaises(gold.GoldHold):
                gold.commit_gold_from_candidate_readback(
                    object(), lambda: object(),
                    single_writer_fence=lambda: True,
                    release_gate=lambda _: False,
                    scope=object(), handoff=object(), candidate_approval={},
                    person_rows=[], visit_rows=[], mapping_version="1",
                    writer_version="1", technical_evidence_sha256="e" * 64)
            read.assert_not_called()
            transaction.assert_not_called()

    def test_gold_writer_new_write_still_requires_release(self):
        with patch.object(gold, "prepare_gold_batch_from_candidate_readback",
                          return_value=object()), patch.object(
            gold, "independent_gold_readback", return_value=False), patch.object(
            gold, "execute_gold_transaction") as transaction:
            with self.assertRaises(gold.GoldHold):
                gold.commit_gold_from_candidate_readback(
                    object(), lambda: object(), single_writer_fence=lambda: True,
                    release_gate=lambda batch: False, scope=object(),
                    handoff=object(), candidate_approval={},
                    person_rows=[], visit_rows=[], mapping_version="1",
                    writer_version="1", technical_evidence_sha256="e" * 64)
            transaction.assert_not_called()


if __name__ == "__main__":
    unittest.main()
