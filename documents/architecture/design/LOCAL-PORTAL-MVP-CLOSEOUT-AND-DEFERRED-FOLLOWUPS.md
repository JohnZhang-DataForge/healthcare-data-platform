---
status: reviewed
scope: local-platform-portal-mvp-p1-p6-closeout
last_verified: 2026-10-25
source_sha: 13c3a72e487e237ef899d71b48a9ea8e1046bf46
evidence:
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308
---

# 本地 Platform Portal P1–P6 MVP 关闭决议与独立遗留事项

> **归档操作当前状态**：用户批准的本地阶段 Closeout 范围裁定已通过 PR #505 并入 Main；独立 Archive PR 正将完整本地 Change 移入 [Archive](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/tasks.md)，同时同步 `openspec/specs/portal-business-lineage/spec.md` 与相关链接。归档实际生效以独立 PR 的 Required CI/最终 Main SHA 为准，不能由本文件的陈述提前推断合并。


> **2026-10-25 用户正式决定**：按已批准的 **OpenLineage Design A** 结束**本地 LAN-only** Portal/Marquez P1–P6 阶段；不为早期 A4 `unknown` 的历史唯一事件根因或 P4 `RDD START-only` 继续投入本阶段开发。这是**验收范围裁定**，不是“bug 已修复”、不是“全部物理 Run 已 COMPLETED”，也不是现在重新部署或运行的证明。
>
> **单独项目边界**：未来**公网匿名只读展示**与**Azure/Fabric/FHIR/HL7 跨平台血缘展示**将另立独立 OpenSpec Change/设计及各自运行、安全、身份与真实 E2E 门槛；**不属于此本地 Change 的归档条件，也不视为已开始实施**。

## 一、本地阶段已经验收的范围（复用原始证据；本 Closeout 不重跑）

