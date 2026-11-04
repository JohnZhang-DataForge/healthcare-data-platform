# Fabric Warehouse / OMOP CDM Schema — Source Map

- [Official OHDSI 5.4 DDL mirror](../../../../azure-fabric/warehouse/omop-cdm-5.4/upstream/OMOPCDM_sql_server_5.4_ddl.sql): source blob pinned and offline verified.
- [Source manifest](../../../../azure-fabric/warehouse/omop-cdm-5.4/manifest.json): source commit, 39 table names, 432 fields, Fabric-only datatype mappings.
- [Fabric-compatible table SQL](../../../../azure-fabric/warehouse/omop-cdm-5.4/tables/): 39 `cdm` CREATE TABLE definitions, no runtime execution.
- [Offline contract tests](../../../../azure-fabric/warehouse/omop-cdm-5.4/tests/test_cdm54_schema.py), [workflow](../../../../.github/workflows/fabric-omop-cdm54-schema-offline.yml).
- These are Git source definitions; actual CDM 5.4 empty tables were deployed and read back in [#41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578). Warehouse connectivity was proven separately by Self-Runner [#41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691). Do not confuse with Schema readback or CDM COMMIT.

- [F1 Vocabulary Blob header / empty-table preflight](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/src/ci/fabric_omop_vocabulary_preflight.py), [F1 replay-safe native COPY loader](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/src/ci/fabric_omop_vocabulary_load.py), and [Self-Runner Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/fabric-omop-vocabulary-import.yml). Execution evidence and current state tracked in [OMOP OpenSpec Tasks](../../../../openspec/changes/fabric-omop-foundation/tasks.md).

- **F1 physical Vocabulary 9/9 real import:** [Self-Runner #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) — 28,703,753 exact source rows loaded into the existing nine `cdm` tables, independent count/Concept ID/date/vocabulary uniqueness checks PASS. Domain/concept relation semantic QA and release metadata audit remain a separate task.

- [Fabric OMOP Foundation identity schema source](../../../../azure-fabric/warehouse/omop-foundation/): 5 empty management table SQL files, Warehouse-wide INT allocator, idempotency ledger and audit contracts; **physically created and independently read back in [Self-Runner #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817); all management tables empty**.

- **F1 Vocabulary semantic DQ (real):** [Self-Runner #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379), 11/11 cross-table links unresolved=0; vocabulary_version blank in 28/47 rows remains an explicit version/licensing review item.

- [F2 pure source-to-INT-ID preview and replay planner](../../../../azure-fabric/warehouse/omop-foundation/writer/identity_plan.py) with [offline collision/overflow/replay tests](../../../../azure-fabric/warehouse/omop-foundation/tests/test_identity_plan.py). This code is SOURCE-ONLY; it does not write Warehouse Gold.

- **F2 real rollback rehearsal:** [Self-Runner #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608), six Warehouse tables real synthetic DML within one transaction, explicit rollback and independently confirmed zero row persistence, PASS. No actual Person/Visit Gold COMMIT.
