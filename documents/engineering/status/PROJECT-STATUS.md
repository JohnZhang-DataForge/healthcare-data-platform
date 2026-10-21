---
status: active
scope: project-status
last_verified: 2026-10-21
source_sha: 3b94af541f3904a731622e51eece027bef4b818c
---

# Healthcare Data Platform — 项目当前状态

> **唯一项目级 CURRENT / NEXT 入口。2026-10-21 交接状态：Local DP NEW_ONLY Person/Visit 真实 E2E + 三项缺陷修复已验收，Discovery 100 预览线上通过；目录迁移历史清理与旧 GHCR 退役仍未完成。Fabric 免费 Trial F4 Workspace/Lakehouse 已真实 Apply；Connection 和 Notebook/Pipeline Live 发布尚未完成。** 下方保留的 2026-10-14～20 记录属于有日期的历史里程碑，不能覆盖本段的 CURRENT。
>
> **定义**：本文仅汇总 **项目/工作线进度、已批准的目标与证据边界**；[总体架构](../../architecture/SYSTEM-OVERVIEW.md) 负责系统设计；具体实现由源码、Contracts、运行记录及后续组件文档承担。`docs/tasks/TASK-STATUS.md` 和旧 Agent Handoff 仍用于历史追溯，但其过时的 `CURRENT/NEXT` **不再覆盖本文**。
>
> **2026-10-21 更新基线**：Healthcare Main `3b94af541f3904a731622e51eece027bef4b818c`、Self-Runner Main `29094515eeb84f79a89c34061e55becd96e7d9ad`。本地业务验收来自 [Run #39679393354](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39679393354)，被测 Healthcare 源码 SHA `bfc843d5cbc5471ca31fbe7bd31d3cd0dbfb7b9f`；该 SHA 与最新 Main **没有 Local DP 代码差异**（仅 Fabric 文件新增修改）。以下 PG 数字是对应 Run 时点的独立读回，**本次只更新 Git 文档，未重新采样 PG/K8s/Azure**。

> **Fabric 2026-10-20 历史设计记录**：旧 Module-first/Bootstrap 讨论与过渡期“未 Apply”说法均已被后续独立 Terraform Roots + 免费 Trial F4 真实验收取代。当前 Fabric 实施任务请以 [deploy-fabric-connection-and-items](../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md) 为准。

> **Fabric 2026-10-20 源码清理历史记录**：移除过度设计的 Bootstrap 支路属于已完成的源码整理，不能用来推断当前 Azure Live 状态；现行按 Workspace / OneLake / Shared Infra 分 Root 管理。

**Fabric 2026-10-20 Plan 历史证据**：Workspace / OneLake / Shared Storage 独立 Terraform Roots 曾完成早期 Plan 验证，期间遇到容量配置阻挡；详见 [organize-fabric-terraform-by-workspace](../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md)。**这些早期失败和当时“尚未创建”的描述不代表 2026-10-21 的最终状态。**

> **Fabric 当前事实（2026-10-21）**：免费 Trial F4 Workspace `johnzhang-test`（ID `d399f361-bc40-4f88-9615-df138ab8ee3b`）和 Lakehouse `lh_johnzhang_test`（ID `5a16b5a1-6274-4b37-8dad-19cb68b5139d`）由独立 Terraform Roots **实际 Apply、二次 Plan 无漂移**，证据 [Self-Runner #39635155333 Attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333)；复用免费 Trial F4，没有创建收费 F2。[PR #372](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/372) Connection Root（默认禁用）、[PR #374](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/374) 原生 Notebook/Pipeline Smoke 源码、[PR #375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/375) 受控 `fabric-cicd` Publisher **均已合并 Main 且属于源码/静态完成**；Self-Runner Trial-only Publisher Workflow [PR #204](https://github.com/JohnZhang-DataForge/Self-Runner/pull/204) 已合并。**Connection 真实授权/Apply，Fabric Notebook/Pipeline 云端发布、Smoke 和 PG→Blob→OneLake 业务 E2E 仍未验收**；切勿把 Git Native 源码存在视为已经部署。权威下一步：[Fabric Items Change](../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md)。

## 1. 一屏总览

| 工作线 | 决策/开发状态 | 已真实验证的范围 | 未完成或下一步 |
| --- | --- | --- | --- |
| **TASK004 — Synthea NEW_ONLY → Local OMOP Person/Visit** | **核心 E2E PASS；仅 Person/Visit NEW_ONLY** | Native Race、多 Parquet、Airflow exact Selection 已修复；三批旧数据全部入库；最新新 Batch 100 Person / 15,326 Visit 完整 COMMIT、PG 读回和重复 SKIP PASS | 下一步集中删除历史冗余代码并合并 Main；8 镜像 Clean Build、合并后 3 批新数据全流程 + 2 批旧数据幂等回归；旧 GHCR 与归档最后处理 |
| **TASK005 — Condition** | **PAUSED（优先级暂缓） / STEP00 READ-ONLY READY / IMPLEMENTATION NOT STARTED** | 已有部分可复用源码/合同；没有 Condition 业务写入的完成证据 | 保留 STEP00 只读预检准备与原计划；重新启动 Condition 开发需另行决定，任何业务 COMMIT 须单独批准 |
| **Platform Portal — Marquez / OpenLineage** | **前期实施/验收完成；下一阶段 Spark 接入方案讨论中** | 独立 PG14、Marquez Web/API、A3 Airflow 事件已真实验证；A4 隔离 Spark Smoke 有实际运行和部分读回证据 | **下一步如何接入真实 Spark 业务链路尚未确定**；Job↔Run 名称挂接和 Dataset I/O 完整血缘待处理，不直接启动新 Spark/共享资源 |
| **Azure/Fabric — OMOP → OneLake** | **免费 Trial F4 Workspace/Lakehouse Terraform Apply PASS；Git Native Publisher 源码 Ready** | Workspace + Lakehouse 实际创建及无漂移；Connection Root、Notebook/Pipeline 定义、受控 `fabric-cicd` Publisher 和 Self-Runner Workflow 已合并、静态测试 PASS | 未完成 Connection 真实认证/RBAC/Apply、Notebook/Pipeline Live 发布与无写入 Smoke、PG→Blob→OneLake 业务 E2E |
| **文档与 OpenSpec 治理** | **Bootstrap G0–G4 完成；Main Required Change Gate 已验证；治理收尾仍 Active** | [Ruleset #25365902](https://github.com/JohnZhang-DataForge/healthcare-data-platform/rules/25365902) 已设可信 Change Gate + OpenSpec Strict Required；负向 [PR #233](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/233) blocked/未合并，正向 [PR #234](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/234) 全绿合并、无需人工审批 | [enforce-openspec-change-gate](../../../openspec/changes/enforce-openspec-change-gate/tasks.md) 仍有 Current Spec/Archive 收尾；G0–G7 [历史计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 非当前实施账本 |

**Local DP 2026-10-21 已验证事实（NEW_ONLY Person/Visit 业务范围）**：
- [三批生成 #39630497311](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39630497311) 共 **300 Person / 43,825 Encounter**。Batch 01 [#39637787637](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39637787637) 真正提交 **100/15,188**；Batch 02/03 通过 [#39653021301](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39653021301) 真正提交 **100/15,400**、**100/13,237**，三者都通过独立 PG Readback 与同 Batch SKIP，合计新提交 300 Person / 43,825 Visit；**02/03 不再是只 READY 未 COMMIT**。
- [最终三项回归 #39679393354](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39679393354) `completed/success`：已完成 Batch 02/03 分别再次 Airflow SKIP，Spark/Writer 均跳过，PG 精确零变化；生成全新 `synthea-new-only-gh-39679393354-01`，**100 Person / 15,326 Visit**，生成、18 CSV、S3 READY、Spark Person/Visit/Reconcile、Writer Atomic COMMIT、独立 PG Readback、同 Batch SKIP + PG 零变化全部 PASS。Manifest SHA `2ff390da999e52420917fd5963c1c5b275d0b764ac42bd46f4e4ec388bdc8173`；PG Person **694→794**，Visit **96,133→111,459**；Writer 实际 Pod Digest `sha256:7e76a43a26c236b6b0a8dc839a7217f35c14827c82b88f23d0385ae1690cb83c`；DAG 暂停状态恢复。临时取证 [Self-Runner PR #208](https://github.com/JohnZhang-DataForge/Self-Runner/pull/208) 关闭未合并。
- [Writer 多 Parquet 专项 #39624499095](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39624499095) 和 [Discovery 29 READY /29 预览 #39640585101](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39640585101) 另有只读/专项证据，不冒充新批次 COMMIT。以上 PG 总数均是相应 Run 结束时读数，并非当前实时承诺。
- [集中清理 PR #332](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/332) **已合并删除 9 个**旧生成 Shell；19/19 正式输出与 17/17 HOLD 仍在当前仓库。删除后历史真实随机 E2E **FAIL/FAIL/PASS**，后续 Native Race、多 Parquet 和 Airflow Selection 原有缺陷分别修复，不能直接把当年失败归因于九个删除文件。当前 Main 未截断 Git Tree：`local-data-platform/` **363 tracked**，包括 **90 Shell（TASK003 60）与 107 Tests**，不是历史 393/371 文件。

**Local DP CURRENT/NEXT — 用户批准的一次性清理与强回归策略**：① 复用历史双仓扫描/备份，按当前 SHA 批量核对实际消费者、动态引用、构建、手工安全恢复需求，生成明示 **C/D 删除 allowlist**；保留 A/B/E（尤其不确定的人工恢复/Writer Fencing/Contract/测试），**不做逐脚本 Runtime 验证**。② 在一个清理 PR **一次删除全部合格 C/D**，同步 CODE.md、导航和 Git 恢复 SHA；最终 HEAD 适用 CI、Contract、DagBag、**8/8 镜像 Clean Build、入口/来源与 Digest** 全绿后按 Merge-first 合并 Main。③ 核对新 Main Airflow GitSync/DAG 和真实镜像版本；从合并 Main 串行生成 **至少 3 批互相独立的新随机 Synthea**，每批完整 S3 READY→Spark Person/Visit/Reconcile→Writer Atomic COMMIT→PG 独立读回与同 Batch SKIP 零变化，再重跑 **2 个已 COMMIT Batch** 做 SKIP/PG 零变化；专项保留 Native Race、多 Parquet、Discovery exact Selection 测试。失败 STOP 新写入、只读判定实际 COMMIT、修复或 Git revert，不能假定 PG/S3 回滚。④ 真正全部 PASS 后才处理 GHCR 旧版本、OpenSpec 4/5 结项归档。**E2E 只证明所执行的业务路径，不能证明未测试的维护/恢复脚本无价值。新的批量删除还未执行。**

**具体变更进度统一来自 Active OpenSpec Changes**：[本地目录迁移](../../../openspec/changes/relocate-local-data-platform/tasks.md)（物理目录与 GitSync 已修复、新唯一 Batch E2E PASS；其余路径覆盖/历史清理未完成）、[PR 治理](../../../openspec/changes/enforce-openspec-change-gate/tasks.md)（Ruleset 已验证、归档待办）、[Engineering 整理（已完成、归档）](../../../openspec/changes/archive/2026-10-18-engineering-governance-cleanup/tasks.md)（只改文档）、[Legacy 重构](../../../openspec/changes/modernize-legacy-task-code/tasks.md)（仅作为尚未获运行授权的未来计划）。本页不复制这些 Change 的 Tasks。

**2026-10-20 本地源码迁移后实时验收补记**：[Helm GitSync 修复 #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924) SUCCESS，Scheduler/DAG Processor 已指向 `local-data-platform/airflow/dags`；[新 Synthea Batch 生成/发布 #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846) SUCCESS；[新根真实 E2E #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) SUCCESS。独立 PG 总行数 Person **208→224**、Visit **21934→26193**，新增批次 `synthea-new-only-gh-39421910846` 16 Person / 4259 Visit 完成 OMOP Writer Atomic COMMIT、Claim COMPLETED 和同 Batch 再次执行 SKIP、零数据库变化。严格区分本次新批次运行成功与未完成的镜像构建兼容/历史代码清理；技术细节、固定 SHA/Digest/Manifest/重复执行证据以 [Active Change Task 4.6](../../../openspec/changes/relocate-local-data-platform/tasks.md) 为准。

**两个不同的“04”**：业务 **TASK004 已 CLOSED**，本次 **Documentation Rebuild STEP04** 是文档整理步骤，完成前者不等于后者提前完成。

> **2026-10-20 曾观察到的随机 Batch Writer 失败（历史问题，后续已分别修复）**：Native Race 映射在 [独立 Change](../../../openspec/changes/fix-synthea-native-race-mapping/tasks.md) 下完成修复；Spark 多 Parquet 部分写入也经 [Writer Change](../../../openspec/changes/fix-multi-parquet-omop-writer-read/tasks.md) 定向修复和真实两分片只读回归，并在后续新 Batch E2E 通过 COMMIT/SKIP。旧失败日志仍保留供追溯，不代表现在的未解决告警；也**不**声称所有可能的随机 Batch 都已覆盖。

## 2. 本地业务：TASK004 已关闭

**明确的最终验收范围**是 **NEW_ONLY + Person/Visit + 手工受控 Airflow 消费和原子 Writer**，并不等于 Healthcare 所有业务域或 UPDATE_ONLY / MIX_DATA 已实现。

- 真实 Airflow `new_only_omop_consumer` 成功执行一次第三批完整链路，之后对同一已完成批次再次触发会路由到 `already_completed_no_replay`，Spark/Writer 不重复执行。
- 2026-10-14 最终验收时的 **PostgreSQL 历史读数**：`cdm.person = 208`、`cdm.visit_occurrence = 21,934`、三条已完成 Batch Claim；第三批新增 **1 Person + 244 Visit**。这些是验收时点数字，不能当作 2026-10-16 实时库存。
- 业务 DAG 的 `schedule=None`，接受已授权的手工 Batch；定时 `landing_batch_discovery` 的默认读取/发现不等于自动业务 COMMIT。
- UPDATE_ONLY、MIX_DATA、Condition Writer、复杂的双 Writer 并发与灾难恢复属于独立后续范围；本次关闭不证明这些已完成。

**证据**：[TASK004 Final Acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) · [实际 Airflow + PG 只读验收 Run 38657060822](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657060822) · [相同 Batch SKIP Run 38657630069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657630069) · [Airflow 源码](../../../local-data-platform/airflow/dags/new_only_omop_consumer.py)。

**Condition 优先级（2026-10-18 更新）**：TASK005 业务开发暂缓；历史 [Condition 计划](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 的 STEP00 READ-ONLY 仍可作为将来恢复的起点；不自动授权数据库写入、批次处理或资源部署。当前主线以 OpenSpec 管理剩余 Local DP 路径兼容，随后根据独立授权推进 PG→Fabric 双表 MVP，随后按独立 Change 引入 FHIR/HL7；开发优先级仍由用户每轮确认。

## 3. Portal：已实施到 A3 / A4 Smoke；后续 Spark 集成方式仍在讨论

**现行组件知识入口**：[Platform Portal 组件说明](../../systems/platform-portal/README.md)。

**已经落地/证实（历史验收）**

- Marquez 0.51.1 API + 官方原生 Web，独立 `dw-postgre14` PostgreSQL14 元数据数据库；Web-only NodePort 30999 的内网服务/HTTP 已验收，不等于公网/个人电脑浏览器可访问。
- A3 Airflow OpenLineage Provider → Marquez 的独立 DAG/Task/Run 事件已做实际验证。
- A4 **独立探针**：真实 SparkApplication 完成、三行模拟 CSV 聚合成功，Marquez 中有真实带 Spark facets 的 `COMPLETED` Run。首轮完整 Workflow 因错误 Job 匹配而 **FAILURE**，随后三次只读验收 **SUCCESS**；不能抹去原始失败。

**尚未讨论定稿/实现验收的部分**

- 用户正在讨论下一阶段**如何把 OpenLineage 正式接入真实 Spark 业务处理链路**；此处记录为 **DESIGN DISCUSSION / NOT APPROVED**，**不指定**应采取哪种 Listener、配置变更或部署方式。
- A4 应用 Job `portal_a4_a438628542127` 的 `latestRun` 为空，真实完成 Run 被记录在 `unknown` Job；Input/Output Dataset facets、Airflow→Spark→OMOP 完整业务血缘尚未证实。
- 任何新的 SparkApplication、修改 Airflow Scheduler/Operator、共享资源部署或运行 Self-Runner Live，都需要用户针对具体操作协调和授权；不可因为前期 Smoke 完成而自动执行。
- Portal **目前不是自建 Web UI**；实际提供的是 Marquez 原生 Web。

**证据**：[Portal 源码总地图](../../systems/platform-portal/CODE.md) · [Marquez 部署验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) · [A3 Airflow Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) · [A4 Spark Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) · [多 Session 协调](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md)。

## 4. Azure/Fabric：当前 Terraform Trial F4 Apply 成功；下文 4.2 为 2026-10-15 历史 Plan 基线

**现行组件知识入口**：[Azure/Fabric 组件说明](../../systems/azure-fabric/README.md)。

### 4.1 已确认的目标（设计定稿）

```text
Local PostgreSQL OMOP (authoritative)
  → Consistent Read-only Exporter (future implementation)
  → EXISTING Azure Blob Storage / OMOP snapshot Landing
  → Microsoft Fabric Data Factory Data Pipeline (orchestration)
  → Fabric PySpark Notebook (read / DQ / transform / load)
  → OneLake Lakehouse (Delta analytics copy)
```

- **Fabric Data Factory Data Pipeline** 是 Notebook 的编排者：用户口语中“Notebook + Factory”指这两个组件的组合，实际执行依赖次序是 Pipeline 调用 Notebook，而不是先执行 Notebook 再启动 Pipeline。
- **OneLake Lakehouse 是 MVP 目标**；旧 Warehouse-first、多层冗余云端 ETL 不属于当前最短工期方案。Warehouse 仅作为未来可选项。
- 本地 PG 是已经标准化的 OMOP 数据权威；**Azure Blob 是 PG 导出后的云端 Landing**，与 Synthea → SeaweedFS S3 的原始源批次 Landing 不同。

### 4.2 已完成的基础设施工程（源码与 Plan）

- Healthcare `azure-fabric/infra-terraform/` 已复制旧 `azure/infra-terraform/` 的 **components + modules** 结构以及目标 Lakehouse/Notebook/Data Pipeline 的 Terraform **资源定义**，包括分组件 IAM 占位与边界；原 `azure/` 已在后续完成迁移审计后退役，Backend/State Key 未变。源码复制不代表云端部署，也不是可运行业务 ETL 的完整实现。
- Self-Runner 上独立的 [`Azure-Infra-TF` Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 已完成开发并跑过真实 Terraform Plan；支持 component/env/operation 选项，默认 `plan`，虽提供 `apply`，**本阶段尚未获得执行授权**。
- 已有的 Azure Storage / Blob Landing、Terraform Remote State 和 Fabric Workspace 继续复用；不以本次三个 Plan 声称新建了这些既有资源。

| Component | 目标 Terraform Resource | 2026-10-15 证据 | 实际执行 |
| --- | --- | --- | --- |
| `onelake` | `fabric_lakehouse` / `lh_omop_analytics` | [Run 38799966270 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270/attempts/2) | **Plan PASS：1 add / 0 change / 0 destroy；未 Apply** |
| `notebook` | `fabric_notebook` / `nb_omop_snapshot_load` | [Run 38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550) | **Plan PASS：1 / 0 / 0；未 Apply** |
| `data-factory` | `fabric_data_pipeline` / `pl_omop_snapshot_to_onelake` | [Run 38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221) | **Plan PASS：1 / 0 / 0；未 Apply** |

三个 Plan 都基于 Healthcare SHA `6acb59353f5d7630f65b6f417c8e8bfbd39cf651`；**合计拟新增 3 个资源，但实际创建 0 个**。Storage 与 Foundation-IAM 先前也有独立 Plan 证据，但不把其视为这三个 Fabric Item 已被部署。

### 4.3 尚未讨论完成、尚未落地的实施细节

1. **Exporter / 数据合同**：从 PostgreSQL `cdm.*` 导出哪些表、快照一致性、批次身份、Manifest、文件格式、重试与增量/全量策略。
2. **Notebook / OneLake 装载**：Azure Blob 读取与凭据、Schema/DQ/FK/Hash、Delta 写入、重放幂等和失败恢复；当前 Notebook 只有 fail-closed bootstrap（`raise RuntimeError`）。
3. **Pipeline 运行**：实际 Notebook GUID、`export_id`/`manifest_uri` 参数传递、失败/成功条件、调度方式；当前 `notebook_id=""` 对应一个明确的 **Fail activity**。
4. **部署与验收**：Fabric Workspace/Capacity/权限/既有 Item 核实；分组件独立授权 Apply 与真正远端资源读回；PG → Blob → Notebook → OneLake 的端到端对账。

**此处为 2026-10-15 历史 NEXT**：以本文顶部的 2026-10-21 当前状态和 [Fabric 现行 OpenSpec](../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md) 为准。下一步按既有认证边界核验 Connection Reader/RBAC、受控发布 Notebook/Pipeline 及无数据写入 Smoke；具体 Azure Live 操作仍须独立授权，不自动 Apply。

**依据**：[OneLake-first 方案与真实 Plan 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) · [Terraform 组件](../../systems/azure-fabric/infra-terraform/README.md) · [IaC 架构/IAM](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md) · [Notebook bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) · [Pipeline fail-closed definition](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)。

**2026-10-18 本地源码目录迁移事实**：批准的命名试点已归档；实体目录通过 [PR #225](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/225) 将 393 个本地业务源码文件整体移到 `local-data-platform/`、移除旧业务根路径，Merge `377df7c9fae770cde985f6e7bcbc47d40ecfa355`。随后 [PR #226](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/226) 修复源码文档链接及 CODE Map，[PR #227](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/227) 将 6 个仓库质量文件移至 `.github/quality/`，最终目录基线 Main `7e969718cfad9368fd13866053636c787e24ca7e`。独立备份在私有 Healthcare-Specs 的 PR #2/Main `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`。**PR #225 的 Component CI 曾 FAIL**；物理搬迁本身不构成 Import、DAG/GitSync、Docker/Spark、PG/S3 运行 E2E 验收。随后 NEW_ONLY 运行路径与业务链路已于 2026-10-20 修复并通过新 Batch 实际 E2E，见第二节和 4.6 证据；其余迁移兼容/清理仍是 OpenSpec 待办。现在通过 [Active OpenSpec Change](../../../openspec/changes/relocate-local-data-platform/tasks.md) **事后追溯**上述 PR 并管理待完成运行调试；`documents/systems/data-platform/` 组件文档命名空间不变。

**OpenSpec 首轮命名 Change 的真实验证**：`adopt-local-data-platform-naming` 文档修改 [PR #223](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/223) 已合并 Main `d97f7bb7babe1468cc2fc115e511c836360f721a`；[OpenSpec 1.14.3 Strict Run #39155840396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840396) 与 [Docs Links Run #39155840375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840375) 均 SUCCESS，最终 PR HEAD 为 `f16baba0e993c5f4d92d1aed2b3eb5ec31fcf00f`。完成的 docs-only Change 通过 [Archive PR #224](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/224) 提交，**归档仅在 #224 合并 Main 后生效**；`openspec archive` CLI 未直接执行，按受审 Git 归档。这是命名试点当时的事实；其后的 PR #225–#227 已完成实体目录搬迁，Active `relocate-local-data-platform` Change 负责追溯和未完成的运行验证。

## 5. 文档重建与 OpenSpec（历史 Bootstrap 里程碑，非当前 Tasks）

| 文档里程碑 | 状态 |
| --- | --- |
| STEP01 — Agent 规则、文档治理、迁移入口 | **COMPLETE** — [PR #167](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/167) |
| STEP02 — Healthcare / Self-Runner 开发流程与测试证据 | **COMPLETE** — [PR #168](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/168) |
| STEP03 — Overall architecture（本地 + Portal + OneLake-first） | **COMPLETE** — [PR #169](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/169) |
| **STEP04 — 当前项目统一状态** | **COMPLETE** — [PR #170](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/170) |
| STEP05 — 本地组件文档与新代码命名约束 | **COMPLETE** — [PR #171](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/171)，旧代码未物理 Rename |
| STEP06 — Portal / Azure 专项文档 | **COMPLETE** — [PR #172](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/172) |
| STEP07 — Operations/Decisions/Session + OpenSpec Readiness | **COMPLETE** — [PR #173](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/173) |
| **STEP08 — 最终文档入口和权威校验** | **COMPLETE** — [PR #174](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/174)、[Final Audit](../migration/FINAL-DOCUMENTATION-AUDIT.md)（合并后正式生效） |
| STEP09 — 引入同仓 OpenSpec | **历史 G0–G4 Bootstrap 完成**：[PR #216](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/216)、[#218](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/218)、[#220](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/220)；详见 [G0–G7 历史实施记录](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md)。实际 G5/G6 先物理移动后补建 Change，按 [relocate-local-data-platform](../../../openspec/changes/relocate-local-data-platform/tasks.md) 后续验证；不把历史阶段表当作当前计划 |

**历史事实**：在 STEP08 终审时 `openspec/` 尚未出现，旧 Bootstrap [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) 后来关闭且未合并。**当前事实（2026-10-18）**：新 [PR #216](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/216) 已将官方 CLI 初始化生成的 `openspec/` 合并进入 Main；G2 的简体中文项目配置通过真实 CLI Smoke 验证。前两项仅证明工具和配置落地；G3 静态 CI 已通过 PR #218 真实验证并合并 Main，该 PR 当时的空基线确实为 0 个正式 Specs / Changes；**现有 Changes 已增加**，不表示业务 E2E 已完成。

**OpenSpec 历史证据索引**：[G0–G7 实施计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md) · [Operations](../operations/README.md) · [Session Coordination](../development/SESSION-COORDINATION.md) · [Architecture Decisions](../../architecture/decisions/README.md)。G0–G4 已验证并合并 Main，G3 最终三项 PR CI 均成功。G4 已通过 Healthcare [PR #220](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/220)（Merge SHA `10d65bb8e7a83ca5a308a738201bbf6d82669d22`）、Self-Runner [PR #136](https://github.com/JohnZhang-DataForge/Self-Runner/pull/136)（Merge SHA `ffd0eccecbf0148183b956e6e4416d4b8d99002b`）完成；最终 Healthcare PR HEAD `7b1fc6e6308a0fa5821b418f76ee1da7accf7b2e` 对应 OpenSpec [Run #39149670066](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670066)、Docs [Run #39149670014](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670014) 均 SUCCESS；Self-Runner 真实静态跨仓绑定 [Run #39149690050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39149690050) SUCCESS 并保存 Artifact。G4 历史验收不涉及 Runtime；后续 PR #225–#227 已迁移源码目录，运行兼容/端到端未验收；详见 Active `relocate-local-data-platform` Change。

## 6. 这份状态文档如何更新

- **本页唯一维护**项目总览、跨工作线 NEXT、批准/讨论中/未批准的边界；模块详情、新的真实证据只在所属组件文档或 Run/Closeout 存一份，再从本页链接。
- 修改任务完成状态需要 **真实源码/PR、明确验收范围与相应执行/读回证据**；改变目标方案需有用户确认，不把 Agent 候选建议写成 APPROVED。
- 重要检查附 **来源 SHA + Run/日期/环境**，避免过时数字被当作实时健康指标；Live 验证必须另行获得授权。
- 原 `docs/tasks/TASK-STATUS.md`、Portal 老 Agent Handoff 和旧 Azure Warehouse-first 文件已从 Main 清理；历史内容经 [Legacy Docs 固定快照](../migration/LEGACY-DOCS-SNAPSHOT.md) 可追溯，但不再作为全项目 CURRENT/NEXT。迁移计划见 [MIGRATION-STATUS](../migration/MIGRATION-STATUS.md)。
