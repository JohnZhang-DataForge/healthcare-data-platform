# P6 — 用户提供的真实 LAN 浏览器可视化证据审查（2026-10-25）

> **最新最终结论（覆盖本文下方历次“尚未验证目标 Batch”历史快照）：P6 7.1 方案 A 的真实官方 Marquez GUI 演示已通过。** 用户在同一内网 Chrome 官方 Web 页面实际打开新批次 `synthea-new-only-gh-40208104106` 的 **Encounter 与 Patient 两个 Processing Dataset**，并在该 Batch 的 Table Level / Column Level 看到有向 Job 数据流和逐列映射；对应历史 P5/P6 API GET 已证明 Reconcile 消费两份真实 DatasetVersion。该 GUI 没有展示 Reconcile Application 的完整合并图、完整 Run History 或物理 RDD Action 的最终态；这些限制**仍单独如实披露**。P6 7.3 OpenSpec Archive 仍须另行核对整个 Change 的未完成任务，不能从 7.1 PASS 推导整个 Change 完成。用户截图中带私网地址，**只保留文字审查，不在 GitHub 提交原始图片**。



> **最新分层结论：Safari 首页/Job 列表 PASS；P5 Reconcile Application Chrome GUI Parent job namespace 和 Run ID 前缀可见且与独立 API 证据吻合；Full Graph=ON 时该 Application 仍为单一 Job 节点；另一历史 Batch 在官方 Dataset 页面真实呈现 Column Lineage 连线 PASS。** 但历史 Dataset 属于 2026-10-21 的 Batch，**不是** P5 指定的 2026-10-25 Batch；P6 7.1 的目标 Batch Dataset GUI 精确对账仍 OPEN，7.3 Archive 不可提前关闭。 本登记是用户在项目会话中提供的最初三张手机浏览器截图及后续三张桌面 Chrome Reconcile Job/Run 截图的**文字审查结果**，并不是新的 GitHub Actions、外部网络探测或在本仓库公开的图片附件。未经用户额外批准，**不将含内部网络地址的原始截图上传 GitHub**。

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
| 单一 Job 与 LATEST RUN 详情 | 后续桌面 Chrome 真实打开 Reconcile Spark Application Job 详情：状态 `COMPLETED`，页面 `LATEST RUN` 面板、Job Facets 与 Run Facets 真实渲染，`RUN HISTORY` 页签可见（未打开） | **PASS：已可视化 Job 详情与最新 Run Facets**；Run UUID/完整历史列表仍 NOT_CHECKED |
| Dataset/Lineage 图 | Reconcile Application 的 Full Graph 从 OFF 切到 **ON** 后仍只有单个 JOB 节点；另一个历史批次的 Dataset 页面在 **Column Level** 下可见真实字段映射连线 | **GUI 能绘制历史 Column Lineage = PASS**，但 P5 目标 Batch 的 Dataset 图仍待检查；不能把旧批次图作为本批次展示证据 |
| RDD Action 终态 | 本次截图并未显示 Action 子 Run 的 START-only/RUNNING | **NOT_CHECKED**；设计 A 已知 RDD 限制继续保留，不得推断其已消失 |
| 公开访问或网络安全 | 未测试公网可达性、匿名鉴权防护、PG14 备份 | **NOT_CHECKED**；不因此批准开放 Web NodePort |

## 用户追加 Chrome Reconcile Job / LATEST RUN / Run Facets 截图（2026-10-25）

该组**新增三张桌面 Chrome 屏幕截图**显示与 Safari 同一真实业务环境，但**不在 GitHub 保存任何带局域网私有 IP 的原始图片或完整浏览器 URL**：

