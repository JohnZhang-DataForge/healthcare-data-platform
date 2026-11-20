"""FHIR Candidate -> existing Warehouse Writer, behind independent physical reads.

This module MUST be called only by a trusted GitHub OIDC runner. In particular,
a Notebook flag, user-provided receipt, SHA, or boolean cannot authorize a
write. The runner's readers must use authenticated independent OneLake/SQL
connections and must never log raw Person/Visit records or credentials.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from gold_transaction import (
    _candidate_rows_digest, commit_gold_from_candidate_readback,
    independent_gold_readback, prepare_gold_batch_from_candidate_readback,
)
from silver_identity import F2SnapshotBridge

COMMITTED = "GOLD_COMMITTED_AND_INDEPENDENT_READBACK_PASS"
REPLAYED = "GOLD_VERIFIED_REPLAY_SKIP"


class FhirCommitHold(RuntimeError):
    """Safe diagnostic; no clinical data or business keys in exception text."""


def _physical_candidate_twice(reader: Callable, scope: Any):
    """Reopen all three Candidate Delta tables twice, compare complete rows.

    This validates the supplied *results*, not the provenance of a callback.
    Only protected Runner code may construct and call this entrypoint.
    """
    if not callable(reader):
        raise FhirCommitHold("FHIR_INDEPENDENT_CANDIDATE_READER_REQUIRED")
    observations = []
    try:
        for _ in range(2):
            obs = reader()
            if not isinstance(obs, Mapping) or set(obs) != {
                    "person_rows", "visit_rows", "candidate_approval"}:
                raise FhirCommitHold("FHIR_CANDIDATE_PHYSICAL_SCHEMA_INVALID")
            p, v, approval = (obs["person_rows"], obs["visit_rows"],
                              obs["candidate_approval"])
            if (not isinstance(p, (list, tuple))
                    or not isinstance(v, (list, tuple))
                    or not isinstance(approval, Mapping)):
                raise FhirCommitHold("FHIR_CANDIDATE_PHYSICAL_ROWS_INVALID")
            p_sha = _candidate_rows_digest(p, "person_id", scope.patient_count)
            v_sha = _candidate_rows_digest(
                v, "visit_occurrence_id", scope.encounter_count)
            observations.append((p_sha, v_sha, dict(approval), p, v))
    except FhirCommitHold:
        raise
    except Exception:
        raise FhirCommitHold("FHIR_CANDIDATE_INDEPENDENT_READBACK_FAILED") from None
    first, second = observations
    if first[:3] != second[:3]:
        raise FhirCommitHold("FHIR_CANDIDATE_TWO_READBACKS_DISAGREE")
    return first[3], first[4], first[2]


def _warehouse_snapshot_twice(reader: Callable, scope: Any) -> None:
    """Check independently rebuilt six-table SQL identity snapshot pre-COMMIT.

    The F2SnapshotBridge computation itself requires complete rowsets with
    two equal SQL-connection digests. This adapter adds a second fresh read
    and exact Shared snapshot fingerprint comparison.
    """
    if not callable(reader):
        raise FhirCommitHold("FHIR_INDEPENDENT_WAREHOUSE_READER_REQUIRED")
    try:
        first = reader()
        second = reader()
    except Exception:
        raise FhirCommitHold("FHIR_WAREHOUSE_SQL_READBACK_FAILED") from None
    for observed in (first, second):
        if (not isinstance(observed, F2SnapshotBridge)
                or observed.shared_snapshot_fingerprint
                    != scope.identity_snapshot_fingerprint
                or observed.physical_snapshot_sha256 is None):
            raise FhirCommitHold("FHIR_WAREHOUSE_IDENTITY_SNAPSHOT_DRIFT")
    if (first.physical_snapshot_sha256 != second.physical_snapshot_sha256
            or first.table_sha256 != second.table_sha256):
        raise FhirCommitHold("FHIR_WAREHOUSE_TWO_SQL_SNAPSHOTS_DISAGREE")


def commit_verified_fhir_batch(
    *, connection: Any,
    independent_connection: Callable[[], Any],
    single_writer_fence: Callable[[], bool],
    release_gate: Callable[[Any], bool],
    scope: Any, handoff: Any,
    read_candidate_physical: Callable[[], Mapping[str, object]],
    read_warehouse_physical: Callable[[], F2SnapshotBridge],
    mapping_version: str, writer_version: str,
    technical_evidence_sha256: str,
) -> str:
    """Use actual Candidate/SQL readback; no caller-supplied verified flags.

    Verified replay is intentionally checked BEFORE comparing the historical
    pre-COMMIT identity snapshot: it legitimately changes after the first
    successful write. On an uncertain readback, fail closed, never retry DML.
    """
    if (not callable(independent_connection)
            or not callable(single_writer_fence) or not callable(release_gate)):
        raise FhirCommitHold("FHIR_TRUSTED_SQL_CONNECTION_FENCE_AND_GATE_REQUIRED")
    person_rows, visit_rows, approval = _physical_candidate_twice(
        read_candidate_physical, scope)
    try:
        batch = prepare_gold_batch_from_candidate_readback(
            scope=scope, handoff=handoff, candidate_approval=approval,
            person_rows=person_rows, visit_rows=visit_rows,
            mapping_version=mapping_version, writer_version=writer_version,
            technical_evidence_sha256=technical_evidence_sha256)
    except Exception:
        raise FhirCommitHold("FHIR_CANDIDATE_GOLD_HANDOFF_INVALID") from None
    try:
        if independent_gold_readback(independent_connection, batch):
            return REPLAYED
    except Exception:
        raise FhirCommitHold("FHIR_GOLD_INITIAL_READBACK_UNAVAILABLE_NO_WRITE") from None

    # New writes require real warehouse state still matching the identity
    # snapshot against which the Shared Engine planned Candidate IDs.
    _warehouse_snapshot_twice(read_warehouse_physical, scope)
    try:
        result = commit_gold_from_candidate_readback(
            connection, independent_connection,
            single_writer_fence=single_writer_fence,
            release_gate=release_gate,
            scope=scope, handoff=handoff, candidate_approval=approval,
            person_rows=person_rows, visit_rows=visit_rows,
            mapping_version=mapping_version, writer_version=writer_version,
            technical_evidence_sha256=technical_evidence_sha256)
    except Exception:
        # No automatic retry after an unknown COMMIT acknowledgement.
        raise FhirCommitHold("FHIR_GOLD_TRANSACTION_FAILED_READONLY_RECONCILE") from None
    if result not in (COMMITTED, REPLAYED):
        raise FhirCommitHold("FHIR_COMMIT_OR_INDEPENDENT_READBACK_NOT_VERIFIED")
    return result
