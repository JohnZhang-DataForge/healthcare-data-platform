---
status: active
scope: platform-portal-system
last_verified: 2026-10-25
source_sha: 95f480078da622178f4fa7b68d986d8e05a91ae9
---

# Platform Portal — OpenLineage / Marquez / Portal 可观测性系统

> **2026-10-27 目录归属更新**：面向公网的 UI 属于现有 Platform Portal 的 [`portal/`](../../../platform-portal/portal/) 子组件（[README](portal/README.md) · [CODE](portal/CODE.md)），并非新建第四个顶级系统。仅 P0 Contract/Mock/CI 已实现，Web/Exporter/Worker/Infra 尚未部署；既有 Marquez 和 PG14 不变。下文历史“独立项目”仅指独立变更、安全、验收 Gate。


> **本地 Portal P1–P6 MVP 归档收尾（2026-10-25）**：原有 LAN-only 官方 Marquez Web、NEW_ONLY Airflow→Spark→真实 S3 DatasetVersion、Patient/Encounter Table/Column Level UI、Writer PG17 真 COMMIT 及同批 SKIP 已按 Design A 验收，完整原始 Evidence 随独立 Archive PR 存放 [Portal OpenSpec Archive](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/tasks.md)。旧 A4 `unknown` 唯一事件原因**未证实、独立延期**，P4 物理 RDD START-only 与 `business_dataset_gate=INCOMPLETE` **保留**；不伪造 COMPLETE、不改写原失败 Run。公网匿名只读及 Azure/Fabric/FHIR/HL7 综合展示将在**独立项目**实施，现有 Web NodePort 30999 **不可直接公开**。参见 [长期遗留与独立项目边界](../../architecture/design/LOCAL-PORTAL-MVP-CLOSEOUT-AND-DEFERRED-FOLLOWUPS.md)。归档正式生效以 Archive PR CI/Main Merge 为准。



> **本地 P1–P6 阶段 Closeout 决议（2026-10-25；优先于下方各历史时间点快照）**：用户批准按原已验收 **Design A** 正式结束 LAN-only Portal 阶段。精确 P5 Batch 的 Person/Encounter Table/Column 可视化、真实业务 Parent/DatasetVersion、PG17 durable COMMIT 与同批 SKIP 均保留独立验收；A4 旧 `unknown` 唯一事件级归因**未证实但暂缓、移出此 MVP 前置要求**，P4 物理 RDD START-only / `business_dataset_gate=INCOMPLETE` **继续保留**，不可宣称修复。P6 7.3 **另经 Archive PR 方生效**。公网匿名只读 Portal、Azure/Fabric 统一血缘是**未来两个独立项目**，现有 Web-only NodePort 30999 不得直接暴露公网。统一 [Closeout 与遗留决议](../../architecture/design/LOCAL-PORTAL-MVP-CLOSEOUT-AND-DEFERRED-FOLLOWUPS.md)，下文较早 P6 未通过的段落是历史过程，不代表最新状态。


