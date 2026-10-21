# Design

## Context

已退役的七个 Component Roots 原通过 `modules.tf` 调用可复用 `modules/`；`modules/workspace` 已实现 `fabric_workspace` 与角色分配，`modules/onelake` 已实现 `fabric_lakehouse`。当前 Fabric 账号已存在人工创建的 Workspace **`healthcare-omop`**（DEV 用途）。之前设计的多账号 Account Profile、账号切换和“Environment 名称 + 独立 State Key”方案不再是本轮实施目标。已清理的 `bootstrap/`、`new-environments/`、`tools/`、`tests/` 不恢复。

## Decisions

1. **仅当前账号**：使用当前已授权的 Fabric 管理/部署身份。Azure Subscription、Capacity、现有 Landing 访问、AzureRM State Backend 和必要授权由环境预先提供。Workflow 不接受多账号选择；不开发 Account Profile、Tenant A/B 模式、三 Entra App 或 Bootstrap。将来迁移其他账号需人工重新配置认证与独立 State，不在本 Change 测试。
2. **名称一一对应**：一个 Terraform **CLI Workspace** 对应当前 Fabric 账号中的一个 Fabric Workspace；`terraform.workspace` 值应与 Fabric Workspace 的准确 `display_name` 一致。第一个为 `healthcare-omop`；不能改叫 `dev`，也不得使用默认 `default` Workspace 进行真实部署。后续 QA/PROD 的物理名称另行配置或创建，不在文档中当作已有资源。
3. **Module-first**：仅保留 `components/fabric-environment` 作为单组合 Terraform Root；Root 负责 Provider、Backend、tfvars、依赖和 Outputs，调用原有 `modules/workspace`、`modules/onelake`，不重写共享资源实现；保留 `modules/connection`。不在 Root 重复定义 Fabric Resources。
4. **资源依赖与 Outputs**：Root 用 `workspace_name = terraform.workspace` 给 `module.workspace` 赋值；Lakehouse 使用 `module.workspace.workspace_id`；Root 至少输出 `fabric_workspace_name`、`fabric_workspace_id`、`lakehouse_id`、`connection_id`（适用时）。Output 只提供创建/读取后的值，不负责选择 Terraform Workspace 或初始化 Backend。
5. **State 约定**：沿用当前账号的现有 AzureRM Backend，单组合 Root 选择一个固定 Backend 基础 Key；Terraform 为**非 default CLI Workspace** 管理各自的远程 State 命名空间。具体 Blob Key 由 AzureRM Backend 实际规则生成并在测试中核验，不把 CLI Workspace 与 `fabric/<env>/platform.tfstate` 的人为 Key 双重组合。不得改变或覆盖原来 `dev/*.tfstate` 和其他独立 Root State；CLI Workspace 名称**不构成安全权限隔离**。
6. **已有 `healthcare-omop`**：先只读核对云端 Workspace GUID、当前 State 与历史 Root 所有权；若资源未在目标组合 Root State，按核对结果选择显式 Import 或经审查的 State Move。**不得为同名 Workspace 直接新建第二个资源，也不允许未经审查的 Replace/Delete**。Connection 的可用认证与 Landing Reader 权限须按真实 Provider/租户支持验证。
7. **Workflow 单入口**：继续使用 `Self-Runner/.github/workflows/azure-infra.yaml`，部署身份针对当前账号，只接受一个 Fabric Workspace 名称与 inspect/adopt/plan/apply，不再提供旧 Component 或 dev 选择。全新 Workspace 用默认变量或按名匹配的非秘密 tfvars；已有 healthcare-omop 仅经显式 Import 后部署。不得使用任意 `-target` 隐式删除已管理资源。
8. **唯一资源所有权**：Terraform 管 Workspace/IAM、Lakehouse、Connection；`fabric-cicd` 管业务 Notebook/Pipeline。原独立 Roots 和占位 Item 未经核对不得静默接管。
9. **旧源码清理**：用户授权清理旧独立 Roots、闲置 Modules、旧 `dev.tfvars` 与占位 Notebook/Pipeline Terraform 实现。Git 历史保留旧源码；不通过 Git 删除/迁移历史 Remote State、云端对象或 RBAC。后续 State audit 使用只读 Backend 配置，不依赖旧 Root 源码。\n10. **验收证据**：`fmt/init -backend=false/validate` 是静态验证；真实 Plan、Apply、Fabric API 读回、Landing 联通和重复 Plan 才构成部署证据。Apply 不会因本文而获得自动执行授权。

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


## 本轮统一单 Root 实施补充

- `components/fabric-environment/` 是**唯一** Terraform Root；直接引用
  `modules/workspace`、`modules/onelake`、`modules/connection`。
- 旧的七个独立 Root + 五个不再被调用的 Modules 已从当前 Git 树删除；
  保留历史 Git SHA `20a6449000fe10eac642ab2dbcef37976339572b`，
  远端 `dev/*.tfstate` 不删除。
- 当前唯一人工已存在 Workspace 是 `healthcare-omop`；新 Workspace
  由 Runner 接收合规名字后选择/创建同名 Terraform CLI Workspace，并
  使用同一个 Root 创建同名 Fabric Workspace。
- 过时的 `dev`/Component Workflow 选择框删除；只保留 Workspace
  与 Operation。将来 Terraform CLI Workspace 仍不是权限隔离边界。
