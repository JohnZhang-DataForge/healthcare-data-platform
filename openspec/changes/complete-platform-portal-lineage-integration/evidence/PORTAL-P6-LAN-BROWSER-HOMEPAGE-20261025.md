# P6 — 用户提供的真实 LAN Safari 页面截图审查（2026-10-25）

> **状态：浏览器首页及真实 Job 列表视觉验证 PASS；Job/Run 详情、Dataset Lineage 图仍待截图，P6 7.1 整项 OPEN。** 本登记是用户在项目会话中提供的三张手机浏览器截图的**文字审查结果**，并不是新的 GitHub Actions、外部网络探测或在本仓库公开的图片附件。未经用户额外批准，**不将含内部网络地址的原始截图上传 GitHub**。

## 与机器自动验收的独立关联

- 本次截图审查时 Healthcare Main：`4307ee7ac7c67d07d4a18f7772a363d9e644038e`；图片中的业务 Job 是原始 P5 固定 Batch 的历史资源，**不表示该 Main 重新运行了业务 E2E**。
- 内网官方 Web 机器只读验收 [Self-Runner #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) **SUCCESS**，证实 Web HTML 200、healthcheck OK、Web Proxy/API 数据一致以及真实 Person/Visit/Reconcile 的严格业务 edges。该机器证据与**本次用户提供的 GUI 首页截图是两种不同的证据**。
- 原 P5 Writer COMMIT / PG17 Readback / 同 Batch SKIP：[#40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106)（原 Workflow FAILURE，实际 Writer 已 durable COMMIT）、[独立 Marquez/PG17 #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539)、[SKIP #40209818676](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676)。截图不是新的 PG17 事务证据。

## 实际可观察内容

| 项目 | 三张原始截图能证实的事实 | 验收边界 |
| --- | --- | --- |
| 浏览器设备 | iPhone Safari 呈现了真实 Marquez 官方深色 DataOps UI、侧栏及 Job Card 列表，浏览器地址栏指向内网私网主机 | **PASS：LAN 浏览器首页视觉呈现**。为保护内部拓扑，本仓库故意不记录私网 IP |
| 页面概要 | 用户截图可见 `139 EVENTS`、`23 DATASETS`、`4 SOURCES`、`71 JOBS` 的当时页面统计 | **PASS：页面摘要展示**，仅是截图时点的数字，不作为实时统计或精确 PG14 行数 |
| Airflow DAG | `new_only_omop_consumer` Job Card 可见、状态 `COMPLETED` | **PASS：Job 列表显示**，不等于选中了特定 Run |
| Airflow Writer | `new_only_omop_consumer.execute_new_only_writer` Job Card 可见、状态 `COMPLETED` | **PASS：Writer Job 列表显示**，持久 COMMIT 仍以独立 PG17 Readback 为准 |
| Reconcile 业务任务 | `new_only_omop_consumer.spark_reconcile` Job Card 可见、状态 `COMPLETED` | **PASS：Job 列表显示** |
| Reconcile Spark Application | `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7` Job Card 显示在 `healthcare-platform-spark-business` Namespace，状态 `COMPLETED` | **PASS：跨 Airflow / Spark Namespace 的 UI Job 身份展示**；截图不包含 Run Parent Facet 详情 |
| Airflow 前置任务 | `route_new_only_status`、`inspect_claim_readonly`、`select_verified_new_only_batch`、`scan_ready_manifests`、`route_writer_authorization`、`prepare_writer_handoff` 均可见 Job Card 的 `COMPLETED` 状态 | **PASS：前置任务列表展示** |
| 单一 Run 详情 | 未展示实际某个 Job 的 Run History/Run UUID/ParentRunFacet 详情 | **NOT_CHECKED** |
| Dataset/Lineage 图 | 未展示点击后的上游 `health-landing` / 下游 `health-processing` 数据集或 Person→Reconcile 血缘画布 | **NOT_CHECKED**（尽管独立 API GET 已 PASS） |
| RDD Action 终态 | 本次截图并未显示 Action 子 Run 的 START-only/RUNNING | **NOT_CHECKED**；设计 A 已知 RDD 限制继续保留，不得推断其已消失 |
| 公开访问或网络安全 | 未测试公网可达性、匿名鉴权防护、PG14 备份 | **NOT_CHECKED**；不因此批准开放 Web NodePort |

## 下一步 / 收尾 Gate

P6 7.1 的剩余**唯一浏览器级最低验收路径**：在现有已打开的内网 Safari 官方 Marquez 页面，点击 `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7` Job Card，进入其 Run 详情并核对真实 Run/Parent 关联；随后打开 **Dataset / Lineage** 视图，观察 Person/Visit Processing Dataset 对 Reconcile 的实际输入关系，并提供相应页面截图。也可分别查看 Person 或 Visit 底层 Spark Action Job 的 `s3://health-landing` 输入和 `s3://health-processing` 输出。**如果 GUI 未显示该图**，如实记录 GUI 局限而不能拿 API PASS 冒充屏幕实际呈现。

在得到上述浏览器视觉证据前，OpenSpec `7.1` **不得勾选**、`7.3` **不得归档**。这不影响早已通过的 P5 事务与 API 血缘验收。
