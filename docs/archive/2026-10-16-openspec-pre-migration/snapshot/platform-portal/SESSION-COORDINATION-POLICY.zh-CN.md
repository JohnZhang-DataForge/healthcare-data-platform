# Platform Portal — 多 Session / TASK004 人工协调规则（当前有效）

> **状态：ACTIVE / 2026-10-13 EDT。** 用户确认：TASK004 由另一个 Session 正在开发 Spark；**Portal A4 的实际 Spark 运行、部署与所有可能冲突的共享资源变更暂缓**。本规则适用于以后接手 Portal 的所有 Agent，优先于旧路线文档中“直接开始 Spark/OpenLineage 部署”的历史安排。

## 一、目标：靠用户协调，不建设复杂锁平台

两个 Session 可同时编辑独立代码或只读检查；但**对可能影响同一套 Airflow、Spark 或业务存储的运行/变更，采用人工串行**。不因为不同 GitHub Workflow 文件、不同 PR、不同 Namespace 或同属 `dw-runner-set` 就假设互不干扰。

**职责划分：** TASK004 负责业务数据链路（Synthea / S3 / Airflow 编排 / Spark 处理 / Writer / OMOP）；Portal 负责可观测性（Marquez / OpenLineage / Portal 的独立验证）。两个 Session 各自创建独立 Branch/PR，不擅自修改对方负责的文件和运行组件。

## 二、按“冲突风险”分类，决策在执行之前

| 活动 | Portal 是否可与 TASK004 并行 | 具体要求 |
|---|---|---|
| 阅读文档、GitHub diff、历史 Actions 日志；编写 Portal 文档/独立源代码；不访问共享运行环境的本地语法/单元测试 | **可并行** | 不编辑 TASK004 同名文件，不假设历史 Runtime 状态仍然有效 |
| 针对集群的明确只读 `get` / `describe` / API GET；不启动 Pod/Job，不写缓存/元数据 | **通常可并行** | 控制负载；访问内容不可带 Secret；若测试会消耗大量资源则升级为需协调 |
| 使用 Self-Runner 运行可能启动 Pod/Job 的验收、SparkApplication、Spark driver/executor、PySpark 数据转换 | **必须先询问 + 人工串行** | 即使是 Portal 的独立 Spark Namespace / 测试数据，也会争抢 worker02、Operator、网络或存储资源 |
| Airflow DAG Trigger/Unpause、Scheduler/Helm Values/Provider 配置更新、Airflow/Spark Operator 升级、共享 RBAC/Secret/PV/PVC/StorageClass/Node 配置 | **必须先询问 + 人工串行** | 配置变更可能影响 TASK004 未结束的 DAG/Pod；绝不在另一 Session 使用期间重启共享 Controller |
| 写 SeaweedFS S3、PostgreSQL、生成批次/发布 Manifest，或跨项目共享数据路径 | **必须先询问；默认不执行** | 禁止为了画图触发 TASK004 业务流程、抢占 Claim、修改 Writer 或制造伪造成功 COMMIT |
| 修改 TASK004 的 Spark/Airflow 业务源代码、公共镜像/依赖以及同一 Helm/Workflow 文件 | **停下并协调责任人** | 即便只是 Git 代码修改，也可能与另一 Session 的 Branch/PR 产生逻辑冲突；没有确认不修改 |

注：**只读并不等于无干扰**，大型扫描、资源密集型测试以及有副作用的所谓“检查”按运行类活动处理。GitHub Actions 的不同 `concurrency.group` 之间不互斥，`runs-on: dw-runner-set` 也不提供跨 Session 的排他保护。

## 三、必须执行的人工确认门槛（Portal Agent Checklist）

凡 Portal **准备**进行“必须协调”的任何一步，**先暂停该步**，在回复中明确向用户提问：