| 本地能力 | 精确、独立验收事实 |
| --- | --- |
| Marquez 0.51.1 / PG14 API + 官方 Web 内网 | P1/P6 有界 GET-only [#40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308)：10/10 资源库存核验、HTML 200、`healthcheck=OK`、Web Proxy 与 API Namespace 对账；只能保证**该验收时点** |
| Airflow 单 DAG opt-in + 非 opt-in 有界负向 | NEW_ONLY 真实 DAG/Task OpenLineage [#40126168286](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40126168286)；一个无业务 `airflow_smoke_test` 的真实负向由 [#40247126516](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40247126516)/[#40247531737](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40247531737) SUCCESS 证实；原触发测试 #40247000949 因**后置轮询故障**仍为 FAILURE；并未实机运行所有其它 DAG |
| Spark Person/Visit/Reconcile、Parent 和真实 DatasetVersion | [#40197583583](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197583583) / [#40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539)：实际 Spark Application `COMPLETED` 与 Airflow Parent 对应；Person/Visit Processing DatasetVersion 与 Reconcile 的两份输入精确匹配。**物理 RDD START-only 仍然存在** |
| 原子 Writer E2E 与同批 SKIP | **P5 Batch `synthea-new-only-gh-40208104106`**：原 [#40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) Workflow **FAILURE**（Writer 实际 COMMIT 后辅助 `spark-apps.jsonl` 缺失），独立 PG17 读回 **+100 Person/+15,742 Visit** [#40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539) SUCCESS；同批 SKIP [#40209818676](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209818676) SUCCESS、PG 指纹零变化 |
| 官方 Marquez Web 真实 GUI | 用户内网 Chrome 精确打开 P5 `ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106` 的 `entity=patient`、`entity=encounter`，两份均显示 Table/Column Level 实际输入→Spark Action→输出 Dataset 及字段映射；Reconcile Application 顶层 Full Graph 仍单 Job，不夸称有跨两输入的原生同屏合并图。细节参见 [真实 GUI 验收](../../../openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md) 与 [Showcase Runbook](../../systems/platform-portal/marquez/SHOWCASE-RUNBOOK.md) |

## 二、Deferred：A4 `unknown` 历史事件唯一触发条件

- 历史旧 Probe 的 `unknown` Job 是**真实完成事件归属问题**；原 Workflow [#38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) FAILURE 与独立 [#38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225) 观测不得改写。现有 P3 正向 Probe 已运行通过，但未对历史旧事件做单变量因果证明。
- 上游 OpenLineage 1.47.1 的 `unknown` fallback 机制和旧 Probe 无持久 Output 已通过官方版本源代码确认；**旧事件到底哪次/为何取不到有效 SparkContext/job name，依然 UNVERIFIED**，旧 Marquez 精确记录现在 GET 404；详见 [A4 固定版本法证](OPENLINEAGE-SPARK-A4-UNKNOWN-JOB-FORENSICS.md)。
- **Scope disposition**：OpenSpec 4.1 的“必须唯一证明旧事件根因”被用户批准的本地 MVP Closeout **明确移出本阶段验收要求**。若 task 行勾选，意义仅为**遗留项已独立记录并经范围裁定**，绝不代表根因已证明或 bug 已修复。
- **Resume Trigger**：仅当实际受影响的新 Spark 业务再次出现 `unknown` 或用户另行批准以隔离 A/B 调查历史机制时，创建独立 OpenSpec Change，固定 Spark/Listener/输入，只改一项命名配置，收集真实事件 Payload/Driver DEBUG/ParentRun；不重放旧 Batch、不擅自发合成 COMPLETE。

## 三、Deferred：P4 物理 RDD Action `START_ONLY_OBSERVED`

- 原始真实 Person/Visit/Reconcile 的物理 `map_partitions_parallel_collection` Run 可能只有 START、在 Marquez 看似 RUNNING；**业务 Spark Application 实际 COMPLETED，数据版本边仍可查**。
- 已批准的方案 A 是**继续真实事件与版本边分层验收**；保留 `business_edges_gate=PASS` 与严格 `business_dataset_gate=INCOMPLETE` 两个**不同的**结果。不可把 `INCOMPLETE` 改成 PASS、手工 POST COMPLETE 或按应用级成功推断子 RDD 完成。
- 1.47.1/1.54.0 对照和上游有条件忽略无输出 RDD 终态事件的源码线索见 [RDD Action 方案 A](OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md)。没有原 Driver 对精确 RDD JobEnd 分支的事件级证据，不能宣布官方 bug 已最终证明/修复。
- **Resume Trigger**：新展示要求准确的**每个物理 Action 终态**、告警发生误判或用户另行立项；隔离固定版本验证真实 JobEnd→OpenLineage Run UUID→Marquez 终态，严禁维护原地伪造事件。未来独立 Change 获批准后方可修改 Listener/版本或 UI。

## 四、后续独立项目（没有实施授权继承）

1. **Public Read-Only Portal**：规划静态/缓存投影或新的只读聚合接口，鉴权、速率限制、敏感信息剔除和明确不暴露 Marquez 管理 API。现有官方 Web NodePort 30999 不是匿名安全服务；**不得直接映射公网**。
2. **Azure/Fabric Cross-Platform Lineage Showcase**：FHIR/HL7 Producer / OIE / Azure Blob / Fabric Bronze/Silver 各自需要真实部署和事件/DataSet/版本核验，并决定 Azure 原生血缘与本地 Marquez 的展示边界。当前本地 P5/P6 验收不证明这些云端能力已实现。需单独 OpenSpec Proposal/Design/Tasks 及费用/授权/公网策略。

## 五、归档门槛与长期可追溯性

- 先让本地 Portal `complete-platform-portal-lineage-integration` 的 Tasks 记录 **A4 4.1 = 已作延后范围决策（不代表技术修复）**，P4 依照现有方案 A 的已批准观测缺口继续可见；全量原始 Evidence/失败 Run 不删除。
- **另行独立 Archive PR**：将该 Change 的完整 Proposal/Design/Tasks/Specs/Evidence 移到 `openspec/changes/archive/2026-10-25-complete-platform-portal-lineage-integration/`，按原始 Spec Delta 同步当前可观察的 `portal-business-lineage` Requirement，并修正文档相对链接。只有 PR Required CI SUCCESS、Main Merge 和归档位置复读后才可写“ARCHIVED”。
- GitHub repository **Issues disabled (API 410)**：因此 A4/P4 的长期遗留追踪由**这份位于 Active design 目录的持久文件**承担，不声称已建立 Issues。
- 本轮 Closeout 只修改文档/OpenSpec/Git；**没有** K8s、Airflow、Spark、PostgreSQL14/17、S3、GHCR、Azure 或公网配置写入；不触发任何一次性生产 Batch。
