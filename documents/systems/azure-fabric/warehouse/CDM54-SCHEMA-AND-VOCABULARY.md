---
status: active
scope: fabric-omop-cdm54-schema-vocabulary
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由源码文件 `azure-fabric/warehouse/omop-cdm-5.4/README.md` 迁入；原证据、ID/事务/FK/Replay/授权边界保留。F0/F1 Schema/Vocabulary 及 F2 Synthetic ROLLBACK 的真实 Run 仅证明各自范围，**不等于 Person/Visit Gold COMMIT**。本 PR 不执行 Warehouse SQL。

# OMOP CDM 5.4 — Fabric Warehouse schema source

**Status: SOURCE_FILES_VERSIONED; LIVE CDM SCHEMA AND NINE VOCABULARY TABLES VERIFIED.** Source for the already existing Fabric Warehouse `healthcare-omop/dw-omop-5.4`; no Terraform creation.

- Canonical upstream: [OHDSI/CommonDataModel `b90ae944...`](https://github.com/OHDSI/CommonDataModel/blob/b90ae94430e9a266891890a549ac188137fd7f00/inst/ddl/5.4/sql_server/OMOPCDM_sql_server_5.4_ddl.sql), exact blob SHA-1 `a77fcad931eef37fe113a79fc266f09cb13e9ed0`, locally retained byte-for-byte in `upstream/`.
- All **39 base tables / 432 fields** are emitted as one declarative SQL file per table under `tables/`. This is a **base DDL schema**, not populated Vocabulary or a complete OMOP compliant deployment.
- Explicit Fabric-compatible column adaptations: case-insensitive `integer` → `int` (same T-SQL type) and unsupported SQL Server `datetime` → Fabric Warehouse `datetime2(6)`. Source column names, order and `NULL / NOT NULL` remain unchanged. Upstream `varchar(MAX)` is supported by Fabric Warehouse.
- Original official SQL Server constraints/PK/index scripts are not part of the base DDL. Fabric Warehouse PK/FK/UNIQUE can be `NOT ENFORCED`; the eventual Writer will implement explicit uniqueness/FK/DQ gates.
- SQL files deliberately omit `CREATE SCHEMA`, migration fences, destructive `DROP`, and any runtime execution. A **separate** trusted Self-Runner migration workflow must validate Warehouse GUID, schema state, deployment SHA and readback before first real DDL apply.
- Offline CI validates upstream blob SHA, table inventory, columns and exact transformed SQL, without making Fabric API/SQL calls.

Official datatype guidance: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types

Source OpenSpec: [Fabric OMOP Foundation](../../../../openspec/changes/fabric-omop-foundation).

## Real Fabric deployment evidence

- Existing user-created Warehouse `dw-omop-5.4`, item ID `7a6d08da-278d-4603-8a3b-28640110984c`. [F0 real schema CREATE/readback Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578): 39 official base tables, 432 columns, PASS.
- [F1 nine Vocabulary table COPY/readback Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994): private Blob source, 9/9 SHA256-verified files, 9/9 physical table row reconciliation, **28,703,753 rows** PASS; Concept ID/date and Vocabulary ID checks PASS.
- **Not complete:** Identity Map, Person/Visit Gold writes, full semantic FK/Domain DQ, source Vocabulary release/version metadata audit, CPT4 special processing. Do not infer a complete OMOP clinical dataset from populated Vocabulary.
