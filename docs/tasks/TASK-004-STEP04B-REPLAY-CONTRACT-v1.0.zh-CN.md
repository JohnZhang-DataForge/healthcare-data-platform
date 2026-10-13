# TASK004 STEP04B — Replay / Mapping / Transaction Contract v1.0

> **CODE + TEST ONLY. No PostgreSQL writes.** Based on [STEP04A verified readback](TASK-004-STEP04A-READONLY-FINAL-CLOSEOUT.md).
> This is a *simulation acceptance baseline*, not a functioning production loader or approved DDL.

## Fixed preflight context

- Source batch: `task004-airflow-task004-step03e-38324111846`; manifest SHA256: `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`.
- Processing: 23 Person rows / 3592 Visit rows; confirmed mapping overlap 0 / 0 at STEP04A snapshot.
- Existing historical CDM: 113 Person / 5799 Visit, intact; tables `etl.person_stage` and existing ID maps do **not** have batch_id, manifest_sha256.
- ID maps use `(source_system,source_person_id)` and `(source_system,source_encounter_id)`; identity columns managed by PostgreSQL. Do not reset sequences or assume next allocated values.
- Existing `cdm` schema remains unchanged. SQL/DDL below are **proposed designs only**, not deployed.

## Invariants (must hold in actual STEP04C/D implementation)

1. **One immutable batch identity:** ledger primary key `batch_id`, manifest SHA is an immutable attribute. Same batch_id and another SHA/Processing URI/contract digest → **CONFLICT** (never create second ledger row by treating composite `(batch_id,sha)` as independent identity).
2. **Stable business-key identity:** `(source_system, source_person_id)` or `(source_system,source_encounter_id)`; never include batch_id in surrogate ID map uniqueness.
3. **Batch-scoped stage:** uniqueness `(batch_id,entity,source_system,source_key)` with canonical *business* fingerprint. Same batch/key and changed fingerprint → conflict; operator may not silently replace stage contents. Existing `etl.person_stage` is historical, not a destination.
4. **Fingerprint:** JSON of explicitly approved CDM-relevant business columns only, deterministic field ordering, normalized time/date/decimal/NULL semantics and vocabulary/version references. Exclude `processed_at`, `processing_run_id`, log timestamps, random IDs. The supplied Python `digest()` is an executable proof-of-concept JSON fingerprint, **not** the finalized CDM schema fingerprint.
5. **Person before Visit:** commit/readback Person and persist checkpoint prior to preparing Visit transaction; Visit `person_id` resolved from stable map; reject orphan FK. Never claim both independent commits are globally atomic.
6. **Pre-commit check:** within transaction, lock batch ledger row; verify manifest/contract/source keys and existing mapped CDM business fields, historical-safe conflict policy; allocate missing map IDs with unique constraints, then insert CDM rows. An insert count is evidence only with independent post-commit readback.
7. **No silent update:** identical key + identical CDM business fingerprint = NO-OP; changed fingerprint = **BLOCKED** pending explicit update policy. This applies to same and cross batch.
8. **Unknown COMMIT / pod restart:** first do **read-only** ledger/map/CDM reconciliation; if complete, skip; if partial, resume from persisted Person checkpoint. Never assume transport failure means rollback. No blind source regeneration.
9. **Concurrency:** PostgreSQL row lock or advisory transaction lock on stable batch identity and ordered key-level conflict-safe inserts. Unique constraints are the final arbiter across *different* batches sharing a key. Under serialization/unique conflict, re-read committed rows and decide NO-OP or CONFLICT.
10. **Non-target historical safety:** do not write/delete/update unrelated mapped rows; never `TRUNCATE` shared stage, identity reset or full-table upsert.

## Proposed new schema (DDL design, **not applied**)