> **最新 P6 原生 GUI 验收（2026-10-25，覆盖下列旧版“目标批次 GUI 尚未通过”说明）**：用户 Chrome 官方 Marquez Web 截图明确展示同一 P5 Batch `synthea-new-only-gh-40208104106`（`ingest_date=2026-10-25`）的 **`entity=encounter` 与 `entity=patient`** 两份 `s3://health-processing` Dataset：Table Level 实际输入→Spark Action→输出 Job/Data edges，Column Level 字段映射连线分别可见 `PATIENT→source_person_id`、`STOP→end_datetime` 和 `ETHNICITY→ethnicity_code`、`Id→source_record_id`。Reconcile 精确消费这两个 DatasetVersion 的证据由独立 GET-only P5/P6 Run 完成；**P6 7.1 方案 A PASS，P6 7.2 已完成**。必须继续披露 Reconcile Application Full Graph 孤点、RDD Action START-only / 严格 `business_dataset_gate=INCOMPLETE`、Writer PG17 独立 durable Readback；这些不是新截图能消除的限制。**P6 7.3 Archive 仍 OPEN**，Change 的其他历史任务尚需核对。详见 [Marquez 内网演示指南](marquez/SHOWCASE-RUNBOOK.md) 与 [用户实际 GUI 证据文字审查](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。含内网地址的图片未上传 GitHub，未改运行环境。


> **2026-10-25 P6 新增 GUI 分层验收**：用户真实 Chrome 截图已证明 Reconcile Application `RUN FACETS.parent` 中的 Airflow Namespace 与父 Run ID 前缀吻合既有 API 验收，`Full Graph=ON` 时 Application 图仍仅一个 Job 节点。独立的**历史** Dataset `synthea-new-only-gh-39625216978`（2026-10-21）在 Marquez `Column Level` 页显示真实字段映射连线（如 `PATIENT → source_person_id`），**证明原生 UI 可以绘制列级 Lineage**。但 P5 验收批 `synthea-new-only-gh-40208104106` 的 Dataset 图仍未在浏览器证实，P6 7.1 / 7.3 继续 OPEN。原含内网地址截图不上传 GitHub，仅保存 [文字审查](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)；不涉及新业务运行。

> **2026-10-25 P6 桌面 Chrome Reconcile Job/Run Facets 可视化补证**：在真实官方 Marquez Lineage 页已打开 `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t154718z_7` 的 Job 和最新 Run Facets；显示 `COMPLETED`、`jobType=APPLICATION`、`parent` 字段、Spark 3.5.7/OpenLineage 1.47.1。当前 Application 画布只有孤立的 `JOB` 节点；物理 Action 的真实 Dataset 边仍未在 UI 证明，故 **P6 7.1 及 Archive 7.3 保持 OPEN**。见 [浏览器截图文字审查](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。

> **2026-10-25 P6 真正 LAN 浏览器首页/Job 列表截图补证（更新下方早先“未验证浏览器”结论）**：用户三张 iPhone Safari 截图确证官方 Marquez DataOps UI 及真实 Airflow DAG/Writer/Reconcile、Spark Reconcile Application 的绿色 `COMPLETED` Job Card 正常渲染；截图当时概览显示 139 Events、23 Datasets、4 Sources、71 Jobs。**未查看单 Job 的 Run 详情或 Person/Visit→Reconcile Dataset Lineage 图，7.1 整项保持 OPEN；7.3 Archive 保持 OPEN**。详情 [P6 浏览器截图审查（保护私网地址）](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。

> **2026-10-25 P6 官方 Marquez Web 内网 HTTP/GET 实机验证 PASS（浏览器视觉尚未验收）**：[Self-Runner #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) 校验 K8s Marquez+PG14 资源 **10/10 PASS**；Web 首页 HTML 200、healthcheck OK、官方 Web Proxy 与直接 API 的 7 个 Namespace 完全一致。固定真实 P5 Batch 的 Airflow→Spark Person/Visit/Reconcile 真实 ParentRun 与 DatasetVersion `business_edges_gate=PASS`，Writer Airflow Run `COMPLETED`，物理 RDD Action `RUNNING` 已知限制继续暴露。**LAN 浏览器的可视化点击/截图不在本次 HTTP probe 覆盖范围，因此 OpenSpec P6 7.1 GUI Gate 仍 OPEN**；不会将 API PASS 误报为已完成 GUI 演示，也不会将 Writer Run 状态误报为独立 PG17 COMMIT。详见 [官方 Marquez Web 演示与只读查询指南](marquez/SHOWCASE-RUNBOOK.md)，历史 P5 durable 证据仍单独有效。**P6 7.3 Archive 尚未批准**。



> **2026-10-25 P5 实机方案 A 验收（覆盖下方较早 P4/P2 Pending 描述）**：全新 `synthea-new-only-gh-40208104106` Batch 的 Landing READY→Airflow→三 Spark Application→Writer **真实原子 COMMIT**，PG17 独立读回 **+100 Person/+15,742 Visit**，Ledger/2 VERIFIED Checkpoint/FK 与无活动 Claim 全部通过；[原 Run #40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) **仍为 FAILURE**（COMMIT 后测试采集缺 `spark-apps.jsonl`，原始证据不改写）。单独 [Marquez GET #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) 核对真实 Airflow ParentRun、Person/Visit 真实 Input/Output DatasetVersion、Reconcile 精确复用两个 Processing 版本、Writer Airflow Run 与 PG17 durable COMMIT，`business_edges_gate=PASS`；单独 [同 Batch SKIP #40209818676](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676) 证实 Spark/Writer 全 skipped、PG17 前后八份指纹零变化。P4 5.4 与 P5 6.1–6.4 按**跨三条独立真实 Run 的分层方案 A** 验收，而非原 Workflow 全绿。**RDD 物理 Action START-only / RUNNING 仍是已知观测限制，原严格 `business_dataset_gate=INCOMPLETE` 不改写**；PG17 无已证明的 OpenLineage durable Dataset edge，Writer 可信状态以 PG17 Ledger/Checkpoint/CDM 真读回为准。完整 [P5 验收/失败证据](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P5-FRESH-BATCH-EXECUTION-20261025.md)。**下一步 P6：官方 Marquez Web 演示、README/CODE/最终状态与归档评审**，不开发自建 UI。


> **2026-10-24 实际业务更新（覆盖下方较早 P4 镜像阶段 / P2 仅 Probe 阶段结论）**：[NEW_ONLY Spark-only DagRun #40125211881](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125211881) 的真实 Airflow DagRun **success**，Person / Visit / Reconcile 三业务成功，三个 Pod 的 imageID 均为发布的新 Digest。Marquez [真实 Airflow DAG+Task #40126168286](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40126168286) 证实 **10 个完成的业务 Job/Run**；Spark [子 Job 数据集 #40125843864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125843864) 证实 Person/Visit 各 **1 真实 S3 Input + 1 Output**。Reconcile 的两个输入已真实观测，但两个 Action 子 Run 仍为 RUNNING（[独立读回 #40125995864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125995864)），**P4 未全通过**。原 Workflow 在错误地只查顶层 Spark Job Dataset 时失败，维持失败记录。Writer 按门槛跳过；**没有 COMMIT/PG17 E2E/SKIP**。完整 [当前真实业务验收 Evidence](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P4-REAL-NEWONLY-PERSON-VISIT-RECONCILE-20261024.md)。


> **2026-10-24 P4 源码+镜像发布 PASS（业务 E2E OPEN）**：NEW_ONLY 三个实际 SparkApplication 模板已在 [Healthcare PR #441](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/441) 合并；仅 `landing-processing-v2:latest` 更新为 `sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`，[GHCR #40123946926](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40123946926) Build/Smoke/Registry Readback 成功。**实际 NEW_ONLY Person/Visit/Reconcile、Writer/PG17/同批 SKIP 尚未跑通**，不宣称端到端业务血缘通过。 [镜像证据](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P4-BUSINESS-IMAGE-LATEST-RELEASE-20261024.md)。


> **2026-10-24 更新的 P2/P3 Live 结果（覆盖旧静态状态）**：Airflow 当前 Scheduler OpenLineage Provider/Transport 与 NEW_ONLY GitSync DAG SHA256 [Run #40120678131](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120678131) PASS；两任务真实 Airflow Probe 的 DAG/Task Jobs 在 Marquez [Run #40121352170](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121352170) PASS。隔离 Spark 在 PVC 上真实 Parquet 写出及读回、Marquez 非 unknown Job 下真实 Run、1 Input + 1 Output DatasetVersion [Run #40120840326](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120840326) PASS。**尚未**核对真实 NEW_ONLY 业务 DagRun 或 Person/Visit/Reconcile S3 Dataset/Writer/PG17 E2E。详见 [P2/P3 实机 evidence](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P2-P3-ISOLATED-LIVE-VERIFICATION-20261024.md)。下文 P1 历史数据为空是该次只读检查时点，不是今天后来生成的新事件依然为空。

> **2026-10-24 P1 真实只读验收（新于下方历史验收）**：Marquez API/Web、Web proxy、PG14 数据库、Kubernetes Deployment/Service/Endpoint/PVC **当前健康检查 PASS**；PG14 `marquez` 保留 37 张 Metadata 表。**关键异常**：三个 Namespace 均无 Jobs；PG14 独立精确查询 `namespaces=3, jobs=0, runs=0, lineage_events=0`，历史 A3/A4 事件**当前不存在**。详见 [本次 P1 Evidence](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P1-READONLY-VERIFICATION-20261024.md) 和 [Self-Runner #40093060512](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40093060512)。**基础服务健康不等于真实业务 Lineage 验收**，且此次无写操作、未恢复历史事件；P2/P3 尚未开始。

> **本系统唯一 README 总入口。** Portal 是**旁路数据血缘/运行观测系统**，不是业务 ETL、OMOP 数据库 Writer 或自研前端；实际展示界面是 Marquez 官方 Web。组件代码定位见 [CODE.md](CODE.md)；全项目 CURRENT/NEXT 以 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md) 为准。以下运行结论来自 **2026-10-13/14 历史验收**，不是本次部署或当前在线探针。

## 系统结构与数据边界

```text
Airflow OpenLineage Provider → (A3 真实事件通过) ─┐
                                                     ├→ Marquez API → PostgreSQL 14 元数据
Spark OpenLineage Listener → (A4 隔离 Smoke 部分通过)┘                ↓
                                                           Marquez 官方 Web

真实 Person/Visit 业务 DAG → Spark → OMOP 的 Job/Run/Dataset 全链路：尚未验收
```

Marquez 使用 `dw-marquez` 的 API/Web 与独立 `dw-postgre14` PostgreSQL14 元数据库；**不得触碰** `dw-postgre` PostgreSQL17 的 OMOP 数据。初期 Web 通过 `marquez-web-lan` 的 NodePort **30999** 在受控网络内验证；Web 可以代理 API，**并非匿名只读公网服务**。LAN/VPN/NAT/浏览器外部可达性、备份恢复和持续健康均不能仅凭旧验收得出结论。当前没有自建 Portal UI，也没有交付 Superset、OpenMetadata、Kafka。

## 组件总导航

| 组件 | 说明与源码导航 | 真实源码/配置 | 职责及限制 |
| --- | --- | --- | --- |
| **Marquez** | [README](marquez/README.md) · [CODE](marquez/CODE.md) | [`marquez/`](../../../platform-portal/marquez/) | Helm 配置、API/Web、受控恢复、验证；没有独立自研 UI |
| **PostgreSQL14** | [README](postgres/README.md) · [CODE](postgres/CODE.md) | [`postgres/`](../../../platform-portal/postgres/) | 独立 Marquez metadata 持久化；Git YAML 是历史已部署快照，不是重装指令 |
| **Airflow OpenLineage** | [README](airflow/README.md) · [CODE](airflow/CODE.md) | [`openlineage/airflow/`](../../../platform-portal/openlineage/airflow/) · [Probe DAG](../../../local-data-platform/airflow/dags/platform_portal_openlineage_probe.py) | A3 opt-in Provider 真正的 Task/Run 事件验证；不等于业务全 DAG |
| **Spark OpenLineage** | [README](spark/README.md) · [CODE](spark/CODE.md) | [`openlineage/spark/`](../../../platform-portal/openlineage/spark/) | A4 隔离真实 Smoke 有部分完成的证据；完整 Job↔Run / Dataset I/O **未通过** |

## 已验证结果、保留的失败事实

| 领域 | 有界的历史验收 | 不可扩大解释 |
| --- | --- | --- |
| Marquez / PG14 / Web | API/Web Ready、独立 PG14 **37 张元数据表**、NodePort 30999、HTTP health/API proxy 读回 | 不是今天的网络连通性/集群健康证明 |
| A3 Airflow | opt-in Probe DAG、两项 TaskInstance success、真实 Marquez Job/Run 读回；OpenLineage Provider 2.17.0 | 不证明生产所有业务 DAG、Person/Visit Dataset |
| A4 Spark | 隔离 SparkApplication COMPLETED、3 行 CSV 聚合、Marquez 中含 Spark facets 的 COMPLETED Run | 原 Live Workflow **FAILURE**；后续只读核验验证局部成果，完整映射/输入输出 Dataset 仍失败 |

**A4 的已知阻断事实**：应用 Job `portal_a4_a438628542127` 的 `latestRun` 为空，完成 Run 被挂在 `unknown` Job；`inputDatasetVersions=0`、`outputDatasetVersions=0`。不能宣称根因已解决或完整业务血缘成功，更不能将原失败工作流结果改写为成功。

**固定历史证据**：[Marquez 部署、服务及 30999 验证](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) · [恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493) · [A3 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) · [A3 只读 Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) · [A4 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) · [A4 原失败 Run 38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) · [A4 后续只读 Run 38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225)。

## 下一阶段：仅设计讨论，不代表部署授权

真实业务 Spark OpenLineage 接入方式尚未确定。需要先对现有 Job/Run facets 做只读溯源，调查 `unknown` 命名与关联；随后设计有边界的 Dataset I/O 验证，评估对 Person/Visit 实际 Spark、JAR、镜像、Operator 与 Airflow 的影响，保证不回归已验收的 Writer/Claim/Fence。**不要伪造 lineage event、无授权触发 SparkApplication、重跑冻结批次或改共享 Scheduler。**

本次迁移**只移动经核对的知识、整理源码索引**；`platform-portal/` 下运行相关文件未更改。需要触碰 Kubernetes、PostgreSQL、Airflow、Spark、网络或 Secrets 时，先遵循 [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) 和 [Session Coordination](../../engineering/development/SESSION-COORDINATION.md)，不能从本文件推断执行许可。

**继续阅读**：[系统 CODE](CODE.md) · [Marquez](marquez/README.md) · [Postgres14](postgres/README.md) · [Airflow](airflow/README.md) · [Spark](spark/README.md) · [总体架构](../../architecture/SYSTEM-OVERVIEW.md)。
