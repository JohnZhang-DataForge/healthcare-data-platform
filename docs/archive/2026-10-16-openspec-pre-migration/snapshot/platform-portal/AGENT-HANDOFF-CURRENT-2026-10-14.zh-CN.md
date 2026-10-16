# Platform Portal — 新 Session 接手说明（2026-10-14 EDT / CURRENT）

> **目的**：新 Agent 不再重复部署/验收 A3/A4 已证明的部分，聚焦 A4 剩余“Spark Job↔Run 关联”和真正 Dataset 血缘，随后在 TASK004 业务完成时接 A5。**这是一份交接/待办，不是新一轮 Spark 运行授权。**

## 1. 优先阅读（按序）

1. 本文及 [Portal 入口](./README.md)。
2. [多 Session 人工协调规则（强制）](./SESSION-COORDINATION-POLICY.zh-CN.md)。
3. [A4 真正的 Spark Smoke 及局限](./A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。
4. [A4 代码与验收方案](../../platform-portal/openlineage/spark/README.md) 和 [A3 Airflow 真实 Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。
5. 若要接 TASK004 业务结果：最新 [TASK004 状态](../tasks/TASK-STATUS.md) 和根 [Agent START HERE](../README.md)；先核对 Main 最新 SHA，因为另一个 Session 同时开发、状态变化快。

仓库：`JohnZhang-DataForge/healthcare-data-platform` 和 `JohnZhang-DataForge/Self-Runner`。以 GitHub 当前 Main 和真实 Runner 证据为准，不要把旧历史计划中的 NEXT 当成当前事实。

## 2. 已部署/已验证（不要重复施工）

| 阶段 | 真实完成状态 |
|---|---|
| Marquez + PostgreSQL14 | `dw-marquez` API/Web，`dw-postgre14` 独立持久化 DB；Schema 37 表，Web-only NodePort `30999`（LAN/NAT 实际浏览器仍未验收）。 |
| A3 Airflow → Marquez | **REAL PASS**：Airflow 3.2.2 + OpenLineage Provider 2.17.0，通过 opt-in 测试 DAG 两次真实运行，两项 Task 在 Marquez 各有 2 条 COMPLETED Run。参见 [A3 Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。 |
| A4 Task 1 静态实现 | [Healthcare PR #139](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/139) merged；Spark 3.5.7 隔离模板、配置、3 行 ConfigMap CSV、PySpark 聚合、离线 YAML renderer、6 项静态测试。GitHub-hosted CI [38627135708](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38627135708) **SUCCESS**；未使用 Self-Runner。 |
| A4 单次独立 Spark Smoke | **Spark 计算 PASS + Marquez 真实 Run PASS（组合证据）**，但最初 Live Workflow **FAILURE**，见下节。测试资源已清理，不存在需要继续等待的 Portal Driver/Executor。 |
| TASK004 | **独立 Session 负责**。用户最新说明：Spark 业务处理基本跑通，正在处理数据库 COMMIT 阶段 Secret 问题；不要未经最新核对就声称 TASK004 已完全 COMMIT。 |

## 3. A4 最重要的事实、问题及准确状态

**唯一真实 A4 Spark 应用**：`dw-spark/portal-a4-a438628542127`（已删除）。Spark image `spark:3.5.7-python3`，Listener `io.openlineage.spark.agent.OpenLineageSparkListener`，Agent Maven `io.openlineage:openlineage-spark_2.12:1.47.1`，独立 CSV 只读聚合：3 行 → alpha=40、beta=20。没有访问 TASK004 S3/OMOP、没有触发业务 DAG 或 Writer。

真实证据：

- [Self-Runner **38628542127**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) **WORKFLOW FAILURE**：SparkApplication `COMPLETED`、CSV aggregation `PASS`；最终 Marquez 读回脚本错误地预期含连字符 Job 名称及 Run 同名，查找超时导致整个 Workflow FAIL。**不得将此 Run 整体标为 SUCCESS**。
- [只读诊断 **38629218047**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629218047) SUCCESS：Marquez Namespace `healthcare-platform-spark-probe`；两个 Job：`portal_a4_a438628542127`（规范化下划线）和 `unknown`。
- [只读验证 **38629414644**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629414644) SUCCESS：`unknown` Job 下真实 `COMPLETED` Run UUID `01a13c02-6d9c-7684-913d-f64966d76110`，`startedAt=2026-10-14T20:02:27.550Z`，`endedAt=2026-10-14T20:02:54.236Z`。
- [只读 facets / 清理 **38629607225**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225) SUCCESS：完成 Run 的 facets 包含 `environment-properties` / `processing_engine` / `spark_properties`；Portal 临时应用 Pod 残留 0，ConfigMap 和 SparkApplication 已清理。
- [Self-Runner PR #110](https://github.com/JohnZhang-DataForge/Self-Runner/pull/110) merged：更新的 Live Smoke Workflow **仅支持手工 `workflow_dispatch`，不会因 push 重启 Spark**。修复了读回的名称判断，但**修复版本尚未重新实际执行**。绝不为了修正之前的 Workflow 状态而盲目再次触发 Spark。
- [Healthcare PR #140](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/140) merged：上述真实记录及准确的部分 PASS 已写入 Portal 文档。

**未解决的 2 个 A4 细节：**

**(A) Spark Job↔Run 关联**：应用 Job `portal_a4_a438628542127` 的 `latestRun` 为空，而实际完成的 Run 记在 `unknown` Job 下。存在运行事件，但无法在 Marquez 中把“具体应用 Job”和“这次运行”清楚对应。**根因尚未确认**；不能仅凭名称标准化就断言 Spark Listener 的 Job 命名为什么变成 `unknown`，也不能把观察到的两条独立 Job 伪装成正常 App Job→Run 关系。优先只读查看实际 Job 和 Run facets、已保存的 OpenLineage 元数据、相关 Spark Agent 配置及历史执行日志，提出可验证的最小改动，仅修改 Portal 专属 Spark 模板，避免重装 Operator。

**(B) Dataset 输入输出血缘**：Marquez 中该次 Run 的 `inputDatasetVersions=0`、`outputDatasetVersions=0`，应用 Job `inputs=0`、`outputs=0`。本次仅通过 Kubernetes ConfigMap 挂载的 `file:///opt/spark/portal-a4/input.csv` 读取 3 行虚拟 CSV；没有写 Parquet，所以这 **不是** S3/Parquet 输入输出的完整 Dataset Lineage 证明。要显示类似“哪个 CSV/Parquet 输入 → 哪个 Spark Job → 哪个 Parquet 输出”，后续需在人工放行后使用明确隔离的、真实受支持的输入输出存储路径；或等 TASK004 完成后再通过真实业务 Spark 运行捕获，但不要随意改写 TASK004 Spark 代码、S3 数据、Claim/Writer/OMOP。

## 4. 下一 Session 的建议路线（小步闭环）

**第一步：只读调查，不启动 Spark**。从现有 Marquez API GET 读两个 Job 与完成 Run 的 detail/facets，分析应用 Job 为什么 `latestRun=null`，以及 `unknown` 的 parent/context；查代码中的 Spark/OpenLineage 配置与官方版本契约。形成最小修复设计。此阶段不需要新的共享 Spark 执行窗口。

**第二步：若要验证修复**，先严格按 [人工协调规则](./SESSION-COORDINATION-POLICY.zh-CN.md) **向用户询问**：另一 TASK004 Session 是否还在修改、部署、测试 Spark / Airflow / 共享组件、是否正在跑数据库 COMMIT 联调，是否有未结束的 Workflow / SparkApplication / DagRun。用户明确释放本次窗口后，实时只读核验空闲，再仅运行一次带唯一名称的 Portal smoke；不要为了看起来 PASS 反复执行超过 3 次。完整保留原 FAIL 与新 PASS 证据。

**第三步：Dataset 血缘**。优先考虑最小的 Portal 自有临时 S3/prefix（注意授权与 Secret），或以后在用户明确允许的 TASK004 已成功业务运行上做 Observer/Listener 集成。必须是真实 Dataset in/out 事件；不能手工 POST 一个“漂亮的”虚假完整血缘图。若尚无实际输出，则如实标记未完成。

**第四步：A5**。在 TASK004 真正完成 Person/Visit 写入/COMMIT 和幂等验收后，再规划 Airflow→Spark→S3→OMOP 的业务 lineage。仅当 Writer 实际 COMMIT 才记录“成功入库”。

## 5. 强制约束与验收原则

- **业务优先**：Portal 只是可观测性；不为完善图而延误或改变 TASK004，尽量复用既有 Runner/Workflow；不新建自动 Session 间锁体系。
- **手工排程**：两个 Session 同用 `dw-runner-set` / worker02 / Spark Operator / Airflow，名称或 Namespace 不同也可能争用资源。**任何共享部署/实际 Spark 运行前先问用户**；只读检查不是永久授权。用户说另一个 Session 正在运行就 HOLD。
- **代码隔离**：Portal 放 `platform-portal/openlineage/`、文档 `docs/platform-portal/`、Workflow 用 `portal-a4-*`；不要编辑 `spark/apps/task004`、`airflow/dags/task004_*`、`apps/task004`、TASK004 Writer/Secret/OMOP 配置。
- **Runner 生命周期**：Self-Runner 跑临时 Spark 需最后清理 Portal 专属 ConfigMap/SparkApplication/Pod；如果业务 Job 未结束不要盲删；报告真实 run ID、状态和残留资源。
- **实证分级**：Python 静态 PASS ≠ Spark 真执行；Spark COMPLETED ≠ OpenLineage 事件入库；Marquez COMPLETE Run ≠ App Job 正确关联；Job/Run PASS ≠ Dataset Lineage；Dataset PASS ≠ OMOP COMMIT。每级要有对应的独立证据。
- **Git**：独立 feature branch → PR → review changed filenames / concurrent Main SHA → merge。修改共享 Main 文档时用新增说明覆盖历史旧 NEXT，不覆盖 TASK004 进展。

## 6. 新会话启动提示词（直接复制）

继续开发我的 Healthcare Data Platform 的 **Platform Portal A4**，先以 GitHub Main 当前状态为准：

- 仓库：`https://github.com/JohnZhang-DataForge/healthcare-data-platform`
- Runner：`https://github.com/JohnZhang-DataForge/Self-Runner`
- 必读：`docs/platform-portal/README.md` → `docs/platform-portal/AGENT-HANDOFF-CURRENT-2026-10-14.zh-CN.md` → `docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md` → `docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md`。
- A3 已真实完成，A4 独立 SparkApplication 已 COMPLETED、Marquez 有真实 Spark COMPLETED Run；但应用 Job 名为 `portal_a4_a438628542127`、其 `latestRun` 为空，实际 COMPLETED Run 在 `unknown` Job 下；Dataset 输入/输出版本均 0。当前任务是**先做只读诊断与最小修复设计**，不要重复部署 Spark。
- TASK004 由另一个 Session 开发，最近在解决数据库 Secret / COMMIT；不要修改 TASK004 源码、工作流、S3 或 OMOP。**在任何新的 Spark/Airflow 实际部署/触发前，必须先询问我 TASK004 共享操作是否已暂停并取得本次许可，接着只读确认空闲**。
- 优先 GitHub PR 保留设计/实现与验收证据，失败 3 次停止；不要用虚假 OpenLineage JSON 冒充真实业务关系。每个小步至少完成“代码/读取 → 反馈 → 验证”的完整闭环。
