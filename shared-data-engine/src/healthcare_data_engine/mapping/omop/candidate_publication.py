"""Pure, Vocabulary-version-agnostic P3 Candidate publication/replay plan.

Shared Engine owns ONLY deterministic business admission decisions. Fabric
Notebook owns actual Delta errorifexists writes, independent physical readback,
approval-last, and any separately reviewed execution authorization.
This module does NOT change the strict clinical mapping logic, invent Concept
IDs, grant clinical signoff, allocate durable IDs, or publish Warehouse Gold.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Sequence

from healthcare_data_engine.identity.candidate_handoff import (
    PersonVisitCandidateHandoff,
)
from healthcare_data_engine.mapping.omop.candidates import OmopCandidates

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}\Z")
_ID_STATES = frozenset({"PERSISTED", "PROVISIONAL"})
_WRITE_STEPS = (
    "DELTA_PERSON_CREATE_ERROR_IF_EXISTS",
    "DELTA_VISIT_CREATE_ERROR_IF_EXISTS",
    "INDEPENDENT_BOTH_TABLE_READBACK_COUNT_SCHEMA_KEYS_FK_HASH",
    "CANDIDATE_APPROVAL_WRITE_LAST",
    "INDEPENDENT_APPROVAL_READBACK",
)
_DATA_FAILURES = frozenset({
    "UNMAPPED_SOURCE_CODE", "MISSING_REQUIRED_SOURCE_CODE",
    "NO_VALID_STANDARD_CONCEPT", "WRONG_CONCEPT_DOMAIN",
    "EXPIRED_CONCEPT", "INVALID_SOURCE_VALUE",
})


class CandidatePublicationHold(ValueError):
    """Safe failure reason codes; never echo patient or source values."""


def _name(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SOURCE_ID.fullmatch(value):
        raise CandidatePublicationHold("P3_INVALID_" + label)
    return value


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise CandidatePublicationHold("P3_INVALID_" + label)
    return value


@dataclass(frozen=True)
class FrozenCandidateScope:
    hospital_id: str
    feed_id: str
    source_system: str
    request_id: str
    source_batch_id: str
    manifest_sha256: str
    silver_processing_version: str
    silver_publication_id: str
    mapping_sha256: str
    identity_snapshot_fingerprint: str
    patient_count: int
    encounter_count: int
    provisional_person_count: int
    provisional_visit_count: int

    def __post_init__(self) -> None:
        for label in ("hospital_id", "feed_id", "source_system",
                      "request_id", "source_batch_id", "silver_processing_version",
                      "silver_publication_id"):
            _name(getattr(self, label), label.upper())
        for label in ("manifest_sha256", "mapping_sha256",
                      "identity_snapshot_fingerprint"):
            _sha(getattr(self, label), label.upper())
        parts = self.source_system.split(":")
        if (len(parts) != 3 or parts[1] != self.hospital_id
                or parts[2] != self.feed_id):
            raise CandidatePublicationHold("P3_SOURCE_NAMESPACE_CONFLICT")
        if (type(self.patient_count) is not int or self.patient_count <= 0
                or type(self.encounter_count) is not int or self.encounter_count <= 0):
            raise CandidatePublicationHold("P3_SOURCE_COUNTS_INVALID")
        for count, total in (
            (self.provisional_person_count, self.patient_count),
            (self.provisional_visit_count, self.encounter_count),
        ):
            if type(count) is not int or not 0 <= count <= total:
                raise CandidatePublicationHold("P3_PROVISIONAL_COUNTS_INVALID")

    @property
    def receipt_key(self) -> str:
        """Content-addressable identity for replay comparison, NOT a Gold ID."""
        payload = {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
        return hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def freeze_candidate_scope(
    handoff: PersonVisitCandidateHandoff, candidates: OmopCandidates, *,
    feed_id: str, request_id: str,
) -> FrozenCandidateScope:
    """Bridge existing F2 preview + strict Mapper without recomputing either."""
    if (not isinstance(handoff, PersonVisitCandidateHandoff)
            or handoff.status != "G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED"
            or not isinstance(candidates, OmopCandidates)
            or candidates.status != "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED"):
        raise CandidatePublicationHold("P3_UNTRUSTED_SOURCE_HANDOFF")
    if (type(candidates.person_count) is not int
            or type(candidates.visit_count) is not int
            or candidates.person_count != len(handoff.batch_persons)
            or candidates.visit_count != len(handoff.batch_visits)
            or candidates.person is None or candidates.visit is None):
        raise CandidatePublicationHold("P3_MAPPER_HANDOFF_COUNTS_MISMATCH")
    persons = {(r.source_business_key, r.person_id): r
               for r in handoff.batch_persons}
    visits = {(r.source_encounter_id, r.visit_occurrence_id): r
              for r in handoff.batch_visits}
    if len(persons) != candidates.person_count or len(visits) != candidates.visit_count:
        raise CandidatePublicationHold("P3_DUPLICATE_CANDIDATE_IDENTITY")
    valid_persons = {r.person_id for r in handoff.batch_persons}
    if len(valid_persons) != candidates.person_count:
        raise CandidatePublicationHold("P3_DUPLICATE_PERSON_IDS")
    valid_visits = {r.visit_occurrence_id for r in handoff.batch_visits}
    if len(valid_visits) != candidates.visit_count:
        raise CandidatePublicationHold("P3_DUPLICATE_VISIT_IDS")
    for p in handoff.batch_persons:
        if (p.hospital_id != handoff.hospital_id
                or p.source_system != handoff.source_system
                or p.state not in _ID_STATES
                or type(p.person_id) is not int or p.person_id <= 0):
            raise CandidatePublicationHold("P3_PERSON_HANDOFF_SCOPE_INVALID")
    for v in handoff.batch_visits:
        if (v.hospital_id != handoff.hospital_id
                or v.source_system != handoff.source_system
                or v.state not in _ID_STATES
                or v.parent_state not in _ID_STATES
                or type(v.visit_occurrence_id) is not int or v.visit_occurrence_id <= 0
                or type(v.person_id) is not int or v.person_id not in valid_persons
                or (v.source_person_id, v.person_id) not in persons
                or persons[(v.source_person_id, v.person_id)].state != v.parent_state):
            raise CandidatePublicationHold("P3_VISIT_PARENT_OR_SCOPE_INVALID")
    return FrozenCandidateScope(
        hospital_id=handoff.hospital_id, feed_id=feed_id,
        source_system=handoff.source_system, request_id=request_id,
        source_batch_id=handoff.source_batch_id,
        manifest_sha256=handoff.manifest_sha256,
        silver_processing_version=handoff.processing_version,
        silver_publication_id=handoff.silver_publication_id,
        mapping_sha256=candidates.mapping_sha256,
        identity_snapshot_fingerprint=handoff.snapshot_fingerprint,
        patient_count=candidates.person_count,
        encounter_count=candidates.visit_count,
        provisional_person_count=sum(
            p.state == "PROVISIONAL" for p in handoff.batch_persons),
        provisional_visit_count=sum(
            v.state == "PROVISIONAL" for v in handoff.batch_visits),
    )


@dataclass(frozen=True)
class ObservedCandidate:
    """Adapter-supplied independent physical readback; NOT self-certified."""
    scope: FrozenCandidateScope
    person_delta_exists: bool
    visit_delta_exists: bool
    approval_exists: bool
    person_count: int | None = None
    visit_count: int | None = None
    person_content_sha256: str | None = None
    visit_content_sha256: str | None = None
    approval_status: str | None = None
    independently_reopened: bool = False
    schema_keys_fk_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.scope, FrozenCandidateScope):
            raise CandidatePublicationHold("P3_OBSERVATION_SCOPE_INVALID")
        for field in ("person_delta_exists", "visit_delta_exists", "approval_exists",
                      "independently_reopened", "schema_keys_fk_verified"):
            if type(getattr(self, field)) is not bool:
                raise CandidatePublicationHold("P3_OBSERVATION_BOOL_INVALID")
        for field in ("person_count", "visit_count"):
            count = getattr(self, field)
            if count is not None and (type(count) is not int or count < 0):
                raise CandidatePublicationHold("P3_OBSERVATION_COUNT_INVALID")
        for field in ("person_content_sha256", "visit_content_sha256"):
            digest = getattr(self, field)
            if digest is not None:
                _sha(digest, "OBSERVATION_SHA")
        if self.approval_status not in (None, "CANDIDATE_APPROVED", "HOLD"):
            raise CandidatePublicationHold("P3_OBSERVATION_APPROVAL_INVALID")


@dataclass(frozen=True)
class CandidatePublicationPlan:
    decision: str
    ordered_steps: tuple[str, ...]
    receipt_key: str
    source_only_not_clinically_approved: bool = True
    gold_commit_authorized: bool = False


def decide_candidate_publication(
    scope: FrozenCandidateScope, prior: Sequence[ObservedCandidate], *,
    expected_person_content_sha256: str | None = None,
    expected_visit_content_sha256: str | None = None,
    unknown_write_ack: bool = False,
) -> CandidatePublicationPlan:
    """No I/O. Even NEW only plans a write; never permits one.

    Exact approval-last and independent physical DQ remain the Fabric caller's
    responsibility. Unknown ACK and partial output always re-read first.
    """
    if not isinstance(scope, FrozenCandidateScope):
        raise CandidatePublicationHold("P3_SCOPE_INVALID")
    if type(unknown_write_ack) is not bool or not isinstance(prior, (tuple, list)):
        raise CandidatePublicationHold("P3_OBSERVATIONS_INVALID")
    if (expected_person_content_sha256 is None) != (
            expected_visit_content_sha256 is None):
        raise CandidatePublicationHold("P3_EXPECTED_REPLAY_DIGEST_PAIR_REQUIRED")
    if expected_person_content_sha256 is not None:
        _sha(expected_person_content_sha256, "EXPECTED_PERSON_SHA")
        _sha(expected_visit_content_sha256, "EXPECTED_VISIT_SHA")
    if unknown_write_ack:
        return CandidatePublicationPlan("VERIFY_READONLY", (), scope.receipt_key)
    matched = []
    for item in prior:
        if not isinstance(item, ObservedCandidate):
            raise CandidatePublicationHold("P3_OBSERVATION_INVALID")
        # Request identity is scoped to hospital/feed, not a global string.
        if (item.scope.hospital_id, item.scope.feed_id, item.scope.request_id) != (
                scope.hospital_id, scope.feed_id, scope.request_id):
            continue
        matched.append(item)
    if len(matched) > 1:
        return CandidatePublicationPlan("HOLD_DUPLICATE_PUBLICATIONS", (),
                                        scope.receipt_key)
    if not matched:
        return CandidatePublicationPlan("PLAN_NEW_OFFLINE_ONLY", _WRITE_STEPS,
                                        scope.receipt_key)
    previous = matched[0]
    if previous.scope != scope:
        return CandidatePublicationPlan("HOLD_VERSION_OR_SOURCE_CONFLICT", (),
                                        scope.receipt_key)
    if not (previous.person_delta_exists and previous.visit_delta_exists
            and previous.approval_exists):
        return CandidatePublicationPlan("VERIFY_READONLY", (), scope.receipt_key)
    if not previous.independently_reopened or not previous.schema_keys_fk_verified:
        return CandidatePublicationPlan("VERIFY_READONLY", (), scope.receipt_key)
    # A returned digest is not evidence of equality by itself. Replay SKIP
    # requires an independently computed EXPECTED candidate-row digest pair,
    # distinct from the two observed physical Delta readback digests.
    if expected_person_content_sha256 is None:
        return CandidatePublicationPlan("VERIFY_READONLY", (), scope.receipt_key)
    if (previous.person_count != scope.patient_count
            or previous.visit_count != scope.encounter_count
            or previous.person_content_sha256 != expected_person_content_sha256
            or previous.visit_content_sha256 != expected_visit_content_sha256
            or previous.approval_status != "CANDIDATE_APPROVED"):
        return CandidatePublicationPlan("HOLD_READBACK_OR_APPROVAL_CONFLICT",
                                        (), scope.receipt_key)
    return CandidatePublicationPlan("SKIP_VERIFIED_CANDIDATE_ONLY", (),
                                    scope.receipt_key)


def classify_mapping_failure(code: str) -> str:
    """Data-level missing mappings can be quarantined without changing code.

    This does not authorize partial Gold or silently relax the existing strict
    batch policy; publication still waits for separately reviewed DQ policy.
    """
    if not isinstance(code, str) or not code:
        raise CandidatePublicationHold("P3_FAILURE_CODE_INVALID")
    # Translate only known diagnostic prefixes from the EXISTING strict
    # Mapper/P1 validator. Their suffixes name a source COLUMN, not a patient
    # value. The caller still keeps its strict batch HOLD until a separately
    # approved record-level DQ/Quarantine contract is implemented.
    source_columns = {"gender_code", "race_code", "ethnicity_code",
                      "encounter_class"}
    mapper_unmapped = (code.startswith("G5_UNKNOWN_MAPPING_CODE:")
                       and code.partition(":")[2] in source_columns)
    profile_unmapped = (code.startswith("P1_UNMAPPED_SOURCE_CODE:")
                        and code.partition(":")[2] in source_columns)
    return ("DATA_QUARANTINE_CANDIDATE_HOLD_PUBLICATION"
            if code in _DATA_FAILURES or mapper_unmapped or profile_unmapped
            else "BATCH_HOLD_NO_PUBLICATION")
