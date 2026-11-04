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
