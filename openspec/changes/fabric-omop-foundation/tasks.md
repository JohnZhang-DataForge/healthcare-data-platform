# Tasks — Fabric OMOP Foundation

## F0 — Warehouse inventory and connection

- [x] 0.1 用户创建现有 Warehouse `dw-omop-5.4` 并提供 SQL Endpoint；后由 Self-Runner 独立 REST 读回目标 GUID，见 0.4。
- [x] 0.2 创建独立 OpenSpec Proposal / Design / Delta Spec / Tasks，冻结与 G5 和 Local DP 的边界。
- [x] 0.3 Self-Runner 已完成受信任 main OIDC REST + SQL SELECT 只读探针，含离线正反测试；PR #483/#484 已合并，静态 CI PASS。
- [x] 0.4 **真实只读连接 PASS**：Self-Runner [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) 完整 SUCCESS，目标 Controller SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`；自建 `dw-runner-set` 以 OIDC 执行 Fabric REST 可见性读回；独立托管 Ubuntu 使用相同 Entra SP / ODBC Driver 18 / SQL Audience 执行固定 `SELECT DB_NAME(), CURRENT_USER, 1`。真实 Warehouse Item ID `7a6d08da-278d-4603-8a3b-28640110984c`，`DB_NAME()=dw-omop-5.4`，`SQL_SELECT_PASS=TRUE`。没有运行 DDL/DML/Capacity 操作。
- [x] 0.5 绑定官方 OHDSI CommonDataModel v5.4 固定 Commit / Blob，39 张表、432 字段清单、Fabric 类型适配与 Source-fidelity CI PASS（PR #634/#635）。
- [ ] 0.7 完整 SQL Project / DacFx Schema 迁移、版本升级策略及 Drift Plan 仍须后续独立交付；源文件与首次 CREATE TABLE 不代表已具备 DacFx 升级链路。
- [x] 0.6 已有 Warehouse 首次创建 `cdm` Schema 和 **39 张空 OMOP CDM 5.4 基础表、432 字段**，新建 SQL 连接独立 `INFORMATION_SCHEMA.COLUMNS` 精确读回 PASS；Self-Runner [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578)，controller main SHA `d71cab50f25a01b4b245b915b22400f9d99250c6`，Healthcare pinned schema SHA `860af51ca3c1f7389c2276b68494eab274888f94`。
- [ ] 0.8 已创建 `etl`/`audit` 两个 Schema 和 5 张空管理表；**实际 Identity Map 赋值、版本元数据落库、版本升级管线仍未完成**。F1.1b 只证明空表部署，不证明真实临床身份。

## F1 — Independent identity and vocabulary

- [x] 1.1 设计并落地 Fabric-only Identity Map 的 Git SQL 空表结构与源代码测试（不代表云端部署或实际 ID 分配）。
- [x] 1.1a 设计 Fabric-only Identity Map、仓库级 INT 分配器、医院/来源隔离、Ledger 与快照隔离并发 Gate；提出 SQL Schema/CI（代码与设计就绪，不等于已部署）。
- [x] 1.1b **真实部署成功**：`etl`/`audit` 两个 Schema 下 5 张空管理表真实创建，第二条 SQL 连接独立 `INFORMATION_SCHEMA.COLUMNS` 读回匹配且五表全部为空；[Self-Runner Run #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817) SUCCESS。
- [ ] 1.1c 真正分配稳定 Person/Visit INT IDs、两层唯一性检验、跨医院/跨来源负向和 Replay 验收。
- [x] 1.2 **九张 Vocabulary 文件真实导入 PASS**：Blob 9/9 SHA256，精确字段匹配、源 TSV 解析逐行计数、全部 `COPY INTO` 或严格幂等 SKIP、独立 SQL `COUNT_BIG` 9/9 与源一致，总计 **28,703,753 行**。另外 `concept_id` 唯一性、Concept 日期区间、`vocabulary_id` 唯一性 PASS。Self-Runner [Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) Completed SUCCESS。
- [ ] 1.3 Vocabulary 深度 DQ 完整收尾（包含正式版本/许可审计）。
- [x] 1.3a **真实跨表引用 DQ PASS**：9/9 表源行数一致，11/11 Concept/Domain/Class/Vocabulary/Relationship/Ancestor/Synonym/Drug 强度引用检查未发现缺失；Relationship reverse 与 Concept 日期有效期亦 PASS。[Self-Runner Run #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379) SUCCESS。
- [ ] 1.3b **版本与许可审计仍 OPEN**：`cdm.vocabulary` 47 行中 28 行 `vocabulary_version` 为空，需核查实际 Athena release、CPT4 许可/后处理适用性；`audit.vocabulary_source_file` 目前空表，尚未写入审计 Manifest。不要把 11 项引用 PASS 扩大解释为整个 Vocabulary 版本治理结项。

## F2 — Transactional Gold writer

- [ ] 2.1 实现 Warehouse Writer、Ledger 与原子事务；Person/Visit 真实插入、重放及负向校验（整项仍 OPEN）。
- [x] 2.1a 实现纯 F2 INT ID Preview Planner + Ledger Replay Fence；离线正负向测试覆盖跨医院、同源重跑、冲突、溢出、Snapshot Map/Gold 不一致。**仅 CODE/STATIC，不是实际 Warehouse 分配或 Gold COMMIT。**
- [x] 2.1b **真实多表事务 ROLLBACK PASS**：Self-Runner [Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608) 在现有 Fabric DW 验证六张表 BEGIN→合成非 PHI 数据写入→事务内独立行数检查→ROLLBACK→新 SQL 连接六表均为零。实际 SQL SUCCESS，**无 COMMIT、无 Gold 数据持久化**。
- [ ] 2.1c 实现真实单写入者 Gold 事务：重查 Snapshot → Map/Allocator/Person/Visit/Ledger 原子提交 → 独立读回与 Replay。
- [ ] 2.1d 补齐 G5 Candidate 的 hospital_id Join 与真实 Vocabulary Mapping Profile，验证后才允许 F2 clinical writes（包含 2.1d.1 与 2.1d.2）。
- [x] 2.1d.1 修复 G5 Candidate 源码：显式已验证医院 ID + 当前 F1 Warehouse Identity Map 物理字段，跨医院/全局 Person INT 唯一/大小写碰撞负向测试；仅离线 Wheel 0.1.3，不代表 Gold 读写。
- [ ] 2.1d.2 审批真实 Concept Mapping Profile，使用经独立读回的 G4 Silver + Warehouse ID Map/正式 Wheel 实机 Candidate / Gold 集成。

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

- CI linkage note: this evidence PR uses the existing numeric OpenSpec task `0.6`; follow-up tasks `0.7` and `0.8` remain explicitly open and must not be inferred complete by an empty-table readback.

## F1 Vocabulary Azure Blob → Warehouse execution evidence — 2026-11-03

- Source private container: `johnzhang/omop-vocabulary` (nine root-level files; no GCS/S3/extra Lakehouse). Source verified by [Self-Runner #41768413775](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41768413775): **9/9 exact byte lengths and SHA256 PASS**, OIDC Entra SP direct Blob read PASS. Do not commit raw vocabulary text or CPT4 redistributable content.
- [Self-Runner PR #487](https://github.com/JohnZhang-DataForge/Self-Runner/pull/487) / [Run #41769357041](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41769357041): **readonly F1 preflight PASS**: all nine headers exactly match OHDSI table field order; `FIELDTERMINATOR=0x09`, `ROWTERMINATOR=0x0A` (LF), exact fixed Blob size, nine Warehouse tables empty before first load.
- [Self-Runner PR #488](https://github.com/JohnZhang-DataForge/Self-Runner/pull/488) / [Run #41769826858](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41769826858): **actual Fabric Warehouse COPY INTO PASS** for `cdm.domain=50`, `cdm.concept_class=433`, `cdm.relationship=722`, `cdm.vocabulary=47`. Each row count reconciled with independently streamed source TSV parser; `vocabulary_id` uniqueness PASS.
- [Self-Runner PR #489](https://github.com/JohnZhang-DataForge/Self-Runner/pull/489) / [Run #41770012720](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770012720): deployment switched to **all nine** with immutable storage source ETag, exact row-count replay skip and independent SQL readback. [Run #41770012720](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770012720) loaded **cdm.drug_strength=208,802 rows** and safely skipped the prior four; then held before copying `CONCEPT.csv` due Athena literal-doublequote parse error. [PR #490](https://github.com/JohnZhang-DataForge/Self-Runner/pull/490) proved parser issue at source line 4437, no business data write for CONCEPT. [PR #491](https://github.com/JohnZhang-DataForge/Self-Runner/pull/491) changed CONCEPT and CONCEPT_SYNONYM to literal quote semantics; [Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) **completed SUCCESS** after the literal-quote fix. Nine-table source row counts and independent SQL readbacks all PASS.
- Warehouse item `7a6d08da-278d-4603-8a3b-28640110984c` already existed and 39 CDM tables were deployed in F0; no DDL or Capacity resume in F1. `etl.identity_map` and OMOP Person/Visit Gold remain NOT_YET_DONE.

## F1 9/9 final physical import acceptance — 2026-11-03 ET

Actual immutable evidence: [Self-Runner Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994), main controller SHA `61c279ffa469028f4b46047acaa34319e64ea970`, exact existing Warehouse GUID `7a6d08da-278d-4603-8a3b-28640110984c`.

| Table under `cdm` | Source rows | Warehouse independent SQL rows | Status |
|---|---:|---:|---|
| domain | 50 | 50 | PASS / replay skip |
| concept_class | 433 | 433 | PASS / replay skip |
| relationship | 722 | 722 | PASS / replay skip |
| vocabulary | 47 | 47 | PASS / replay skip |
| drug_strength | 208,802 | 208,802 | PASS / replay skip |
| concept | 1,952,609 | 1,952,609 | PASS / new COPY |
| concept_ancestor | 10,958,071 | 10,958,071 | PASS / new COPY |
| concept_relationship | 13,150,960 | 13,150,960 | PASS / new COPY |
| concept_synonym | 2,432,059 | 2,432,059 | PASS / new COPY |
| **Total** | **28,703,753** | **28,703,753** | **9/9 PASS** |

- Error correction: original source `CONCEPT.csv` uses literal doublequotes inside medical names. Source parser `csv.QUOTE_NONE` and Fabric Warehouse `FIELDQUOTE='0x08'` are used only on CONCEPT / CONCEPT_SYNONYM. This mirrors established OHDSI Athena import guidance. Previous five successful loads preserved and exact-count replay SKIP validated; no `DROP`, `DELETE`, `TRUNCATE` or duplicate re-import.
- Import performs strict source header checks, OAuth private Blob access, immutable-length + ETag checks, source TSV row counts and Warehouse independent `COUNT_BIG` matches for each table. `CONCEPT_UNIQUENESS_AND_VALIDITY=PASS`, `VOCABULARY_ID_UNIQUENESS=PASS`.
- **Outside the accepted boundary:** CPT4 `CONCEPT_CPT4.csv` name post-processing/licensing (not uploaded to the nine standard tables); Identity Map/ledger; Person/Visit Gold data; semantic FK/Domain and release version audit. These remain separate work and are NOT silently declared complete.

## F1 Identity Map / audit design milestone — 2026-11-04

- F1 Schema source under `azure-fabric/warehouse/omop-foundation/` specifies 5 empty tables across `etl`/`audit`, pinned existing Warehouse GUID. Only code/offline CI in this slice; no cloud DDL or patient data writes.
- Canonical patient source PK `(source_system, source_record_id)`, encounter PK `(source_system, source_encounter_id)`. Add hospital scope to both mappings to prevent tenant collision; use a **global per-entity INT allocator** for Person and Visit within Warehouse, never per-hospital counters.
- Fabric `BIGINT IDENTITY` is incompatible with OHDSI CDM 5.4 `person_id int` and `visit_occurrence_id int`. Stable allocation uses an explicit table and controlled transaction with preflight overflow checks.
- Fabric Warehouse snapshot isolation cannot be overridden with SERIALIZABLE; concurrently allocating from `MAX(id)` without a single-writer gate is unsafe. F2 must enforce single-writer scheduling, detect write conflict and use bounded retry; PK/FK/UNIQUE may be NOT ENFORCED.

## F1 live schema and semantic reference acceptance — 2026-11-04

- [Healthcare PR #643](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/643) merged SHA `195b1f9a387e3393c47cbc298b1110fc34ba52d5`: approved F1 SQL source, 5-table manifest, schema contract, INT identity source-key contract and offline CI PASS.
- [Self-Runner PR #494](https://github.com/JohnZhang-DataForge/Self-Runner/pull/494) merged SHA `c578582df3406b2ba3a45522820656f9db6fbd79`. [Run #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817) **SUCCESS**: precheck `EMPTY TABLES=5`, actual `CREATE TABLE` five times (`etl.identity_map`, `etl.id_allocator`, `etl.batch_ledger`, `audit.omop_commit_check`, `audit.vocabulary_source_file`), independently read-back schema, five tables all zero rows. NO Person/Visit ID allocation or clinical inserts.
- [Self-Runner PR #492](https://github.com/JohnZhang-DataForge/Self-Runner/pull/492) initial DQ Run #41818140654 failed in client before first count (ODBC cursor timeout misuse); [PR #493](https://github.com/JohnZhang-DataForge/Self-Runner/pull/493) removed unsupported cursor assignment. [PR #495](https://github.com/JohnZhang-DataForge/Self-Runner/pull/495) added bounded progress and triggered [real DQ Run #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379), **SUCCESS**.
- DQ: nine table COUNT_BIG values exactly match 28,703,753 source rows, all 11 fixed referential checks `UNRESOLVED=0`. `RELATIONSHIP_REVERSE_MISSING=0`, `CONCEPT_INVALID_DATE_RANGE=0`. `VOCABULARY_VERSION_BLANK=28/47` flagged **REVIEW**, not import failure. Semantic linkage PASS does **not** establish license/release validity; no clinical business rows have been committed.


## F2 deterministic Identity/Replay plan — 2026-11-04

- Pure writer planning code lives in `azure-fabric/warehouse/omop-foundation/writer/identity_plan.py`. It **does not** obtain Fabric tokens, insert/allocate durable IDs, operate Spark, or create a Gold receipt.
- Canonical key is `(entity_type,hospital_id,source_system,source_business_key)`. Person Source Key uses G4 canonical `source_record_id`, Encounter uses `source_encounter_id`. Preview IDs positive official CDM 5.4 INT and globally scoped by **entity** in Warehouse, never per-hospital counters.
- Original G5 Candidate mapper requires injected stable `person_id` and still joins source on `(source_system,source_person_id)` without `hospital_id`. This interface mismatch is a **live Gold HOLD**, not a reason to invent a temporary ID. Preview must be revalidated inside a single Warehouse transaction before Map+Person+Visit+Ledger commit.
- Tests cover deterministic order, exact source key replay, hospital namespace separation, casefold/collation collisions, persisted Map/Gold drift, counter rewind/INT overflow, duplicate ledger, conflicting SHA and unverified replay. GitHub CI is source-only; live SQL transaction acceptance is task 2.1b and not yet claimed.


## F2 live transaction rollback rehearsal — 2026-11-04 ET

- [Healthcare PR #645](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/645) merged SHA `ede02cdaf3ff8b41fc39455be387233f538fa8f9`, implements source-only positive INT preview planner and ledger replay negative tests (not a database ID reservation).
- [Self-Runner PR #496](https://github.com/JohnZhang-DataForge/Self-Runner/pull/496) merged SHA `4951bb7cfa0f49d550da727a5838dd3da3eba64d`. [Real Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608) completed SUCCESS on pinned existing Warehouse: target and DB identity match; all six touched tables empty before run; real Vocabulary Concepts confirmed; synthetic non-PHI rows written inside one explicit transaction to `etl.identity_map` (2), `etl.id_allocator` (2), `etl.batch_ledger` (1), `cdm.person` (1), `cdm.visit_occurrence` (1), `audit.omop_commit_check` (1); `ROLLBACK TRANSACTION` executed; reopened SQL connection independently and verified **zero persisted rows in all six**.
- Explicit scope: actual transaction/rollback behavior verified, not a clinical Gold COMMIT. There was **no** insertion of real G4/FHIR Patients or Encounters, no Capacity resume, no Terraform, and no changes to Vocabulary or Local PostgreSQL. Next is source-scoped G5 hospital join and real Writer Commit/Replay (tasks 2.1c/2.1d).

## F2/G5 hospital identity contract validation — 2026-11-04

- [Healthcare PR #647](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/647) merged SHA `13da96a9bc82463c8be23e3d5f8be385a9655ad4`. [Shared Wheel Offline Validation #41827968535](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41827968535) SUCCESS: 3.11/PySpark 3.5.7 complete synthetic tests and reproducible version **0.1.3** Wheel import; 3.13/PySpark 4.1.1 Spark/OMOP tests plus independent installed Wheel import PASS.
- Explicit batch-authoritative `hospital_id` reconciles the actual canonical v1 `source_system` namespace `raw:hospital:feed`, without changing approved Silver v1 columns. G5 accepts F1 physical Map columns `entity_type/hospital_id/source_system/source_business_key/omop_id`, rejects same-key cross-hospital use, Warehouse-global duplicate Person IDs, case-insensitive collisions, unknown entity and missing source mapping.
- Source-only acceptance. **Fabric Environment 0.1.3 publish/runtime import NOT DONE**, Candidate Delta real write NOT DONE, Gold transaction COMMIT and independent Replay NOT DONE; tasks 2.1c/2.1d.2 remain OPEN.
