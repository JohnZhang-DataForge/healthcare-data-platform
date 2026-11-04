# OMOP Warehouse INT allocation state machine (design, not deployed)

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
