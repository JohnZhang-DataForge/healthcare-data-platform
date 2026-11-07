---
status: active
scope: fabric-dbt-project-governance
last_verified: 2026-11-07
source_sha: 641215bcb9dc94fdda1da0da60904cf16c5bef5a
---

# Fabric dbt — 标准工程目录与 Agent 准入规则

> **AI/Agent 必读：** 这是正式的**未来源码归属规则**，不是现有源码已经迁移的声明。任何新 dbt 目录、模型、项目改名或迁移必须先检查最新 Main、[正式采用的 dbt Current Spec](../../../../openspec/specs/fabric-dbt-project-layout/spec.md)、[OpenSpec dbt Change](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 与现有 CODE Map。

## 唯一归属

**以后 Fabric 数据平台的正式 dbt Core 项目统一放在 `azure-fabric/dbt/<project>/`。** 已确定第一个项目为 `hl7-canonical/`，内部 `dbt_project.yml` 的 `name: hl7_canonical`。**目前这个目标目录不存在**：真实、已验证的 dbt 项目仍位于 `local-data-platform/spark/apps/hl7/`，当前唯一 Source Owner 是 [HL7 CODE](../../data-platform/hl7/CODE.md)，[HL7 实际链路](../../data-platform/hl7/README.md)。

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

**现有可信 CI 冲突，必须先解决：** `.github/quality/scripts/check_repository_layout.py` 目前会拒绝源码中任何新 `tests/`，包括 `tests/.gitkeep`。不能只修改本 README 就绕过 Ruleset。必须用独立 OpenSpec、受信任的 Checker 维护和真实正反测试，只给予已审核 dbt 项目 SQL 测试目录有限白名单；一般源码目录自动化测试继续被拒绝。**在此之前不创建不完整的“假标准项目”。**

## 新项目如何审批

| 需求 | 规则 |
| --- | --- |
| 新医院或 HL7 Observation/Condition 等实体 | 在同一个 `hl7-canonical` 扩展，不按医院/实体新建工程 |
| 新增 FHIR 的 dbt 路线 | 可提案 `fhir-canonical`，先审查现有 PySpark/Shared Engine 和独立运行需求，走新 OpenSpec |
| 新增 CSV 的 dbt 路线 | 可提案 `csv-canonical`，同样先走 OpenSpec |
| 直接用 dbt 做跨来源 Canonical/OMOP 业务 | 可能独立 `canonical-transform`，但**未预先批准**；先确定与 Shared Engine 的唯一职责和迁移方式，禁止两套 Mapper |
| 单表、单医院、单 Workflow 的临时想法 | 先复用现有 Project，默认不准直接新建 |

新项目必须交代业务范围、是否真需要另一个 Project、数据库适配器与执行地、输入输出 Contract、数据发布授权边界、唯一 CODE Owner 和 CI/模型测试。正式 Canonical Silver 批准与 OMOP Publisher 仍由统一共享路径管理，**dbt Candidate 不是已发布 Silver 或 Gold**。

## 迁移的文件手续

先核对最新 Main、开放 PR、[根 AGENTS 规则](../../../../AGENTS.md)、[OpenSpec Change](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 和 [Fabric Medallion ADR](../../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。单独解决受保护 Gate 后，再**移动而非复制**现有 HL7 dbt SQL/config/profiles，更新唯一 CODE Map、Workflow/Self-Runner 消费路径、依赖与文档，并重新执行 Local Spark Delta + dbt compile/run/test + Replay + Canonical 合同独立读回。不能因为本文件生效就声称代码已迁移、真实 42 条 Azure HL7 已消费、远端 Fabric 计算已执行或正式 Silver/Gold 已验收。

**核心原则：一处归属、一份正式源码、先 OpenSpec/Review 再新建目录。**
