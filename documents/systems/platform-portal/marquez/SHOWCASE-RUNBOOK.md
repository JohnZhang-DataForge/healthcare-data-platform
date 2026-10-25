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

> **验收边界**：2026-10-25 17:54 UTC 的独立受控 [GET-only Run #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) **SUCCESS**；[Artifact #12609050399](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308/artifacts/12609050399) 保存 4 份不含患者记录的原始报告。已验证 Marquez Web 首页 HTML 200、`/healthcheck=OK`、Web Proxy API 200/直接 API 一致、K8s 10/10 Ready/Bound/Endpoint、真实业务 DatasetVersion 与 ParentRun。**用户后续于 2026-10-25 提供三张 iPhone Safari 的真实 LAN 页面截图，证明官方 Dashboard/Job 列表已在实际手机浏览器中正常呈现**（见 [视觉补证](../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)）。**但是尚未点击 Job 的 Run History 或展示 Dataset Lineage 图**，因此 OpenSpec P6 7.1 完整浏览器演示 Gate 仍 OPEN；不能把 HTML 200、页面 Job Card 或 API GET 误称为已完成真实血缘图交互验收。

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

以上 Spark Application 全名用于查 **Application 自身**的真实 `COMPLETED` 和 Airflow `ParentRunFacet`；底层 Spark Action Job 可能不是这个完全限定名字，而是 `task004_person_...<action>` 等。**业务读写 DatasetVersion 位于真实的子 Action Job**；不能仅凭 Application 的 Dataset 列表为空就否认已有读写血缘。

## 3. GUI 演示顺序（首页/Job 列表已真实执行；Run 详情和 Dataset 图仍待人工验证）

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

## 5. 已实际通过的验收与未验证项

| Gate | 本次现场证据 |
| --- | --- |
| K8s namespace/deployment/service/endpoint/PG14 Pod+PVC | `k8s-inventory.json` **10/10 PASS** |
| 官方 Web 首页 HTML、`/healthcheck`、Web Proxy API | `web-http-api.json` **PASS**；HTTP 200、OK、直接 API / Proxy 相同 7 namespaces |
| Person/Visit→Reconcile Data edges + Parent | `business-lineage.json`：`business_edges_gate=PASS`、`p4_design_a_gate=PASS_WITH_KNOWN_RDD_LIMITATION` |
| Writer Marquez Run | `writer-run.json`：指定真实 UUID `COMPLETED` |
| PG17 真 COMMIT 与同批 SKIP | **引用先前独立 P5 Run**；P6 本身未访问 PG17 |
| 物理 RDD Action | `START_ONLY_OBSERVED`、原严格 `business_dataset_gate=INCOMPLETE`，未伪造终态 |
| 用户 LAN 浏览器首页及业务 Job 列表 | **PASS（用户 Safari 截图）**；官方 Dashboard，Airflow DAG/Writer/Reconcile Spark Application 的 COMPLETED Job Cards，139 events / 23 datasets / 4 sources / 71 jobs 的截图时点统计 | 
| Job Run History / ParentRun 详情、Dataset/Lineage 图 | **NOT_CHECKED**；三张截图均未进入 Job 详情或数据集血缘可视化画布 | 
| 外网安全 / 公网可达性 | **NOT_CHECKED**；不据此开放 NodePort 30999 |
| 真实 Listener outage 故障注入 / PG14 备份恢复 | **NOT_CHECKED**；不属于 P6 本次 GET-only Run |

**终结标准**：实际打开官方 Web 和观察真实 Job Card 已在用户 Safari 截图中证明；P6 7.1 后续须进入 Job/Run、查看 Dataset/Lineage 图（并记录是否受 RDD 限制影响），仅由此才能勾选浏览器级验收。后续 P6 7.3 的 OpenSpec Archive 必须在实际 Main/CI/证据核对与治理规则满足后单独申请；**本文件及成功 Run 均不自动授权 Archive**。
