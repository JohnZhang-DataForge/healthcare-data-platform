# Platform Portal — 真实数据血缘与数据平台可观测性

> **当前定位（2026-10-14 EDT）：** 本目录是 Healthcare Data Platform 的 **OpenLineage + Marquez 可观测性子项目**，不是 Microsoft Fabric、MLflow、Mirth 或独立 Web 门户的已完成实现。Airflow OpenLineage 和独立 Spark Smoke 存在实际验收，但完整业务 Job/Run 关联及 Dataset I/O 血缘仍待开发。**TASK004 Person/Visit OMOP 主链路已完成并通过幂等性验收**（[最终 Closeout](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)）；旧文档里“TASK004 仍在开发”的表述是先前状态，不再是最新进度。

## Directory map / 模块入口

| 路径 | 用途 |
| --- | --- |
| [`marquez/`](marquez/) | Marquez Helm 配置、部署、Web 恢复和验证脚本 |
| [`openlineage/airflow/`](openlineage/airflow/README.md) | Airflow OpenLineage 配置和真实事件验证 |
| [`openlineage/spark/`](openlineage/spark/README.md) | Spark OpenLineage 独立探针、静态测试及 SparkApplication 模板 |
| [`postgres/`](postgres/README.md) | Marquez 使用的独立 PostgreSQL 14 资源快照 |
| [`../docs/platform-portal/`](../docs/platform-portal/README.md) | Portal 的详细设计、运行记录、交接与多 Session 协作规则 |



> **A4 独立 Spark Smoke 有真实运行证据**：[完整中文 Closeout](../docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)；SparkApplication `COMPLETED`，3 行 CSV 聚合成功，Marquez 真实 Spark `COMPLETED` Run 已读回（原首个 Live Workflow 的错误 Job 查询导致整体 FAILURE；三个后续只读 Workflow SUCCESS）。仅 Portal 独立资源，已清理，未改 TASK004。Job/Run 命名、Dataset I/O 血缘仍为后续工作。

> **A4 任务1 静态源码**：[`openlineage/spark/README.md`](./openlineage/spark/README.md)（独立 SparkApplication/ConfigMap 模板、纯只读 CSV 探针、离线渲染、静态测试；未部署，实际 Spark 执行必须经人工协调）。

> **执行前必读**：[多 Session 人工协调规则](../docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md)。**当另一 Session 正在使用共享 Airflow/Spark 资源时**，Portal 开发应先做独立静态代码/文档；启动 SparkApplication、Runner 真实集群验证或修改共享组件前，先询问用户其他 Session 是否正在修改/部署/测试 Spark，明确协调后再检查共享资源是否空闲。

本目录保存 **实际正在开发/运行** 的 Marquez、OpenLineage、专用数据库和后续 Portal 组件。业务 ETL 仍在原有 `airflow/`、`spark/`、`apps/` 与 `scripts/`，不搬家。

- `marquez/helm/values.yaml` — PostgreSQL14 外部数据库配置（**不存 Secret**）
- `marquez/kubernetes/deploy.sh` — 非破坏式、固定 upstream 版本部署入口
- `marquez/tests/verify.sh` — API/Web/PG14 真实验收
- `postgres/*.yaml` — 由已部署的 PostgreSQL 14 实际 YAML 保存的 Git 快照。**不代表重新部署**。
- `openlineage/spark/` — A4 独立候选 Agent/探针/离线 YAML，**不修改共享 Spark Operator 或 TASK004 应用**。
- `../docs/platform-portal/` — 统一文档（架构、计划、部署、验收、运维和历史归档）

当前 Marquez Namespace 固定 `dw-marquez`，PostgreSQL14 Namespace 固定 `dw-postgre14`；不接触 `dw-postgre` 中的 OMOP/Airflow 数据库。初期只有经 LAN/VPN 的原生 Marquez Web，**不是自定义网站**。
