# Platform Portal A3 — Airflow Provider → Marquez 真正的 Job/Run 验收 Closeout

**日期**：2026-10-13 EDT / 2026-10-14 UTC  
**阶段**：A3；**结果**：**REAL PASS**，真实 Airflow Task → OpenLineage Provider → Marquez PostgreSQL14 记录。  
**隔离条件**：无 Synthea/S3/Spark/OMOP/Writer 业务操作，TASK004 业务逻辑不改动；Marquez API 使用内部 ClusterIP。

## 1. 原始证据和可追踪 SHA

- [第一轮无副作用环境预检 Run 38501427974](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38501427974) **SUCCESS**：运行中的 Scheduler 是 Airflow 3.2.2，Provider 2.17.0 / openlineage-python 1.47.1，默认 transport 未配置，选择性功能可用，Airflow 到 Marquez 私有 API HTTP 200。
- [静态源码和真实 Airflow 运行时加载 Run 38501866970](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38501866970) **SUCCESS**：加载 Portal 的两任务 opt-in DAG，不触发业务/数据库/集群变更。
- [Healthcare PR #110](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/110) **MERGED** SHA **63c56afbf617c5aa844eeaa9bb25b84c3bc2f85d**，Portal 独立 DAG、受控 Scheduler 配置和读回脚本。
- [首次实际接入 Run 38502006416](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502006416) **FAILED**：检查 Airflow 活跃任务=0、到 Marquez HTTP=PASS、Scheduler 环境变量已配置；在 Scheduler 滚动更新回读时误选已终止的旧 Pod，未触发 DAG。**不能称为接入 PASS**。
- [Healthcare PR #111](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/111) **MERGED** SHA **ab7570d109f3c7cb36b8228fd3d870657b4ba268**：仅排除 terminating Scheduler Pod，不改变 TASK004。
- **[实际 DAG + Provider 接入 Run 38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961)：SUCCESS**。检查活跃任务=0，滚动 Scheduler 选择性配置 PASS，GitSync 原始 DAG SHA / DagBag 选择性标记 PASS，真实 Airflow DagRun 和两项 TaskInstance SUCCESS，Marquez API 真正返回 3 个 Job。
- [只读定位 Run 38502637283](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502637283) **SUCCESS**：原始新 DAG 默认为 PAUSED，DagRun 当时 QUEUED，Marquez 尚无 Job，符合调度前实际状态。
- [仅激活 Portal DAG Run 38502759492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502759492) **SUCCESS**：解除 platform_portal_openlineage_probe 暂停状态，其他 DAG 不变。随后第一轮真实 DagRun 才正常执行成功。
- **[Marquez 真正 Run 完成状态读回 Run 38502899963](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502899963)：SUCCESS**，从 Marquez 官方 Jobs/Runs GET API 回读两个 Task Run，各有 1 条，state **COMPLETED**；不曾手工伪造 OpenLineage 事件。

## 2. 真正的运行数据

- **Airflow Dag ID**：platform_portal_openlineage_probe；**真实 DagRun ID**：portal-ol-38502227961；Airflow DagRun state **success**。
- Airflow TaskInstances：**observe_runtime=success**、**confirm_runtime=success**。
- Marquez namespace：**healthcare-platform-airflow**，真实返回 Job：
  - platform_portal_openlineage_probe
  - platform_portal_openlineage_probe.observe_runtime
  - platform_portal_openlineage_probe.confirm_runtime
- Marquez Runs API：observe_runtime **1 个 COMPLETED**、confirm_runtime **1 个 COMPLETED**。
- Marquez 持久化后端仍为独立 **dw-postgre14/marquez**（原有 PostgreSQL14.24），不是 OMOP/airflow 数据库。
- 收集途径：现成 **apache-airflow-providers-openlineage 2.17.0** 自动生成真实任务事件；没有独立 POST 假数据，也没有生成虚构 S3 Dataset/OMOP COMMIT 成功边。

## 3. 选择性隔离 / 运维约束

- 配置只写入 **dw-airflow-scheduler** 主容器：
  - Transport：内部 Marquez API service + api/v1/lineage
  - Namespace：healthcare-platform-airflow
  - selective_enable = True
  - disable_source_code = True
  - execution_timeout = 5 seconds
- 只有由 enable_lineage() opt-in 的 Portal DAG 发出事件。TASK004 的现有业务 DAG、Claim、Spark/Writer、PostgreSQL17 未改。
- Scheduler 共享部署滚动更新前，使用 ORM **TaskInstance active/queued/scheduled/retry 计数=0** Gate；本次 PASS。仍应注意这个配置属于实际 K8s Deployment env 修改，**尚未同步到正式 Airflow Helm values**，未来 Helm upgrade 可能重置配置，需在下一轮运维化计划对齐。
- 新 Portal DAG 首次创建会默认 paused；已在独立 Run 中只 unpause 这一个 DAG。日后新部署环境应单独检查 DAG 默认暂停设置。
- 已创建的 Web-only NodePort 30999 网络访问控制尚未做家庭路由器 NAT/firewall 正式验收。原生 Web 仍代理 API，不能称匿名公网只读门户。

## 4. 当前准确的下一步

**A3 = PASS，NEXT = A4 Spark OpenLineage Agent 的独立验证**：先用完全与 TASK004 隔离的 SparkApplication + 试验输入/输出观察真实 Driver/Executors 运行事件；再验证 Marquez Spark Job/Run。不要为了画完整数据线而绕开 TASK004 Claim/OMOP Writer 的业务成功门槛。

完整 Synthea → S3 → Airflow → Spark → PostgreSQL 成功链条仍等待 TASK004 的真正写入、reconciliation 和 COMMIT 证据；TASK005 仍 ON HOLD。
