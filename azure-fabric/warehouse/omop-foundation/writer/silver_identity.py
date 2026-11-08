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

    # Canonical FK is exact; casefold collisions are rejected by plan_ids.
    person_sources = {key.source_business_key for key in patient_keys}
    for row in encounters:
        parent = row.get("source_person_id")
        clean(parent, "source_business_key")
        if parent not in person_sources:
            raise PlanningHold("SILVER_ENCOUNTER_PERSON_FK_MISSING")
    allocation = plan_ids(
        [*patient_keys, *visit_keys], existing, next_free, gold_ids,
    )
    assigned = dict(allocation.assigned)
    person_by_source = {
        key.source_business_key: assigned[key] for key in patient_keys
    }
    persons = tuple(sorted(
        (key.source_business_key, assigned[key]) for key in patient_keys
    ))
    visits = tuple(sorted(
        (key.source_business_key, assigned[key], person_by_source[row["source_person_id"]])
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


# Explicit bridge: SQL reader supplies FULL rows, not merely six SHA strings.
# This is pure source-level reconciliation. Only the trusted external caller
# can prove that rows were collected from two newly authenticated connections.
_F2_WAREHOUSE_ID = "7a6d08da-278d-4603-8a3b-28640110984c"
_F2_ROWS = {"identity_map": 7, "allocator": 3, "person": 1, "visit": 2,
            "ledger": 11, "audit": 5}
_F2_KINDS = {"PERSON": "cdm.person",
             "VISIT_OCCURRENCE": "cdm.visit_occurrence"}


@dataclass(frozen=True)
class F2SnapshotBridge:
    """Physical table row digest and Shared preview fingerprint are DISTINCT."""
    snapshot: object
    physical_snapshot_sha256: str
    table_sha256: tuple[tuple[str, str], ...]
    status: str = "F2_SQL_ROWS_TO_SHARED_SNAPSHOT_SOURCE_ONLY_NOT_AUTHENTICATED"

    @property
    def shared_snapshot_fingerprint(self) -> str:
        return self.snapshot.fingerprint


def bridge_f2_sql_readback_rows(
    rows: Mapping[str, Sequence[tuple]],
    *, first_table_sha256: Mapping[str, str],
    second_table_sha256: Mapping[str, str],
    warehouse_id: str,
) -> F2SnapshotBridge:
    """Adapt six FULL physical SQL SELECT rowsets to the ONE Shared Snapshot.

    Table fingerprints use the exact existing Self-Runner bounded_table v1
    length-prefixed UTF-8 JSON encoding. Recompute from provided raw rows and
    demand TWO identical independent connection hashes; hashes without raw
    rows are rejected. The caller is responsible for OIDC/Warehouse DB identity,
    proving genuinely independent SQL connections, real Approved Silver and
    short-lived freshness. No SQL/network/Cloud I/O or approval is performed.
    """
    import hashlib
    import json
    import re

    from healthcare_data_engine.identity.preview import (
        IdentitySnapshot, IdentityPreviewHold, PersistedIdentity,
    )
    from healthcare_data_engine.mapping.omop.registry import DerivedRowKey

    if (warehouse_id != _F2_WAREHOUSE_ID
            or not isinstance(rows, Mapping)
            or not isinstance(first_table_sha256, Mapping)
            or not isinstance(second_table_sha256, Mapping)
            or set(rows) != set(_F2_ROWS)
            or set(first_table_sha256) != set(_F2_ROWS)
            or set(second_table_sha256) != set(_F2_ROWS)):
        raise PlanningHold("F2_PHYSICAL_SNAPSHOT_SCOPE_HOLD")

    normalized = {}
    hashes = {}
    for table, width in _F2_ROWS.items():
        supplied = rows[table]
        if not isinstance(supplied, (list, tuple)) or len(supplied) > 20000:
            raise PlanningHold("F2_PHYSICAL_ROW_BOUND_OR_TYPE_HOLD")
        digest = hashlib.sha256()
        records = []
        for raw in supplied:
            if not isinstance(raw, (list, tuple)) or len(raw) != width:
                raise PlanningHold("F2_PHYSICAL_SQL_ROW_SHAPE_HOLD")
            row = tuple(raw)
            try:
                encoded = json.dumps(row, ensure_ascii=False,
                                     separators=(",", ":"), default=str).encode("utf-8")
            except (TypeError, ValueError, UnicodeError):
                raise PlanningHold("F2_PHYSICAL_ROW_ENCODING_HOLD") from None
            digest.update(len(encoded).to_bytes(4, "big") + encoded)
            records.append(row)
        expected = digest.hexdigest()
        if (first_table_sha256[table] != expected
                or second_table_sha256[table] != expected
                or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
            raise PlanningHold("F2_PHYSICAL_TWO_CONNECTION_SHA_MISMATCH")
        hashes[table] = expected
        normalized[table] = tuple(records)

    mapping = []
    for entity, hospital, source, key, number, first_batch, version in normalized["identity_map"]:
        if (entity not in _F2_KINDS
                or any(not isinstance(v, str) or not v for v in
                       (hospital, source, key, first_batch, version))):
            raise PlanningHold("F2_PHYSICAL_MAP_FIELDS_HOLD")
        mapping.append(PersistedIdentity(
            DerivedRowKey(_F2_KINDS[entity], hospital, source, key), number))

    alloc = normalized["allocator"]
    gold = {
        "cdm.person": tuple(r[0] for r in normalized["person"]),
        "cdm.visit_occurrence": tuple(r[0] for r in normalized["visit"]),
    }
    for _, person_id in normalized["visit"]:
        if person_id not in gold["cdm.person"]:
            raise PlanningHold("F2_PHYSICAL_VISIT_PARENT_MISSING")

    if not alloc:
        # The original real Warehouse F2 snapshot was virgin: ALL SIX empty.
        # Never silently infer a new allocator when any durable state exists.
        if any(normalized.values()):
            raise PlanningHold("F2_PHYSICAL_ALLOCATOR_MISSING_WITH_STATE")
        next_free = (("cdm.person", 1), ("cdm.visit_occurrence", 1))
    else:
        if len(alloc) != len(_F2_KINDS):
            raise PlanningHold("F2_PHYSICAL_ALLOCATOR_INCOMPLETE")
        seen = set()
        counter = []
        for entity, value, version in alloc:
            if (entity not in _F2_KINDS or entity in seen
                    or not isinstance(version, str) or not version):
                raise PlanningHold("F2_PHYSICAL_ALLOCATOR_INVALID")
            seen.add(entity)
            counter.append((_F2_KINDS[entity], value))
        next_free = tuple(sorted(counter))

    ledger_keys = [(row[0], row[1], row[2]) for row in normalized["ledger"]]
    audit_keys = [(row[0], row[1]) for row in normalized["audit"]]
    if (len(ledger_keys) != len(set(ledger_keys))
            or len(audit_keys) != len(set(audit_keys))):
        raise PlanningHold("F2_PHYSICAL_LEDGER_OR_AUDIT_DUPLICATE")

    # This digest binds all six physical table hashes and the actual target
    # Warehouse, not a substitute for Shared's logical snapshot fingerprint.
    raw_digest = json.dumps({
        "warehouse_id": warehouse_id,
        "schema": "fabric-f2-six-table-physical-sha256-v1",
        "tables": sorted(hashes.items()),
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    physical = hashlib.sha256(raw_digest).hexdigest()
    try:
        shared = IdentitySnapshot(
            tuple(mapping), next_free,
            tuple(sorted((k, v) for k, v in gold.items())),
            hashes["ledger"], physical,
        )
    except IdentityPreviewHold:
        raise PlanningHold("F2_PHYSICAL_SHARED_SNAPSHOT_CONFLICT") from None
    return F2SnapshotBridge(
        shared, physical, tuple(sorted(hashes.items())))
