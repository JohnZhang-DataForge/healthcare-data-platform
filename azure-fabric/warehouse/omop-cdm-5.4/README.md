# OMOP CDM 5.4 — Fabric Warehouse schema source

**Status: GIT_SOURCE_ONLY / NO_FABRIC_DDL_APPLY.** Source for the already existing Fabric Warehouse `healthcare-omop/dw-omop-5.4`; no Terraform creation.

- Canonical upstream: [OHDSI/CommonDataModel `b90ae944...`](https://github.com/OHDSI/CommonDataModel/blob/b90ae94430e9a266891890a549ac188137fd7f00/inst/ddl/5.4/sql_server/OMOPCDM_sql_server_5.4_ddl.sql), exact blob SHA-1 `a77fcad931eef37fe113a79fc266f09cb13e9ed0`, locally retained byte-for-byte in `upstream/`.
- All **39 base tables / 432 fields** are emitted as one declarative SQL file per table under `tables/`. This is a **base DDL schema**, not populated Vocabulary or a complete OMOP compliant deployment.
- Explicit Fabric-compatible column adaptations: case-insensitive `integer` → `int` (same T-SQL type) and unsupported SQL Server `datetime` → Fabric Warehouse `datetime2(6)`. Source column names, order and `NULL / NOT NULL` remain unchanged. Upstream `varchar(MAX)` is supported by Fabric Warehouse.
- Original official SQL Server constraints/PK/index scripts are not part of the base DDL. Fabric Warehouse PK/FK/UNIQUE can be `NOT ENFORCED`; the eventual Writer will implement explicit uniqueness/FK/DQ gates.
- SQL files deliberately omit `CREATE SCHEMA`, migration fences, destructive `DROP`, and any runtime execution. A **separate** trusted Self-Runner migration workflow must validate Warehouse GUID, schema state, deployment SHA and readback before first real DDL apply.
- Offline CI validates upstream blob SHA, table inventory, columns and exact transformed SQL, without making Fabric API/SQL calls.

Official datatype guidance: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types

Source OpenSpec: [Fabric OMOP Foundation](../../../openspec/changes/fabric-omop-foundation/).
