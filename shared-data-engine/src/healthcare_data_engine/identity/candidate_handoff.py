"""Strict, platform-neutral F2 preview -> G5 Candidate ID handoff.

A first batch has no persisted Person/Visit ID map. The existing F2 planner
may propose IDs against a COMPLETE caller-supplied Warehouse snapshot; this
function reconciles those proposals with independently approved Canonical
source keys WITHOUT passing provisional IDs off as durable mappings.

This is **SOURCE_ONLY**. It does not read SQL/Silver, allocate IDs, grant
clinical Concept approval, construct SparkSession, write Delta, reserve IDs,
or COMMIT Warehouse state. A platform integration must re-open physical data
and maintain the provisional/persisted flags through Candidate and Gold.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from healthcare_data_engine.identity.preview import (
    IdentityPreview, IdentityPreviewHold, IdentitySnapshot,
    require_preview_snapshot_unchanged,
)
from healthcare_data_engine.mapping.omop.registry import DerivedRowKey


_PERSON = "cdm.person"
_VISIT = "cdm.visit_occurrence"
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class CandidateIdentityHold(ValueError):
    """Safe diagnostic codes only. Never include source values or PHI."""


def _source(value: object, label: str, limit: int = 256) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > limit or any(ord(c) < 32 for c in value)):
        raise CandidateIdentityHold("G5_PREVIEW_INVALID_" + label)
    return value


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise CandidateIdentityHold("G5_PREVIEW_INVALID_" + label)
    return value


@dataclass(frozen=True)
class CandidatePersonId:
    hospital_id: str
    source_system: str
    source_business_key: str
    person_id: int
    state: str

    def person_identity_lookup_row(self) -> tuple[str, str, str, str, int, str]:
        """Mapper-compatible Person lookup with explicit identity state."""
        return ("PERSON", self.hospital_id, self.source_system,
                self.source_business_key, self.person_id, self.state)

    def f1_lookup(self) -> tuple[str, str, str, str, int, str]:
        """Legacy caller compatibility; use person_identity_lookup_row."""
        return self.person_identity_lookup_row()


@dataclass(frozen=True)
class CandidateVisitId:
    hospital_id: str
    source_system: str
    source_encounter_id: str
    source_person_id: str
    visit_occurrence_id: int
    person_id: int
    state: str
    parent_state: str


@dataclass(frozen=True)
class PersonVisitCandidateHandoff:
    """Source-only proposal to construct candidates; no Gold rights.

    \`person_lookup\` may include *existing* whole-Warehouse mappings, while
    \`batch_persons\` and \`batch_visits\` are exactly the approved Silver batch.
    The caller MUST retain each row's state and snapshot pin when joining
    actual Spark Candidate data; it may not persist these as \`etl.identity_map\`.
    """

    person_lookup: tuple[CandidatePersonId, ...]
    batch_persons: tuple[CandidatePersonId, ...]
    batch_visits: tuple[CandidateVisitId, ...]
    hospital_id: str
    source_system: str
    source_batch_id: str
    manifest_sha256: str
    processing_version: str
    silver_publication_id: str
    snapshot_fingerprint: str
    status: str = "G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED"

    def person_lookup_rows(self) -> tuple[tuple[str, str, str, str, int, str], ...]:
        """Legacy mapper-compatible columns + `identity_state` (never F1 DML)."""
        return tuple(row.person_identity_lookup_row() for row in self.person_lookup)

    def visit_id_rows(self) -> tuple[tuple[str, str, int, str], ...]:
        """Input for later target Visit ID join, NOT a Gold destination table."""
        return tuple(
            (row.source_system, row.source_encounter_id,
             row.visit_occurrence_id, row.state)
            for row in self.batch_visits
        )


def plan_candidate_identity_handoff(
    *, patients: Sequence[Mapping[str, object]],
    encounters: Sequence[Mapping[str, object]],
    approval: Mapping[str, object],
    hospital_id: str,
    source_system: str,
    source_batch_id: str,
    manifest_sha256: str,
    processing_version: str,
    snapshot: IdentitySnapshot,
    preview: IdentityPreview,
) -> PersonVisitCandidateHandoff:
    """Reconcile a COMPLETE F2 ID preview against source-only G4 acceptance.

    \`approval\` / snapshot / source rows come from the caller. This checks
    internal integrity but cannot prove a physical readback; runtime must
    independently re-open Silver, Approval, Warehouse Map/Gold/Allocator/Ledger.
    There is deliberately no \`clinical_approved=True\` bypass.
    """
    hospital_id = _source(hospital_id, "HOSPITAL", 96)
    source_system = _source(source_system, "SOURCE_SYSTEM", 96)
    source_batch_id = _source(source_batch_id, "BATCH", 128)
    manifest_sha256 = _hash(manifest_sha256, "MANIFEST_SHA")
    processing_version = _source(processing_version, "PROCESSING_VERSION", 128)
    parts = source_system.split(":")
    if len(parts) != 3 or not all(parts) or parts[1] != hospital_id:
        raise CandidateIdentityHold("G5_PREVIEW_SOURCE_NAMESPACE_MISMATCH")
    if not isinstance(patients, (tuple, list)) or not isinstance(
            encounters, (tuple, list)) or not patients or not encounters:
        raise CandidateIdentityHold("G5_PREVIEW_SOURCE_ROWS_INVALID")
    if (not isinstance(approval, Mapping)
            or approval.get("status") != "SILVER_APPROVED"
            or approval.get("source_batch_id") != source_batch_id
            or approval.get("manifest_sha256") != manifest_sha256
            or approval.get("processing_version") != processing_version
            or type(approval.get("patient_count")) is not int
            or type(approval.get("encounter_count")) is not int
            or type(approval.get("quarantine_count")) is not int
            or approval["patient_count"] != len(patients)
            or approval["encounter_count"] != len(encounters)
            or approval["quarantine_count"] != 0
            or not isinstance(approval.get("publication_id"), str)
            or not approval["publication_id"]):
        raise CandidateIdentityHold("G5_PREVIEW_APPROVAL_NOT_MATCHED")
    try:
        require_preview_snapshot_unchanged(preview, snapshot)
    except IdentityPreviewHold as exc:
        raise CandidateIdentityHold("G5_PREVIEW_SNAPSHOT_CHANGED_OR_INVALID") from exc
    # The snapshot must be warehouse-wide for BOTH required targets. No
    # hospital-only Map subset may be passed as a substitute for global state.
    if set(dict(snapshot.next_free)) != {_PERSON, _VISIT}:
        raise CandidateIdentityHold("G5_PREVIEW_TARGET_SCOPE_INCOMPLETE")
    if ({table for table, _ in preview.next_free}
            != {table for table, _ in snapshot.next_free}):
        raise CandidateIdentityHold("G5_PREVIEW_ALLOCATOR_SCOPE_INVALID")

    # Build the exact proposal lookup once: G4 currently contains 5,918
    # encounters, and repeated IdentityPreview.for_key scans would be O(n²).
    proposals = {}
    folded_proposals = set()
    for candidate in preview.identities:
        key = candidate.key
        if (key in proposals or key.folded() in folded_proposals
                or candidate.snapshot_fingerprint != preview.snapshot_fingerprint):
            raise CandidateIdentityHold("G5_PREVIEW_DUPLICATE_OR_DRIFTED_ID")
        proposals[key] = candidate
        folded_proposals.add(key.folded())
    persisted = snapshot.persisted()
    lookup: dict[DerivedRowKey, CandidatePersonId] = {}
    for key, omop_id in persisted.items():
        if key.target_table != _PERSON:
            continue
        lookup[key] = CandidatePersonId(
            key.hospital_id, key.source_system, key.source_business_key,
            omop_id, "PERSISTED")

    for item in preview.identities:
        if item.key.target_table not in {_PERSON, _VISIT}:
            raise CandidateIdentityHold("G5_PREVIEW_UNEXPECTED_TARGET")
        if item.key.derived_role != "primary" or item.key.derived_discriminator:
            raise CandidateIdentityHold("G5_PREVIEW_DERIVED_KEY_UNSUPPORTED")
        if item.key.target_table != _PERSON:
            continue
        current = lookup.get(item.key)
        if current is not None:
            if current.person_id != item.omop_id or item.state != "PERSISTED":
                raise CandidateIdentityHold("G5_PREVIEW_PERSISTED_MAP_CONFLICT")
        else:
            if item.state != "PROVISIONAL":
                raise CandidateIdentityHold("G5_PREVIEW_UNBACKED_PERSISTED_ID")
        lookup[item.key] = CandidatePersonId(
            item.key.hospital_id, item.key.source_system,
            item.key.source_business_key, item.omop_id, item.state,
        )

    # The candidate handoff must also reject a forged Preview with two
    # Visit IDs or two Person IDs mapped to the same per-target INT. F2's
    # legitimate proposal already enforces this, but this boundary is public.
    target_ids = {(key.target_table, item.omop_id)
                  for key, item in proposals.items()}
    if len(target_ids) != len(proposals):
        raise CandidateIdentityHold("G5_PREVIEW_TARGET_ID_COLLISION")

    # Prevent global duplicated prospective Person IDs and case-insensitive
    # source collisions even when the underlying Warehouse constraints are
    # declared NOT ENFORCED.
    if len({row.person_id for row in lookup.values()}) != len(lookup):
        raise CandidateIdentityHold("G5_PREVIEW_DUPLICATE_PERSON_ID")
    if len({key.folded() for key in lookup}) != len(lookup):
        raise CandidateIdentityHold("G5_PREVIEW_PERSON_COLLATION_CONFLICT")

    def validate_row(row: object, pk: str) -> str:
        if (not isinstance(row, Mapping)
                or row.get("source_system") != source_system
                or row.get("source_batch_id") != source_batch_id):
            raise CandidateIdentityHold("G5_PREVIEW_SOURCE_ROW_SCOPE_DRIFT")
        return _source(row.get(pk), "SOURCE_ID")

    seen_person: set[str] = set()
    batch_persons: list[CandidatePersonId] = []
    person_by_source: dict[str, CandidatePersonId] = {}
    for row in patients:
        key = validate_row(row, "source_record_id")
        if key.casefold() in seen_person:
            raise CandidateIdentityHold("G5_PREVIEW_DUPLICATE_PERSON_SOURCE")
        seen_person.add(key.casefold())
        # OMOP person_source_value has a varchar(50) target. No truncation.
        _source(key, "PERSON_SOURCE_VALUE_LENGTH", 50)
        planned = proposals.get(DerivedRowKey(
            _PERSON, hospital_id, source_system, key))
        if planned is None:
            raise CandidateIdentityHold("G5_PREVIEW_PERSON_ID_NOT_FOUND")
        item = lookup.get(planned.key)
        if (item is None or item.person_id != planned.omop_id
                or item.state != planned.state):
            raise CandidateIdentityHold("G5_PREVIEW_PERSON_LOOKUP_MISMATCH")
        batch_persons.append(item)
        person_by_source[key] = item

    seen_visit: set[str] = set()
    batch_visits: list[CandidateVisitId] = []
    for row in encounters:
        source_visit = validate_row(row, "source_encounter_id")
        parent_source = _source(row.get("source_person_id"), "VISIT_PERSON_SOURCE_ID")
        visit_class = _source(row.get("encounter_class"),
                              "VISIT_SOURCE_VALUE_LENGTH", 50)
        if source_visit.casefold() in seen_visit:
            raise CandidateIdentityHold("G5_PREVIEW_DUPLICATE_VISIT_SOURCE")
        seen_visit.add(source_visit.casefold())
        parent = person_by_source.get(parent_source)
        if parent is None:
            raise CandidateIdentityHold("G5_PREVIEW_PARENT_PERSON_NOT_IN_SILVER")
        target = proposals.get(DerivedRowKey(
            _VISIT, hospital_id, source_system, source_visit))
        if target is None:
            raise CandidateIdentityHold("G5_PREVIEW_VISIT_ID_NOT_FOUND")
        # The F2 preview must be exact and must not be allowed to switch a
        # proposed ID to PERSISTED when there is no matching Warehouse map.
        original = persisted.get(target.key)
        if ((target.state == "PERSISTED" and original != target.omop_id)
                or (target.state == "PROVISIONAL" and original is not None)):
            raise CandidateIdentityHold("G5_PREVIEW_VISIT_PERSISTENCE_CONFLICT")
        batch_visits.append(CandidateVisitId(
            hospital_id, source_system, source_visit, parent_source,
            target.omop_id, parent.person_id, target.state, parent.state))

    # The planner's incoming set must be EXACTLY the accepted batch. A
    # preview for an extra source record may never become an approved batch.
    batch_expected = {DerivedRowKey(_PERSON, hospital_id, source_system,
                                    row.source_business_key)
                      for row in batch_persons}
    batch_expected.update(
        DerivedRowKey(_VISIT, hospital_id, source_system, row.source_encounter_id)
        for row in batch_visits
    )
    if {entry.key for entry in preview.identities} != batch_expected:
        raise CandidateIdentityHold("G5_PREVIEW_EXTRA_OR_MISSING_BATCH_IDS")
    return PersonVisitCandidateHandoff(
        tuple(sorted(lookup.values(), key=lambda x: (
            x.hospital_id, x.source_system, x.source_business_key))),
        tuple(sorted(batch_persons, key=lambda x: x.source_business_key)),
        tuple(sorted(batch_visits, key=lambda x: x.source_encounter_id)),
        hospital_id, source_system, source_batch_id, manifest_sha256,
        processing_version, approval["publication_id"],
        preview.snapshot_fingerprint,
    )
