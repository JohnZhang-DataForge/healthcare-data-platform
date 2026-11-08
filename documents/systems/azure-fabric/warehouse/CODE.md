## Actual Warehouse ownership vs Git SQL source

**Physical Workspace:** `healthcare-omop`, ID `745ce03b-15b6-4870-b0e5-8c5750aa18dc`.
**Existing Warehouse:** `dw-omop-5.4`, physical Item GUID
`7a6d08da-278d-4603-8a3b-28640110984c`. It is in **the same**
Workspace as the root-level Git-native items
[`nb_fhir_ingest.Notebook/`](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/),
[`pl_fhir_ingest.DataPipeline/`](../../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/),
[`env_healthcare.Environment/`](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/),
and [`lh_omop_analytics.Lakehouse/`](../../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/).

**Git layout distinction:** The Warehouse was created manually and remains
a **Workspace-only, Git UpdateFromGit-protected item**. It currently has no
native `workspaces/healthcare-omop/dw-omop-5.4.Warehouse/` directory.
The existing `azure-fabric/deployment/warehouse/omop-cdm-5.4/` and
`azure-fabric/deployment/warehouse/omop-foundation/` are versioned SQL DDL and identity/audit manifests used by separately authorized migrations; Writer Python remains in `azure-fabric/warehouse/omop-foundation/writer/`;
they are **not** the Warehouse's Fabric Git-native item definition. The two
empty legacy Notebook/Pipeline folder placeholders have been removed in
favor of the real root-level `*.Notebook/` / `*.DataPipeline/` items.

Do not relocate the Warehouse sources again or introduce a `*.Warehouse/` Git
item without a separate OpenSpec, dependency/CI path migration, physical
GUID/type verification and revision of the existing Workspace-only
protection. No data, Warehouse schema, or Fabric resource was changed in
this directory cleanup.

---

# Fabric Warehouse / OMOP CDM Schema — Source Map

**业务与验收概览**：[Warehouse README](README.md)。唯一详细技术合同：[CDM/Vocabulary](CDM54-SCHEMA-AND-VOCABULARY.md)、[F1 Identity/Audit](IDENTITY-AND-AUDIT-SCHEMA.md)、[F2 Writer](WRITER-PREVIEW-TO-COMMIT.md)、[INT Allocation](ID-ALLOCATION-STATE-MACHINE.md)。这些文档来自原源码 README/PUBLISHER 类文件，仅说明源码与受控证据；不授权执行 Gold。


