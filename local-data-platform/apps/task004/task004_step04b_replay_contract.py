"""TASK004 STEP04B: pure simulation contract; never connects to databases.

The batch identity, immutable row content, and stable business keys are separate.
This module models fail-closed decisions; it is not a production loader.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json
import re


class Conflict(ValueError):
    pass


class Retryable(RuntimeError):
    pass


def digest(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Batch:
    batch_id: str
    manifest_sha256: str
    source_system: str
    person_uri: str
    visit_uri: str

    def __post_init__(self):
        if not self.batch_id or not re.fullmatch(r"[0-9a-f]{64}", self.manifest_sha256):
            raise Conflict("invalid_batch_identity")
        if self.source_system != "synthea":
            raise Conflict("unsupported_source_system")
        if not all(self.batch_id in u and u.startswith("s3a://health-processing/") for u in (self.person_uri, self.visit_uri)):
            raise Conflict("processing_lineage_invalid")


@dataclass
class Store:
    batches: dict = field(default_factory=dict)
    # Stable keys are (source_system, source_id), NEVER (batch_id, source_id).
    person: dict = field(default_factory=dict)
    visit: dict = field(default_factory=dict)
    next_person_id: int = 114
    next_visit_id: int = 5800
    stage: dict = field(default_factory=dict)
    locks: set = field(default_factory=set)
    events: list = field(default_factory=list)

    def acquire(self, batch_id):
        if batch_id in self.locks:
            raise Retryable("batch_lock_busy")
        self.locks.add(batch_id)

    def release(self, batch_id):
        self.locks.discard(batch_id)

    def register(self, batch):
        identity = (batch.manifest_sha256, batch.source_system, batch.person_uri, batch.visit_uri)
        old = self.batches.get(batch.batch_id)
        if old is not None and old["identity"] != identity:
            raise Conflict("same_batch_different_manifest_or_lineage")
        if old is None:
            self.batches[batch.batch_id] = {"identity": identity, "state": "REGISTERED", "person": None, "visit": None}
        return self.batches[batch.batch_id]

    def prepare(self, batch, entity, rows):
        if entity not in ("person", "visit"):
            raise Conflict("invalid_entity")
        if self.batches.get(batch.batch_id) is None:
            raise Conflict("batch_not_registered")
        seen = set()
        data = []
        for row in rows:
            key = (batch.source_system, row["source_id"])
            if not isinstance(key[1], str) or not key[1].strip() or key in seen:
                raise Conflict("null_or_duplicate_business_key")
            seen.add(key)
            if row.get("source_batch_id") != batch.batch_id:
                raise Conflict("mixed_source_batch")
            if not isinstance(row.get("payload"), dict):
                raise Conflict("missing_payload")
            if entity == "visit" and not row.get("source_person_id"):
                raise Conflict("missing_visit_person_fk")
            data.append((key, digest(row["payload"]), row.get("source_person_id")))
        # Stage is scoped to the exact batch and entity, never shared historic tables.
        stage_key = (batch.batch_id, entity)
        snapshot = tuple(sorted(data))
        existing = self.stage.get(stage_key)
        if existing is not None and existing != snapshot:
            raise Conflict("stage_replay_payload_conflict")
        self.stage[stage_key] = snapshot
        return snapshot

    def commit(self, batch, entity, *, simulate_unknown_commit=False):
        # Simulation of independently committed Person and Visit transactions.
        self.acquire(batch.batch_id)
        try:
            ledger = self.register(batch)
            if entity == "visit" and ledger["person"] != "COMMITTED":
                raise Retryable("person_not_committed")
            snapshot = self.stage.get((batch.batch_id, entity))
            if snapshot is None:
                raise Conflict("no_batch_scoped_stage")
            target = self.person if entity == "person" else self.visit
            # Full validation before any simulated mutation; no partial commit.
            for key, fingerprint, parent in snapshot:
                existing = target.get(key)
                if existing is not None and existing["fingerprint"] != fingerprint:
                    raise Conflict("existing_key_changed_payload")
                if entity == "visit" and (batch.source_system, parent) not in self.person:
                    raise Conflict("orphan_visit_person")
            planned = [(key, fp) for key, fp, _ in snapshot if key not in target]
            start = self.next_person_id if entity == "person" else self.next_visit_id
            for offset, (key, fingerprint) in enumerate(planned):
                target[key] = {"id": start + offset, "fingerprint": fingerprint}
            if entity == "person":
                self.next_person_id += len(planned)
            else:
                self.next_visit_id += len(planned)
            ledger[entity] = "COMMITTED"
            ledger["state"] = "VISIT_COMMITTED" if entity == "visit" else "PERSON_COMMITTED"
            self.events.append((batch.batch_id, entity, len(planned)))
            if simulate_unknown_commit:
                # COMMIT happened, but caller lost acknowledgement.
                raise Retryable("commit_outcome_unknown_readback_required")
            return len(planned)

        finally:
            self.release(batch.batch_id)

    def reconcile(self, batch, entity):
        ledger = self.register(batch)
        snapshot = self.stage.get((batch.batch_id, entity))
        if snapshot is None:
            raise Conflict("no_stage_for_readback")
        target = self.person if entity == "person" else self.visit
        for key, fp, parent in snapshot:
            actual = target.get(key)
            if actual is None or actual["fingerprint"] != fp:
                raise Conflict("readback_mismatch")
            if entity == "visit" and (batch.source_system, parent) not in self.person:
                raise Conflict("readback_orphan")
        if ledger[entity] != "COMMITTED":
            raise Conflict("ledger_target_state_mismatch")
        return True
