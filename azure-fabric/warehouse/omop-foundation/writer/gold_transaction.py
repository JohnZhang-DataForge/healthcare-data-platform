"""F2 Warehouse Gold transaction adapter (SOURCE_ONLY until live authorization).

One approved source/identity/clinical payload, one externally fenced Warehouse
writer, one DB-API connection and one SQL transaction. Never call this from
untrusted Notebook parameters. A COMMIT acknowledgement alone is *not* Gold
acceptance; independently verify with a different SQL connection.

The original identity_plan owns all allocation and ledger replay policy.
Neither this adapter nor Fabric invents Concept mappings or OMOP IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from typing import Callable, Mapping, Sequence

from identity_plan import BatchFence, IdentityKey, PlanningHold, plan_ids, replay, Receipt, SHA

PERSON_COLS = (
    "person_id", "gender_concept_id", "year_of_birth", "month_of_birth",
    "day_of_birth", "birth_datetime", "race_concept_id",
    "ethnicity_concept_id", "location_id", "provider_id", "care_site_id",
    "person_source_value", "gender_source_value", "gender_source_concept_id",
    "race_source_value", "race_source_concept_id",
    "ethnicity_source_value", "ethnicity_source_concept_id",
)
VISIT_COLS = (
    "visit_occurrence_id", "person_id", "visit_concept_id",
    "visit_start_date", "visit_start_datetime", "visit_end_date",
    "visit_end_datetime", "visit_type_concept_id", "provider_id",
    "care_site_id", "visit_source_value", "visit_source_concept_id",
    "admitted_from_concept_id", "admitted_from_source_value",
    "discharged_to_concept_id", "discharged_to_source_value",
    "preceding_visit_occurrence_id",
)
P_EXTRA = {"identity_state"}
V_EXTRA = {"source_system", "source_encounter_id", "source_person_id",
           "identity_state", "parent_identity_state"}
ENTITY = {"PERSON": ("cdm.person", "person_id"),
          "VISIT_OCCURRENCE": ("cdm.visit_occurrence", "visit_occurrence_id")}
MAX_ROWS = 20000


class GoldHold(PlanningHold):
    """Fail closed; diagnostic messages contain no patient values."""


@dataclass(frozen=True)
class GoldBatch:
    fence: BatchFence
    identities: tuple[tuple[IdentityKey, int], ...]
    persons: tuple[Mapping[str, object], ...]
    visits: tuple[Mapping[str, object], ...]
    mapping_version: str
    clinical_review_sha256: str
    license_review_sha256: str
    candidate_approval_sha256: str


def _require_batch(batch: GoldBatch) -> None:
    if not isinstance(batch, GoldBatch):
        raise GoldHold("GOLD_BATCH_TYPE")
    if (len(batch.persons) != batch.fence.person_count
            or len(batch.visits) != batch.fence.visit_count
            or not 0 < len(batch.persons) + len(batch.visits) <= MAX_ROWS
            or not isinstance(batch.mapping_version, str)
            or not 0 < len(batch.mapping_version) <= 32
            or any(not isinstance(s, str) or not SHA.fullmatch(s) for s in
                   (batch.clinical_review_sha256, batch.license_review_sha256,
                    batch.candidate_approval_sha256))):
        raise GoldHold("GOLD_UNVERIFIED_SCOPE_OR_EVIDENCE")
    ids = dict(batch.identities)
    if len(ids) != len(batch.identities) or len(ids) != len(batch.persons) + len(batch.visits):
        raise GoldHold("GOLD_IDENTITY_CARDINALITY")
    for key, value in batch.identities:
        if (not isinstance(key, IdentityKey)
                or key.hospital_id != batch.fence.hospital_id
                or key.source_system != batch.fence.source_system
                or type(value) is not int or not 1 <= value <= 2147483647):
            raise GoldHold("GOLD_IDENTITY_SCOPE_OR_INT")
    pk_person = set()
    pk_visit = set()
    for row in batch.persons:
        if (not isinstance(row, Mapping)
                or not set(row).issubset(set(PERSON_COLS) | P_EXTRA)
                or any(k not in row for k in ("person_id", "person_source_value",
                    "gender_concept_id", "race_concept_id", "ethnicity_concept_id",
                    "year_of_birth"))):
            raise GoldHold("GOLD_PERSON_SCHEMA")
        key = IdentityKey("PERSON", batch.fence.hospital_id,
                          batch.fence.source_system, row["person_source_value"])
        if (ids.get(key) != row["person_id"]
                or row["person_id"] in pk_person
                or row.get("identity_state") not in ("PERSISTED", "PROVISIONAL")
                or any(type(row[k]) is not int or row[k] <= 0 for k in
                       ("gender_concept_id", "race_concept_id",
                        "ethnicity_concept_id", "year_of_birth"))):
            raise GoldHold("GOLD_PERSON_MAP_OR_PROFILE")
        pk_person.add(row["person_id"])
    for row in batch.visits:
        if (not isinstance(row, Mapping)
                or not set(row).issubset(set(VISIT_COLS) | V_EXTRA)
                or any(k not in row for k in ("visit_occurrence_id", "person_id",
                    "source_encounter_id", "source_person_id", "source_system",
                    "visit_concept_id", "visit_type_concept_id",
                    "visit_start_date", "visit_end_date"))):
            raise GoldHold("GOLD_VISIT_SCHEMA")
        key = IdentityKey("VISIT_OCCURRENCE", batch.fence.hospital_id,
                          batch.fence.source_system, row["source_encounter_id"])
        if (ids.get(key) != row["visit_occurrence_id"]
                or row["visit_occurrence_id"] in pk_visit
                or row["person_id"] not in pk_person
                or row["source_system"] != batch.fence.source_system
                or ids.get(IdentityKey("PERSON", batch.fence.hospital_id,
                        batch.fence.source_system, row["source_person_id"])) != row["person_id"]
                or row.get("identity_state") not in ("PERSISTED", "PROVISIONAL")
                or row.get("parent_identity_state") not in ("PERSISTED", "PROVISIONAL")
                or type(row["visit_concept_id"]) is not int or row["visit_concept_id"] <= 0
                or type(row["visit_type_concept_id"]) is not int
                or row["visit_type_concept_id"] <= 0):
            raise GoldHold("GOLD_VISIT_MAP_FK_OR_PROFILE")
        pk_visit.add(row["visit_occurrence_id"])


def _rows(cursor, query: str, params: tuple = ()) -> list[tuple]:
    cursor.execute(query, params)
    result = [tuple(row) for row in cursor.fetchall()]
    if len(result) > MAX_ROWS:
        raise GoldHold("GOLD_SNAPSHOT_SCAN_BOUND")
    return result


def _snapshot(cursor):
    raw = _rows(cursor, "SELECT entity_type, hospital_id, source_system, "
                "source_business_key, omop_id FROM etl.identity_map")
    existing = [(IdentityKey(*row[:4]), row[4]) for row in raw]
    alloc = _rows(cursor, "SELECT entity_type, next_omop_id FROM etl.id_allocator")
    if len(alloc) != len({row[0] for row in alloc}):
        raise GoldHold("GOLD_DUPLICATE_ALLOCATOR")
    gold_ids = {
        kind: [r[0] for r in _rows(cursor, "SELECT " + key + " FROM " + table)]
        for kind, (table, key) in ENTITY.items()
    }
    if not alloc:
        if existing or any(gold_ids.values()):
            raise GoldHold("GOLD_MISSING_ALLOCATOR_WITH_PERSISTED_ROWS")
        next_free = {kind: 1 for kind in ENTITY}
    else:
        next_free = dict(alloc)
    return existing, next_free, gold_ids


def _ledger(cursor, fence: BatchFence) -> list[Receipt]:
    recs = _rows(cursor,
        "SELECT hospital_id, source_system, batch_id, source_manifest_sha256, "
        "mapping_profile_sha256, writer_version, batch_status, "
        "expected_person_count, expected_visit_count, committed_person_count, "
        "committed_visit_count FROM etl.batch_ledger "
        "WHERE hospital_id=? AND source_system=? AND batch_id=?",
        (fence.hospital_id, fence.source_system, fence.batch_id))
    return [Receipt(BatchFence(*r[:6], r[7], r[8]), r[6], r[9], r[10]) for r in recs]


def _insert_rows(cursor, table: str, cols: tuple[str, ...],
                 records: Sequence[Mapping[str, object]]) -> None:
    active = tuple(k for k in cols if any(k in row for row in records))
    sql = ("INSERT INTO " + table + " (" + ", ".join(active) + ") VALUES ("
           + ", ".join("?" for _ in active) + ")")
    for row in records:
        cursor.execute(sql, tuple(row.get(k) for k in active))


def _compare_rows(cursor, table: str, cols: tuple[str, ...],
                  expected: Sequence[Mapping[str, object]], key: str) -> bool:
    if not expected:
        return False
    active = tuple(k for k in cols if any(k in r for r in expected))
    query = "SELECT " + ", ".join(active) + " FROM " + table
    actual = _rows(cursor, query)
    requested = {row[key]: row for row in expected}
    found = {}
    for raw in actual:
        row = dict(zip(active, raw))
        if row[key] in requested:
            if row[key] in found:
                return False
            found[row[key]] = row
    if set(found) != set(requested):
        return False
    def normalize(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value
    return all(all(normalize(found[ident][col]) == normalize(row.get(col))
                   for col in active) for ident, row in requested.items())


def independent_gold_readback(new_connection: Callable[[], object],
                              batch: GoldBatch) -> bool:
    """Must use a freshly authenticated SQL connection, including for replay."""
    _require_batch(batch)
    conn = new_connection()
    try:
        cursor = conn.cursor()
        existing, _, gold = _snapshot(cursor)
        if (any(dict(existing).get(k) != v for k, v in batch.identities)
                or any(len(gold[kind]) != len(set(gold[kind])) for kind in ENTITY)
                or not _compare_rows(cursor, "cdm.person", PERSON_COLS,
                                      batch.persons, "person_id")
                or not _compare_rows(cursor, "cdm.visit_occurrence", VISIT_COLS,
                                      batch.visits, "visit_occurrence_id")):
            return False
        if replay(batch.fence, _ledger(cursor, batch.fence),
                  independently_verified=True) != "VERIFIED_SKIP":
            return False
        audit = _rows(cursor, "SELECT check_name, expected_count, observed_count, "
            "check_status FROM audit.omop_commit_check WHERE batch_id=?",
            (batch.fence.batch_id,))
        return (len(audit) == 2
                and {(r[0], r[1], r[2], r[3]) for r in audit} ==
                {("PERSON", batch.fence.person_count, batch.fence.person_count, "PASS"),
                 ("VISIT_OCCURRENCE", batch.fence.visit_count,
                  batch.fence.visit_count, "PASS")})
    except (GoldHold, PlanningHold):
        return False
    finally:
        conn.close()


def execute_gold_transaction(connection, batch: GoldBatch, *,
                             single_writer_fence: Callable[[], bool],
                             release_gate: Callable[[GoldBatch], bool]) -> str:
    """Writes only after trusted external review/fence. No automatic retry.

    Caller must separately authenticate reviewer, license, real P3 Candidate
    Approval, full F2 physical snapshot, target Warehouse, and exclusive
    cross-workflow writer lease. Boolean/SHA supplied from Notebook parameters
    is *never* a trusted release_gate. A true return is not clinical signoff.
    """
    _require_batch(batch)  # reject invalid mappings before any SQL
    if (not callable(single_writer_fence) or not callable(release_gate)
            or single_writer_fence() is not True
            or release_gate(batch) is not True):
        raise GoldHold("GOLD_RELEASE_OR_SINGLE_WRITER_HOLD")
    cursor = connection.cursor()
    cursor.execute("BEGIN TRANSACTION")
    committing = False
    try:
        if single_writer_fence() is not True or release_gate(batch) is not True:
            raise GoldHold("GOLD_FENCE_LOST")
        existing, next_free, gold = _snapshot(cursor)
        receipts = _ledger(cursor, batch.fence)
        # Do not SKIP based on an ACK or ledger row; readback must happen on
        # another SQL connection. Even an exact existing receipt is HOLD here.
        if receipts:
            replay(batch.fence, receipts, independently_verified=False)
            raise GoldHold("GOLD_EXISTING_RECEIPT_REQUIRES_INDEPENDENT_READBACK")
        planned = plan_ids([k for k, _ in batch.identities], existing, next_free, gold)
        if dict(planned.assigned) != dict(batch.identities):
            raise GoldHold("GOLD_CANDIDATE_IDS_VS_TRANSACTION_SNAPSHOT")
        if len(planned.inserted) != len(batch.identities):
            raise GoldHold("GOLD_PARTIAL_PERSISTED_MAPPING_REQUIRES_REVIEW")
        now = datetime.utcnow()
        for key, omop_id in planned.inserted:
            cursor.execute(
                "INSERT INTO etl.identity_map (entity_type, hospital_id, "
                "source_system, source_business_key, omop_id, first_batch_id, "
                "mapping_version, created_at_utc) VALUES (?,?,?,?,?,?,?,?)",
                (key.entity_type, key.hospital_id, key.source_system,
                 key.source_business_key, omop_id, batch.fence.batch_id,
                 batch.mapping_version, now))
        for kind, nxt in planned.next_free:
            if kind in next_free and any(k == kind for k, _ in
                                         _rows(cursor, "SELECT entity_type, next_omop_id "
                                               "FROM etl.id_allocator")):
                cursor.execute("UPDATE etl.id_allocator SET next_omop_id=?, "
                    "mapping_version=?, updated_at_utc=? WHERE entity_type=? "
                    "AND next_omop_id=?",
                    (nxt, batch.mapping_version, now, kind, next_free[kind]))
                if cursor.rowcount != 1:
                    raise GoldHold("GOLD_ALLOCATOR_CONCURRENT_CHANGE")
            else:
                cursor.execute("INSERT INTO etl.id_allocator "
                    "(entity_type, next_omop_id, mapping_version, updated_at_utc) "
                    "VALUES (?,?,?,?)", (kind, nxt, batch.mapping_version, now))
        _insert_rows(cursor, "cdm.person", PERSON_COLS, batch.persons)
        _insert_rows(cursor, "cdm.visit_occurrence", VISIT_COLS, batch.visits)
        cursor.execute("INSERT INTO etl.batch_ledger (hospital_id, source_system, "
            "batch_id, source_manifest_sha256, mapping_profile_sha256, writer_version, "
            "batch_status, expected_person_count, expected_visit_count, "
            "committed_person_count, committed_visit_count, committed_at_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (batch.fence.hospital_id, batch.fence.source_system,
             batch.fence.batch_id, batch.fence.manifest_sha256,
             batch.fence.mapping_sha256, batch.fence.writer_version,
             "COMMITTED", batch.fence.person_count, batch.fence.visit_count,
             batch.fence.person_count, batch.fence.visit_count, now))
        for name, count in (("PERSON", batch.fence.person_count),
                            ("VISIT_OCCURRENCE", batch.fence.visit_count)):
            cursor.execute("INSERT INTO audit.omop_commit_check "
                "(batch_id, check_name, expected_count, observed_count, "
                "check_status, checked_at_utc) VALUES (?,?,?,?,?,?)",
                (batch.fence.batch_id, name, count, count, "PASS", now))
        if single_writer_fence() is not True:
            raise GoldHold("GOLD_FENCE_LOST_BEFORE_COMMIT")
        committing = True
        cursor.execute("COMMIT TRANSACTION")
        return "GOLD_COMMIT_ACK_VERIFY_INDEPENDENT_SQL_NOT_ACCEPTED"
    except Exception:
        if committing:
            # Connection/ACK may be uncertain; NEVER retry or assume rollback.
            return "GOLD_UNKNOWN_COMMIT_ACK_VERIFY_READONLY"
        connection.rollback()
        raise
