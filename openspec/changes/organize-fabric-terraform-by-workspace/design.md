# Design

## Context

当前 Main 中 `azure-fabric/infra-terraform/components/` 是七个旧独立 Roots 加一个 `fabric-environment` 组合 Root；`modules/` 包含可复用 Workspace、Onelake、Warehouse、Storage、Connection 等资源定义，还含已决定停止管理的 Notebook/Pipeline 占位实现。Self-Runner `azure-infra.yaml` 仍引用旧 Roots。**这些是当前源码事实，不是新架构已实现的证据。**

用户最终决定：不要 `fabric-environment`、不要 Apply-All，按真实 Fabric Workspace / Resource 目录逐个 Plan/Apply；预先存在的 Workspace 如阻碍新建可以由用户在 Fabric Portal 手工删除，不以历史资源 Import/State Migration 作为开发任务。

## Decisions

1. **两组部署目录 + 一个公共 Modules 目录**：
   - `fabric-workspace/<name>/<type>/`：Fabric Workspace 本体、Lakehouse/OneLake、Warehouse 等；每个 `<type>` 是一个独立 Terraform Root。
   - `shared-infra/<type>/`：Azure Storage、Capacity、租户/账号级 Connection、共享 IAM；由单独 Root/Workflow 管理。
   - `modules/<type>/`：通用 Terraform Module；沿用/修正被新 Root 调用的通用资源定义，不复制业务逻辑。
2. **名称一一对应**：`<name>` = Terraform CLI Workspace = Fabric Workspace `display_name`；当前目标拼写严格为 `healthcare-omop`。`dev` 是业务环境标签而非 Workspace 名；Root 不允许 `default` Workspace 在 Fabric 工作空间资源上生效。
3. **目录与资源配置**：Workspace 的父目录（如 `healthcare-omop/`）不放 `workspace.tf` / `main.tf`；`workspace/` 子目录才负责创建 Workspace 与 IAM。其他 `onelake/`、`warehouse/` 等为平级独立 Roots，`main.tf` 调用 `../../../../modules/<type>`（具体相对路径写代码时按真实目录校核）。每个 Root 保留版本、Provider、变量、Output 和非秘密 `terraform.tfvars`；IAM 仅在需要时有 `iam.tf`。
4. **独立 State，两层标识不重复拼接**：Fabric Workspace 资源 Roots 采用固定的**资源类型基础 Backend Key**，例如 `fabric-workspace/workspace.tfstate`、`fabric-workspace/onelake.tfstate`、`fabric-workspace/warehouse.tfstate`。不同 Fabric Workspace 通过非 default Terraform CLI Workspace 独立 State；同名不同资源类型通过不同 Backend Key 独立 State。实际 AzureRM Blob Key 的 Workspace 前缀在首轮 Init/State 查看时验证，**不额外把 `<name>` 拼进 Key，避免两次隔离重复**。Shared Infra 使用另一组独立基础 Key（如 `shared-infra/storage.tfstate`），由其自身工作流/State 管理。
5. **跨 Root 依赖必须是 Remote State Output**：`<name>/workspace/` Root 导出 `fabric_workspace_id`（来自 Workspace Module 的真实 GUID）。`<name>/onelake/` 等 Root 使用 `data "terraform_remote_state" "workspace"`，指向相同 AzureRM Backend、基础 Key `fabric-workspace/workspace.tfstate` 及**同名** CLI Workspace `<name>`，读取 `outputs.fabric_workspace_id`。不能用独立 Root 之间的 `module.workspace.workspace_id` 直接引用。若上游 State / Output 不存在，后续资源的 Plan 必须失败，不得造假 GUID、创建替代 Workspace 或静默跳过。
6. **依赖执行顺序**：首次部署先保证共享 Backend/Capacity/必要授权可用（如果已经存在就复用）；再 `workspace plan→apply`；再按需 `onelake` / `warehouse` 等 `plan→apply`；最后单独 `fabric-cicd` 创建和发布 Notebook/Pipeline，并进行数据链路验证。不做自动串行 Apply-All。
7. **Notebook/Pipeline 退出 Terraform**：新 `fabric-workspace/` 树不得含 Terraform `fabric_notebook`、`fabric_data_pipeline` 或为它们建立资源 Root。旧 Modules 的对应源码作为待退役的历史实现保留直到独立安全清理；Self-Runner 新入口不得再路由旧 Notebook/Pipeline Root。Item 的整个生命周期和源码交付由 `fabric-cicd` 负责。
8. **原有代码和 State 不迁移**：不把旧 `components/` 文件搬到新路径，不运行 `terraform state mv`，不改 `dev/*.tfstate` 或旧 `fabric/platform.tfstate`。在新目录调用原有通用 Modules；Workflow 指向新 Root 与新 Backend。新建同名资源若遇到 Portal 旧对象冲突，返回清楚错误，由用户决定手工删除或另选名称；不强制执行历史 Import 审计/自动覆盖。
9. **Workflow 简化**：Fabric 基础设施 Workflow 选择 `workspace_name`（校验且必须是仓库实际目录）、`resource_type`（对应目录）和 `operation=plan|apply`；执行目录由输入构成但必须防止路径穿越，Plan 保存并审查后 Apply。Shared Infra Workflow 单独选择 `resource_type`。不恢复 `dev` 下拉框或 Apply-All；静态 CI 验证 Backend Key 一致、Root 输出/跨 State 依赖与资源唯一所有权。
10. **权限和成本**：Fabric 管理员账户是 Fabric 层的实施起点，不自动意味着拥有 Azure Subscription RBAC、Blob Data-plane、Backend 或 Capacity 权限。需要为实际部署账号/Runner 配置对应授权；Capacity 已有优先复用，不能自动增加持续计费资源，Secrets 不进入 Git。
11. **不修改云端的设计变更**：本轮只形成设计/任务/PR 证据。后续用户授权开发后再测试真实 Init、Plan、Apply；不提前删除既有 Workspace，也不把已经有用户可删除的云端 Workspace 当成架构障碍。

