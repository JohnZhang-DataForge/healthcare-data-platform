---
status: active
scope: azure-fabric-terraform-technical-architecture-and-plan-evidence
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Fabric Terraform — 技术架构、安全约束及历史验收

> **本页的旧 Root/Module、State、Plan 证据是现存实现事实。** 新目标架构沿用已存在的 `components → modules → environments` 分层，详见 [Module-first Architecture](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)；新的开发进度见 [Change Tasks](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。以下过时的 Bootstrap/Tenant 实施决策不覆盖新目标。

> **已完成组件文档收口（ACTIVE）**。依据现存 Terraform `README.md` 与 `docs/ARCHITECTURE.md` 的长期有效技术内容、Git 源文件和历史 GitHub Actions Run 整理；本次仅为文档静态审查，**没有读取当前云端资源/Remote State，也没有运行 Plan/Apply**。功能概述见 [README.md](README.md)，实际文件入口见 [CODE.md](CODE.md)。

## Root/module implementation model

```text
Self-Runner azure-infra.yaml (component / dev / operation)
      ↓
azure-fabric/infra-terraform/components/<component>/
  versions.tf / providers.tf / modules.tf / iam.tf / variables.tf
  outputs.tf / environments/dev.tfvars
      │ source = ../../modules/<component>
      ↓
azure-fabric/infra-terraform/modules/<component>/
  main.tf / iam.tf / outputs.tf
      ↓
已有 Azure Blob remote State: johnzhang/tfstate/dev/<component>.tfstate
```

七个独立 Root：`storage`、`workspace`、`onelake`、`data-factory`、`notebook`、`warehouse`、`foundation-iam`。每个 Root 有独立 State，但跨 Root 的执行顺序**不会自动推导和 Apply**。Fabric Item Root 通过工作流变量获取已存在 Workspace GUID，不应虚构 ID 或引用尚未 Apply 的别的 Root 输出。旧 `components/iam` 与 `modules/iam` 已被 `foundation-iam` 替代；历史 `dev/iam.tfstate` 不自动迁移、清理或假设为空。

## IAM and existing resource boundaries

| Root | 真实权限定义 | 当前规则 |
| --- | --- | --- |
| `storage` | [Storage IAM](../../../../azure-fabric/infra-terraform/modules/storage/iam.tf) | 查找现有 Blob；`blob_role_assignments={}` 时不新增授权 |
| `workspace` | [Workspace IAM](../../../../azure-fabric/infra-terraform/modules/workspace/iam.tf) | 可选 Workspace Admin/Member/Contributor/Viewer；`role_assignments={}` 默认不新增 |
| `onelake` | [OneLake IAM](../../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) | `fabric_onelake_data_access_security` 是预览功能；`data_access_roles={}` 时不授予 |
| `data-factory` / `notebook` | [Pipeline IAM](../../../../azure-fabric/infra-terraform/modules/data-factory/iam.tf) · [Notebook IAM](../../../../azure-fabric/infra-terraform/modules/notebook/iam.tf) | 不虚构 Fabric provider 尚不支持的 Item 级授权 |
| `warehouse` | [Warehouse IAM](../../../../azure-fabric/infra-terraform/modules/warehouse/iam.tf) | Workspace 角色与 SQL `GRANT/REVOKE` 分属不同流程 |
| `foundation-iam` | [Foundation IAM](../../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf) | 只负责可选 RG 级共享绑定；`shared_role_bindings={}` 默认为空 |

- **Entra 权限主体**：角色分配使用 Entra **object ID**，不等同于 application/client ID；仅有 RG Contributor 不保证拥有 `Microsoft.Authorization/roleAssignments/write`。这些模块不创建新的 Azure 自定义 Role Definition。
- **原有资源不归新配置自动所有**：已有 OMOP Resource Group、`johnzhang` Storage、`landing` / `tfstate` 容器、Bootstrap Service Principal 和历史 Portal 建立的 RBAC/OIDC 需分别核对所有权；不得因 Plan 而重建或重复授予。
- **Workspace 采用**：既有 `healthcare-omop` 是手工创建；需核验真实 Workspace ID、容量/Trial、角色与 Terraform State。现有工作流在 State 缺少 `module.workspace.fabric_workspace.current` 时阻断 `workspace` Apply；**名字相同并不等于已经 Import**。
- **权限面互不等价**：Azure RG 管理平面 RBAC、Blob 数据平面 RBAC、Fabric Workspace 权限和 OneLake 数据访问是不同体系；OneLake 预览支持可通过 [Provider](../../../../azure-fabric/infra-terraform/components/onelake/providers.tf) 配置，但不能凭 Terraform 文件断言租户支持或已生效。

## Remote State, OIDC and workflow boundaries

远程 Backend 使用已有 Azure Storage Account `johnzhang` / container `tfstate`，通过 Azure AD/GitHub OIDC 身份认证。七个 State Key 保持：`dev/storage.tfstate`、`dev/workspace.tfstate`、`dev/onelake.tfstate`、`dev/data-factory.tfstate`、`dev/notebook.tfstate`、`dev/warehouse.tfstate`、`dev/foundation-iam.tfstate`。不能把 State、planfile、真实 `.env`、证书、Secret 或个人数据提交 Git，也不能把 Runner 临时磁盘作为 State 的永久位置。

OIDC Federated Identity 绑定的是 **Self-Runner** 身份及相应 ref，而不是 Healthcare 源代码仓库。正式 [Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 检出 Healthcare `main` 并记录实际 Source SHA。输入选择受限；`operation=plan|apply`，默认 Plan，不提供 Destroy。执行包含 Terraform format、Remote Backend init、validate、saved Plan；单独授权的 Apply 使用保存的 Plan 并阻断替换/删除计划。**技术防护不构成实际授权**，且 Plan 自身会访问云端、读/锁定远程 State。

两个旧 Self-Runner Smoke Workflows 使用固定历史 Healthcare Commit，并非新的标准执行入口；旧 One-Off OIDC/Blob Smoke Root 已从当前源码移除，不应复原。已经从 `main` 退役的 `azure/infra-terraform/` 副本只在 Git 历史中可追溯，**不得从历史版本重建第二个共用 State 的执行目录**。

## Fabric Bootstrap and source ownership

目前 Terraform 能描述的是 **Fabric Item 的基础壳与失败保护**，不是可工作的业务 ETL。[Notebook module](../../../../azure-fabric/infra-terraform/modules/notebook/main.tf) 引用 [`notebook-content.py`](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py)，使用 `export_id` / `manifest_uri` 参数但故意抛出 `RuntimeError`。Data Pipeline module [`main.tf`](../../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) 在 `notebook_id=""` 时使用 [Fail Activity](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)，真实 GUID 存在时可选择 [Notebook Activity 模板](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json)，但这仍**不代表已实现 Notebook 业务入库**。

`azure-fabric/workspaces/healthcare-omop/` 是留给 Fabric Git 原生 Item 的源码区域，真实 Item 必须保留 Fabric 生成的 `.platform` 等文件，并明确 Git Integration 与 Terraform Item 的**唯一交付权属**，避免两个机制覆盖相同 Item。仓库中尚未实现本地 PG Exporter、Blob 不可变 READY 发布、云端幂等 Delta Loader 或独立跨平台对账；Warehouse 可选，Fabric Trial Capacity 也不是这些 Root 所负责创建。

## Verified Plan evidence

以下是有界的**历史 GitHub Actions 结果**，不构成 2026-10-18 Azure 实时状态或 State 实测。

| 时点 | 对象 | 原始证据 | 仅证明 |
| --- | --- | --- | --- |
| 2026-10-15 OIDC/Backend | `storage` | [Run 38761100632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632) | 原有 Storage 查询、Backend、Plan，无 Apply |
| 2026-10-15 IAM 改造 | `foundation-iam` | [Run 38767227655 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655/attempts/2) | 共享授权为空时的 Plan |
| 2026-10-15 Provider 修正 | `onelake` | [Run 38797932758 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38797932758/attempts/2) | `microsoft/fabric 1.13.0` 解析，计划增加一个 Lakehouse |
| 2026-10-15 MVP Plans | `onelake`、`notebook`、`data-factory` | [Run 38799966270](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270) · [Run 38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550) · [Run 38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221) | 每项 Plan PASS，分别报告 1 add / 0 change / 0 destroy，无 Apply |
| 2026-10-16 新路径回归 | 全部七个 Root | 下方单项 Run | 七个 Plan Job 均 SUCCESS，未要求 Apply |

**New-path Plan-only runs（2026-10-16 EDT）：**

- `storage`：[38988729752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988729752)
- `workspace`：[38988731519](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988731519)
- `onelake`：[38988732887](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988732887)
- `data-factory`：[38988734473](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988734473)
- `notebook`：[38988735923](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988735923)
- `warehouse`：[38988737433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988737433)
- `foundation-iam`：[38988738899](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988738899)

七个 Job 的命名为 `plan / <component> / dev`，各自结论为 SUCCESS；对应的 [受控批量触发 Run 38988718305](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988718305) 也成功。上述记录中的准确 `add/change/delete` 数量需从各自保存的 Plan 日志读取，**不得从 Job 成功状态推断**。

## Deployment and data boundaries

- Apply 前独立核实真实 Workspace ID/容量、现有 Blob、IAM principals、State 与可能已存在的 Fabric Items；State 为空不意味着 Azure 上不存在对应资源。
- `storage`、`workspace` 的既有资源采用问题须独立处理；OneLake Lakehouse、Notebook 和 Pipeline 是提出的 MVP Item，Warehouse 及新建 Azure Data Factory Account 并非必选。
- 只读 Exporter 需要一致性快照、不可变 Manifest/Hash；Fabric Workspace 权限不自动赋予 Azure Blob 数据读取权限。
- 完成标准必须有真实 PostgreSQL 导出、Azure Blob READY 发布、Notebook/Delta 幂等写入及独立对账的可审计证据；Plan、Item 壳或部分 Git 文件均不代表 E2E。
- 任何实际运行操作均遵守 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)，本文件本身不构成操作许可。
