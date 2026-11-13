"""Pure multi-entity ID snapshot and existing Fabric F2 planner result bridge.

The current single allocator remains Fabric F2 identity_plan.plan_ids.
This module validates its output; it NEVER reserves IDs, reads SQL, or grants
Gold COMMIT. Physical snapshot readback and single-writer locking belong to
the Warehouse runtime, which MUST re-read all state inside its transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, DerivedRowKey, EntityRegistry,
)

MAX_OMOP_INT = 2_147_483_647
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_F2_TARGETS = {"PERSON": "cdm.person", "VISIT_OCCURRENCE": "cdm.visit_occurrence"}


class IdentityPreviewHold(ValueError):
    """Failure reason code only; never emit source/business identifiers."""


def _id(value: object, *, next_free: bool = False) -> int:
    if type(value) is not int or not 1 <= value <= MAX_OMOP_INT + int(next_free):
        raise IdentityPreviewHold("IDENTITY_INT_RANGE_INVALID")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise IdentityPreviewHold("IDENTITY_SNAPSHOT_SHA_NOT_PINNED")
    return value


def _targets(registry: EntityRegistry) -> set[str]:
    if not isinstance(registry, EntityRegistry):
        raise IdentityPreviewHold("IDENTITY_REGISTRY_INVALID")
    return {t.table for definition in registry.definitions for t in definition.targets}


@dataclass(frozen=True)
class PersistedIdentity:
    key: DerivedRowKey
    omop_id: int

    def __post_init__(self):
        if not isinstance(self.key, DerivedRowKey):
            raise IdentityPreviewHold("IDENTITY_KEY_INVALID")
        _id(self.omop_id)


@dataclass(frozen=True)
class IdentitySnapshot:
    """Complete *supplied* Map/Gold/Allocator/Ledger snapshot, not cloud proof.

    The caller owns independent SQL evidence of completeness and physical
    readback. A 64-char digest alone does not establish clinical approval,
    readback, transaction locking or persistence.
    """
    existing: tuple[PersistedIdentity, ...]
    next_free: tuple[tuple[str, int], ...]
    gold_ids: tuple[tuple[str, tuple[int, ...]], ...]
    ledger_sha256: str
    readback_sha256: str
    registry: EntityRegistry = DEFAULT_OMOP_REGISTRY

    def __post_init__(self):
        _sha(self.ledger_sha256)
        _sha(self.readback_sha256)
        expected = _targets(self.registry)
        if (not isinstance(self.existing, tuple)
                or any(not isinstance(x, PersistedIdentity) for x in self.existing)
                or not isinstance(self.next_free, tuple)
                or not isinstance(self.gold_ids, tuple)
                or any(not isinstance(item, tuple) or len(item) != 2
                       for item in (*self.next_free, *self.gold_ids))):
            raise IdentityPreviewHold("IDENTITY_SNAPSHOT_SCHEMA_INVALID")
        counter = dict(self.next_free)
        physical = dict(self.gold_ids)
        if (len(counter) != len(self.next_free)
                or len(physical) != len(self.gold_ids)
                or set(counter) != expected or set(physical) != expected):
            raise IdentityPreviewHold("IDENTITY_SNAPSHOT_INCOMPLETE")
        for value in counter.values():
            _id(value, next_free=True)
        folded = set()
        map_ids = {name: set() for name in expected}
        for entry in self.existing:
            table = entry.key.target_table
            if table not in expected:
                raise IdentityPreviewHold("IDENTITY_SNAPSHOT_TARGET_UNREGISTERED")
            if entry.key.folded() in folded:
                raise IdentityPreviewHold("IDENTITY_PERSISTED_KEY_COLLISION")
            folded.add(entry.key.folded())
            if entry.omop_id in map_ids[table]:
                raise IdentityPreviewHold("IDENTITY_PERSISTED_ID_COLLISION")
            map_ids[table].add(entry.omop_id)
        for table, ids in physical.items():
            if not isinstance(ids, tuple) or any(type(x) is not int for x in ids):
                raise IdentityPreviewHold("IDENTITY_GOLD_SCHEMA_INVALID")
            values = [_id(x) for x in ids]
            if len(values) != len(set(values)) or set(values) != map_ids[table]:
                raise IdentityPreviewHold("IDENTITY_MAP_GOLD_DRIFT")
            if map_ids[table] and counter[table] <= max(map_ids[table]):
                raise IdentityPreviewHold("IDENTITY_ALLOCATOR_REWIND")

    @property
    def fingerprint(self) -> str:
        metadata = sorted([
            [d.entity_key, d.definition_version, d.canonical_contract_sha256,
             sorted(t.table for t in d.targets)] for d in self.registry.definitions
        ])
        payload = {
            "contract": "omop-identity-snapshot-v1",
            "registry": metadata,
            "map": sorted([list(row.key.folded()) + [row.omop_id]
                           for row in self.existing]),
            "allocators": sorted(self.next_free),
            "gold": sorted((table, sorted(ids)) for table, ids in self.gold_ids),
            "ledger_sha256": self.ledger_sha256,
            "readback_sha256": self.readback_sha256,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def persisted(self) -> dict[DerivedRowKey, int]:
        return {entry.key: entry.omop_id for entry in self.existing}


@dataclass(frozen=True)
class PlannedIdentity:
    key: DerivedRowKey
    omop_id: int
    state: str
    snapshot_fingerprint: str

    def __post_init__(self):
        if not isinstance(self.key, DerivedRowKey):
            raise IdentityPreviewHold("IDENTITY_PLANNED_KEY_INVALID")
        _id(self.omop_id)
        if self.state not in ("PERSISTED", "PROVISIONAL"):
            raise IdentityPreviewHold("IDENTITY_PLANNED_STATE_INVALID")
        _sha(self.snapshot_fingerprint)


@dataclass(frozen=True)
class IdentityPreview:
    identities: tuple[PlannedIdentity, ...]
    snapshot_fingerprint: str
    next_free: tuple[tuple[str, int], ...]
    status: str = "ID_PREVIEW_ONLY_NOT_PERSISTED"

    def for_key(self, key: DerivedRowKey) -> PlannedIdentity:
        for item in self.identities:
            if item.key == key:
                return item
        raise IdentityPreviewHold("IDENTITY_PREVIEW_KEY_NOT_FOUND")


def verify_allocation_proposal(
    snapshot: IdentitySnapshot,
    assigned: Sequence[tuple[DerivedRowKey, int]],
    inserted: Sequence[tuple[DerivedRowKey, int]],
    proposed_next: Mapping[str, int],
) -> IdentityPreview:
    """Check F2's proposal, NOT implement a second allocator.

    Enforce monotonic, contiguous new IDs in the same source-key ordering as
    F2. Any changed Map/Gold/Ledger/Allocator readback must invalidate this
    fingerprint and make the eventual writer HOLD until re-planned.
    """
    if not isinstance(snapshot, IdentitySnapshot):
        raise IdentityPreviewHold("IDENTITY_SNAPSHOT_INVALID")
    tables = _targets(snapshot.registry)
    if not isinstance(proposed_next, Mapping) or set(proposed_next) != tables:
        raise IdentityPreviewHold("IDENTITY_PROPOSAL_COUNTERS_INVALID")
    if (not isinstance(assigned, (tuple, list)) or not assigned
            or not isinstance(inserted, (tuple, list))):
        raise IdentityPreviewHold("IDENTITY_PROPOSAL_INVALID")
    old = snapshot.persisted()
    original_next = dict(snapshot.next_free)

    def collect(rows):
        found = {}
        folded = set()
        for item in rows:
            if (not isinstance(item, tuple) or len(item) != 2
                    or not isinstance(item[0], DerivedRowKey)
                    or item[0].target_table not in tables):
                raise IdentityPreviewHold("IDENTITY_PROPOSAL_KEY_INVALID")
            key, number = item
            _id(number)
            if key in found or key.folded() in folded:
                raise IdentityPreviewHold("IDENTITY_PROPOSAL_KEY_COLLISION")
            found[key] = number
            folded.add(key.folded())
        return found

    all_assigned = collect(assigned)
    new = collect(inserted)
    if not set(new).issubset(all_assigned):
        raise IdentityPreviewHold("IDENTITY_PROPOSED_SET_INVALID")
    for key, number in all_assigned.items():
        if key in old:
            if old[key] != number or key in new:
                raise IdentityPreviewHold("IDENTITY_PERSISTED_ID_CHANGED")
        elif (new.get(key) != number
              or any(key.folded() == existing.folded() for existing in old)):
            raise IdentityPreviewHold("IDENTITY_PROVISIONAL_SET_INVALID")
    for table in sorted(tables):
        per_table = sorted(
            ((key, number) for key, number in new.items()
             if key.target_table == table),
            key=lambda item: (item[0].hospital_id, item[0].source_system,
                              item[0].source_business_key, item[0].derived_role,
                              item[0].derived_discriminator),
        )
        expected = list(range(original_next[table],
                              original_next[table] + len(per_table)))
        if (expected and expected[-1] > MAX_OMOP_INT
                or [number for _, number in per_table] != expected
                or type(proposed_next[table]) is not int
                or proposed_next[table] != original_next[table] + len(per_table)):
            raise IdentityPreviewHold("IDENTITY_PROPOSED_COUNTER_DRIFT")
    pinned = snapshot.fingerprint
    planned = tuple(
        PlannedIdentity(key, number, "PERSISTED" if key in old else "PROVISIONAL",
                        pinned)
        for key, number in sorted(
            all_assigned.items(),
            key=lambda item: item[0].folded(),
        )
    )
    return IdentityPreview(planned, pinned, tuple(sorted(proposed_next.items())))


def bridge_f2_person_visit_allocation(
    f2_allocation: Any, snapshot: IdentitySnapshot,
) -> IdentityPreview:
    """Translate the EXISTING Fabric F2 AllocationPlan without importing it.

    Future entity kinds are held, not implicitly allocated with this adapter.
    """
    if set(dict(snapshot.next_free)) != set(_F2_TARGETS.values()):
        raise IdentityPreviewHold("IDENTITY_F2_SCOPE_PERSON_VISIT_ONLY")
    if not all(hasattr(f2_allocation, attr)
               for attr in ("assigned", "inserted", "next_free")):
        raise IdentityPreviewHold("IDENTITY_F2_ALLOCATION_INVALID")

    def rows(source: Iterable[tuple[Any, int]]):
        result = []
        for legacy_key, number in source:
            kind = getattr(legacy_key, "entity_type", None)
            if kind not in _F2_TARGETS:
                raise IdentityPreviewHold("IDENTITY_F2_KIND_NOT_REVIEWED")
            result.append((
                DerivedRowKey(_F2_TARGETS[kind], legacy_key.hospital_id,
                              legacy_key.source_system, legacy_key.source_business_key),
                number,
            ))
        return tuple(result)

    try:
        next_free = {_F2_TARGETS[kind]: number
                     for kind, number in f2_allocation.next_free}
    except (KeyError, TypeError, ValueError) as exc:
        raise IdentityPreviewHold("IDENTITY_F2_COUNTERS_INVALID") from exc
    if len(next_free) != len(_F2_TARGETS):
        raise IdentityPreviewHold("IDENTITY_F2_COUNTERS_INVALID")
    return verify_allocation_proposal(snapshot, rows(f2_allocation.assigned),
                                      rows(f2_allocation.inserted), next_free)


# Business name for the existing Fabric AllocationPlan-to-IdentityPreview
# adapter. Historical F2 callers remain byte-for-byte compatible.
adapt_person_visit_allocation_preview = bridge_f2_person_visit_allocation


def require_preview_snapshot_unchanged(
    preview: IdentityPreview, current_snapshot: IdentitySnapshot,
) -> IdentityPreview:
    """Fail closed when a freshly supplied full snapshot no longer matches.

    This pure comparison is mandatory at the eventual Writer boundary but is
    NOT a substitute for independent Warehouse readback or writer fencing.
    """
    if (not isinstance(preview, IdentityPreview)
            or preview.status != "ID_PREVIEW_ONLY_NOT_PERSISTED"
            or not isinstance(current_snapshot, IdentitySnapshot)):
        raise IdentityPreviewHold("IDENTITY_PREVIEW_STATE_INVALID")
    if (preview.snapshot_fingerprint != current_snapshot.fingerprint
            or any(item.snapshot_fingerprint != preview.snapshot_fingerprint
                   for item in preview.identities)):
        raise IdentityPreviewHold("IDENTITY_SNAPSHOT_CHANGED_BEFORE_COMMIT")
    return preview
