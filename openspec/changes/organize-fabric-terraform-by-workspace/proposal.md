# Proposal

## Why

用户明确收敛 Microsoft Fabric 基础设施开发：**不要 `fabric-environment`，不要 Apply-All，不迁移原有 Component Root 源码或远端 State**。旧的 `components/<resource>/` 按资源类型组织，与真实 Fabric Workspace 的组织方式不一致；此前强制接管已存在 `healthcare-omop` 以及反复改造组合 Root 阻碍数据平台推进。

期望的起点是**当前有权使用的 Fabric 管理/部署账号**，新增 Workspace 直接新增同名目录，执行独立 Terraform Plan/Apply；账号仍须具有所使用 AzureRM Backend、Capacity 及 Azure 数据访问的相应权限。已有 `healthcare-omop` 不是迁移前置：用户可按实际需要在 Portal 删除，未来按全新基础设施重新创建；本文不授权自动删除。

## What Changes

- **真实 Workspace 即目录**：新增目标 `azure-fabric/infra-terraform/fabric-workspace/<fabric-workspace-name>/<resource-type>/`；准确名称首选 `healthcare-omop`。根级 Workspace 目录只装资源类型子目录，不再放 `workspace.tf` 或 `fabric-environment` 编排文件。
- **每种资源独立 Root**：`workspace/`、`onelake/`、`warehouse/` 等各自定义 `main.tf`、`iam.tf`（适用时）、`variables.tf`、`outputs.tf`、`versions.tf`、`providers.tf`、`terraform.tfvars`（仅非秘密）；继续复用 `modules/<resource>/` 通用模型。
- **同名映射但不共享 State**：真实 Fabric Workspace、目录名称与 Terraform CLI Workspace 名一致。每种资源采用独立、稳定的 AzureRM Backend 基础 Key，非 default Terraform CLI Workspace 隔离同一资源类型的不同 Fabric Workspaces。禁止把同一实际云端资源放到两个 States。
- **Workspace ID 依赖**：先 Plan/Apply `<name>/workspace/`，以 Output 导出 Workspace GUID；其他独立 Roots 通过对应 Terraform CLI Workspace 的 `terraform_remote_state` 输出引用 GUID；不复制/硬编码 Workspace ID，也不假装同目录普通 Output 能跨 Root 自动访问。
- **共享资源独立管理**：`shared-infra/` 与 `fabric-workspace/` 同级，用于 Azure Storage、Capacity、账号/租户级 Connection、共享 IAM 等；可以通过不同 Workflow 部署，不强制归属任意 Fabric Workspace。Capacity 默认为复用，创建额外计费资源必须另行明确授权。
- **唯一 Item 所有权**：Notebook、Pipeline（含 Item 创建、修改、删除及内容发布）全部交由 `fabric-cicd`；Terraform 新部署入口不声明这两类 Item。旧 Modules/Components 中的相关源码不作为未来部署入口。
- **简单执行**：Self-Runner Workflow 只需要 Workspace 名、资源类型、Plan/Apply；可使用独立 Shared Infra Workflow；不实现 Apply-All、自动发现、跨账号 Profile、复杂注册表。
- **新的源码，新 State**：直接创建新目录及新 Backend 命名空间，Workflow 改指向新目录。旧 `components/`、`components/fabric-environment/`、旧 State 只作历史保留/以后单独清理，不迁移、不导入为必经步骤。当前手工 Workspace 若与新建名称冲突，由用户按需手工处理。

## Capabilities

### New Capabilities

- `fabric-workspace-scoped-terraform`：按真实 Fabric Workspace 名称和资源类型管理独立 Terraform Roots、State 与依赖输出，通过单资源 Plan/Apply 创建基础设施，Notebook/Pipeline 由 `fabric-cicd` 唯一管理。

### Modified Capabilities

- 先前 `simplify-fabric-environment-iac` 的 Apply-All、组合 Root、先 Import 现有 Workspace 才可开展开发的实施方向由此 Change **取代**，先前记录保留历史证据，不再作为后续实现授权。
- 原多账号 Bootstrap、旧七个 `dev.tfvars` Root 部署方案不作为新部署入口。

## Impact

本轮**仅编写长期架构及 OpenSpec Change 文档**，执行 PR/CI 评审，不改变 Terraform 源码、Self-Runner Workflow、Fabric/Azure 资源或远端 State。后续由本 Change 的未完成任务逐步新建源码、切换 Workflow、真实 Plan/Apply 和验收。旧代码不迁移，旧 State 不修改。
