# Tasks — Unified FHIR → OMOP Gold

## P0 — 接管及证据（2026-11-04）

- [x] 0.1 独立核对双仓 main、PR、最近 Actions；确认 Marquez 并行 PR 不应覆盖。
- [x] 0.2 G5 Source Readonly #41874126635 Job `e5038133-8120-4afe-b132-9abf6fb652ab` 确认实际 PASS，补入原 G5 OpenSpec，关闭 3.5–3.7 而保留 Candidate/Gold OPEN。
- [x] 0.3 核对实际 etl/audit 五张 SQL 管理表字段、纯身份 Preview、Candidate Mapper 接口和正式 0.1.3 基线。

## P1 — Concept Profile

- [x] 1.1 建立不硬编码临床值的来源代码/词表 Concept 校验函数（仅纯函数/离线），包含有效日期、Domain、标准标记、SHA、防截断和异常 HOLD。
- [x] 1.2 P1 离线正负向 CI 完成并合并 main：Healthcare PR #662 / 合并 commit `5a67d12cb13dbea98b732e5a80e1a1f3fda3eef4`，6 项 PR checks SUCCESS、31/31 Python Tests PASS。仅证明 P1 纯函数预检。
- [x] 1.6 正式 Notebook 新增 `G5_CONCEPT_SOURCE_INVENTORY_READONLY` 模式，复用 G5 真实物理 Approval Reader 后获取五组源代码/频数和源值长度，带 SHA、来源身份、行数的受控 JSON read-only receipt；仅 CODE/OFFLINE，真实云端仍待执行。
- [x] 1.3 从已批准 G4 Silver 真实独立读回五组 code/count；Patient=100、Encounter=5918、源 SHA/Hospital/Source Batch 保持一致：真实 Runner #41920328470、Spark Job `082a5fac-f3f4-4e06-8d0c-0c606e1d1b23` PASS、ERROR=NONE；实际代码数和有争议的源值见下方证据。
- [ ] 1.4 从真实 F1 Warehouse 读回这些 Concept 明细；核对九文件 release/manifest、许可、有效日期、Domain、Vocabulary 审计。
- [x] 1.7 真实 F1 Warehouse **SQL SELECT-only** lexical discovery PASS：Self-Runner Run `41922120812`，源为固定 G4 Runner `41920328470` 的 59 个真实代码；报告清楚区分 Concept Domain/Standard/Invalid/Validity 与正式临床映射。**不是** 1.4 的 release/license 复核通过，也不是 1.5 Profile 审批。
- [ ] 1.5 临床映射审查与正式版本 SHA 冻结；未知、不合法、无授权的全部 HOLD；禁止发布伪 Profile。
- [x] 1.8 F1 Release/Source Provenance 的**纯离线检查工具**：Self-Runner [PR #526](https://github.com/JohnZhang-DataForge/Self-Runner/pull/526) 已合并 main `3613f7bb84753f3cb49d9ff4241ae28b270d60ca`，离线 [Run #42208801101](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42208801101) **12/12 PASS**。实现两条固定只读 `cdm.vocabulary` 与 `audit.vocabulary_source_file` SQL 合同，按既有九份 Blob SHA/Size/Rows 源 Manifest 校验输入，拒绝重复/缺档/版本漂移及多 Release 混合；明确仅 `P1_RELEASE_PROVENANCE_PREFLIGHT_ONLY_NOT_APPROVED`。**本次没有实机 SQL 执行、没有 CPT4 或临床审核**；P1.4 真实版本/许可/来源审计及 P1.5 Mapping 人工审批仍 OPEN。

- [x] 1.9 F1 来源/版本只读审计的**真实 ODBC 适配与有界查询源码**，Self-Runner [PR #527](https://github.com/JohnZhang-DataForge/Self-Runner/pull/527) 合并 main `db8a010df25c522cbbd7f51bdf60bd6b4dd957cd`；[Offline Run #42212808029](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42212808029) **16/16 PASS**。接受非 tuple/list 的 `pyodbc.Row`，Vocabulary SQL 限 `TOP (48)`、Source Audit SQL 限 `TOP (10)`、保存缺少版本的 Vocabulary IDs 供人工审查；不自动填入版本、不推断 CPT4 许可证或临床 Signoff。**仅 CODE/OFFLINE，未新增自动 OIDC 云端执行入口，也未实际进行 F1 SQL 读回。** P1.4 / P1.5 仍 OPEN。

- [x] 1.10 **F1 版本/来源数据库元数据实机只读核验（P1.4 限定子任务）**：Self-Runner [PR #528](https://github.com/JohnZhang-DataForge/Self-Runner/pull/528) squash merged `8a4474cef192e56f32b3f418638fa3b8a7b05a37`，真实 [OIDC Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) 的 offline-contract 与 live-reference-audit 均 **SUCCESS**。源 runner复用现有 Vocabulary Deep DQ OIDC、REST Warehouse GUID 及 SQL DB_NAME 真实验证；两条有界 SQL SELECT 独立读回 `cdm.vocabulary=47`、版本空值 `28`、`audit.vocabulary_source_file=0`，缺少 **9/9 数据库来源审计记录**。九张 Vocabulary 物理表总数仍 `28,703,753`，11 项跨表引用校验均 0 缺失。审批保持 `P1_RELEASE_PROVENANCE_PREFLIGHT_ONLY_NOT_APPROVED` 和 `F1_METADATA_PHYSICAL_READONLY_PASS_REVIEW_HOLD`，未查询或写入临床 Gold，未启动 Capacity。本实机 SQL 元数据子任务已通过，**1.4 真正 release/license 文件和临床 Concept 的完整审计及 1.5 临床人工 Signoff 继续 OPEN**。
  - 不可变证据：GitHub Run Artifact `fabric-p1-f1-metadata-42219030641`、ZIP SHA256 `4c6eab8f7177f3dab42c6c51de34a139e5bb8665377dedf4f6b311071314710e`、内含 `report.json` SHA256 `d822605d00fb7e741b3d7ab7ccf8135f539f499f51fdff73a3343b44662ebb97`；原始报告包含全部 28 个空版本 Vocabulary ID（多为内部/类别词表，逐一评审而非擅自填造版本）。报告 `sql_readback=true`、`sql_write_attempted=false`、`candidate_delta_written=false`、`gold_committed=false`、`clinical_mapping_approved=false`、`vocabulary_license_approved=false`。

## P2–P5 — 候选、事务、管线

- [ ] 2.1 以真实 Warehouse 完整 ID/Allocator/Gold/Ledger 快照验证跨医院稳定 INT 分配，保留并发 Single-writer fence。

- [x] 2.1a **真实六表 SQL SELECT-only、双连接独立指纹核验（empty-snapshot 子任务）**：Self-Runner [PR #546](https://github.com/JohnZhang-DataForge/Self-Runner/pull/546) 与报告键修复 [PR #547](https://github.com/JohnZhang-DataForge/Self-Runner/pull/547) 已合并；准确控制仓库源码 `15ae0e0a977cbf3250117b1c173339830505b3a3`，真正 Main [Run #42305323595](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42305323595) **completed/success**。复用现有 OIDC/SQL F0 Probe，Warehouse REST 身份 `7a6d08da-278d-4603-8a3b-28640110984c`、DB_NAME SQL 身份、六张固定 SELECT 均 PASS；`etl.identity_map=0`、`etl.id_allocator=0`、`cdm.person=0`、`cdm.visit_occurrence=0`、`etl.batch_ledger=0`、`audit.omop_commit_check=0`。每张表 SHA256 皆为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空记录指纹）；第二条独立 SQL 连接读回完全相等，`P2_INDEPENDENT_SQL_READBACK=PASS`。`P2_IDENTITY_SNAPSHOT=READONLY_PASS_REVIEW_HOLD`，`PROVISIONAL_IDS_PERSISTED=FALSE`，`SQL_DML=NO`、`GOLD_COMMITTED=FALSE`、`CLINICAL_APPROVED=FALSE`。早先首次实机 [Run #42304980210](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42304980210) 因输出键名不匹配 **FAIL**，修复后方获得上述实机 PASS；保留历史失败证据。**2.1 主项仍 OPEN**：empty snapshot 证明没有持久身份，不能实测跨医院已持久化稳定 ID/Single-writer Gold 分配；使用既有 F2 Planner/Shared Handoff 的 `PROVISIONAL` 身份只能作为预览，真实提交时必须原子重查快照与单写入者事务。

- [x] 2.2 完成 F2 Preview + 完整 Warehouse Snapshot → G5 Candidate ID Handoff（首次空 Map 的接口鸡生蛋问题），显式区分 PROVISIONAL/PERSISTED，校验 Person/Visit 100/5918、跨医院及 Parent FK；源码纯逻辑实现经 CI/PR 核验并合并后才关闭这一 SOURCE_ONLY 子项，真实 Gold 仍在 P4 OPEN。

- [ ] 3.1 真正 Candidate Delta 物理写入、独立读回、Approval-last、同 Request Replay SKIP。
- [ ] 4.1 Warehouse 单事务 Map/Allocator/Person/Visit/Ledger/Audit COMMIT；独立 SQL 新连接读回、Rollback/Unknown-ACK/Replay/DQ 负向验证。
- [ ] 5.1 原生 Pipeline 实际 FHIR→OMOP E2E：默认 HALT/无自动 Schedule/retry=0；记录 Job、Spark、SQL 三类独立证据。

## P1 native Notebook offline verification

- [Notebook CI #41918612581](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41918612581) PASS for the first source head of this PR. This is a **local PySpark fixture test** of the new `G5_CONCEPT_SOURCE_INVENTORY_READONLY` mode, not evidence of actual Fabric execution. The follow-up PR check-gate correction uses numeric task `1.6`.
- Mode is read-only, G5 original physical source gate still required, and G4 P100/E5918 code frequencies must later be independently obtained by an explicit real Spark Job. Neither P1 clinical approval nor Candidate/Gold have been achieved.

## Evidence

- Offline P1 pure-profile CI initial [Run #41917799155](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41917799155): 31/31 OMOP Foundation unit tests PASS (9 new Concept Profile tests included), no cloud writes. PR gate checks are tracked separately; initial PR body omitted required OpenSpec tags, corrected before re-run.
- Source-only [Run #41874126635](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41874126635) PASS；G4 request `atlanta-fhir-gh-41552666929`，Manifest `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`。
- F0/F1 DDL / Vocabulary、F2 ROLLBACK 维持历史真实验收；**P1 real concept mapping / Candidate / Gold COMMITTED / E2E 均未通过**。

## 2026-11-04 — G4 P1 真实代码分布物理读回（与 Gold 明确分离）

- Self-Runner [Run #41920328470](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41920328470)：正式 Notebook Job `082a5fac-f3f4-4e06-8d0c-0c606e1d1b23`，严格只读结果 `P1_G4_CODE_INVENTORY_PHYSICAL_READONLY_PASS`、`ERROR=NONE`、`JOB_POST_ATTEMPTED=True`；完整机器证据：该 Run Artifact `fabric-p1-code-inventory-readonly-41920328470`，`report.json` 原始 SHA256 `9efadb985e9b4fe2a06c582bb55fc451a9d818fedd096e957b8421b5a5bb27c7`。
- 已核对真实 Healthcare main `2752ba402e55edec2245e48ba4337c3143f710c0`、Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`、Notebook `8311ab6b-3484-4e96-8370-badeeb751633`、Lakehouse `e67c42ee-5ab2-4bc8-a013-7bdf9741ef68`、Warehouse `7a6d08da-278d-4603-8a3b-28640110984c`、Engine 0.1.3 已发布、正式 Notebook 定义同步；历史 G4 processing 0.1.1 仍原样。
- Source request `atlanta-fhir-gh-41552666929`，Manifest SHA256 `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`；Source batch `2e110eb1971fcfa3ebb4dda6782c49a7608955855a2de45a3d77ada47fea8adb`；Hospital `atlanta-hospital-a`，Source `synthea-fhir:atlanta-hospital-a:atlanta-hospital-a-fhir-r4`。
- Gender **2** 代码 / **100** 行：female=54, male=46；Race **6** / **100**：2054-5=53, 2106-3=38, 2028-9=5, UNK=2, 1002-5=1, 2076-8=1；Ethnicity **2** / **100**：2186-5=92, 2135-2=8。
- Encounter Class **5** / **5918**：ambulatory=5684, emergency=164, inpatient=55, virtual=11, home=4；Encounter Source Code **44** / **5918**：最多的 185347001=2149, 185349003=815, 162673000=736, 410620009=417, 185345009=331。完整 44 项及频数必须直接从归档 Artifact 读取；不靠抽样推断。
- 下一步 P1.4/P1.5：物理 Warehouse Vocabulary Domain、validity、映射与版本固定和人工审查。Race `UNK`、Encounter `virtual`/`home` 需要显式规则或 HOLD；**源代码频率读取通过不等于 Concept Profile 临床审批，也不等于 Candidate/Gold 写入**。

## 2026-11-04 — 真实 F1 Vocabulary lexical discovery (not clinical approval)

- [Self-Runner Vocabulary Deep DQ Run #41922120812](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41922120812) 实际 SQL 只读查询：`P1_VOCABULARY_REAL_SQL_READONLY_PASS`，`ERROR=NONE`，原有 11 项 DQ 再次 PASS，`GOLD_WRITE_ATTEMPTED=False`，`CLINICAL_MAPPING_APPROVED=False`。归档 Artifact：`fabric-p1-vocabulary-candidates-41922120812`，`report.json` SHA256 `a64a3819eb35697977ee41465d40b92b54fdd628312426d189507e8945d7d767`。
- 查询针对真实物理 Warehouse `7a6d08da-278d-4603-8a3b-28640110984c` 的 `cdm.concept`、`cdm.vocabulary`、`audit.vocabulary_source_file`；来源输入来自已验收 G4 Run #41920328470 的 canonical receipt SHA256 `1a89a7d575997ed6ed94ff5a77589f514d32c4b876180961e220bd2cdeff2925`，源 5 类共 59 distinct codes。
- **已确认的真正标准 Domain Gender**：female → Person gender_concept_id 候选 8532；male → 候选 8507（两者为标准有效，待版本/Profile 正式批准）。
- **Race 不能直接转换**：5 个 LOINC 源值匹配的 SQL Concepts 是 `Measurement` Domain（虽 `S` 但不能用于 Person Race）；`UNK` 字面匹配 Race Concept 8552 已于 2014-07-31 失效，`standard_concept=NULL`，2 条源记录必须 HOLD/明确策略。
- **Ethnicity 不能直接转换**：两种 LOINC 源值 2135-2 / 2186-5 对应 `Measurement` Domain Concept 3034757 / 3021104，不得写作 `ethnicity_concept_id`。
- **Visit 不能直接转换**：5 个 `encounter_class` 仅 `home` 字面匹配 `Visit` Domain 42627966，但其 `standard_concept=NULL` 且 vocabulary=CPT4，存在许可/非标准阻断；其余 4 类无字面匹配。
- 全部 44 个 `source_code` 均找到词表记录，但 **36 个 Observation + 8 个 Procedure**，没有任何一个直接是有效标准 Visit Domain；候选覆盖率不能冒充目标 Domain 合规通过。
- `cdm.vocabulary` 行数 47、`vocabulary_version` 空 28；`audit.vocabulary_source_file` 行数 0，F1 release/license/audit 任务仍须独立完成。
- **禁止**将词法命中冒充临床标准映射或将 Wrong Domain Concept 充作正式 OMOP Gold；P1.4/P1.5、P2、P3 Candidate、P4 Gold COMMIT、P5 Pipeline E2E 依旧 OPEN。

## P2 Source-only ID Handoff evidence (not physical SQL)

[Healthcare PR #727](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/727), source `02084e4b1b59a922c9888182d82e985cfec95c6d`, [Wheel CI #42207621020](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42207621020) PASS (dual runtime 66/66 multi-entity tests + existing FHIR/Spark/OMOP regression). Pure F2 preview → G5 first-batch identity candidate interface task 2.2 complete; **P1.4 release/license audit, P1.5 reviewed clinical Concept Profile, P2.1 real Warehouse snapshot, P3 Candidate physical Delta, P4 Gold COMMIT and P5 Pipeline remain OPEN**.

## 2026-11-06 Fabric 正式开发接管（在现有任务继续，不新开并行架构重构）

- [x] 6.1 **入口基线已验收、可以正式继续业务开发**：唯一 Shared Engine 0.1.6 与冻结 Canonical Patient/Encounter v1，实际 [Environment GA Publish #42284453546](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42284453546) PASS，[正式 Native Notebook Git 定义读回 #42291355563](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291355563) PASS，[现有 `nb_fhir_ingest` 只读 Spark 4.1 `RUNTIME_SMOKE` #42297766098](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42297766098) Job Completed 且精确退出 PASS。G4 已验收 **100 Patient / 5,918 Encounter / 0 Quarantine**，受控来源 `atlanta-fhir-gh-41552666929`、Manifest SHA256 `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`，保留 G4 `engine-0.1.1` 历史处理标识及 Approval。当前 Notebook/Pipeline 默认 HALT，不能把 import-only Smoke 当作业务数据读写。
- [x] 6.2 **开发责任切换**：Local DP 生产保持维护模式，不必为了 Fabric 先迁移 Local Mapper/PG Writer；Shared 0.1.6 单业务引擎/Registry/Identity Snapshot/Concept/FK/Candidate API 已作为核心基线，禁止 Fabric 再实现一份 Mapper/Identity Planner。跨系统设计权威见 [Shared Engine Owner](../../../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)，正式代码地图见 [Shared CODE](../../../documents/systems/data-platform/shared-engine/CODE.md) 和 [Fabric CODE](../../../documents/systems/azure-fabric/CODE.md)。后续多实体 Condition 用 [独立公共多实体 Change](../extend-shared-omop-multi-entity/tasks.md) 增量扩展，不阻断当前 Person/Visit 主线。

### 下一轮执行的唯一优先顺序（现有 P1–P5 的 OPEN 项不重复造任务）

1. **P1.4 / P1.5 — F1 真实 Vocabulary provenance + Clinical Concept Profile**：先复核 `cdm.vocabulary=47` 中 **28** 个空 `vocabulary_version`、`audit.vocabulary_source_file=0`（缺少 9/9 来源审计记录），原 Blob 九文件 hash/rows/license/release、CPT4 边界和实际 clinical reviewer；继续复用现有 Self-Runner OIDC SELECT-only/Manifest 审计和 G4 源代码对照。Race/Ethnicity LOINC Domain 多为 Measurement，Encounter 的 virtual/home 和 `UNK` 需显式审查，**不允许写默认假 Concept、不允许把 lexical match 当获准 Profile**。若审批未完成，只做只读/纯离线调查，不进行临床 Gold。
2. **P2.1 — F2 完整物理 Snapshot/ID Preview**：从现有 Warehouse `dw-omop-5.4`（ID `7a6d08da-278d-4603-8a3b-28640110984c`）独立只读核对 `etl.identity_map`、Allocator、Gold Person/Visit、Ledger、Audit 及 SQL fingerprint；调用**现有** `azure-fabric/warehouse/omop-foundation/writer/identity_plan.py::plan_ids` 与 Shared `identity/preview.py` / `identity/candidate_handoff.py`；明确 `PROVISIONAL` 与 `PERSISTED`，禁止行号/临时哈希充作真实 ID。真实 SQL 事务写前必须在 single-writer fence 下重新读回并校验 Snapshot。
3. **P3.1 — G5 Candidate Delta**：复用现有 `nb_fhir_ingest` G4 Approved Silver reader 和 `healthcare_data_engine.mapping.omop.candidates`，冻结本次 Request/Manifest/Source/Contract/Approval，Person/Visit Candidate-only Delta 写入、独立 Count/Schema/Key/Hash/FK 读回、Approval-last、重跑 SKIP/冲突 HOLD。**无真实已审临床映射则只能 SOURCE_ONLY 或 HOLD，不伪造临床 Concept**；阶段证据同时归 [G5 tasks](../fabric-g5-approved-silver-omop-candidate/tasks.md)。
4. **P4.1 — F2 Warehouse Gold 原子提交**：复用现有 [OMOP Foundation](../fabric-omop-foundation/tasks.md) Writer/SQL source，单写入者 fence，事务重检完整 Map/Allocator/Gold/Ledger，然后 Person/Visit/Map/Allocator/Ledger/Audit 单事务 COMMIT；新 SQL 连接读回、FK/DQ、Rollback、Replay SKIP、Unknown-ACK 先 GET。绝不把 Candidate 或合成 ROLLBACK 测试写成真正 Gold PASS。
5. **P5.1 — 原生 Pipeline E2E**：完成从受控 FHIR/Approved Silver → Candidate → Warehouse 的单次完整链路验证，保留默认 `HALT`、无 schedule、retry=0，实际 Spark Job/Delta/SQL 三层独立证据与 Git/Run/Artifact SHA；不主动重跑既有已完成 G4 批次。

### 启动及安全前置条件

- 在新 Session **先**读最新 Healthcare/Self-Runner main、Active PR/Actions、root/scoped AGENTS、[Safe Operations](../../../documents/engineering/operations/SAFE-OPERATIONS.md) 和 [Session Coordination](../../../documents/engineering/development/SESSION-COORDINATION.md)，再次独立查询 Fabric 当前 Item/Published Wheel/Git HEAD/本地改动/容量状态；上方验收证据是 2026-11-06 的**历史有效记录**，不可替代下一次实际操作前实时 GET。
- 只在原有 Active OpenSpec 增量改动对应唯一 Owner 源码、测试、README/CODE；先合同与合成/负向回归，再代码 PR/CI/合并，最后单次授权的真实读回或受控写入；禁止重复模块、污染 Local 运行链或采用未批准临床概念。
- 当前仅确认 **FABRIC_READY_CORE**；仍 **NOT GOLD_COMMITTED / NOT FULL_PIPELINE_E2E / NOT THIRD_ENTITY_DONE**。Local、HL7/dbt、Condition 不作为本轮 FHIR Person/Visit G5 的前置条件。


## 2026-11-06 — Fabric 实时部署/来源审计闸门（无业务写入）

- Self-Runner [Workspace GET-only Run #42304980071](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42304980071) **SUCCESS**，`env_healthcare` Published/Staging Wheel 均真实读回 **0.1.6**，正式 Notebook、Warehouse、Lakehouse 物理 GUID/类型/名称 REST 可见。**仅物理 Item 身份，未进行本轮 Notebook Definition 内容独立读回**（`G5_NOTEBOOK_DEFINITION_FRESH_READBACK=NOT_RUN`）。该次 Git status 远端 HEAD `840abc45e4c6c74ce9981608143739b1a59cf0c0`、Workspace HEAD `f15d359d12f6116e5e3ccd3af84653f6f015ae3d`；Workspace 四项本地变更：Warehouse Added、Lakehouse Modified、Pipeline Modified、Notebook Modified，remote changes=0。此为该 Run 时间点状态；**禁止无差别 UpdateFromGit**，后续修改 Native Item 前须重新读回四项状态/definition 并保护 Workspace-only Warehouse。此 Run 未进行 Fabric Git/Capacity/Notebook 或 SQL 写入。
- P1.4 来源审计继续引用真实 [Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641)：`cdm.vocabulary=47`、空版本 `28`、`audit.vocabulary_source_file=0`（九份物理来源审计记录全缺），需按已冻结 Blob SHA/size/row Manifest 单独核对原始 Athena release、license（尤其 CPT4）、标准标记、Domain 与有效日期；**没有**因此判定源文件丢失。P1.5 clinical reviewer 的 Race/Ethnicity/Visit 目标标准映射未批准，`UNK`、`virtual/home` 和 Wrong Domain 继续 HOLD。禁止任何伪造 Concept Profile/临床值、Candidate 物理写入或 Gold COMMIT；P1.4/P1.5/P3.1/P4.1/P5.1 均仍 OPEN。

## 2026-11-06 — P1.4 九份原始 Athena Blob 真实物理元数据双读回（仍未完成 Release/License/Clinical Gate）

- [x] **1.4a 只读证据子项**：Self-Runner [PR #549](https://github.com/JohnZhang-DataForge/Self-Runner/pull/549) squash merged `b372eea71716bfd79a3fd807059d573eff9acccf`; CI 正负向 PASS。真实 GitHub OIDC Storage scope / Azure Blob [Run #42313042119](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42313042119) **SUCCESS**，artifact `fabric-p1-blob-head-42313042119`（Artifact ID `13549821309`，ZIP digest SHA256 `eb8006bdd107e9597cb114caf641aeba7ee3b61d90967b21ca68a3f79ba27d14`）。固定 `johnzhang/omop-vocabulary` 九份 CSV **9/9 双次条件 HEAD，共 18 次**，Blob `BlockBlob`、ETag/Last-Modified 稳定，所有 Content-Length **与冻结原始 Manifest 的每文件 bytes 一致**；没有任何 Blob/SQL/Capacity/Notebook/Pipeline 写入，原有 F1 九张表 count 9/9 PASS 与 11 项 Reference DQ 11/11 PASS。
- **验收边界**：本次是 *Blob 存在性/长度/ETag 稳定性*，**不是九文件完整内容 SHA256 重新计算**。真实 HEAD 元数据 **未提供** `x-ms-version-id`，也**未提供** `x-ms-meta-sha256`；因此不能宣称对象有不可变版本或已有经独立核验的完整摘要。必须保留 `FULL_CONTENT_SHA256_NOT_READ_BACK` 和 `ATHENA_RELEASE_AND_MANIFEST_ORIGIN_REVIEW`。历史冻结 SHA 是原来源清单已声明的摘要，不是本轮 HEAD 现场测得。
- **仍阻塞 P1.4/P1.5**：历史实际 SQL [Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) 中 47 Vocabulary、28 个空版本、`audit.vocabulary_source_file=0`（缺少 9/9 入库审计），本次没有擅自修复或填补；Athena Release 来源/全文件哈希/许可特别是 CPT4，及 Race/Ethnicity/Visit 临床 Concept Profile 缺少批准。独立只读字节流核验须另行评估受控下载容量与授权；不能用 HEAD 替代 SHA，也不得伪造 License/Release/Clinical Signoff。
- **下步开发**：完成冻结 Manifest 的 Athena Release 来源及许可证据整合；形成需临床 Reviewer 审查的 Person/Visit Mapping 决策表（不从 Lexical Matching 自动审批）；在这些 Gate 真实通过前只推进 P3 Candidate/P4 Writer 的无写入源码与负向 CI。**1.4、1.5、2.1 完整事务、3.1、4.1、5.1 仍 OPEN，NOT GOLD_COMMITTED。**

## 2026-11-06 — P1.4 Athena Release 实物文件 SHA + 全 47 Vocabulary SQL 对账（P1.4b 限定验收）

- [x] **1.4b 单个 Vocabulary 元数据文件的真实完整内容校验**：Self-Runner [PR #550](https://github.com/JohnZhang-DataForge/Self-Runner/pull/550) squash `922c387ab4c808e7886988d4dd81f2984070eb62`，真实 [Run #42322067991](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42322067991) **SUCCESS**；本轮只对 Azure Blob `VOCABULARY.csv`（4,378 字节）先 HEAD 再按 ETag `If-Match` 做一次有界完整 GET，重新计算 **文件字节 SHA256 = `795e50e96470e3425556522d15dd99d32a9ddd8044f9e446d9f0e71ee3debd87`**，与既有冻结 Manifest 精确一致。按 TSV 原始 Schema 解析 **47 行**，与独立 Warehouse OIDC SQL `cdm.vocabulary` **47/47 vocabulary_id / vocabulary_version / vocabulary_reference 全量一致**；SQL warehouse GUID/DB_NAME 实际核验，现有 9 表 Count 与 11 项 Reference DQ 继续 PASS。归档 Artifact `fabric-p1-athena-release-42322067991`，ID `13553177319`，ZIP SHA256 `4b18754d135c9abb1164aa6d1e1179cae94dd46276345235f94142dab3d6de27`。
- **实际整包版本标识已找回**：真实 `vocabulary_id='None'` 的 `vocabulary_version` 为 **`v5.0 27-FEB-26`**（2026-02-27），且独立 SQL 与已验证 SHA 的 Azure 源文件同值。其余具体版本/来源保存在原 Artifact：例如 CPT4=`2025 Release`、LOINC=`LOINC 2.80`、RxNorm=`RxNorm 20260105`、SNOMED=`2025-02-01 SNOMED CT International Edition; 2025-03-01 SNOMED CT US Edition; 2025-04-09 SNOMED CT UK Edition`、Visit=`Visit 20211216`。注意 VOCABULARY 中 `CDM` 子词汇的 `CDM v6.0.0` 是该词汇条目版本，**不等于**目标 Warehouse 已部署的 OMOP CDM Schema v5.4 发生变化。
- **28 个空版本不是 28 个已证明的损坏条目**：原 Artifact 精确列出 28 个 ID，多为 `Concept Class`、`Domain`、`Gender`、`Visit Type` 等内部/分类词汇；需按官方来源语义审核，不自动填版本。SQL `audit.vocabulary_source_file` 仍 **0/9**，本轮未补写来源审计。
- **审计边界/下一动作**：`VOCABULARY.csv` 完整 SHA 与 47/47 SQL 对账已经真实 PASS，不能扩大为本次重算所有九文件 SHA、Athena Portal 原始下载交易/下载 Manifest、CPT4 许可或临床审核通过。**P1.4 总项、P1.5 临床映射审批、P3 Candidate 物理写入、P4 Gold COMMIT、P5 Pipeline E2E 仍 OPEN/HOLD**。 OHDSI 官方 [CDM 5.4 Vocabulary 指南](https://ohdsi.github.io/CommonDataModel/cdm54.html#vocabulary) 明确 `None` 行用于整套词汇版本标识；本次实机读回比文档说明更具项目证据效力。下一步整理证据并按源授权审查 CPT4 / Athena 下载来源及九条 source-file 审计的受控写入方案；不凭已有版本号直接写 Gold。
