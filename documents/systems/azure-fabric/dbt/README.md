---
status: active
scope: fabric-dbt-project-governance
last_verified: 2026-11-07
source_sha: c36ed72ba140d6b2956d71ab97206baa2965bd58
---

# Fabric dbt — 标准工程目录与 Agent 准入规则

> **AI/Agent 必读：** 本文既是 dbt 源码归属规则，也说明已通过本地验收的 `hl7-canonical` 及其消费者切换边界；不要把离线 CI 视为远端 Fabric 发布。任何新 dbt 目录、模型、项目改名或迁移必须先检查最新 Main、[正式采用的 dbt Current Spec](../../../../openspec/specs/fabric-dbt-project-layout/spec.md)、[OpenSpec dbt Change](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 与现有 CODE Map。

## 唯一归属

**以后 Fabric 数据平台的正式 dbt Core 项目统一放在 `azure-fabric/dbt/<project>/`。** 已确定第一个项目为 `hl7-canonical/`，内部 `dbt_project.yml` 的 `name: hl7_canonical`。**P3 工程由 [PR #820](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/820) 正式合并 Main；本次消费者切换将唯一维护中的本地 dbt CI 入口设为 [新 dbt CODE](CODE.md) 的 `hl7-canonical` 工程。** Local DP 的 Parser/Manifest/Delta Staging Writer 仍由 [旧 HL7 CODE](../../data-platform/hl7/CODE.md) 管理，旧 dbt SQL/config 是冻结参考，未清理；真实 Azure/Fabric Silver/Gold 仍未部署。

不在 `Self-Runner/` 长期维护业务 SQL（只执行和保存历史 POC）；不塞进 `azure-fabric/workspaces/`（仅真实 Native Notebook/Pipeline/Environment/Lakehouse）；不在 `shared-data-engine/` 复制 dbt 或 OMOP 业务内核；**不新增 `azure-fabric/ingestion/`**。FHIR Native Items 及共享 Adapter 已分别在 Workspace 与 Shared Engine。HL7 Parser/Delta Staging Writer 仍在 Local DP，它们的未来迁移不在本次授权内。

## 首次正式建项时的完整骨架

```text
azure-fabric/
└── dbt/
    └── hl7-canonical/
        ├── dbt_project.yml
        ├── models/
        │   ├── staging/
        │   ├── intermediate/
        │   └── canonical/
        ├── macros/
        ├── tests/
        ├── seeds/
        ├── snapshots/
        ├── analyses/
        └── profiles/
            └── local/
                └── profiles.yml
```

**目录完整、业务实现按需**：标准空目录必须使用 `.gitkeep` 保留，不要写没有业务价值的占位 SQL；`packages.yml` 只有真实依赖时再建。`models/` 按 staging → intermediate → canonical 分层，也可按实体再细化。dbt staging 是 SQL Model 分层，不是 Parser 写入的物理 `hl7_staging.hl7_events` Delta 表。Profiles 不能提交 Token、账户密钥或凭据。dbt 原生 `tests/` 用于 singular SQL tests；schema/data tests 可在模型旁 YAML 定义；Python/集成测试仍在 `.github/quality/tests/`。

**dbt 原生 SQL Tests 例外已正式生效并通过真实 PR 验证（2026-11-07 ET）：** [治理 PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) 已将精确白名单部署到受保护的 Main checker。仅允许 `azure-fabric/dbt/hl7-canonical/tests/.gitkeep` 和该目录下命名合规的 singular `*.sql`，其他源码目录及 Python/YAML/README 测试依然拒绝。真实正向 [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) 四项 Required PASS，负向 [#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 被受保护的 `require-trusted-change` 阻止；两 PR 均关闭且未合并。Ruleset #25365902 Active，四项 Required 已恢复。**P3 #820 已以全新合成 HL7 + 物理本地 Delta + dbt 5/5 model、15/15 tests、18/27 Contract、Replay/负向检验取得 [Run #42445172602](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42445172602) SUCCESS；消费者切换仍须以本次独立 PR 的新 CI 结果为准。**

## 新项目如何审批

| 需求 | 规则 |
| --- | --- |
| 新医院或 HL7 Observation/Condition 等实体 | 在同一个 `hl7-canonical` 扩展，不按医院/实体新建工程 |
| 新增 FHIR 的 dbt 路线 | 可提案 `fhir-canonical`，先审查现有 PySpark/Shared Engine 和独立运行需求，走新 OpenSpec |
| 新增 CSV 的 dbt 路线 | 可提案 `csv-canonical`，同样先走 OpenSpec |
| 直接用 dbt 做跨来源 Canonical/OMOP 业务 | 可能独立 `canonical-transform`，但**未预先批准**；先确定与 Shared Engine 的唯一职责和迁移方式，禁止两套 Mapper |
| 单表、单医院、单 Workflow 的临时想法 | 先复用现有 Project，默认不准直接新建 |

新项目必须交代业务范围、是否真需要另一个 Project、数据库适配器与执行地、输入输出 Contract、数据发布授权边界、唯一 CODE Owner 和 CI/模型测试。正式 Canonical Silver 批准与 OMOP Publisher 仍由统一共享路径管理，**dbt Candidate 不是已发布 Silver 或 Gold**。

## 新工程开发与旧实现退役的文件手续

先查看 [dbt 业务 CODE Map](CODE.md)，并核对最新 Main、开放 PR、[根 AGENTS 规则](../../../../AGENTS.md)、[OpenSpec Change](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 和 [Fabric Medallion ADR](../../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。**采用用户确认的“冻结参考 → 新工程直接开发 → 验收 → 一次切换和清理”**：P1/P2 Gate 和 P3 新 SQL 及独立验收已经完成。本次受控切换 PR 将原 GitHub-hosted HL7 回归 Workflow 改为执行 `azure-fabric/dbt/hl7-canonical/`，保留 Python Parser/Manifest/Delta Writer 与既有 18/27 Contract Readback；新工程唯一管理后续 dbt SQL，**旧 dbt 模型/配置已从现行源码树退役，仅在固定历史 PR/SHA 中保留，不再执行或新增业务功能**。Self-Runner `experiments/hl7-dbt-canonical/` 使用固定历史 SHA 和独立 POC 模型，未被指定为 Healthcare 生产消费者。**独立 P3 3.4 清理 PR** 仅退役旧 dbt SQL/project/profiles；当前 HL7 Python Parser/Intake/Delta Writer、所需测试和混合 requirements 必须按依赖另行审查，不删除整个 HL7 目录。完整逐文件状态、删除门槛见 [HL7 CODE](../../data-platform/hl7/CODE.md)。不能因为本文件生效就声称代码已迁移、真实 42 条 Azure HL7 已消费、远端 Fabric 计算已执行或正式 Silver/Gold 已验收。

**核心原则：新 dbt 工程是唯一维护入口；旧版由历史 Git SHA/PR 回溯，业务 Parser/Intake/Delta Writer 和必要回归测试持续保留。远端 Fabric/正式 Silver/Gold 未经另行授权不得执行。**
