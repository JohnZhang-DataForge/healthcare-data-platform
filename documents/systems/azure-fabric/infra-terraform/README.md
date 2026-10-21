---
status: active
scope: azure-fabric-terraform-component
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Fabric Terraform — 基础设施组件

> **当前实施目标已修订**：[Fabric Module-first Environment Architecture](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) · [新 Change Tasks](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。已有 `components → modules → environments` 是复用基础；已授权 Fabric 部署身份/Capacity、既有 Landing 与 Backend 为外部前置。下方“三身份 Bootstrap”“A=B”讨论小节是**旧方案与当前源码现状**，不得作为下一阶段必做任务；目前尚未实施统一 Root 或真实 Apply。

> **已完成组件文档收口（ACTIVE）**：本组件参照 [Data Platform 组件双入口](../../data-platform/README.md) 整理。**README 说明职责与边界， [CODE.md](CODE.md) 是 Terraform 唯一组件级源码导航**；深入的 IAM、OIDC、State 与历史 Plan 证据见 [ARCHITECTURE.md](ARCHITECTURE.md)。源码区旧说明文件在完成引用修复后退役；本次没有修改 Terraform 执行入口。

## 当前目标：基于现有 Components 和 Modules 开发

> **2026-10-20 用户批准集中清理**：`bootstrap/`、`tests/`、`tools/`、`new-environments/` 及相关旧 Preflight 示例已经退出 Git 工作树。现有七个 `components/` 和全部 `modules/`、环境 `dev.tfvars`、原有 Self-Runner `azure-infra.yaml` 继续保留。真实源码见 [CODE.md](CODE.md)，新架构见 [Module-first](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)。这不是已执行云端 Apply 的证据。

## 组件职责与系统位置

Terraform 仅负责 Azure/Fabric 的基础设施资源定义、身份及权限边界，属于 [Azure/Fabric 云端分析子系统](../README.md)，而不是本地 OMOP PostgreSQL 数据导出器、Fabric PySpark 业务 Notebook 或完整的数据处理流水线。

既定目标数据流：**本地 PostgreSQL OMOP → 未来只读 Exporter/不可变 Manifest → 已有 Azure Blob Landing → Fabric Data Pipeline 编排 Notebook → OneLake Lakehouse/Delta**。本组件负责其中可由 IaC 管理的基础资源与可选权限，不代表业务链路已部署。

## 当前架构边界

已授权的 Fabric 部署身份、可用 Capacity、现成 Landing 访问和已有 Terraform State Backend 是外部前置条件。基于原有 `components → modules → environments/*.tfvars` 设计继续开发，避免再增加以 Bootstrap/Tenant 拓扑为中心的长期 Root 或测试脚手架。新增环境使用独立 State Key，资源由可复用 Modules 管理。实施和后续真正的 Plan/Apply 验收见 [OpenSpec](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。

## 七个独立 Terraform Root

| Root | 职责 | 现有事实与执行限制 |
| --- | --- | --- |
| `storage` | 查找已有 Storage/Blob Landing，可选 RBAC | 以既有资源为前提，不把 lookup 当作新建 |
| `workspace` | Fabric Workspace 与可选成员关系 | 既有 `healthcare-omop` 手工 Workspace，必须核对 ID、State 与 Import 才能考虑接管 |
| `onelake` | Fabric Lakehouse 与可选 OneLake 数据访问规则 | IAM 预览功能默认不新增授权 |
| `notebook` | Fabric Notebook Item 基础资源 | 当前代码是主动失败的 Bootstrap，**不是业务 ETL** |
| `data-factory` | Fabric Data Pipeline Item 定义 | 并非独立 Azure Data Factory Account；没有真实 Notebook GUID 时使用 Fail Activity |
| `warehouse` | 可选 Fabric Warehouse | 不属于 OneLake-first MVP 必选前置资源 |
| `foundation-iam` | 可选 Resource Group 级共享角色绑定 | 不重复管理各组件专属权限 |

每个 `components/<component>/` 是独立 Terraform Root；`modules/<component>/` 保存实际资源定义。每个 Root 独立使用 `dev/<component>.tfstate`，**相同远程 State 不得通过第二份源码并行操作**。Root 间的先后依赖不会因为目录并列而自动执行。代码位置、环境参数、IAM 与安全占位源码的逐文件入口见 [CODE.md](CODE.md)。

## 当前验收边界

- **已存在**：七个 Root 和对应 Module 的 Git 源码；Self-Runner `azure-infra.yaml` 指向 `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`。
- **历史 Plan-only 验收**：2026-10-16 七个 Root 在新路径上对应的 GitHub Actions Plan Job 均为 SUCCESS；[独立 Run 证据](ARCHITECTURE.md#verified-plan-evidence)保留原始链接。Plan 成功不等于 Apply，也不意味着云端资源已创建。
- **尚未证明**：Workspace/Lakehouse 的实际资源采用、Azure/Fabric 所有权限、Notebook/Pipeline 业务执行、Blob 到 Delta 的数据加载及独立 E2E 对账。
- **操作安全**：Self-Runner 可选 `plan` 或 `apply`（默认 Plan），能力不等于授权。即使 Plan 也会访问云端及远程 State；未经单独批准不得触发。详见 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md) 与 [技术架构](ARCHITECTURE.md)。

**进一步阅读**：[源码地图](CODE.md) · [Terraform 技术架构与历史验收](ARCHITECTURE.md) · [Notebooks 组件](../notebooks/README.md) · [Pipelines 组件](../pipelines/README.md) · [当前项目状态](../../../engineering/status/PROJECT-STATUS.md)。