- **实际页面/身份**：Marquez 真实 `Lineage / Job` 画布选中 `healthcare-platform-spark-business` 中的 `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7`。表级（`Table Level`）模式、`Depth=2`，截图中 `Full Graph` 关闭；画布只有孤立的一枚绿色 `JOB` 节点。**不能把该图报告为已经展示 Person/Visit→Reconcile 的 Dataset 图**。
- **实际 Job 详细面板**：成功打开右侧详情，`RUNNING STATUS=COMPLETED`、`TYPE=BATCH`、`LAST RUNTIME=0m 50s`，时间显示 2026-10-25 上午 11:47–11:48；`PARENT JOB` 字段存在但名称截断，不能靠它单独判定精确 Parent UUID。
- **实际最新 Run / facets**：`LATEST RUN` 页签处于选中状态，`RUN HISTORY` 页签可点击但尚未截图确认历史明细。Job Facets 的 `jobType=APPLICATION`、`integration=SPARK` 可见。展开的 `RUN FACETS` 包含 `environment-properties`、`parent`、`spark_properties`、`processing_engine`；后者显示 `name=spark`、`version=3.5.7`、`openlineageAdapterVersion=1.47.1`。Facet 的 `parent.job`、`parent.run` 仍是折叠的子对象；**仅能证实 parent 元数据存在，具体 job/Run ID 仍需展开确认**。
- **历史机器独立对账范围**：已成功的 [P5 GET-only #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 与 [P6 GET-only #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) 曾用精确 Parent UUID / 子 Spark Action DatasetVersion 在 Marquez API 得到 `business_edges_gate=PASS`；本组 UI 验证的是**Application 本身**，物理 Action 的 Dataset 图应转至带实际输入输出 DatasetVersion 的 Action Job / Dataset 页面核验，不能将 Application 孤点图理解为 ETL 未产生数据。
- **安全**：截图中的 `DELETE` 是 Marquez Job 详情自带操作按钮，**绝对不得点击**；此次仅打开页面，没有操作删除、修改 Job、写数据或人为补发 OpenLineage COMPLETE。
- **仍 OPEN 的 P6 7.1 残余 GUI Gate**：浏览器展开 `parent.job` 与 `parent.run` 至具体身份，再进入 Person/Visit 或 Reconcile 的实际 **Spark Action** Job 或 Dataset 页面，检查 `health-landing` 输入、`health-processing` 输出以及 Reconcile 消费两条 Processing Dataset 的可视化关系。若 GUI 版本无法绘制该依赖，则如实记录限制，不能靠后端 GET 冒充 GUI 连线。

## 用户进一步 Chrome 截图：Reconcile Parent + 历史 Column Lineage（2026-10-25）

本轮用户新增的 **3 张桌面 Chrome 真实截图**分别显示 Reconcile Application Full Graph、其 Run Parent Facet 展开结果，以及另一个数据集的 Column Level 血缘图。原始图片包含局域网地址，**不上传 GitHub**。三个画面的身份与适用范围必须分开审查：

1. **P5 Reconcile Application Full Graph：**目标仍为 `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7`（namespace `healthcare-platform-spark-business`）。截图中 `Full Graph` 开关已明确开启（绿色），`Compact Nodes` 仍关，`Depth=2`、`Table Level`；画布**仍仅一个 JOB 节点**，无可见 Dataset edges。此结果表明简单开启 Full Graph 没有解决 Application 顶层节点的图形呈现缺口；它不推翻独立 Marquez API 的真实 Spark Action / DatasetVersion 数据。
2. **P5 真实父子关联可视化：**Reconcile Application 的 `RUN FACETS → parent → job` 已展开，显示 namespace 为 **`healthcare-platform-airflow`**，`name` 前缀 `new_only_omop_consumer.spark_r...`；`parent → run → runId` 已展开，页面可见前缀 `01a173bb-987a-7b3b-a0ec-e1ce42...`。该前缀与早前 [独立 ParentRun GET #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 所确认的 Reconcile Airflow Run UUID `01a173bb-987a-7b3b-a0ec-e1ce422e01ed` **一致**。**完整名称/UUID 在截图中被 UI 省略号截断**；GUI 级通过“可见 Parent namespace / 前缀与 API 完整 ID 对齐”，不宣称完整 UUID 在屏幕完全展示或 RUN HISTORY 曾被点击。
3. **真实历史 Column Lineage 图：**用户在官方 Datasets 页面进入 `Mode=Column Level`，可看到左、右两组 Dataset 字段及逐列连线，包括 `STOP → end_datetime`、`PATIENT → source_person_id`、`PROVIDER → source_provider_id`、`START → start_datetime`、`Id → source_encounter_id`、`PAYER_COVERAGE → payer_coverage`，以及其余可见字段映射。目标页面显示 `Namespace=s3://health-processing`，Dataset 名包含 **`ingest_date=2026-10-21/batch_id=synthea-new-only-gh-39625216978/entity=encounter`**。这是**历史的不同 Batch**，不能因此宣称最新 P5 Batch `synthea-new-only-gh-40208104106` 在 GUI 中已有同样的 Column Lineage。截屏中输入端完整 Dataset namespace/name 未全部露出，也不能将输入端猜作 `s3://health-landing`。
4. **P6 后续验收结论：**官方 Column Level 血缘图形渲染能力 **PASS（历史独立 Batch）**；目标 P5 Reconcile 的 Airflow Parent Facet GUI 显示 **PASS_WITH_TRUNCATED_IDS**；P5 的**精确批次** Dataset 输入输出 GUI 仍 **OPEN**。不因为 GUI 图形可视化能力通过就伪造 `business_dataset_gate=PASS`，原物理 RDD `START_ONLY_OBSERVED` 已知限制不变。
5. **最短剩余步骤：**在 Datasets 页选择 `s3://health-processing`，只打开 Dataset 名包含 `ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106` 的 `entity=person` 或 `entity=encounter` Processing 输出，查看其 Column/Table Level 的真实输入边；也可进入该 Batch 的实际 Spark Action Job，而不是 Application 顶层孤点。记录屏幕上可见的目标 Batch、Dataset namespace 和连线。若 GUI 无法显示目标 Batch 的边则记录事实，不虚构。
6. **安全：**截图中的浏览器连接标记/局域网主机等均不进入仓库，元数据页面也不包含已授权的新写入动作；不触发 Spark/Airflow/Writer、PG 或任意事件补发，不点击 GUI 的 `DELETE`。

## P6 7.1 目标 Batch 浏览器可视化正式验收：真实 Encounter + Patient（2026-10-25）

此节是用户最后提供的 **4 张桌面 Chrome 内网官方 Marquez Web 截图**的视觉审查，按截图页面显示的完整 DataSet 名称与既有 P5 Manifest/Run 身份核对。原始带私网主机地址的图片**仅保留在会话中，不上传 GitHub**；原 P5 无需也未重新运行。当前 Docs-only 源码基线为 Healthcare Main `e9feb459c8f2f75b4d3bba68b1f917aadfa68ef0`，业务事件本身仍绑定当时的 Healthcare `95f480078da622178f4fa7b68d986d8e05a91ae9`。

| GUI 观察内容 | 确切独立 Batch 身份 / 对应事实 | 结果 |
| --- | --- | --- |
| **Encounter / Visit Processing Dataset** | 页面 Column Level 头部明确显示 `Namespace=s3://health-processing`、`ingest_date=2026-10-25`、`batch_id=synthea-new-only-gh-40208104106`、`entity=encounter`、`run_id=task004-encounter-20261025T154424Z-9`、`work/normalized/data` | **PASS：精确目标 Batch 的实体及运行身份** |
| Encounter Table Level | 同一命名空间的目标 Dataset 画布显示一个上游 Dataset，经过 `task004_encounter...` Spark Action Job 连接到输出 Dataset；图中有输入/作业/输出节点 | **PASS：真实 Table Level 数据流可视化** |
| Encounter Column Level | 在目标 `40208104106` 的 Column Level 截图中，字段间实际可见 `STOP→end_datetime`、`PATIENT→source_person_id`、`PROVIDER→source_provider_id`、`START→start_datetime`、`Id→source_encounter_id`、`PAYER_COVERAGE→payer_coverage` 等边 | **PASS：精确目标 Batch 的列级转换可视化** |
| **Patient / Person Processing Dataset** | 页面 Column Level 头部明确显示 `Namespace=s3://health-processing`、`ingest_date=2026-10-25`、`batch_id=synthea-new-only-gh-40208104106`、`entity=patient`、`run_id=task004-person-20261025T154424Z-9`、`work/normalized/data` | **PASS：精确目标 Batch 的实体及运行身份**；此处真实路径是 `entity=patient`，不是 `entity=person` |
| Patient Table Level | 同一目标 Dataset 显示上游 Dataset → `task004_person_...` Spark Action Job → Processing 输出 Dataset | **PASS：真实 Table Level 数据流可视化** |
| Patient Column Level | 目标 Batch 的两个 Dataset 列节点之间实际可见 `ETHNICITY→ethnicity_code`、`BIRTHDATE→birth_date`、`Id→source_record_id`、`DEATHDATE→death_date`、`GENDER→gender_code`、`RACE→race_code` | **PASS：精确目标 Batch 的列级映射可视化** |
| Reconcile Parent 与两份输入版本 | 浏览器之前已展示 Reconcile Application 的 `RUN FACETS.parent`、匹配 Airflow ParentRun 前缀；原 [独立 GET-only #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 和 [P6 API #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) **PASS** 精确证明 Reconcile 真实子 Spark Action 消费 Person/Encounter 上述两份 Processing DatasetVersion | **PASS：GUI 的两份真实输出 + 独立 GET 的版本关联**；未声称浏览器同一个画布上显示 Reconcile 双输入 |
| Writer PG17 durable COMMIT + 同批 SKIP | 原 [#40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) 原 Workflow **FAILURE** 但实际 Writer COMMIT；后续 [独立只读 #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 与 [同批 SKIP #40209818676](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676) 分别证明 PG17 +100 Person/+15,742 Visit 和幂等零变化 | **PASS：保留原有独立证据，不以截图代替 DB 提交** |

**方案 A 判定**：官方 Marquez 内网浏览器的首页、真实业务 Job、ParentRun Facet、**P5 同一新 Batch 的 Person 和 Encounter 两份 Dataset 的 Table/Column Level 连线**，与 GET-only 的精确 Reconcile 输入 DatasetVersion 已形成相互独立、可重复查询的演示证据。因此原 P6 **7.1 通过**，在 OpenSpec 勾选 `[x]`，原有 [演示 Runbook](../../../../../documents/systems/platform-portal/marquez/SHOWCASE-RUNBOOK.md) 按真实路径更新。**保留三个不同的边界**：(a) `Full Graph=ON` 的 Reconcile *Application* 顶层仍仅一个 Job 节点；(b) 物理 RDD `START_ONLY_OBSERVED`，原严格 `business_dataset_gate=INCOMPLETE` **绝不改成 PASS**；(c) 本次并未做 GUI 的完整 `RUN HISTORY` 浏览、公共网络可达性或 PG14 备份恢复演练。

**Archive 安全 Gate**：该 OpenSpec Change 在勾选 P6 7.1 之前仍有总计 11 个未勾选条目（包括 P2/P3 历史项、P6 7.1/7.3、8.x 及后续镜像/Listener 验收项）。本次仅凭屏幕+历史 API 证据关闭 **7.1**；其他项逐项核对并依据对应 PR/Run 关闭或拆分之前，**7.3 和整个 Change Archive 仍 OPEN**。本轮没有 K8s/Airflow/Spark/S3/PG 写入、镜像重建或 OpenLineage 人工 COMPLETE。

## 后续归档前检查 / 历史遗留 GUI 步骤（以下旧说明已由上节最终结果覆盖）

P6 7.1 的剩余浏览器级验收路径：Reconcile Application 的 `parent.job.namespace` 及 `parent.run.runId` 前缀已展示且与独立 GET 证据吻合；Full Graph=ON 仍为孤点。历史 Batch 的 Column Level 图已展示。**请在 Datasets 页面改选 P5 指定 Batch `synthea-new-only-gh-40208104106`（`ingest_date=2026-10-25`）而非历史 `39625216978`，核对至少一个真实 Processing Dataset 的输入/输出连线并截图。** 理想情况还要在相同 Batch 上看到 Person + Visit 两个 Processing Dataset 对 Reconcile 的输入关联。**如果 GUI 未显示该图**，如实记录 GUI 局限而不能拿 API PASS 冒充屏幕实际呈现。

在得到上述浏览器视觉证据前，OpenSpec `7.1` **不得勾选**、`7.3` **不得归档**。这不影响早已通过的 P5 事务与 API 血缘验收。
