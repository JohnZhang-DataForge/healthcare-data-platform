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

## P2–P5 — 候选、事务、管线

- [ ] 2.1 以真实 Warehouse 完整 ID/Allocator/Gold/Ledger 快照验证跨医院稳定 INT 分配，保留并发 Single-writer fence。
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
