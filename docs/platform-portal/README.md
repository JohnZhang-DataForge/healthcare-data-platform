# Platform Portal 文档入口（Current）

> **A4 Spark 独立真实 Smoke 最新记录（2026-10-14 EDT）**：Spark 3.5.7 在 worker02 的专属 Portal SparkApplication **COMPLETED**，3 行 CSV 实际聚合 PASS；Marquez 新 Namespace 下出现真实 Spark Job 和 1 条带 `processing_engine`/`spark_properties` facets 的 **COMPLETED Run**，见 [A4 实测 Closeout](./A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。**首次完整 Workflow 因 Job 名称含下划线以及 Completed Run 归在 `unknown` Job 而 FAIL**；后续三次只读诊断 SUCCESS，不能把首次 Workflow 标作 SUCCESS。输入/输出 Dataset 血缘和理想的 App Job→Run 关联仍未通过。该次独立 SparkApplication、ConfigMap 和 Pod 已清理，TASK004 业务代码/Writer/OMOP 未修改。新的 Spark 实验仍需人工协调。

> **A4 TASK1 历史静态开发阶段（已完成，见上方最新 Smoke）**：已新增独立 Spark OpenLineage 探针源码、每轮 ConfigMap + SparkApplication 离线渲染与静态测试（只运行 GitHub-hosted，不使用 Self-Runner）；该 TASK1 当时**实际 Spark Driver/Executor/Marquez Run 尚未执行**；其后已完成独立 Smoke。TASK004 正在解决 COMMIT 前的 Secret，后续若再执行新的 Spark 实验，仍须先向用户确认共享执行窗口并只读核查。详见 [A4 静态开发与人工放行门槛](./A4-SPARK-OPENLINEAGE-STATIC-PLAN-2026-10-14.zh-CN.md)。

> **当前并行开发协调 / 2026-10-13 EDT**：另一个 Session 正在开发 TASK004 Spark。**Portal A4 允许设计、文档和独立静态代码；SparkApplication/Runner 实际运行、Airflow 触发与共享组件变更全部 HOLD**，先问用户对方是否已经暂停 Spark 部署/测试、是否有未结束的 Workflow / SparkApplication，取得本次明确人工放行后再做实时只读检查。[**Portal 多 Session 人工协调规则（每任 Agent 必读）**](./SESSION-COORDINATION-POLICY.zh-CN.md)。不用另建自动锁服务。

> **A3 最新 REAL LIVE PASS**：真实 Airflow Provider 事件已进入 Marquez，两个独立 DagRun、两种 Task 各 **2 个 COMPLETED Run**。[Run 38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961)、[Run 38502283003](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502283003)、[Readback Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) 均 SUCCESS。[A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。**NEXT = A4 Spark OpenLineage 的设计/静态开发；实际 Spark 运行待用户人工放行**；TASK004 Claim/Writer 不变。

> 用户确认从 `docs/demo-plan/` **正式迁移为** `docs/platform-portal/`，代码在 `platform-portal/`。历史方案保存在 `archive/`，不再把静态前端旧版方案当成当前 NEXT。

- [架构](./architecture.md)：Marquez、OpenLineage、PostgreSQL14 与现有业务流
- [人工协调规则](./SESSION-COORDINATION-POLICY.zh-CN.md)：跨 Session Spark/Airflow 等共享操作必须先问用户确认再运行（**ACTIVE / 必读**）
- [实施计划](./implementation-plan.md)：当前路线 A 与分期验收
- [A4 Spark OpenLineage 静态开发与 Live Gate](./A4-SPARK-OPENLINEAGE-STATIC-PLAN-2026-10-14.zh-CN.md)：独立探针、版本候选、静态验收与人工放行
- [**A4 Spark 真实 Smoke 与 Marquez Run 读回**](./A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)：独立 Spark COMPLETED、观测 Run、命名缺陷、未完成 Dataset Lineage
- [部署与恢复](./deployment-guide.md)：固定版本、Secret 处理和 Helm/Runner
- [真实验收](./validation.md)：Marquez 安装与 A3 Airflow 实际 Job/Run 证据
- [A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)
- [运维](./operations.md)：PV、备份、访问限制与回滚
- [历史归档](./archive/2026-10-13/README.md)：Marquez A0 预检、旧 Demo v2 方案、三次停止

**已存在的独立数据仓库**：`dw-postgre14` PostgreSQL 14.24 / DB `marquez` / Service `dw-postgre14.dw-postgre14.svc.cluster.local:5432` / Retain PVC `dw-postgre14-data`。不用重装。**任务主线 TASK004 仍独立开发**。

**当前部署阶段（2026-10-13 EDT / 2026-10-14 UTC）**：[Marquez Helm/PG14 Schema 真实 Run 38499534795](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499534795) 的 API+Web 1/1 Ready、PG14 37 张表 PASS（此 Run 后续 NodePort 代码失误导致 workflow FAIL）；[独立 Web-only 恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493) **最终 SUCCESS**，30999 Service 已创建、Web /healthcheck PASS、同源 /api/v1/namespaces HTTP 200。详见 [validation.md](./validation.md)。LAN 浏览器和公网 NAT 尚未实测，Airflow 的真实 OpenLineage 已在 A3 接通；Spark/Writer 下一阶段接入。
