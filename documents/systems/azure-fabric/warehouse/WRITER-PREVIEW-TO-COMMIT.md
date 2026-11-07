---
status: active
scope: fabric-omop-f2-writer-preview-gate
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由源码文件 `azure-fabric/warehouse/omop-foundation/writer/README.md` 迁入；原证据、ID/事务/FK/Replay/授权边界保留。F0/F1 Schema/Vocabulary 及 F2 Synthetic ROLLBACK 的真实 Run 仅证明各自范围，**不等于 Person/Visit Gold COMMIT**。本 PR 不执行 Warehouse SQL。

# F2 preview-to-commit contract

**Status: SOURCE_ONLY / NOT GOLD_COMMITTED.** This module is a deterministic ID preview, not a Warehouse write or a persistent reservation.

**Input:** Canonical keys must include entity type, hospital ID, source system, and source business key. Patient uses `source_record_id`; Encounter uses `source_encounter_id`. All ID allocations are positive INT within 2,147,483,647 and global per entity across the Warehouse, not per hospital. The planner fails on casefold collisions, duplicates, invalid fields, Map/Gold drift, counter rewind, and overflow.

**Preview:** Read the actual Warehouse Identity Map, Gold rows, allocator and ledger under a verified source batch/manifest/mapping hash. The planner produces proposed ID assignments without saving them. Existing IDs remain stable; new IDs are reproducible regardless of the input ordering.

**Gold gate:** The future Writer must recheck the whole snapshot inside a single-writer Warehouse transaction, resolve the G5 Candidate hospital-scope join, validate real Concept mappings, then atomically write identity map, `cdm.person`, `cdm.visit_occurrence`, the allocator and a COMMITTED ledger. Unknown commit acknowledgement requires independent readback, not blind retry.

**Fabric limits:** Warehouse snapshot isolation does not provide a SERIALIZABLE allocator lock; PK/FK/UNIQUE constraints are not assumed enforced. Use a verified global writer fence, short transactions, explicit conflict detection and safe bounded retries. Current Fabric IDENTITY only supports BIGINT, while official OMOP ID columns are INT.

**Still open:** F2 SQL transaction rehearsal, the real clinical Gold Writer, Patient/Visit commit readback, G4 100/5918 input, G5 hospital join and mapping profile, replay proof and release/license audit. Do not call an offline planner GOLD_COMMITTED.

References:
- https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions
- https://learn.microsoft.com/en-us/fabric/data-warehouse/identity
- https://learn.microsoft.com/en-us/fabric/data-warehouse/ingest-data-tsql

## Real transaction rehearsal — 2026-11-04

- [Self-Runner PR #496](https://github.com/JohnZhang-DataForge/Self-Runner/pull/496): source-controlled synthetic/no-PHI transaction test.
- [Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608): real `BEGIN TRANSACTION`; six tables contained exactly the expected synthetic rows within one transaction; explicit `ROLLBACK TRANSACTION`; independent new SQL connection verified all six zero rows. **PASS, NO GOLD COMMIT**.
- The remaining task is an authorized Writer that rechecks verified Candidate inputs and commits stable IDs, clinical rows and Ledger atomically, then reads back for Replay; this rehearsal is not that writer.

## Canonical G4 Silver → F2 Identity preview bridge (source-only)

`silver_identity.py` consumes only independently verified canonical Silver Person/Encounter source key columns, exact hospital/source/batch namespace, physical Silver approval and zero-quarantine confirmation. It validates Visit-to-Patient FK, then calls the unchanged global `identity_plan.plan_ids` against a trusted complete Warehouse Map/Gold/Allocator snapshot. Output proposes both `person_id` and `visit_occurrence_id` with each Visit's linked Person INT.

Synthetic tests include 100 Patient / 5,918 Encounter, deterministic ordering, exact replay, cross-hospital same business keys, duplicate/casefold collision, foreign FK, approval drift, Map/Gold drift and allocator rewind.

**Do not mistake preview for allocation or Gold.** This helper neither connects to Fabric nor persists an Identity Map, Candidate Delta, Person/Visit, audit or Ledger. The existing published 0.1.3 Candidate Wheel still needs integration of verified Visit IDs and the formal Concept Mapping Profile. A future single-writer SQL transaction must independently reload all Warehouse state and commit everything atomically, followed by independent SQL/DQ/readback and Replay SKIP verification.

## P4 Gold transaction adapter — source-only (2026-11-07)

[Gold transaction adapter](../../../../azure-fabric/warehouse/omop-foundation/writer/gold_transaction.py) is a Warehouse DB-API DML implementation beside the existing F2 planner, **not** a new Mapper, clinical Concept Profile or identity allocator. It strictly validates complete Person/Visit mapping, preserves candidate `PROVISIONAL` IDs until transactionally persisted, compares them to a fresh full Warehouse Map/Gold/Allocator snapshot under an externally held single-writer fence, rejects cross-hospital batch-ID reuse, inserts Map/Allocator/clinical tables/Ledger/Audit together, reconciles clinical rows before committing, and handles failures with rollback. If COMMIT ACK is uncertain, **no retry or rollback assumption is made**: independently reconnect and GET. An acknowledged COMMIT still returns **VERIFY_REQUIRED**, never Gold PASS.

The writer accepts a `release_gate` callback only from a trusted execution controller; user-supplied booleans or SHA strings are **not** legal release approvals. Clinical mapping reviewer/license signoff, persisted F2 snapshot/lease identity, Candidate Approval physical readback, and exact Warehouse connection identity must be verified by that controller before ever calling the writer. The current source does **not** connect the formal Native Pipeline to Warehouse DML and cannot run without an explicit trusted caller. Synthetic SQLite six-table tests test transaction behavior but are **not** an equivalent Fabric DB transaction acceptance. Genuine OIDC/Fabric SQL COMMIT, new-connection readback, Replay SKIP and P5 remain OPEN.
