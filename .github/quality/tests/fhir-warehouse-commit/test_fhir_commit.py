"""Offline acceptance checks for the FHIR Warehouse commit boundary."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))
import fhir_commit as subject


def params():
    return dict(
        connection=object(), independent_connection=lambda: object(),
        single_writer_fence=lambda: True, release_gate=lambda _: True,
        scope=object(), handoff=object(), candidate_approval={},
        person_rows=[], visit_rows=[], mapping_version="1",
        writer_version="1", technical_evidence_sha256="a" * 64,
        physical_candidate_verified=True,
        physical_warehouse_snapshot_verified=True,
    )


class FhirCommitTests(unittest.TestCase):
    def test_unverified_inputs_never_write(self):
        for flag in ("physical_candidate_verified", "physical_warehouse_snapshot_verified"):
            with self.subTest(flag=flag), patch.object(
                subject, "commit_gold_from_candidate_readback"
            ) as writer:
                args = params()
                args[flag] = False
                with self.assertRaises(subject.FhirCommitHold):
                    subject.commit_verified_fhir_batch(**args)
                writer.assert_not_called()

    def test_commit_and_replay_must_be_independently_verified(self):
        for status in (subject.COMMITTED, subject.REPLAYED):
            with self.subTest(status=status), patch.object(
                subject, "commit_gold_from_candidate_readback", return_value=status
            ) as writer:
                self.assertEqual(subject.commit_verified_fhir_batch(**params()), status)
                writer.assert_called_once()

    def test_unknown_commit_ack_is_not_success(self):
        with patch.object(subject, "commit_gold_from_candidate_readback",
                          return_value="GOLD_COMMIT_ACK_UNVERIFIED_READONLY_RECONCILE"):
            with self.assertRaisesRegex(subject.FhirCommitHold, "READBACK_NOT_VERIFIED"):
                subject.commit_verified_fhir_batch(**params())

    def test_missing_trusted_controller_dependencies_halt(self):
        for field in ("independent_connection", "single_writer_fence", "release_gate"):
            with self.subTest(field=field), patch.object(
                subject, "commit_gold_from_candidate_readback"
            ) as writer:
                args = params()
                args[field] = None
                with self.assertRaises(subject.FhirCommitHold):
                    subject.commit_verified_fhir_batch(**args)
                writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
