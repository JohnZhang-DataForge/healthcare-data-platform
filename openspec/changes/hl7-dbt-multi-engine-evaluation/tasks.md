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
- [x] 2.4 dbt Core + Local Spark (dbt-fabricspark session) compile/seed/run/test 与本地物理 Delta `_delta_log`、Candidate、MERGE 目标独立 SparkSession 读回、基础/重跑/双医院扩展均已通过 [Run #42207568265](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42207568265)。适用 PySpark 3.5.5 + delta-spark 3.3.2；当前 Fabric Spark 4.1 的兼容性不由该 POC 证明。
- [ ] 2.5 同一 synthetic fixture 对齐 Candidate 值、异常分类、SQL/Delta 能力、运行成本；对比打分，**测试后**提议选型。

## 3. 正式 HL7 集成（OIE/Raw 上游已获批验收；后续 Silver/Gold 仍未授权）
- [x] 3.1 OIE V2 来源扩展与真实字段审计已完成（DOB/Gender/US Core CDCREC Race/Ethnicity、A01 admission + A03 discharge），新合成请求的 42 Message OIE 独立持久 GET 在 P2 Run #42410482514 PASS；共享 Azure Publisher 的 42 HL7 Raw + Manifest-last/远端独立 GET/HEAD/Blob-only replay 在 P3 Run #42412009780 PASS。**只代表已限定合成 Johns Creek Hospital B 上游 Producer/Raw 链路，不代表 HL7→Canonical Silver 已交付。**
- [ ] 3.2 以单独 Implementation OpenSpec 完善实体插件/Schema/版本化 Profile、单一 Silver Publisher、quarantine、replay、readback。
- [ ] 3.3 Azure/Fabric 真实 E2E 需要单独的执行授权和证据；不得因本地 POC PASS 推导真实 Silver Approved 或 Gold COMMITTED。

## Evidence / Blockers
- 设计基线：2026-11-05 Healthcare 最新 main 的 Medallion ADR、DATA-FLOW、OIE Channel 文档、两个 Local Canonical v1 Contract。
- **2026-11-07 新事实：** OIE V2 P2 真实 21 A01 + 21 A03 Message ID 持久化 GET 在 [Run #42410482514](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42410482514) PASS；同一冻结来源 42 个原始 HL7 Azure Blob 对象 + Manifest 的独立 GET/HEAD、Blob-only Replay 在 [P3 Run #42412009780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42412009780) PASS。**HL7 Raw Landing 已完成**，但这不等于 HL7 Parser/dbt 消费了真实 Azure 数据或 Fabric Approved Silver / Gold 已完成。
- 旧版单独 A01 事件无法证明 completed Encounter 的 Canonical v1 必需 end_datetime；新版 OIE V2 经合成 FHIR 来源真实 Profile 评审已带真实 DOB/Gender/Race/Ethnicity 及有据可查的 A03，**只有合法 A01+A03 成对时才可生成完成 Encounter Candidate**。其它医院 Profile、未知或多编码病例仍应 HOLD，不得造默认临床事实。
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

## 2026-11-06 ET — Actual local Delta candidate/readback acceptance

- [Self-Runner Run #42207568265](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42207568265) 的两个 CI jobs 均 `SUCCESS`：GitHub-hosted ubuntu-latest，Synthetic HL7 parser 10/10；DuckDB dbt 2 models + 16/16 tests（三阶段）；Local Spark dbt 3 models（含独立 Delta MERGE probe）+ 16/16 tests（三阶段）。没有使用 Fabric Capacity、Azure/OneLake/OIE 实机或其他云凭据。
- **最重要的增量 Delta 证据：** 第二个**独立** SparkSession 对 `canonical_patient`、`canonical_encounter` 与 `delta_event_merge_probe` 逐表执行 `DESCRIBE DETAIL` 确认 `format=delta`，检查目标物理 `_delta_log` 存在，并独立读回。同批重跑不增加重复；第二个合成医院相同来源 local Patient/Visit ID 进入独立 source namespace，Patient/Encounter 1→2，原 MSH-10 所属 source 更新 `processing_run_id` synthetic-poc-001→002，probe 行数由 2→4，证明在此本地组合中 `MERGE` 更新/插入有验证。
- **重要限制：** 上轮 Spark 3.5.7 + delta-spark 3.3.2 `CREATE OR REPLACE TABLE` `truncate in batch mode` FAIL，换成 PySpark **3.5.5** 才通过；运行日志出现不致失败的 `HiveAlterHandler` error，应单独评审其在本地 metastore 的副作用。这与 Fabric 4.1 或 OneLake 真实远端 Delta 兼容性仍是不同验收层级。
- 最新 Self-Runner PR [#525](https://github.com/JohnZhang-DataForge/Self-Runner/pull/525) 还增加了两个后端对 Canonical 关键字段值的精确断言/规范化哈希对照；该**新 HEAD 的测试尚未在此文档提交时获得完成验收**，所以 2.5 保持 OPEN、dbt 执行后端保持 PENDING。

## 2026-11-06 ET — Full Canonical v1 and local Candidate delivery gate

- Self-Runner PR [#525](https://github.com/JohnZhang-DataForge/Self-Runner/pull/525) 继续保持**隔离实验源码唯一归属**；Healthcare 此更新只记录证据，不增添实验代码、正式 Contract 的第二份权威、Fabric Notebook/Job 或 CI。使用的 `fixtures/canonical-v1.snapshot.json` 明确是离线测试用只读快照，引用 Healthcare Patient 18 字段及 Encounter 27 字段合同 Git Blob SHA；未来实施必须与权威合同最新 SHA 再对照。
- [CI Run #42213497623](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42213497623) **DuckDB job SUCCESS**：开源 hl7apy 的 15 个合成正反向 parser 用例，通过严格 HL7 来源隔离、无效性别/人口学代码、时间冲突、重复 MSH-10 不同 SHA 的 HOLD；Canonical Patient 18/18、Encounter 27/27 字段顺序/类型/非空数据/来源联合主键、联合 FK 测试通过，dbt 16/16；两医院合成输出 2 Patient、2 Encounter。缺失 A03 的 A01-only 测试保持 Patient 1、completed Encounter **0**，没有造出院时间。
- 同一 DuckDB Job 还验证本地（**非云端**）Candidate Parquet `manifest-last` 交付包的 object SHA256/size/row-count 独立读回、同版本 replay SKIP 和单字节篡改拒绝；Package Status 明确 `CANDIDATE_ONLY_NOT_APPROVED`。这是**未来 Fabric Silver Publisher 的接口 POC**，不能宣称 OneLake/Blob 已接入、远程 Approval 已完成。
- **Spark 最新 Full Contract gate PASS：** [Run #42213497623](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42213497623) 的 DuckDB 与 Local Spark 两个作业均 SUCCESS（最新 HEAD `61bf15b7b0db6e593dc556020c28465573018bd3`）。Local Spark `dbt-fabricspark method=session` 在 PySpark 3.5.5 / Delta 3.3.2 下，Patient 18/18 字段、Encounter 27/27 字段、SQL 类型、强制非空数据、来源联合 PK/FK、16/16 dbt tests、真实 Delta `_delta_log`、单独 MERGE probe 的 baseline/replay/双医院扩展/独立读回全通过。两后端关键 Canonical 字段的 SHA256 在 baseline/expanded 场景逐一相同。**并不等于 Fabric Spark 4.1 / 远端 OneLake E2E 已通过。**
- **明确剩余范围：** 虽然 Delta `MERGE` probe 已在 Local Spark 测过，正式 Patient/Encounter Candidate dbt models 仍为 `table` materialization，并非已完成生产增量模型；真实 OIE A01 信息不完整、Azure Blob Producer/Publisher 与 Fabric Approved Silver Publisher E2E 均未验证。
- **Self-Runner PR #525 已合并 Main：** [PR](https://github.com/JohnZhang-DataForge/Self-Runner/pull/525)，squash commit `f45131f72091cbf4170132640a6a0c0d38ac7a67`。变更仅 26 个文件：`experiments/hl7-dbt-canonical/` + 一项隔离新 CI Workflow。由此 POC 代码、Schema 只读快照、日志链接和运行说明均可从 Self-Runner Main 找到；绝无 Healthcare 实验代码。
- **选型比较（当前可核查的 POC 结论，非生产性能测评）：**

  | 维度 | dbt-duckdb / Runner | dbt-fabricspark local session / Runner |
  | --- | --- | --- |
  | HL7 Parser → dbt SQL / 18+27 Canonical 合同 | PASS | PASS |
  | 本地增量与同源重跑 | SQL 重算/readback PASS；dbt 原生增量未验证 | 独立 Delta MERGE probe PASS；正式 Candidate 增量仍待做 |
  | Candidate 物理格式 | Parquet + Manifest-last SHA / tamper reject PASS | 真实 Delta + `_delta_log` PASS |
  | 两家医院相同 local PK 隔离 | PASS | PASS |
  | 本地引擎计算需 Fabric Spark CU？ | 不需要 | 不需要（`method: session`） |
  | CI 小合成数据工作流主要执行/读回阶段 | 历史 ~38 秒 | 历史 ~395 秒（JVM/Hive 启动明显更重） |
  | 版本和迁移问题 | DuckDB→OneLake Delta 发布接口未验收 | PySpark 3.5.7/Delta 3.3.2 组合曾失败；3.5.5 能通过但有 HiveAlterHandler 错误日志 |
  | Fabric 4.1 / 远端 OneLake Publisher | 未验证 | 未验证 |

- **决策保持 PENDING**：当前本地技术可行性已验证，但只有真实 Silver Publisher 的受控交付/单 Writer 边界、OIE 原生 HL7 必需事实、Canon-v1/v2 放行策略和成本/恢复验收明确后，才作最后 DuckDB / Local Spark / Fabric remote 路线选择。禁止因成功 POC 推断正式 Silver/Gold 已完成；`2.5` 持续 OPEN 直至完成后端决策记录。
