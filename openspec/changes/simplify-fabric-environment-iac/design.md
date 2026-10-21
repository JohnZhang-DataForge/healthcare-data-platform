# Design

## Context

原有七个 Component Roots 通过 `modules.tf` 调用可复用 `modules/`；`modules/workspace` 已实现 `fabric_workspace` 与角色分配，`modules/onelake` 已实现 `fabric_lakehouse`。当前 Fabric 账号已存在人工创建的 Workspace **`healthcare-omop`**（DEV 用途）。之前设计的多账号 Account Profile、账号切换和“Environment 名称 + 独立 State Key”方案不再是本轮实施目标。已清理的 `bootstrap/`、`new-environments/`、`tools/`、`tests/` 不恢复。

## Decisions

1. **仅当前账号**：使用当前已授权的 Fabric 管理/部署身份。Azure Subscription、Capacity、现有 Landing 访问、AzureRM State Backend 和必要授权由环境预先提供。Workflow 不接受多账号选择；不开发 Account Profile、Tenant A/B 模式、三 Entra App 或 Bootstrap。将来迁移其他账号需人工重新配置认证与独立 State，不在本 Change 测试。
2. **名称一一对应**：一个 Terraform **CLI Workspace** 对应当前 Fabric 账号中的一个 Fabric Workspace；`terraform.workspace` 值应与 Fabric Workspace 的准确 `display_name` 一致。第一个为 `healthcare-omop`；不能改叫 `dev`，也不得使用默认 `default` Workspace 进行真实部署。后续 QA/PROD 的物理名称另行配置或创建，不在文档中当作已有资源。
3. **Module-first**：新建 `components/fabric-environment` 作为单组合 Terraform Root；Root 负责 Provider、Backend、tfvars、依赖和 Outputs，调用原有 `modules/workspace`、`modules/onelake`，必要时整理但不为改名而重命名资源地址；新增 `modules/connection`。不在 Root 重复定义 Fabric Resources。
4. **资源依赖与 Outputs**：Root 用 `workspace_name = terraform.workspace` 给 `module.workspace` 赋值；Lakehouse 使用 `module.workspace.workspace_id`；Root 至少输出 `fabric_workspace_name`、`fabric_workspace_id`、`lakehouse_id`、`connection_id`（适用时）。Output 只提供创建/读取后的值，不负责选择 Terraform Workspace 或初始化 Backend。
5. **State 约定**：沿用当前账号的现有 AzureRM Backend，单组合 Root 选择一个固定 Backend 基础 Key；Terraform 为**非 default CLI Workspace** 管理各自的远程 State 命名空间。具体 Blob Key 由 AzureRM Backend 实际规则生成并在测试中核验，不把 CLI Workspace 与 `fabric/<env>/platform.tfstate` 的人为 Key 双重组合。不得改变或覆盖原来 `dev/*.tfstate` 和其他独立 Root State；CLI Workspace 名称**不构成安全权限隔离**。
6. **已有 `healthcare-omop`**：先只读核对云端 Workspace GUID、当前 State 与历史 Root 所有权；若资源未在目标组合 Root State，按核对结果选择显式 Import 或经审查的 State Move。**不得为同名 Workspace 直接新建第二个资源，也不允许未经审查的 Replace/Delete**。Connection 的可用认证与 Landing Reader 权限须按真实 Provider/租户支持验证。
7. **Workflow 最小改造**：复用 `Self-Runner/.github/workflows/azure-infra.yaml`，部署身份针对当前账号，增加 Terraform Workspace 选择、必要配置文件映射与组合 Root Plan/Apply。首版优先 `Full Platform`；若提供资源选择，不得通过关闭其他 Module 或随意 `-target` 使已管理资源被移除；只能采用经测试不破坏同一 State 的操作方式。
8. **唯一资源所有权**：Terraform 管 Workspace/IAM、Lakehouse、Connection；`fabric-cicd` 管业务 Notebook/Pipeline。原独立 Roots 和占位 Item 未经核对不得静默接管。
9. **验收证据**：`fmt/init -backend=false/validate` 是静态验证；真实 Plan、Apply、Fabric API 读回、Landing 联通和重复 Plan 才构成部署证据。Apply 不会因本文而获得自动执行授权。

## Implementation phases

- D1：核实 Modules、旧 State 地址、已有 `healthcare-omop` 的实际资源和 Self-Runner 依赖。
- D2：增加 Connection Module、统一 Root、Terraform CLI Workspace 命名/配置、Outputs 与简单 CI；对 `default`、State 碰撞、部分资源非预期删除做测试。
- D3：在当前账号对已有 `healthcare-omop` 执行受控 Import/State Move（如需），真实 Plan/Apply、Fabric API 读回、连接 Landing 与再次 Plan。
- D4：扩展原 Self-Runner Workflow；同账号下使用另一个独立 Terraform/Fabric Workspace 验证复用，再接入 `fabric-cicd` 与真实业务 E2E。

## Risks and recovery

- 已有 Workspace 为人工创建，不能把 `terraform.workspace` 名称匹配误认为 Terraform 已自动导入资源；必须先确定拥有者与 State。
- Terraform CLI Workspaces 共享 Backend 配置和访问控制；环境级 State 隔离不等于 Azure RBAC/凭据隔离。若将来需要生产强隔离，必须另行评估独立 Backend。
- 当前 `providers.tf` 使用固定 OIDC，需按实际 Runner/本地 CLI 身份支持进行最小调整；不要假设管理员角色自动包含 Blob/Capacity/Backend 权限。
- 不提交任何 Credential/Token/Secret，不购买付费 Capacity；不得从设计文档推断已部署。