> **跨 Session 冲突确认：** 我下一步要在共享集群执行「<准确操作、Namespace、资源名、Workflow 名>」，可能影响 Spark/Airflow 或 worker02。**另一个 TASK004 Session 现在是否还在修改、部署或测试 Spark（以及其他共享组件）？是否存在尚未结束的 GitHub Actions / SparkApplication / DAG Run，或马上计划启动的操作？** 如果已经暂停并释放共享运行资源，请回复“TASK004 共享运行已暂停，Portal 可以执行本次 <具体操作>”；否则我只继续 Portal 文档、独立代码和静态验证，不启动这一步。

**决策规则：**

1. **未收到用户明确确认、用户说 TASK004 正在开发/运行、或无法判断** → 当前有冲突风险的步骤标记 `HOLD / HUMAN COORDINATION REQUIRED`；不得执行共享部署、Trigger 或运行类 Workflow，也不得因为等待失败就私自重试。
2. 用户明确确认已暂停/释放 → **再实时只读检查**相关 Github Actions 状态、现存 SparkApplication/Driver/Executor、Airflow DagRun/TaskInstance、Pod/Deployment 是否有未完成工作。若检查发现仍有冲突 → `HOLD`，告知用户；**只读检查不替代人的授权**，人的授权也不替代真实运行状态检查。
3. 两项均满足，且操作范围仍与确认的一致 → 仅执行已说明的 Portal 单个受控开发/验收闭环，限制资源、固定版本、保留真实证据。不把一次授权推广为后续所有高风险操作的永久许可。
4. 操作完成或失败停止 → 告知用户已释放资源、Run/PR、是否残留 Pod/Job、需要 TASK004 注意的配置；然后 TASK004 才恢复使用。**不得假称存在自动 Session 间通信/全局互斥锁**。
5. 在执行过程中发现另一 Session 已开始操作，或用户撤销/改变协调状态 → 停止**新增**冲突性操作；先评估正在运行的工作能否安全结束，避免粗暴删除正在运行的 Pod/Job。

**强制适用范围**：不仅是“修改 Spark Operator”，还包括看似隔离的 Portal A4 Spark Agent 单独实验；也包括 Airflow Scheduler 重启、Helm 变更和任何可能影响 TASK004 的 Runner 实际任务。

## 四、当前阶段和实际下一步

- **A3 已完成 / LIVE PASS**：Airflow Provider 发出两次真实独立 Portal DAG 的 Task/Run 事件，Marquez 两个 Task Job 各存储 2 条 `COMPLETED` Run。详见 [A3 Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。
- **TASK004 Spark Session：用户当前明确说还在开发 Spark**。不要因其开发没有传入本 Session 就认定“未运行”。
- **A4 Spark OpenLineage：DESIGN / STATIC-ONLY；LIVE EXECUTION = HOLD**。允许整理 Spark Agent 版本、SparkApplication YAML、测试代码、静态检查、文档；**在本轮只做文档，不触发任何 Runner 工作流**。真正的 Spark Operator Job、Pod 和 Airflow 联动一律先执行第三节确认。
- **A5 业务血缘联调：继续 HOLD**；等 TASK004 具备实际对应业务证据，并另行人工协调共享运行窗口。未经成功 Writer COMMIT 不显示成功入库边。
- **现有 A3 Airflow Scheduler 配置**：已经实测工作，但经 `kubectl set env` 修改；将来纳入 Helm Values 也是共享资源修改，需经过同样的人工确认，不趁 TASK004 开发 Spark 时改动。

## 五、给下一任 Portal Session / Agent 的上手顺序

先看 [Portal 首页](./README.md) → **本人工协调规则** → [Portal 实施计划](./implementation-plan.md) → [A3 真实验收](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) → [运行运维](./operations.md)。TASK004 的实时进展以其当前 Session/最新 GitHub Main 为准；不要依赖 Portal 历史规划推断 Spark 现在是否空闲。

在创建或触发涉及集群共享资源的 GitHub Actions 之前，必须先问用户；**GitHub Branch/PR 仅用于独立文档/代码开发，不能代替人工排程**。如果当前仍在 TASK004 Spark 开发窗口，只更新独立 Portal 文档或源代码，保持 A4 Live Gate 为 HOLD。