- [Official OHDSI 5.4 DDL mirror](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/upstream/OMOPCDM_sql_server_5.4_ddl.sql): source blob pinned and offline verified.
- [Source manifest](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/manifest.json): source commit, 39 table names, 432 fields, Fabric-only datatype mappings.
- [Fabric-compatible table SQL](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/tables/): 39 `cdm` CREATE TABLE definitions, no runtime execution.
- [Offline contract tests](../../../../.github/quality/tests/azure-fabric/warehouse/omop-cdm-5.4/test_cdm54_schema.py), [workflow](../../../../.github/workflows/fabric-omop-cdm54-schema-offline.yml).
- These are Git source definitions; actual CDM 5.4 empty tables were deployed and read back in [#41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578). Warehouse connectivity was proven separately by Self-Runner [#41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691). Do not confuse with Schema readback or CDM COMMIT.

- [F1 Vocabulary Blob header / empty-table preflight](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/src/ci/fabric_omop_vocabulary_preflight.py), [F1 replay-safe native COPY loader](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/src/ci/fabric_omop_vocabulary_load.py), and [Self-Runner Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/fabric-omop-vocabulary-import.yml). Execution evidence and current state tracked in [OMOP OpenSpec Tasks](../../../../openspec/changes/fabric-omop-foundation/tasks.md).

- **F1 physical Vocabulary 9/9 real import:** [Self-Runner #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) — 28,703,753 exact source rows loaded into the existing nine `cdm` tables, independent count/Concept ID/date/vocabulary uniqueness checks PASS. Domain/concept relation semantic QA and release metadata audit remain a separate task.

- [Fabric OMOP Foundation identity schema source](../../../../azure-fabric/deployment/warehouse/omop-foundation/): 5 empty management table SQL files, Warehouse-wide INT allocator, idempotency ledger and audit contracts; **physically created and independently read back in [Self-Runner #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817); all management tables empty**.

- **F1 Vocabulary semantic DQ (real):** [Self-Runner #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379), 11/11 cross-table links unresolved=0; vocabulary_version blank in 28/47 rows remains an explicit version/licensing review item.

- [F2 Gold SQL transaction adapter (SOURCE_ONLY)](../../../../azure-fabric/warehouse/omop-foundation/writer/gold_transaction.py): reuses the same identity planner and existing SQL schema for external-fenced single-transaction Map/Allocator/Person/Visit/Ledger/Audit writes, guarded in-transaction reconciliation, rollback and unknown-ACK verification-only outcome; an independent new SQL connection is required for acceptance. [Offline atomicity/replay tests](../../../../.github/quality/tests/azure-fabric/warehouse/omop-foundation/test_identity_plan.py) use SQLite synthetic data only. **No Fabric Warehouse clinical COMMIT is authorized or claimed.**

- [F2 six-table physical-to-Shared Snapshot source bridge](../../../../azure-fabric/warehouse/omop-foundation/writer/silver_identity.py): `bridge_f2_sql_readback_rows` recomputes existing Self-Runner six-table SQL per-row digests from supplied **full rows**, compares two distinct-connection SHA sets, validates Warehouse/Map/Gold/Allocator/FK and returns the existing Shared `IdentitySnapshot` plus separate logical/physical fingerprints. SOURCE_ONLY; does not authenticate connections, approve clinical mapping or execute SQL/Gold. Synthetic negative coverage remains in the existing exact four-file Warehouse tests at `.github/quality/tests/azure-fabric/warehouse/omop-foundation/test_identity_plan.py`.

- [F2 G4 Silver and Shared Snapshot preview reconciliation](../../../../azure-fabric/warehouse/omop-foundation/writer/silver_identity.py): `plan_silver_identity_with_f2_bridge` reuses existing F2 `plan_silver_identity` / `plan_ids` and Shared `bridge_f2_person_visit_allocation`, validates all Person/Visit proposed IDs and FK against exactly one `F2SnapshotBridge`. Existing four-file Warehouse CI [test_silver_identity.py](../../../../.github/quality/tests/azure-fabric/warehouse/omop-foundation/test_silver_identity.py) covers synthetic 100/5918, cross-hospital, replay and negative cases; the module itself is PURE/SOURCE_ONLY. Separately, the trusted existing Self-Runner physical pipeline [Main Run #42490347923](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42490347923) **actually GET-read the committed G4 Patient/Encounter Canonical identity/provenance columns (100/5918), Silver Approval Q0, and two independent F2 Warehouse SQL six-table snapshots**, then invoked this exact pinned Shared Preview with PASS; aggregate-only Artifact `fabric-f2-g4-silver-readonly-42490347923` (ID `13620899472`). Existing Warehouse durable IDs remain empty, this run created no persistent Map/Gold, and no clinical/License Approval or Candidate/Gold COMMIT was authorized.

- [F2 pure source-to-INT-ID preview and replay planner](../../../../azure-fabric/warehouse/omop-foundation/writer/identity_plan.py) with [offline collision/overflow/replay tests](../../../../.github/quality/tests/azure-fabric/warehouse/omop-foundation/test_identity_plan.py). This code is SOURCE-ONLY; it does not write Warehouse Gold.

- **F2 real rollback rehearsal:** [Self-Runner #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608), six Warehouse tables real synthetic DML within one transaction, explicit rollback and independently confirmed zero row persistence, PASS. No actual Person/Visit Gold COMMIT.


## P3.3 统一 Warehouse 回归测试位置（2026-11-04）

- [OHDSI CDM54 schema](../../../../.github/quality/tests/azure-fabric/warehouse/omop-cdm-5.4/test_cdm54_schema.py)：固定上游 Blob SHA 和 39/432 DDL 结构；[CDM Schema Offline CI](../../../../.github/workflows/fabric-omop-cdm54-schema-offline.yml) 至少发现/运行 2 个测试。
- [F1/F2 OMOP Foundation tests](../../../../.github/quality/tests/azure-fabric/warehouse/omop-foundation/)：Concept negative/DQ/Identity/Replay/Silver ID 预演；[Identity Schema Offline CI](../../../../.github/workflows/fabric-omop-foundation-identity-schema-offline.yml) 必须准确发现 4 文件、至少运行 31 个测试。
- Schema SQL/Manifest 已由本次有界 OpenSpec 搬至 `deployment/warehouse/`，Writer Python 原位保留；测试不得自动触发 DDL/DML/Schema Apply，真实 F2 Gold COMMIT 仍未验收。
