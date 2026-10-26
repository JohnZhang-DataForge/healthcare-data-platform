---
status: reviewed
scope: platform-portal-marquez-p6-lan-showcase
last_verified: 2026-10-25
source_sha: b92ccc9b7976e740d9dd77994a0725b115693705
evidence:
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676
---

# P6 — Marquez 官方 Web / OpenLineage 内网演示指引

> **最终 GUI 接受范围（2026-10-25，覆盖下文更早的“未验证目标 Batch”历史描述）：P6 7.1 已按照方案 A PASS。** 用户真实 Chrome 内网浏览器已打开 P5 新批次 `synthea-new-only-gh-40208104106` 的 **Encounter（`entity=encounter`）和 Patient（`entity=patient`）** 两份 `s3://health-processing` 输出 Dataset，路径均包含 `ingest_date=2026-10-25`，并在 Table Level 看见输入 Dataset → 真实 Spark Action → 输出 Dataset，在 Column Level 看见真实字段映射。Reconcile 的两份输入 DatasetVersion 由独立 API [#40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 精确匹配；Writer PG17 durable COMMIT/同批 SKIP 以历史独立 SQL 读回证明。**Reconcile Application Full Graph ON 仍为孤立 Job，物理 RDD START-only 与严格 `business_dataset_gate=INCOMPLETE` 未改变。** 实际 UI 未同屏展示 Reconcile 的双输入连线，不能因此声称有完整同屏 Workflow 图。用户图像带局域网地址，未上传仓库；详见 [P6 GUI 文字验收记录](../../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。P6 7.3 Archive 仍 OPEN，先复核整个 OpenSpec Change 未完成任务。



> **验收边界**：2026-10-25 17:54 UTC 的独立受控 [GET-only Run #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) **SUCCESS**；[Artifact #12609050399](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308/artifacts/12609050399) 保存 4 份不含患者记录的原始报告。已验证 Marquez Web 首页 HTML 200、`/healthcheck=OK`、Web Proxy API 200/直接 API 一致、K8s 10/10 Ready/Bound/Endpoint、真实业务 DatasetVersion 与 ParentRun。**用户后续于 2026-10-25 提供三张 iPhone Safari 的真实 LAN 页面截图，证明官方 Dashboard/Job 列表已在实际手机浏览器中正常呈现**（见 [视觉补证](../../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)）。**用户随后提交的桌面 Chrome 截图已打开 Reconcile Spark Application 的 Job / LATEST RUN Facets 面板**，看到 `COMPLETED`、`jobType=APPLICATION`、`parent` Facet 存在与 Spark/OpenLineage 3.5.7/1.47.1。但该 Application 的表级 Lineage 画布只有一个 Job 节点，`parent.job`/`parent.run` 仍折叠，未可视化真实 Dataset 边；详见 [现有补证记录](../../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。因此 OpenSpec P6 7.1 完整浏览器演示 Gate 仍 OPEN；不能把 HTML 200、页面 Job Card 或 API GET 误称为已完成真实血缘图交互验收。

## 1. 网络与安全

- **仅 LAN/VPN 内访问**：在能路由至此 K8s 节点的受控网络浏览器中打开 `http://<K8s-node-private-IP>:30999`。具体私网节点 IP 必须由内网管理员从实际环境获得；此文档**不凭 DNS 猜测地址**。
- `dw-marquez/marquez-web-lan` 是**仅官方 Web** 的 NodePort 30999；`dw-marquez/marquez` 与 `dw-marquez/marquez-web` 仍是 ClusterIP。NodePort 不保证主机防火墙、路由、用户浏览器或认证已满足公网安全要求；**禁止**未经评审将 30999 直接映射到公网或宣称匿名只读。
- 仅用于展示已有 metadata。不执行 `deploy.sh`、`recover-web.sh`、`kubectl apply`、`helm upgrade`、`airflow dags trigger`、Spark/Writer、OpenLineage event POST 或 PostgreSQL 写入。不会生成、重放或修改 Synthea Batch。
- 不能以 Marquez 的运行状态替代 `dw-postgre` PG17 OMOP 的真实 COMMIT；Marquez 的 Metadata 存于**独立** `dw-postgre14`。

## 2. 固定真实演示用例（不要运行新 Batch）

| 字段 | 固定真实身份 |
| --- | --- |
| Batch | `synthea-new-only-gh-40208104106` |
| S3 Manifest SHA256 | `cad0a79c1f536e5d3fed0e732c2b2da4cc7af48c89355c6fa95f0b380042130e` |
| Healthcare 业务源码 SHA | `95f480078da622178f4fa7b68d986d8e05a91ae9` |
| Airflow DagRun | `portal-p5-commit-40208104106` |
| Airflow namespace | `healthcare-platform-airflow` |
| Spark namespace | `healthcare-platform-spark-business` |
| Person Spark Application | `new_only_omop_consumer.spark_patient.task004_person_20261025t154424z_9` |
| Visit Spark Application | `new_only_omop_consumer.spark_encounter.task004_encounter_20261025t154424z_9` |
| Reconcile Spark Application | `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7` |
| Writer Airflow Job | `new_only_omop_consumer.execute_new_only_writer` |
| Writer OpenLineage Run UUID | `01a173bb-987a-7916-b46d-e562e9e036a9` |

**更新的真实 GUI 结果（用户后续 Chrome 三图）**：`Full Graph` **已切到 ON**、`Depth=2` 时，P5 Reconcile Application 依旧只有单个 `JOB` 节点，**不是数据处理失败证据**。其 `LATEST RUN → RUN FACETS → parent → job/run` 已展开，屏幕可见 `healthcare-platform-airflow` 与精确 ParentRun UUID 的一致前缀 `01a173bb-987a-7b3b-a0ec-e1ce42...`（UI 省略号截断）。用户也展示了官方 Datasets **Column Level** 的真实字段映射连线，如 `PATIENT → source_person_id` 和 `STOP → end_datetime`，但**该图属于旧 Batch `synthea-new-only-gh-39625216978`（`ingest_date=2026-10-21`）**，不是 P5 新批次 `40208104106`。因此已验证官方 Column Lineage GUI 能画线，**P5 精确 Batch 的 Dataset GUI 连线仍待验收**。文字记录见 [浏览器证据](../../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。**请勿点击 `DELETE`。**

以上 Spark Application 全名用于查 **Application 自身**的真实 `COMPLETED` 和 Airflow `ParentRunFacet`；底层 Spark Action Job 可能不是这个完全限定名字，而是 `task004_person_...<action>` 等。**业务读写 DatasetVersion 位于真实的子 Action Job**；不能仅凭 Application 的 Dataset 列表为空就否认已有读写血缘。

## 3. GUI 演示顺序（首页、Job 列表及 Reconcile 最新 Run Facets 已实测；底层 Dataset 图仍待核对）

1. 在 LAN 浏览器打开官方 Web 首页，确认能进入 **Jobs / Datasets / Lineage** 导航；搜索栏先查 `new_only_omop_consumer`。如无法访问，先确认节点私网可路由及网络策略；不要修改 NodePort/Ingress 或导出 PG 密码排障。
2. 选择 Namespace `healthcare-platform-airflow`；依次查询 `new_only_omop_consumer.spark_patient`、`spark_encounter`、`spark_reconcile`、`execute_new_only_writer`，在 **Job / RUN HISTORY** 面板核对实际任务 Run。对 Writer 的真实 Run ID 核对上述 UUID（Marquez 返回 `COMPLETED`）。
3. 切换 Namespace `healthcare-platform-spark-business`，搜索上表 Person、Visit、Reconcile 的完整限定 Application Job 名。确认这三个真实 Application `COMPLETED`，ParentRun 对应同一次 Airflow DagRun 内对应任务 Run UUID。
4. 搜索 Spark 内的 Person/Visit **Action** Job 名（以 `task004_person_20261025t154424z_9` / `task004_encounter_20261025t154424z_9` 为前缀）。在其 Job/Lineage/Dataset 视图验证真实 `s3://health-landing` CSV 输入与 `s3://health-processing` Parquet 输出，不要误将 Spark Application 空 `outputDatasetVersions` 理解为全链路没有写入。
5. 在 Reconcile 对应 Action Job 查看两个输入 DatasetVersion，要求精确匹配上一步 Person、Visit 所产生的 Processing DatasetVersion（不仅是相似的路径或同 Batch 标签）。
6. 回到 Writer `new_only_omop_consumer.execute_new_only_writer`：区分 Marquez 的 Airflow Run `COMPLETED` 与 PG17 的持久 COMMIT。实际 PG17 新增 **100 Person / 15,742 Visit**、Ledger/Checkpoint/Readback 的不可替代证据来自 [P5 原始失败但已 COMMIT #40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) 和 [独立只读 #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539)，随后 [同 Batch SKIP #40209818676](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676) 实际证明 PG17 零变化。
7. 观察部分物理 `map_partitions_parallel_collection` Action 仍为 `RUNNING`，尽管业务 Application `COMPLETED`；这是 [方案 A ADR](../../../architecture/design/OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md) 中的已知 OpenLineage 观测缺口，**不是**有权手工 POST `COMPLETE` 的理由。

> 官方操作参考：[Marquez Quickstart：UI 搜索 Job、RUN HISTORY 与 Dataset 详情](https://marquezproject.ai/docs/quickstart/)；[OpenLineage Getting Started：业务血缘图与数据集](https://openlineage.io/getting-started/)。不同 Marquez 版本的菜单名称可能略有不同；上述点击过程需要在**本集群实际 Web** 人工确认，不能用官方教程截图充当本环境截图。

## 4. 有界只读 API 复核（仅可信内网终端）

以下为只发送 `GET` 的复制查询示例。请在可解析 `*.svc.cluster.local` 的已授权**集群内**终端执行（不是一般家用电脑终端）；不需创建 Pod、port-forward 或向集群写对象：

```bash
API='http://marquez.dw-marquez.svc.cluster.local/api/v1'
WEB='http://marquez-web.dw-marquez.svc.cluster.local'

curl --max-time 10 -fsS "$WEB/healthcheck"
curl --max-time 10 -fsS "$API/namespaces"
curl --max-time 10 -fsS "$WEB/api/v1/namespaces"
curl --max-time 10 -fsS "$API/namespaces/healthcare-platform-airflow/jobs/new_only_omop_consumer.execute_new_only_writer/runs?limit=20"
curl --max-time 10 -fsS "$API/jobs/runs/01a173bb-987a-7916-b46d-e562e9e036a9"
curl --max-time 10 -fsS "$API/namespaces/healthcare-platform-spark-business/jobs/new_only_omop_consumer.spark_patient.task004_person_20261025t154424z_9/runs?limit=20"
```

API 响应原文可能包含字段元数据；对外展示前检查内容，**不上传患者级记录、Secret、凭证、私有节点 IP 或不需要的源 ID**。对严格 DatasetVersion/ParentRun 映射，应优先引用当前 `platform-portal/marquez/tests/verify_business_lineage.py` 和上述原始 P6 Artifact，而不是截取一个没有 Run UUID 的孤立网页。

## 5. 真实 P5 批次 Table / Column Level GUI 演示（2026-10-25 已现场通过）

> 业务固定批次：`synthea-new-only-gh-40208104106`，源业务 SHA `95f480078da622178f4fa7b68d986d8e05a91ae9`。不同于此前曾展示的 `2026-10-21 / 39625216978` 历史数据。

| Processing Output | 真实截图可见固定路径段 | GUI 连接 / 映射 |
| --- | --- | --- |
| Encounter | `s3://health-processing`、`ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106/entity=encounter/run_id=task004-encounter-20261025T154424Z-9/work/normalized/data` | Table Level 上游 Dataset→`task004_encounter` Spark Action→输出；Column Level `STOP→end_datetime`、`PATIENT→source_person_id`、`PROVIDER→source_provider_id` 等 |
| Patient | `s3://health-processing`、`ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106/entity=patient/run_id=task004-person-20261025T154424Z-9/work/normalized/data` | Table Level 上游 Dataset→`task004_person` Spark Action→输出；Column Level `ETHNICITY→ethnicity_code`、`BIRTHDATE→birth_date`、`Id→source_record_id`、`GENDER→gender_code`、`RACE→race_code` 等 |

- **Reconcile 在 GUI 看法**：顶层 `APPLICATION` 的 Full Graph 单 Job 并非后台无血缘；业务真实输入在底层 Spark Action 和两个 Processing DatasetVersion。独立 GET 已核实消费相同两份版本。若演示观众希望看到全局图，可分别展示两份 Table/Column 数据流与真实 Parent/Run，**不许拼接伪造一个官方未渲染的同屏大图**。
- **数据实体命名**：Person Stage 在 Processing S3 路径中实际是 `entity=patient`，Visit 是 `entity=encounter`，不要用 `entity=person/visit` 过滤漏掉它们。
- **遗留观察**：物理 RDD Action 显示 START-only 的情形按方案 A 保留独立说明；本次只审查真实已有 Dataset 元数据，不触发新的 Spark/Writer，也不包含公网或备份验收。

## 6. 机器独立验收及历史 GUI 补证矩阵（以下旧行保留当时快照）

| Gate | 本次现场证据 |
| --- | --- |
| K8s namespace/deployment/service/endpoint/PG14 Pod+PVC | `k8s-inventory.json` **10/10 PASS** |
| 官方 Web 首页 HTML、`/healthcheck`、Web Proxy API | `web-http-api.json` **PASS**；HTTP 200、OK、直接 API / Proxy 相同 7 namespaces |
| Person/Visit→Reconcile Data edges + Parent | `business-lineage.json`：`business_edges_gate=PASS`、`p4_design_a_gate=PASS_WITH_KNOWN_RDD_LIMITATION` |
| Writer Marquez Run | `writer-run.json`：指定真实 UUID `COMPLETED` |
| PG17 真 COMMIT 与同批 SKIP | **引用先前独立 P5 Run**；P6 本身未访问 PG17 |
| 物理 RDD Action | `START_ONLY_OBSERVED`、原严格 `business_dataset_gate=INCOMPLETE`，未伪造终态 |
| 用户 LAN 浏览器首页及业务 Job 列表 | **PASS（用户 Safari 截图）**；官方 Dashboard，Airflow DAG/Writer/Reconcile Spark Application 的 COMPLETED Job Cards，139 events / 23 datasets / 4 sources / 71 jobs 的截图时点统计 | 
| Reconcile Application 的 Job/LATEST RUN Facets | **PASS（用户桌面 Chrome 截图）**；真实 Job 状态 COMPLETED、LATEST RUN 面板、parent Run Facet 存在，Spark 3.5.7 / OpenLineage Adapter 1.47.1 | 
| P5 Reconcile Parent 视觉匹配 / Run History | **PARTIAL PASS**：Airflow Namespace、Run UUID 可见前缀匹配 #40209504539；完整 UUID 被屏幕省略号截断，RUN HISTORY 仍未检查 | 
| 官方 Column Level 实际字段连线（另一历史 Batch） | **PASS**：历史 `synthea-new-only-gh-39625216978` / `ingest_date=2026-10-21` Dataset 可见 Column lineage；不是 P5 新批次 | 
| P5 指定 Batch 的 Dataset Lineage 视觉连接 | **OPEN**：`40208104106` 的 Reconcile Application Full Graph ON 仍只有单 JOB；需查本批次实际 Processing Dataset / Spark Action | 
| 外网安全 / 公网可达性 | **NOT_CHECKED**；不据此开放 NodePort 30999 |
| 真实 Listener outage 故障注入 / PG14 备份恢复 | **NOT_CHECKED**；不属于 P6 本次 GET-only Run |

**验收与归档边界（最终）：**最终四张用户截图已经完成 P5 精确 `ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106` 的 **Encounter + Patient** Table/Column Level 真实 Lineage 可视化；结合先前独立 Reconcile DatasetVersion GET，**P6 7.1 方案 A 可验收**。但 Reconcile Application 孤点 / 物理 RDD START-only 依旧保留，未经证明的同屏双输入图不予声称。**7.3 Archive 未批准**：需先逐项处理整个 Change 的其他 OPEN Task、核对 Main/CI/Live Evidence，再单独 Review Archive PR。
