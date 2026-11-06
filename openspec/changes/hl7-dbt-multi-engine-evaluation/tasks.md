# Tasks — HL7 + dbt Multi-Engine Canonical Evaluation

> 当前仅是**设计与隔离验证**，不是原生生产实施；dbt 后端选择为 **PENDING**。实验源码只在 Self-Runner，Healthcare 不写 POC 代码。每个 PASS 必须有明确真实运行证据。

## 1. 讨论内容持久化（先于实验）
- [x] 1.1 核对现有 FHIR / OIE 运行事实、Canonical v1 合同、Unified Silver 与 Shared Engine 归属。
- [x] 1.2 写入多来源、多处理引擎、统一 Canonical / OMOP 的目标、风险与未来 Entity 扩展原则。
- [x] 1.3 写清本地 dbt-duckdb、本地 dbt-fabricspark session、远端 Livy 三条路线的算力/成本边界；明确后端待实验验证后选择。
- [x] 1.4 docs-only PR #725 经 OpenSpec Change Gate、Static Validation、Links、Active Index 检查通过，已合并 main commit `47ee4673fe72efaf5a53c2cf08e093b80f8b08f3`。

## 2. Self-Runner 纯本地离线 POC
- [x] 2.1 在 Self-Runner 自有隔离目录建立独立实验代码、固定版本、合成 HL7 fixtures 和 runner-only 测试入口；不得引入云凭据/真实集群访问。Self-Runner PR #525（SOURCE/CI）。
- [x] 2.2 验证开源 HL7 Parser 的 v2.5.1 解析以及部分缺字段/版本/出院事件/重复消息负向断言（合成固定样例 6/6 PASS；转义、时区、多医院完整矩阵尚未覆盖，留在 2.5）。
- [x] 2.3 执行 dbt Core + DuckDB seed/run/test 及独立读回、同数据重跑（合成事件 2，Patient 1，Encounter 1，14/14 dbt tests PASS；不是 Delta 验收）。
- [ ] 2.4 执行 dbt Core + Local Spark (dbt-fabricspark session) compile/run/test，记录版本和本地 Delta 读写；不可运行则提供具体阻断证据。
- [ ] 2.5 同一 synthetic fixture 对齐 Candidate 值、异常分类、SQL/Delta 能力、运行成本；对比打分，**测试后**提议选型。

## 3. 正式 HL7 集成（尚未授权、与 POC 分离）
- [ ] 3.1 评审 OIE Producer 扩展（PID-7/8、race/ethnicity 真实来源、A03 discharge 或 Canonical v2）及原始 HL7 Blob Publisher。
- [ ] 3.2 以单独 Implementation OpenSpec 完善实体插件/Schema/版本化 Profile、单一 Silver Publisher、quarantine、replay、readback。
- [ ] 3.3 Azure/Fabric 真实 E2E 需要单独的执行授权和证据；不得因本地 POC PASS 推导真实 Silver Approved 或 Gold COMMITTED。

## Evidence / Blockers
- 设计基线：2026-11-05 Healthcare 最新 main 的 Medallion ADR、DATA-FLOW、OIE Channel 文档、两个 Local Canonical v1 Contract。
- OIE 真实 FHIR→HL7 消息已验收，但 HL7 Blob 发布未验收；FHIR G4 Approved Silver 已验收，Gold 仍 OPEN。
- A01 单消息缺少 Canonical v1 必需字段；必须将缺失事实与来源 Profile 约束作为阻断条件，不得靠默认值绕过。
- 本 Change 实验全部执行证据指向 Self-Runner 的单独 PR/commit/run；不往 Healthcare 增加实验资产。

## 2026-11-05/06 ET — First isolated Self-Runner experiment evidence

- Self-Runner PR [#525](https://github.com/JohnZhang-DataForge/Self-Runner/pull/525) — `experiments/hl7-dbt-canonical/` only + GitHub-hosted read-only test Workflow；无 Healthcare 业务源码修改/真实云资源访问。
- GitHub Actions [Run #42158571603](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42158571603), HEAD `340f0d08359ca19818ac6018a296c2b64c84162f`: DuckDB job SUCCESS。Parser 6/6 合成正负用例 PASS；dbt seed=1、table models=2、dbt tests=14/14；两次 SQL run/test/readback PASS：staging 2 unique HL7 events，Candidate 1 Patient/1 Encounter。证明纯本地 dbt-duckdb 可以完成受控 SQL ELT；不是 HL7 OIE live → Blob，也不是真实 Silver Delta 发布。
- 同一 Run 的本地 dbt-fabricspark session Job FAIL：`SparkSession` / `dbt debug` 正常，seed 在内置 Hive `spark_catalog` 执行 `REPLACE TABLE` 时 `UNSUPPORTED_FEATURE.TABLE_OPERATION`；属于 Delta Catalog 环境配置差异，尚不能据此判定后端不可用。Self-Runner PR 已追加 Delta Catalog + delta-spark 依赖，**复验结果待核实**。
- **后端 A/B/C 选型仍为 PENDING**；同时缺原始真实 OIE 必需字段、增量/多医院/replay conflict/Delta 外部写入验证；不得宣布完成 2.4/2.5/3.x。

## 2026-11-06 ET — Isolated POC follow-up (no backend selection)

- Self-Runner PR [#525](https://github.com/JohnZhang-DataForge/Self-Runner/pull/525) 的所有实验资产仍位于 `experiments/hl7-dbt-canonical/`，GitHub-hosted Runner 离线执行，**不修改 Healthcare 正式业务代码、Azure Blob、Fabric、OIE 或 Gold**。原架构讨论 PR [#725](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/725) 已合并。
- [Run #42158786199](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42158786199) 在配置 Delta Catalog 后，local `dbt-fabricspark` 的 seed、两个基础 SQL model、14 项 dbt test **PASS**；**没有**验证目标真实 Delta 格式或 MERGE，不能称 Delta E2E 成功。
- [Run #42206889854](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42206889854) 使用新跨医院合成 fixture：DuckDB **PASS**（hl7apy 10 个单测、16 项 dbt tests、基础/重跑/双医院独立读回，Patient/Encounter 1→2，events 2→4）。Local Spark (PySpark 3.5.7/Delta 3.3.2) 在显式 Delta `CREATE OR REPLACE TABLE` 报 `does not support truncate in batch mode`，因此 **Delta FAIL**，尚非语义模型失败。社区相似问题：https://github.com/delta-io/delta/issues/4671。
- 针对该具体兼容问题，Self-Runner 仅实验分支将本地 PySpark pin 到 3.5.5，并将物理 Delta 验收限定在实际 Candidate 与 MERGE 目标（dbt Seed 是 Parquet fixture，不冒充 Delta）。[Run #42207568265](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42207568265) **提交文档时尚未获得完成的复验结论**；使用者必须先检查其最终日志与实际 HEAD，不可推断 PASS。
- **仍未完成 2.4 / 2.5**：对 Spark 的 `_delta_log`、独立 Delta Reader、真实 `MERGE` 更新/插入、同批 Replay、两种引擎字段值等价、实际 OIE→Blob→Silver 的物理验收；所以 dbt-duckdb vs Local Spark vs Fabric 远程运行 **PENDING**，任何后续选择都须以真实证据为据。