## Example target tree

```text
azure-fabric/infra-terraform/
├── modules/
│   ├── workspace/          # 通用 Workspace/IAM
│   ├── onelake/            # 通用 Lakehouse/OneLake
│   ├── warehouse/
│   ├── connection/
│   ├── storage/
│   └── foundation-iam/
├── fabric-workspace/
│   └── healthcare-omop/   # 精确的 Fabric Workspace display_name
│       ├── workspace/     # 独立 Root + 独立 State
│       │   ├── main.tf
│       │   ├── iam.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   ├── providers.tf
│       │   ├── versions.tf
│       │   └── terraform.tfvars
│       ├── onelake/       # 同结构，读取 workspace remote state Output
│       └── warehouse/     # 同结构，按需启用
└── shared-infra/
    ├── storage/
    ├── capacity/          # 可选，默认不创建
    ├── connection/
    └── foundation-iam/
```

此处是**目标目录**，不是本次 PR 已创建的源码；未来新增真实 Workspace 如 `healthcare-qa`，需新增其相应资源 Root 目录并在 Workflow 输入该名称。

## Risks / compatibility / recovery

- **State 依赖顺序**：若 Workspace Root 未成功 Apply，`terraform_remote_state` 无有效 Output，下游失败是预期保护；不能绕过。
- **并发**：同一个 Fabric Workspace 中不同资源 Root 有独立 State，但仍可能通过共享 Workspace/Capacity 发生 API 并发冲突；Workflow 需要合理限制并发。
- **单一真实资源所有权**：同一个 Workspace GUID 不得被两个活动 State 管理；首次新建时使用新 State，如 Portal 仍有同名 Workspace 应显式报错，不自动 Import/Destroy。
- **成本与删除**：可以人工清理可丢弃的历史云端资源，但 Portal 删除与 Terraform State 删除是两回事；不是本次文档 PR 的自动操作。
- **迁移策略**：本次不回写旧 State/旧代码。若用户以后确认完全不用旧 Roots，可单独清理 Git 旧源码与 Workflow 入口，仍不能随意删除 Backend Blob State；通过 Git 历史恢复源码即可回滚文档方向。
- **安全审查**：非秘密 `terraform.tfvars` 可以提交；凭据只能使用 Runner Secret/OIDC/Key Vault，`apply` 前检查计划有无 Delete/Replace。
