---
status: active
scope: project-status
last_verified: 2026-10-16
source_sha: c4991d8fe1d4b6b9e65e024c2217f6c140eb17ed
---

# Healthcare Data Platform — 项目当前状态

> **唯一项目级 CURRENT / NEXT 入口（OpenSpec G0–G4 已接入）** · 运行证据快照日期：2026-10-16 EDT；开发优先级更新：2026-10-18（计划决定，不是 Live 复测）。
>
> **定义**：本文仅汇总 **项目/工作线进度、已批准的目标与证据边界**；[总体架构](../../architecture/SYSTEM-OVERVIEW.md) 负责系统设计；具体实现由源码、Contracts、运行记录及后续组件文档承担。`docs/tasks/TASK-STATUS.md` 和旧 Agent Handoff 仍用于历史追溯，但其过时的 `CURRENT/NEXT` **不再覆盖本文**。
>
> **核对基线**：Healthcare Main `c4991d8fe1d4b6b9e65e024c2217f6c140eb17ed`；Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7`。本页根据当前仓库源码、用户确认的方向和已保存的最终真实验收整理，**不是本日重新执行的集群、PG 或 Azure Live 健康检查**。历史验证数值应附原运行日期；没有本轮探针时不写「此刻 Running」。

## 1. 一屏总览

| 工作线 | 决策/开发状态 | 已真实验证的范围 | 未完成或下一步 |
| --- | --- | --- | --- |
| **TASK004 — Synthea NEW_ONLY → Local OMOP Person/Visit** | **COMPLETED / CLOSED** | 独立 Synthea、S3 READY → Airflow 手工 Consumer → Spark Person/Visit → 原子 OMOP COMMIT；独立 PG 对账及同批次 SKIP | 已验收范围冻结；不因后续任务而重放已完成批次 |
| **TASK005 — Condition** | **PAUSED（优先级暂缓） / STEP00 READ-ONLY READY / IMPLEMENTATION NOT STARTED** | 已有部分可复用源码/合同；没有 Condition 业务写入的完成证据 | 保留 STEP00 只读预检准备与原计划；重新启动 Condition 开发需另行决定，任何业务 COMMIT 须单独批准 |
| **Platform Portal — Marquez / OpenLineage** | **前期实施/验收完成；下一阶段 Spark 接入方案讨论中** | 独立 PG14、Marquez Web/API、A3 Airflow 事件已真实验证；A4 隔离 Spark Smoke 有实际运行和部分读回证据 | **下一步如何接入真实 Spark 业务链路尚未确定**；Job↔Run 名称挂接和 Dataset I/O 完整血缘待处理，不直接启动新 Spark/共享资源 |
| **Azure/Fabric — OMOP → OneLake** | **目标方案已敲定；IaC/Runner 工程及三个目标资源 Plan 完成；NO APPLY** | 已有 Azure Blob Landing / Workspace；Terraform 各组件资源定义、IAM 边界和 `Azure-Infra-TF` Workflow 在 Git；Lakehouse、Notebook、Pipeline 三个独立 Plan PASS | Exporter、真实 Notebook ETL、Pipeline 与 Notebook 绑定、Fabric 资源部署和数据 E2E 尚未讨论完成/实现；下一阶段先明确细节与验收门槛 |
| **文档重建 / OpenSpec** | **STEP01–08 COMPLETE；STEP09 G0–G4 COMPLETE（G4 双仓 PR 已合并）** | G0 审计、G1 官方 CLI Init、G2 中文配置均已完成；G3 [OpenSpec Run #39148008534](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008534) 及 [Naming Run #39148008629](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008629) SUCCESS：Node22/CLI1.14.3、Schema/中文指令、严格验证、正反测试、未来 `data-platform/**` 命名与 CODE Map 审核；当前 0 Specs / 0 Changes | [G0–G7 实施计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md)：G3 合并 SHA `b28660a28e7c9d6b72cc64ae19d3584d7f6f52e9`；G4 Agent/PR/Self-Runner 静态接力 COMPLETE（Healthcare PR #220 / Self-Runner PR #136 均已合并）；下一步 G5 设计阶段，G6–G7 未启动，没有业务 Runtime 操作 |

**两个不同的“04”**：业务 **TASK004 已 CLOSED**，本次 **Documentation Rebuild STEP04** 是文档整理步骤，完成前者不等于后者提前完成。

## 2. 本地业务：TASK004 已关闭

**明确的最终验收范围**是 **NEW_ONLY + Person/Visit + 手工受控 Airflow 消费和原子 Writer**，并不等于 Healthcare 所有业务域或 UPDATE_ONLY / MIX_DATA 已实现。

- 真实 Airflow `new_only_omop_consumer` 成功执行一次第三批完整链路，之后对同一已完成批次再次触发会路由到 `already_completed_no_replay`，Spark/Writer 不重复执行。
- 2026-10-14 最终验收时的 **PostgreSQL 历史读数**：`cdm.person = 208`、`cdm.visit_occurrence = 21,934`、三条已完成 Batch Claim；第三批新增 **1 Person + 244 Visit**。这些是验收时点数字，不能当作 2026-10-16 实时库存。
- 业务 DAG 的 `schedule=None`，接受已授权的手工 Batch；定时 `landing_batch_discovery` 的默认读取/发现不等于自动业务 COMMIT。
- UPDATE_ONLY、MIX_DATA、Condition Writer、复杂的双 Writer 并发与灾难恢复属于独立后续范围；本次关闭不证明这些已完成。

**证据**：[TASK004 Final Acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) · [实际 Airflow + PG 只读验收 Run 38657060822](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657060822) · [相同 Batch SKIP Run 38657630069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657630069) · [Airflow 源码](../../../airflow/dags/new_only_omop_consumer.py)。

**Condition 优先级（2026-10-18 更新）**：TASK005 业务开发暂缓；历史 [Condition 计划](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 的 STEP00 READ-ONLY 仍可作为将来恢复的起点；不自动授权数据库写入、批次处理或资源部署。当前主线改为 OpenSpec G0–G4、Data Platform G5/G6、PG→Fabric 双表 MVP，随后按独立 Change 引入 FHIR/HL7；开发优先级仍由用户每轮确认。

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

## 4. Azure/Fabric：目标架构已确定；Terraform 资源定义与 Plan 完成，实际 ETL 未开始

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

**当前 NEXT**：继续讨论、冻结最小可实施范围与数据合同；按用户单独批准的步骤再实施。**没有自动触发 Apply 或创建云端资源的许可**。

**依据**：[OneLake-first 方案与真实 Plan 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) · [Terraform 组件](../../systems/azure-fabric/infra-terraform/README.md) · [IaC 架构/IAM](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md) · [Notebook bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) · [Pipeline fail-closed definition](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)。

## 5. 文档重建与 OpenSpec

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
| STEP09 — 引入同仓 OpenSpec | **G0–G4 COMPLETE**：G1 [PR #216](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/216) 官方初始化；G2 [Run #39145378211](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39145378211) 中文配置；G3 [PR #218](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/218) 已合并，最终 PR HEAD `39972abf19535d892bc5759fd792187c89f29d67`；[OpenSpec Run #39148192774](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192774)、[Naming Run #39148192762](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192762)、[Links Run #39148192871](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192871) 均 SUCCESS；Main Merge SHA `b28660a28e7c9d6b72cc64ae19d3584d7f6f52e9`；G4 [Healthcare PR #220](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/220) / [Self-Runner PR #136](https://github.com/JohnZhang-DataForge/Self-Runner/pull/136) 已合并，G5–G7 未开始 |

**历史事实**：在 STEP08 终审时 `openspec/` 尚未出现，旧 Bootstrap [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) 后来关闭且未合并。**当前事实（2026-10-18）**：新 [PR #216](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/216) 已将官方 CLI 初始化生成的 `openspec/` 合并进入 Main；G2 的简体中文项目配置通过真实 CLI Smoke 验证。前两项仅证明工具和配置落地；G3 静态 CI 已通过 PR #218 真实验证并合并 Main，但仓库仍为 0 个正式业务 Specs / Changes，不表示业务验收或 Runtime 验收。

**OpenSpec 当前实施入口**：[G0–G7 实施计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md) · [Operations](../operations/README.md) · [Session Coordination](../development/SESSION-COORDINATION.md) · [Architecture Decisions](../../architecture/decisions/README.md)。G0–G4 已验证并合并 Main，G3 最终三项 PR CI 均成功。G4 已通过 Healthcare [PR #220](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/220)（Merge SHA `10d65bb8e7a83ca5a308a738201bbf6d82669d22`）、Self-Runner [PR #136](https://github.com/JohnZhang-DataForge/Self-Runner/pull/136)（Merge SHA `ffd0eccecbf0148183b956e6e4416d4b8d99002b`）完成；最终 Healthcare PR HEAD `7b1fc6e6308a0fa5821b418f76ee1da7accf7b2e` 对应 OpenSpec [Run #39149670066](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670066)、Docs [Run #39149670014](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670014) 均 SUCCESS；Self-Runner 真实静态跨仓绑定 [Run #39149690050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39149690050) SUCCESS 并保存 Artifact。G5 仅允许另外设计首个 Change；没有触发业务 Runtime。

## 6. 这份状态文档如何更新

- **本页唯一维护**项目总览、跨工作线 NEXT、批准/讨论中/未批准的边界；模块详情、新的真实证据只在所属组件文档或 Run/Closeout 存一份，再从本页链接。
- 修改任务完成状态需要 **真实源码/PR、明确验收范围与相应执行/读回证据**；改变目标方案需有用户确认，不把 Agent 候选建议写成 APPROVED。
- 重要检查附 **来源 SHA + Run/日期/环境**，避免过时数字被当作实时健康指标；Live 验证必须另行获得授权。
- 原 `docs/tasks/TASK-STATUS.md`、Portal 老 Agent Handoff 和旧 Azure Warehouse-first 文件已从 Main 清理；历史内容经 [Legacy Docs 固定快照](../migration/LEGACY-DOCS-SNAPSHOT.md) 可追溯，但不再作为全项目 CURRENT/NEXT。迁移计划见 [MIGRATION-STATUS](../migration/MIGRATION-STATUS.md)。
