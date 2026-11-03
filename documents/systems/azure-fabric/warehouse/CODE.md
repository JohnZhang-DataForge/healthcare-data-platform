# Fabric Warehouse / OMOP CDM Schema — Source Map

- [Official OHDSI 5.4 DDL mirror](../../../../azure-fabric/warehouse/omop-cdm-5.4/upstream/OMOPCDM_sql_server_5.4_ddl.sql): source blob pinned and offline verified.
- [Source manifest](../../../../azure-fabric/warehouse/omop-cdm-5.4/manifest.json): source commit, 39 table names, 432 fields, Fabric-only datatype mappings.
- [Fabric-compatible table SQL](../../../../azure-fabric/warehouse/omop-cdm-5.4/tables/): 39 `cdm` CREATE TABLE definitions, no runtime execution.
- [Offline contract tests](../../../../azure-fabric/warehouse/omop-cdm-5.4/tests/test_cdm54_schema.py), [workflow](../../../../.github/workflows/fabric-omop-cdm54-schema-offline.yml).
- Cloud execution is NOT part of this commit. Warehouse connectivity proven separately by Self-Runner [#41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691). Do not confuse with Schema readback or CDM COMMIT.
