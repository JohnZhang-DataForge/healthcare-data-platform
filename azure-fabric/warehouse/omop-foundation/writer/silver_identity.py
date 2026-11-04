"""F2 G4 Silver to stable Person/Visit ID preview; no Fabric or SQL I/O.

Consumes source-key columns from independently read-back approved canonical
Patient and Encounter rows. Never reserves IDs, grants Gold writes or approves
a Concept Mapping Profile. A real single-writer SQL transaction must reopen
the Warehouse snapshot before a later Gold COMMIT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from identity_plan import (
    AllocationPlan, IdentityKey, PlanningHold, SHA, clean, plan_ids,
)


@dataclass(frozen=True)
class SilverIdentityPreview:
    allocation: AllocationPlan
    persons: tuple[tuple[str, int], ...]
    visits: tuple[tuple[str, int, int], ...]
    status: str = "F2_ID_PREVIEW_ONLY_NOT_PERSISTED"


def plan_silver_identity(
    patients: Sequence[Mapping[str, object]],
    encounters: Sequence[Mapping[str, object]],
    *,
    hospital_id: str,
    source_system: str,
    source_batch_id: str,
    approval: Mapping[str, object],
    physical_readback_verified: bool,
    quarantine_zero_verified: bool,
    existing: Sequence[tuple[IdentityKey, int]],
    next_free: Mapping[str, int],
    gold_ids: Mapping[str, Sequence[int]],
) -> SilverIdentityPreview:
    """Only preview IDs after source namespace, approval and FK validations.

    physical_readback_verified means the trusted caller independently reopened
    persisted Silver Patient, Encounter and Approval Delta paths;
    quarantine_zero_verified also requires an independent negative DQ proof.
    Boolean assertions are NOT durable receipts or commit authorization.
    """
    if physical_readback_verified is not True or quarantine_zero_verified is not True:
        raise PlanningHold("SILVER_PHYSICAL_APPROVAL_OR_DQ_NOT_VERIFIED")
    clean(hospital_id, "hospital_id")
    clean(source_system, "source_system")
    clean(source_batch_id, "batch_id")
    parts = source_system.split(":")
    if len(parts) != 3 or not all(parts) or parts[1] != hospital_id:
        raise PlanningHold("SILVER_HOSPITAL_NAMESPACE_MISMATCH")
    if not isinstance(patients, (list, tuple)) or not isinstance(encounters, (list, tuple)):
        raise PlanningHold("SILVER_SOURCE_ROWS_INVALID")
    if not patients or not encounters:
        raise PlanningHold("SILVER_PATIENT_OR_ENCOUNTER_EMPTY")
    if not isinstance(approval, Mapping):
        raise PlanningHold("SILVER_APPROVAL_MISSING")
    sha = approval.get("manifest_sha256")
    version = approval.get("processing_version")
    publication = approval.get("publication_id")
    if (
        approval.get("status") != "SILVER_APPROVED"
        or approval.get("source_batch_id") != source_batch_id
        or not isinstance(sha, str) or not SHA.fullmatch(sha)
        or not isinstance(version, str) or not version
        or not isinstance(publication, str) or not publication
        or type(approval.get("patient_count")) is not int
        or type(approval.get("encounter_count")) is not int
        or approval["patient_count"] != len(patients)
        or approval["encounter_count"] != len(encounters)
    ):
        raise PlanningHold("SILVER_APPROVAL_COUNTS_OR_HASH_MISMATCH")

    def key_of(row: Mapping[str, object], entity: str, key_field: str) -> IdentityKey:
        if not isinstance(row, Mapping):
            raise PlanningHold("SILVER_CANONICAL_ROW_INVALID")
        if row.get("source_system") != source_system or row.get("source_batch_id") != source_batch_id:
            raise PlanningHold("SILVER_CANONICAL_NAMESPACE_OR_BATCH_DRIFT")
        return IdentityKey(entity, hospital_id, source_system, row.get(key_field))

    patient_keys = [key_of(row, "PERSON", "source_record_id") for row in patients]
    visit_keys = [key_of(row, "VISIT_OCCURRENCE", "source_encounter_id") for row in encounters]

    # Compare casefolded keys too: Warehouse collation may be case-insensitive.
    person_sources = {key.source_business_key.casefold() for key in patient_keys}
    for row in encounters:
        parent = row.get("source_person_id")
        clean(parent, "source_business_key")
        if parent.casefold() not in person_sources:
            raise PlanningHold("SILVER_ENCOUNTER_PERSON_FK_MISSING")
    allocation = plan_ids(
        [*patient_keys, *visit_keys], existing, next_free, gold_ids,
    )
    assigned = dict(allocation.assigned)
    person_by_folded = {
        key.source_business_key.casefold(): assigned[key] for key in patient_keys
    }
    persons = tuple(sorted(
        (key.source_business_key, assigned[key]) for key in patient_keys
    ))
    visits = tuple(sorted(
        (key.source_business_key, assigned[key], person_by_folded[row["source_person_id"].casefold()])
        for key, row in zip(visit_keys, encounters)
    ))
    if (
        len(persons) != approval["patient_count"]
        or len(visits) != approval["encounter_count"]
        or len({id for _, id in persons}) != len(persons)
        or len({id for _, id, _ in visits}) != len(visits)
    ):
        raise PlanningHold("SILVER_PREVIEW_CARDINALITY_OR_ID_COLLISION")
    return SilverIdentityPreview(allocation, persons, visits)