- `etl.task004_batch_ledger`: primary key `batch_id`; NOT NULL `manifest_sha256`, `source_system`, `source_version`, `source_ingest_date`, `person_processing_uri`, `visit_processing_uri`, `contract_version`, `status`, `created_at`, `updated_at`; CHECK for legal status. Immutable identity fields enforced by controlled transactional writer (and optionally DB trigger); no auto-overwrite with `ON CONFLICT DO UPDATE`.
- `etl.task004_batch_stage`: `batch_id` FK to ledger, `entity` constrained to Person/Visit, `source_system`, `source_key`, `source_person_key` for Visit, `row_fingerprint`, `canonical_payload` JSONB, `contract_version`; primary key `(batch_id,entity,source_system,source_key)`; stage CHECK enforces Visit parent presence. Consider per-batch retention and data minimization/PHI.
- `etl.task004_batch_commit`: primary key `(batch_id,entity)`, FK ledger; `stage_digest`, `stage_rows`, `mapped_rows`, `inserted_rows`, `updated_rows` (initially zero), `readback_digest`, `commit_state`, checkpoint timestamps. This provides durable Person-complete gate and uncertain commit resolution.
- Optional `etl.task004_source_fingerprint`: unique `(entity,source_system,source_key)` with last approved CDM business fingerprint and mapper/vocabulary version, bridging stable mapping and target readback. The safe update policy must explicitly define how a preexisting historical map without this record is verified against CDM before insertion.
- **Mapping uniqueness gate:** verify existing unique indexes on `etl.person_id_map(source_system,source_person_id)`, `etl.visit_occurrence_id_map(source_system,source_encounter_id)`; add missing index only after safe migration review. Existing historical identities must remain untouched.

## State machine & transactional boundaries

```text
VERIFIED_SOURCE (immutable manifest)
    → REGISTERED (ledger validated/locked)
    → PERSON_STAGED (row fingerprints checked)
    → PERSON_COMMITTED (map+CDM transaction; independent readback)
    → VISIT_STAGED (FK to committed Person checked)
    → VISIT_COMMITTED (map+CDM transaction; independent readback)
    → RECONCILED (batch source/map/stage/CDM fingerprints, old rows protected)
```

Person/Visit transactions are separate. On a conflict no state moves; on unknown outcome enter **READBACK_REQUIRED**, not FAILED_RETRY. Never run the old Stage+full-table upsert directly. A same batch replay reuses verified source identity; skips generation if immutable Landing+Processing are already accepted.

## Executable offline acceptance evidence

`apps/task004/task004_step04b_replay_contract.py` with `tests/task004/test_step04b_replay_contract.py` simulates:
A1 new Person→Visit, A2 identical replay NO-OP IDs stable, A3 retry, A4 Person persisted/Visit failure, A5 unknown commit readback, A6 same batch changed SHA blocked, A7 cross-batch reuse, A8 changed content blocked, A9 lock serialization, A10 historical protection, A11 independent target readback; plus missing-Person gate, stage content conflict, duplicate keys, mixed batches.

Verified GitHub-hosted independent [Self-Runner run 38383896683](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38383896683) **SUCCESS**; 15/15 tests; `DATABASE_MUTATION=NO`.

## Not yet implemented / explicit next gates

- Real PostgreSQL DDL migration and transaction implementation; no schema migration executed.
- Actual OMOP Person/Visit field mappings, concept IDs, null/required-field validation, production fingerprint canonicalization and exact historical collision checks remain **open**.
- The `Store` class uses arbitrary deterministic simulated starting IDs 114/5800; production must use existing PostgreSQL IDENTITY sequences and map uniqueness. In-memory `Store.locks` is NOT distributed locking.
- Production multi-writer race tests, real stage retention, PostgreSQL role privileges, unknown-commit DB scenarios and A1–A11 **live database** checks remain outstanding.
- STEP04C/D real writes require **separate explicit authorization** with expected scope/rows; TASK005 stays ON HOLD.

**STEP04B replay contract simulation passed; STEP04B design baseline does not authorize database mutation.**
