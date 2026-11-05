---
status: active
scope: fabric-omop-int-allocator-state-machine
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由源码文件 `azure-fabric/warehouse/omop-foundation/ID-ALLOCATION-STATE-MACHINE.md` 迁入；原证据、ID/事务/FK/Replay/授权边界保留。F0/F1 Schema/Vocabulary 及 F2 Synthetic ROLLBACK 的真实 Run 仅证明各自范围，**不等于 Person/Visit Gold COMMIT**。本 PR 不执行 Warehouse SQL。

# OMOP Warehouse INT allocation state machine (design-only; not a Gold deployment)

## Existing contracts

- Canonical Patient source key = `hospital_id/source_system/source_record_id`.
- Canonical Encounter source key = `hospital_id/source_system/source_encounter_id`.
- Target `cdm.person.person_id` and `cdm.visit_occurrence.visit_occurrence_id` are official CDM 5.4 **INT**, not BIGINT.
- The shared canonical record identity is distinct from temporary batch identity. Never allocate from source row ordinal, SHA modulo or personally identifiable fields.

## State transitions

`NEW_CANDIDATE → VERIFIED_SOURCE → VERIFIED_EXISTING_MAP_OR_RESERVED_INT → ATOMIC_GOLD_COMMIT → READBACK_VERIFIED`.

- If source key already has exactly one mapping: retain its positive INT ID; do not reassign.
- If source key is unmapped: acquire an exclusive single-writer gate for the entire Warehouse and both entity types, check full source-key uniqueness, allocate from `etl.id_allocator.next_omop_id` with a preflight INT-bound test, persist mapping, Person/Visit and `etl.batch_ledger` in **one explicit transaction**.
- Validate every Visit source Person reference resolves to the **same hospital/source namespace**; no cross-hospital resolution.
- On replay of exact batch ID and manifest/mapping hashes with independently verified committed row counts: SKIP.
- On same batch ID with different manifest/mapping hashes, duplicate source keys, allocator drift, namespace collision, unknown Concept or table write conflicts: HOLD without new COMMITTED receipt.
- On SQL commit acknowledgement loss: first **read back the durable ledger and both CDM tables**, then decide SKIP/HOLD; never blindly retry inserts.

## Fabric caveats

- Fabric Warehouse `BIGINT IDENTITY` does not supply compliant `INT` ID columns for the frozen OHDSI schema.
- Fabric Warehouse uses snapshot isolation; requesting SERIALIZABLE does not establish a stronger lock. A SQL `MAX(omop_id)+1` based allocator **without single-writer fencing** is unsafe; even with an allocator table, handle optimistic conflict and retry with bounded attempt count.
- PK / FK / UNIQUE declarations may be `NOT ENFORCED`, so data-quality uniqueness and cross-entity FK checks are mandatory rather than cosmetic.
- No patient mapping or row writes occur from this source-only design.

Official Fabric references:
- https://learn.microsoft.com/en-us/fabric/data-warehouse/identity
- https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions
