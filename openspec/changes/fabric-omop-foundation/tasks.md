# Tasks — Fabric OMOP Foundation

## F0 — Warehouse inventory and connection

- [x] 0.1 用户创建现有 Warehouse `dw-omop-5.4` 并提供 SQL Endpoint；后由 Self-Runner 独立 REST 读回目标 GUID，见 0.4。
- [x] 0.2 创建独立 OpenSpec Proposal / Design / Delta Spec / Tasks，冻结与 G5 和 Local DP 的边界。
- [x] 0.3 Self-Runner 已完成受信任 main OIDC REST + SQL SELECT 只读探针，含离线正反测试；PR #483/#484 已合并，静态 CI PASS。
- [x] 0.4 **真实只读连接 PASS**：Self-Runner [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) 完整 SUCCESS，目标 Controller SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`；自建 `dw-runner-set` 以 OIDC 执行 Fabric REST 可见性读回；独立托管 Ubuntu 使用相同 Entra SP / ODBC Driver 18 / SQL Audience 执行固定 `SELECT DB_NAME(), CURRENT_USER, 1`。真实 Warehouse Item ID `7a6d08da-278d-4603-8a3b-28640110984c`，`DB_NAME()=dw-omop-5.4`，`SQL_SELECT_PASS=TRUE`。没有运行 DDL/DML/Capacity 操作。
- [x] 0.5 绑定官方 OHDSI CommonDataModel v5.4 固定 Commit / Blob，39 张表、432 字段清单、Fabric 类型适配与 Source-fidelity CI PASS（PR #634/#635）。
- [ ] 0.7 完整 SQL Project / DacFx Schema 迁移、版本升级策略及 Drift Plan 仍须后续独立交付；源文件与首次 CREATE TABLE 不代表已具备 DacFx 升级链路。
- [x] 0.6 已有 Warehouse 首次创建 `cdm` Schema 和 **39 张空 OMOP CDM 5.4 基础表、432 字段**，新建 SQL 连接独立 `INFORMATION_SCHEMA.COLUMNS` 精确读回 PASS；Self-Runner [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578)，controller main SHA `d71cab50f25a01b4b245b915b22400f9d99250c6`，Healthcare pinned schema SHA `860af51ca3c1f7389c2276b68494eab274888f94`。
- [ ] 0.8 `etl`/`audit` 管理 Schema、Identity Map、版本元数据、Vocabulary 和部署升级管线尚未创建/验收；独立 F1 实施。

## F1 — Independent identity and vocabulary

- [ ] 1.1 设计 Fabric-only Identity Map、稳定分配策略、院区隔离、唯一键、并发与恢复语义。
- [ ] 1.2 导入有版本与校验的正式 Vocabulary；Concept/有效日期/域验证真实 PASS。

## F2 — Transactional Gold writer

- [ ] 2.1 实现 Warehouse Writer、Ledger 与原子事务；Person/Visit 真实插入、重放及负向校验。

## F3 — Approved G4 to Gold E2E

- [ ] 3.1 使用已批准的 G4 Silver Patient/Encounter，真实 100 Patient / 5,918 Encounter 输入执行并对账。
- [ ] 3.2 独立 SQL readback、DQ/FK/Replay PASS，最后再与 G5 Pipeline 明确集成。

## F0 real execution evidence — 2026-11-03

- [Healthcare OpenSpec PR #632](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/632) merged SHA `99d71e3966bc05183683be5b8637fcb2561f77ec`. OpenSpec validation, Change Gate and link CI PASS; unrelated Workers preview failure was not interpreted as F0 acceptance.
- [Self-Runner probe PR #483](https://github.com/JohnZhang-DataForge/Self-Runner/pull/483) merged SHA `a72932e3f0044e58ae5f08cec94fa35fe8cdd9fe`. First [Run #41645029049](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645029049) **FAIL** before REST/SQL due `python3 -m pip` unavailable on self-hosted Runner; Warehouse SQL auth was not yet tested. Original failure preserved.
- [Self-Runner fix PR #484](https://github.com/JohnZhang-DataForge/Self-Runner/pull/484) merged SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`. Two-stage job: no-pip self-hosted REST + ephemeral hosted ODBC SQL SELECT. [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) completed **SUCCESS**: offline unit tests PASS; REST `FABRIC_WAREHOUSE_REST_VISIBLE=PASS` for exact Warehouse GUID; SQL encrypted TDS `SQL_SELECT_PASS=TRUE`, target DB match, authenticated SP observed. Logs contain no OMOP business rows.
- **Bounded PASS**: Workspace item visibility + SQL connectivity only. **NOT_YET_DONE**: official CDM 5.4 SQL Project, DDL deployment, schema physical readback, Vocabulary, Identity Map, Writer and Gold transactions. These remain explicit tasks 0.5/0.6, F1/F2/F3.

## F0 OHDSI schema-source implementation (design/code, not deployed)

- Official upstream OHDSI `CommonDataModel` pinned commit `b90ae94430e9a266891890a549ac188137fd7f00`, source blob `a77fcad931eef37fe113a79fc266f09cb13e9ed0`; canonical SQL Server 5.4 Base DDL (39 tables, 432 fields).
- SQL source/manifest generated in `azure-fabric/warehouse/omop-cdm-5.4/` with only Fabric-supported type adaptations `datetime`→`datetime2(6)`, `integer`→`int`. An offline PR build verifies fidelity; `0.5` remains OPEN until required CI and reviewed DDL deployment package criteria are satisfied.
- No `CREATE SCHEMA`, no real Warehouse DDL/SQL write, no Vocabulary content or Gold rows have been executed in this schema-source slice. `0.6` remains OPEN.

## F0 source inventory correction — 2026-11-03

- The official OHDSI 5.4 SQL Server DDL contains **39 tables / 432 columns**, including the quoted `note_nlp."offset"` field. Initial manifest/test accidentally counted 431 because the local inventory regex ignored quoted identifiers. This is corrected in the source manifest and tests with unchanged official upstream blob `a77fcad931eef37fe113a79fc266f09cb13e9ed0`.
- Deployment Run [#41647856432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41647856432) failed at `DDL_COLUMN_INVALID` **before any Warehouse token or SQL write**. Subsequent offline parsing revealed the count mismatch before another cloud deploy. Preserve both diagnostics. DDL source/readback still NOT_DONE at this point.

## F0 verified empty-CDM physical deployment — 2026-11-03

- [Self-Runner PR #485](https://github.com/JohnZhang-DataForge/Self-Runner/pull/485) added first bounded schema deploy. [Initial Run #41647856432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41647856432) **FAIL** before OIDC/SQL due official `note_nlp."offset"` rejection by local DDL parser; **no Warehouse mutation**. Offline PR verification later revealed the 431-vs-432 manifest error, also before any SQL operation.
- [Healthcare PR #635](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/635) merged SHA `860af51ca3c1f7389c2276b68494eab274888f94` with precise 39-table/432-column source inventory and updated source tests; OHDSI upstream DDL blob itself unchanged.
- [Self-Runner PR #486](https://github.com/JohnZhang-DataForge/Self-Runner/pull/486) merged SHA `d71cab50f25a01b4b245b915b22400f9d99250c6`. PR offline CI fully parses 39 DDL files and validates 432 fields, including quoted `offset`.
- **Real deployment [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578) SUCCESS**: exact Warehouse REST item `7a6d08da-278d-4603-8a3b-28640110984c`; SQL identity / Database readback PASS; initial `cdm` was absent with 0 columns; applied `CREATE SCHEMA cdm` and 39 individual `CREATE TABLE` statements (official CDM 5.4 base DDL); reconnected independently with SQL token and verified `CDM54_SCHEMA_READBACK=PASS TABLES=39 COLUMNS=432 EMPTY_DDL_ONLY=YES`. Actual output lists all 39 `CREATED_EMPTY_TABLE` events.
- Runtime scope is **CDM BASE SCHEMA PHYSICAL DEPLOY + READBACK PASS** only. No `etl` / `audit` schema, no PK/FK enforcement guarantee, no Vocabulary data, no ID allocation, no OMOP Person/Visit rows, no Gold transaction, no Spark/FHIR Pipeline execution, no Warehouse re-provision, no Capacity mutation.
- Earlier evidence blocks are historical as of their respective PRs; this live acceptance supersedes only the earlier `schema NOT_DONE` status, not pending F1–F3.
