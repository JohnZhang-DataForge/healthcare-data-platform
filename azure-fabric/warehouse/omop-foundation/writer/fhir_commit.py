"""Trusted orchestration boundary for a physically read-back FHIR OMOP batch.

This adapter deliberately does not authorize writes based on Notebook parameters,
candidate metadata, or a claimed approval flag. A trusted runner must supply
independently verified physical rows, an approval receipt, and a global writer
fence. All ID planning and SQL mutations remain in the existing Gold writer.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from gold_transaction import commit_gold_from_candidate_readback

COMMITTED = "GOLD_COMMITTED_AND_INDEPENDENT_READBACK_PASS"
REPLAYED = "GOLD_VERIFIED_REPLAY_SKIP"


class FhirCommitHold(RuntimeError):
    """Do not include clinical identifiers or row contents in errors."""


def commit_verified_fhir_batch(
    *,
    connection: Any,
    independent_connection: Callable[[], Any],
    single_writer_fence: Callable[[], bool],
    release_gate: Callable[[Any], bool],
    scope: Any,
    handoff: Any,
    candidate_approval: Mapping[str, object],
    person_rows: Sequence[Mapping[str, object]],
    visit_rows: Sequence[Mapping[str, object]],
    mapping_version: str,
    writer_version: str,
    technical_evidence_sha256: str,
    physical_candidate_verified: bool,
    physical_warehouse_snapshot_verified: bool,
) -> str:
    """Commit only verified Candidate rows; require independent Gold readback.

    The two physical flags are assertions from the *trusted controller*, not
    authorization inputs accepted from an HTTP request or Fabric Notebook.
    The underlying Gold writer checks exact row digests, identity handoff,
    technical evidence, single-writer fencing, and post-commit SQL state.
    """
    if physical_candidate_verified is not True:
        raise FhirCommitHold("FHIR_CANDIDATE_PHYSICAL_READBACK_REQUIRED")
    if physical_warehouse_snapshot_verified is not True:
        raise FhirCommitHold("FHIR_WAREHOUSE_PHYSICAL_SNAPSHOT_REQUIRED")
    if not callable(independent_connection) or not callable(single_writer_fence):
        raise FhirCommitHold("FHIR_TRUSTED_SQL_CONNECTION_AND_FENCE_REQUIRED")
    if not callable(release_gate):
        raise FhirCommitHold("FHIR_TRUSTED_RELEASE_GATE_REQUIRED")
    result = commit_gold_from_candidate_readback(
        connection, independent_connection,
        single_writer_fence=single_writer_fence,
        release_gate=release_gate,
        scope=scope,
        handoff=handoff,
        candidate_approval=candidate_approval,
        person_rows=person_rows,
        visit_rows=visit_rows,
        mapping_version=mapping_version,
        writer_version=writer_version,
        technical_evidence_sha256=technical_evidence_sha256,
    )
    if result not in (COMMITTED, REPLAYED):
        raise FhirCommitHold("FHIR_COMMIT_OR_INDEPENDENT_READBACK_NOT_VERIFIED")
    return result
