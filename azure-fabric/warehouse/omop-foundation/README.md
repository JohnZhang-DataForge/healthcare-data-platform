# Fabric OMOP Foundation — F1 identity and audit schema source

This directory contains a **proposed and versioned schema**, not proof of cloud deployment.

Target: existing `healthcare-omop/dw-omop-5.4`; Warehouse Item ID `7a6d08da-278d-4603-8a3b-28640110984c`. These SQL files are **empty management tables**, distinct from the already deployed 39 official `cdm` tables.

- `etl.identity_map`: source-to-OMOP INT identity mapping with canonical `hospital_id`, `source_system`, `source_business_key`. For Patient use canonical `source_record_id`; for Encounter use `source_encounter_id`. Source key stability is **not** derived from a row number, ad hoc hash, name or birth date.
- `etl.id_allocator`: next free positive INT by entity type, **global to the Warehouse** (not per hospital). Avoid cross-hospital collisions. It is **not** a Fabric BIGINT IDENTITY.
- `etl.batch_ledger`: exact input/manifests/mapping hashes and committed Person/Visit receipts. Same batch+hash is replay SKIP after independent readback; same batch/different SHA is HOLD.
- `audit.omop_commit_check`: independent reconciliation evidence, not a substitute for OMOP clinical tables.
- `audit.vocabulary_source_file`: source file SHA256, row count and release metadata. Do not record licensed term text.

**No PK/FK/UNIQUE constraint enforcement is assumed** for Fabric Warehouse. Future F2 writer must run explicit uniqueness checks and prevent parallel writers; Fabric enforces snapshot isolation even if a higher isolation level is requested. The writer must account for conflicts and safe retries. Keep all ID allocations + Person/Visit rows + COMMITTED ledger in one guarded Warehouse transaction.

**INT limit:** Official OHDSI CDM 5.4 Person and Visit target IDs are `int`. Fabric Warehouse `IDENTITY` supports only `BIGINT`, so inserting BIGINT IDENTITY blindly into CDM would be wrong. Explicitly manage positive INT IDs and fail before overflow (2,147,483,647). Do not reuse source IDs or fabricate stable IDs with modulo hashes.

Source references: [Microsoft Fabric Warehouse IDENTITY](https://learn.microsoft.com/en-us/fabric/data-warehouse/identity) and [Fabric Warehouse transactions](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions).

Next gates: source/SQL offline CI → PR review → trusted Self-Runner empty schema deployment + independent readback → separately reviewed F2 mapping and batch commits. There are **no Patient/Visit inserts** in this change.
