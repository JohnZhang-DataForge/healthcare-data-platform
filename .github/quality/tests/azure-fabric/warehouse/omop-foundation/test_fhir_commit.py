"""Tests for the trusted FHIR commit boundary; no external Warehouse writes."""
import importlib.util
from pathlib import Path
import sys
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[6]
WRITER = ROOT / "azure-fabric/warehouse/omop-foundation/writer"
sys.path.insert(0, str(WRITER))
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


@pytest.mark.parametrize("flag", [
    "physical_candidate_verified", "physical_warehouse_snapshot_verified"
])
def test_unverified_physical_input_never_calls_writer(monkeypatch, flag):
    writer = Mock()
    monkeypatch.setattr(subject, "commit_gold_from_candidate_readback", writer)
    values = params()
    values[flag] = False
    with pytest.raises(subject.FhirCommitHold):
        subject.commit_verified_fhir_batch(**values)
    writer.assert_not_called()


@pytest.mark.parametrize("status", [
    subject.COMMITTED, subject.REPLAYED
])
def test_only_independently_verified_status_is_accepted(monkeypatch, status):
    writer = Mock(return_value=status)
    monkeypatch.setattr(subject, "commit_gold_from_candidate_readback", writer)
    assert subject.commit_verified_fhir_batch(**params()) == status
    writer.assert_called_once()


def test_unknown_commit_ack_is_not_reported_as_success(monkeypatch):
    writer = Mock(return_value="GOLD_COMMIT_ACK_UNVERIFIED_READONLY_RECONCILE")
    monkeypatch.setattr(subject, "commit_gold_from_candidate_readback", writer)
    with pytest.raises(subject.FhirCommitHold, match="READBACK_NOT_VERIFIED"):
        subject.commit_verified_fhir_batch(**params())
