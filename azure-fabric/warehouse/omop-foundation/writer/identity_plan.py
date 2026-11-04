"""Pure F2 ID preview and Ledger replay plan. This module has no SQL, Spark or Azure I/O.

A preview is NOT a durable allocation. The eventual Warehouse Writer must
re-read the pinned data and atomically commit ID map, Person/Visit and Ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

MAX_ID = 2_147_483_647
KINDS = ("PERSON", "VISIT_OCCURRENCE")
SHA = re.compile("[0-9a-f]{64}\\Z")
LIMITS = {"hospital_id": 96, "source_system": 96, "source_business_key": 256,
          "batch_id": 128, "writer_version": 32}


class PlanningHold(ValueError):
    """Error codes only; do not embed clinical or source identifiers."""


def clean(value: object, field: str) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > LIMITS[field] or any(ord(c) < 32 for c in value)):
        raise PlanningHold("INVALID_" + field.upper())
    return value


def valid_id(value: object) -> int:
    if type(value) is not int or value < 1 or value > MAX_ID:
        raise PlanningHold("OMOP_INT_INVALID")
    return value


@dataclass(frozen=True, order=True)
class IdentityKey:
    entity_type: str
    hospital_id: str
    source_system: str
    source_business_key: str

    def __post_init__(self):
        if self.entity_type not in KINDS:
            raise PlanningHold("ENTITY_NOT_ALLOWLISTED")
        for field in ("hospital_id", "source_system", "source_business_key"):
            clean(getattr(self, field), field)

    def folded(self) -> tuple[str, ...]:
        return tuple(x.casefold() for x in (self.entity_type, self.hospital_id,
                                            self.source_system, self.source_business_key))


@dataclass(frozen=True)
class AllocationPlan:
    assigned: tuple[tuple[IdentityKey, int], ...]
    inserted: tuple[tuple[IdentityKey, int], ...]
    next_free: tuple[tuple[str, int], ...]


def plan_ids(incoming: Sequence[IdentityKey], existing: Sequence[tuple[IdentityKey, int]],
             next_free: Mapping[str, int],
             gold_ids: Mapping[str, Sequence[int]]) -> AllocationPlan:
    """Requires independently validated complete Warehouse Map + Gold snapshot.

    New assignments are deterministic across source order. They are not
    reservations; a transaction executor must recheck the snapshot before DML.
    """
    if not incoming:
        raise PlanningHold("EMPTY_SOURCE")
    if set(next_free) != set(KINDS) or set(gold_ids) != set(KINDS):
        raise PlanningHold("INCOMPLETE_WAREHOUSE_SNAPSHOT")
    old = {}
    used = {kind: set() for kind in KINDS}
    old_folded = set()
    for key, omop_id in existing:
        if not isinstance(key, IdentityKey) or key in old:
            raise PlanningHold("DUPLICATE_PERSISTED_SOURCE")
        if key.folded() in old_folded:
            raise PlanningHold("PERSISTED_COLLATION_COLLISION")
        old_folded.add(key.folded())
        value = valid_id(omop_id)
        if value in used[key.entity_type]:
            raise PlanningHold("DUPLICATE_PERSISTED_OMOP_ID")
        old[key] = value
        used[key.entity_type].add(value)
    for kind in KINDS:
        physical = [valid_id(x) for x in gold_ids[kind]]
        if len(set(physical)) != len(physical) or set(physical) != used[kind]:
            raise PlanningHold("MAP_GOLD_PARTIAL_OR_DRIFT")

    pending = set()
    folded = set()
    for key in incoming:
        if not isinstance(key, IdentityKey):
            raise PlanningHold("SOURCE_KEY_INVALID")
        if key.folded() in old_folded and key not in old:
            raise PlanningHold("SOURCE_PERSISTED_COLLATION_COLLISION")
        if key in pending:
            raise PlanningHold("DUPLICATE_SOURCE")
        if key.folded() in folded:
            raise PlanningHold("SOURCE_COLLATION_COLLISION")
        pending.add(key)
        folded.add(key.folded())

    counters = {}
    for kind in KINDS:
        counter = next_free[kind]
        if type(counter) is not int or counter < 1 or counter > MAX_ID + 1:
            raise PlanningHold("INVALID_ALLOCATOR_NEXT")
        if used[kind] and counter <= max(used[kind]):
            raise PlanningHold("ALLOCATOR_REWIND")
        counters[kind] = counter
    assigned, inserted = {}, {}
    for key in sorted(incoming):
        if key in old:
            assigned[key] = old[key]
            continue
        counter = counters[key.entity_type]
        if counter > MAX_ID:
            raise PlanningHold("INT_OVERFLOW")
        if counter in used[key.entity_type]:
            raise PlanningHold("ALLOCATOR_COLLISION")
        assigned[key] = counter
        inserted[key] = counter
        counters[key.entity_type] = counter + 1
        used[key.entity_type].add(counter)
    return AllocationPlan(tuple(sorted(assigned.items())),
                          tuple(sorted(inserted.items())), tuple(sorted(counters.items())))


@dataclass(frozen=True)
class BatchFence:
    hospital_id: str
    source_system: str
    batch_id: str
    manifest_sha256: str
    mapping_sha256: str
    writer_version: str
    person_count: int
    visit_count: int

    def __post_init__(self):
        for field in ("hospital_id", "source_system", "batch_id", "writer_version"):
            clean(getattr(self, field), field)
        if (not isinstance(self.manifest_sha256, str) or not SHA.fullmatch(self.manifest_sha256)
                or not isinstance(self.mapping_sha256, str) or not SHA.fullmatch(self.mapping_sha256)):
            raise PlanningHold("INVALID_BATCH_SHA256")
        if (type(self.person_count) is not int or self.person_count < 1
                or type(self.visit_count) is not int or self.visit_count < 0):
            raise PlanningHold("INVALID_BATCH_COUNTS")


@dataclass(frozen=True)
class Receipt:
    fence: BatchFence
    status: str
    actual_person_count: int | None
    actual_visit_count: int | None


def replay(fence: BatchFence, receipts: Sequence[Receipt], *,
           independently_verified: bool) -> str:
    relevant = [r for r in receipts if
                (r.fence.hospital_id, r.fence.source_system, r.fence.batch_id) ==
                (fence.hospital_id, fence.source_system, fence.batch_id)]
    if len(relevant) > 1:
        raise PlanningHold("DUPLICATE_BATCH_LEDGER")
    if not relevant:
        return "NEW"
    item = relevant[0]
    if item.fence != fence:
        raise PlanningHold("CONFLICTING_BATCH_HASH_OR_COUNTS")
    if (item.status != "COMMITTED" or item.actual_person_count != fence.person_count
            or item.actual_visit_count != fence.visit_count):
        raise PlanningHold("INCOMPLETE_BATCH_RECEIPT")
    if not independently_verified:
        raise PlanningHold("GOLD_READBACK_REQUIRED")
    return "VERIFIED_SKIP"
