# Fabric OMOP Foundation — F1 identity and audit schema source

The management **schema source is versioned and physically deployed**; Fabric Warehouse readback succeeded in [Self-Runner #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817). Five tables remain empty (no patient or encounter rows, no allocated OMOP IDs).

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

## Actual live milestone (2026-11-04)

- `etl.identity_map`, `etl.id_allocator`, `etl.batch_ledger`, `audit.omop_commit_check`, `audit.vocabulary_source_file` were truly created and independently schema-read-back PASS in [Self-Runner #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817). Five tables were empty on acceptance.
- [Vocabulary semantic reference DQ #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379) checked 11 cross-table reference predicates, all `UNRESOLVED=0`; 9 table source count matches, date range and reverse references PASS.
- `VOCABULARY_VERSION_BLANK=28` of 47 rows is a **manual release/version and licensing audit work item**. No automatic version value was invented, no CPT4 postprocessing was applied, and `audit.vocabulary_source_file` has yet to be populated.
- NEXT: single-writer, Warehouse-global INT ID allocation, strict source-key mapping, transactionally consistent Person/Visit/ledger writer, independent readback and Replay. Nothing in this PR writes clinical data.
