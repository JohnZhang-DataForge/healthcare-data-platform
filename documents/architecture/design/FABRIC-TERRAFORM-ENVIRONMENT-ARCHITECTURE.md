---
status: active
scope: fabric-terraform-workspace-scoped-target-architecture
decision_date: 2026-10-20
implementation_status: design-approved-runtime-pending
---

# Fabric Terraform 基础设施 — 按真实 Workspace / 资源类型组织

> **最新有效设计，取代旧 \`fabric-environment\` / Apply-All 方案。**
> 实施任务以 [OpenSpec Workspace-scoped Change](../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md) 为准。
> 本文描述目标，**当前 Main 仍是旧 \`components/\` 结构；新目录、Workflow、Azure/Fabric 资源尚未部署**。

## 1. 核心决定

- **一个 Fabric Workspace，一个同名父目录**：\`fabric-workspace/healthcare-omop/\`；对应的 Terraform CLI Workspace 也叫 \`healthcare-omop\`。不再使用 \`dev\` 作为命名映射。
- **每个资源类型目录独立 Terraform Root**：\`workspace/\`、\`onelake/\`、\`warehouse/\` 等独立 Plan/Apply，具有各自的 Remote State。**Workspace 父目录不直接放 \`workspace.tf\`**。
- **Modules 是通用资源模型**：新 Root 调用已有 \`modules/workspace\`、\`modules/onelake\` 等。具体实例、变量、IAM 和 Outputs 由各 Resource Root 管理，不复制 Provider 资源实现。
- **没有组合环境 Root**：不开发 \`fabric-environment\`、Apply-All、组件自动发现或复杂注册表。新增实际 Fabric Workspace = 添加同名父目录及需要的 Resource Roots，再逐项 Plan/Apply。
- **共享基础设施独立**：\`shared-infra/\` 与 \`fabric-workspace/\` 同级，管理 Storage、Capacity、账号/租户级 Connection、共享 IAM，可独立 Workflow。Capacity 默认为复用，不自动生成额外计费资源。
- **Notebook 和 Pipeline 仅由 \`fabric-cicd\` 管理**：包含资源创建、更新、删除与代码发布；Terraform 新部署入口不含这两种 Item，避免双重管理。
- **不迁移旧代码/旧 State**：新建目录直接开发，Workflow 切换到新目录。现有 \`components/\` 和所有旧 State 均保持原状，之后如需清理另行批准。已有 Portal Workspace 可由用户按需手工删除，不作为新架构的 Import/迁移障碍。

## 2. 目标源码结构

\`\`\`text
azure-fabric/infra-terraform/
├── modules/                           # 共享通用 Terraform 模型
│   ├── workspace/
│   ├── onelake/
│   ├── warehouse/
│   ├── storage/
│   ├── connection/
│   └── foundation-iam/
├── fabric-workspace/
│   └── healthcare-omop/               # 真实 Fabric Workspace = Terraform CLI Workspace
│       ├── workspace/                 # 创建 Workspace 和 IAM（先执行）
│       │   ├── main.tf
│       │   ├── iam.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   └── terraform.tfvars       # 非秘密参数
│       ├── onelake/                   # 创建 Lakehouse；读取 workspace State Output
│       │   ├── main.tf
│       │   ├── iam.tf                 # 适用时
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   └── terraform.tfvars
│       └── warehouse/                 # 可选；结构相同，独立 Plan/Apply
└── shared-infra/
    ├── storage/
    ├── capacity/                       # 可选，创建须单独获费用许可
    ├── connection/
    └── foundation-iam/
\`\`\`

目录树是**目标示例**而非实际文件清单。新增 \`healthcare-qa\` 时新增同名父目录及所需资源子目录；资源未配置就不创建。Notebook/Pipeline 的项目代码继续在 Fabric Item / \`fabric-cicd\` 的独立领域中管理，不放入此 Terraform 树。

## 3. Terraform Workspace、远端 State 与 Outputs

Terraform CLI Workspace 名按父目录确定，且必须与目标 Fabric Workspace 的 display_name 完全一致。各 Resource Root 的 Backend **基础 Key**按资源类型固定，例如：

| 根目录 | Terraform CLI Workspace | AzureRM Backend 基础 Key |
| --- | --- | --- |
| \`healthcare-omop/workspace/\` | \`healthcare-omop\` | \`fabric-workspace/workspace.tfstate\` |
| \`healthcare-omop/onelake/\` | \`healthcare-omop\` | \`fabric-workspace/onelake.tfstate\` |
| \`healthcare-omop/warehouse/\` | \`healthcare-omop\` | \`fabric-workspace/warehouse.tfstate\` |
| \`healthcare-qa/workspace/\` | \`healthcare-qa\` | \`fabric-workspace/workspace.tfstate\` |
| \`shared-infra/storage/\` | 单独管理 | \`shared-infra/storage.tfstate\` |

同一资源类型的不同 Workspace 由 **Terraform CLI Workspace** 实际隔离；不同资源类型由不同 Key 隔离；**不要再将 \`<workspace-name>\` 额外拼进基础 Key**。第一次上线用 Terraform CLI/Backend 读回实际 Blob Key 派生方式。State 隔离不等于 Azure 权限隔离。

\`workspace/\` Root 通过 \`outputs.tf\` 导出真实 \`fabric_workspace_id\`。因为其他目录是**不同的 Terraform Roots**，\`onelake/\`、\`warehouse/\` 等必须用 \`terraform_remote_state\`（指向 Workspace Root 的 Backend Key 和同名 CLI Workspace）读取 \`outputs.fabric_workspace_id\`，而**不是**直接写 \`module.workspace.workspace_id\` 跨 Root 引用。

没有有效 Workspace State/Output，后续 Root 的 Plan 直接失败。共享 Storage/Capacity 等如需跨 Root 关联，也通过明确的 Outputs/已验证资源 ID 获取，不制造隐藏部署顺序。

## 4. Workflow 和部署顺序

**Fabric 资源 Workflow**：输入 \`workspace_name\`、\`resource_type\`、\`operation=plan|apply\`；只接受真实存在、且匹配规则的 Git 目录；执行对应 Root，设置同名非 default Terraform CLI Workspace 和本资源固定 Backend Key。一次操作只执行一个 Root；不调用 Apply-All。Plan 及代码 SHA/State 信息保存到 Run 证据，Apply 前验证无非预期 Delete/Replace。

**Shared Infra Workflow**：可独立选择 \`storage\`、\`connection\`、\`foundation-iam\` 等，不要求 Fabric Workspace 名称。即使以一个 Fabric 管理员账号为起点，也须具备实际订阅、容量、Blob/Backend 访问权限；这些是部署权限要求，不恢复多账号 Bootstrap 系统。

推荐首次部署顺序：

1. 准备已有或授权创建的 Backend / Capacity / Landing / IAM（\`shared-infra\`，按需）。
2. \`fabric-workspace/<name>/workspace/\`：Plan → Apply → 校验 GUID Output。
3. \`fabric-workspace/<name>/onelake/\`：读取 Workspace Output → Plan → Apply。
4. \`warehouse/\` 等其他资源：按需独立 Plan → Apply。
5. \`fabric-cicd\`：创建并发布 Notebook/Pipeline，随后做 Landing → OneLake 真实业务 E2E。

不需要一个“自动执行所有资源”的工具；新增资源类型时新建 Module（需要时）与相应 Resource Root，更新部署顺序即可。

## 5. 现有对象与旧源码

当前已存在的 \`healthcare-omop\` 不是新设计必须 Import 的对象。用户拥有可丢弃的测试资源，可以选择在 Fabric Portal 手工清除同名旧对象后由新 State 建立新资源；**本 Change 不自动删除**。如果旧同名云端资源仍在，新建应明确报冲突而不是强行覆盖。

旧 \`components/\` / \`components/fabric-environment/\` 和旧 \`dev/*.tfstate\`、\`fabric/platform.tfstate\` 是历史源码/State，不作搬迁、修改或新 Workflow 执行路径。后续历史清理可独立审批。新 Terraform 目录不管理 Notebook/Pipeline Item，旧 Terraform 占位实现不再作为交付机制。

## 6. 测试与交付边界

文档 PR 只证明目标设计已冻结，不证明源码已实现。后续必须：模块/Root \`fmt\`、\`init -backend=false\`、\`validate\`、State 隔离及 Remote Output 缺失失败测试；真正 OIDC、Backend、Capacity、Plan/Apply、Fabric GUID 读回、重复 Plan 稳定；最后 \`fabric-cicd\` 与业务 E2E。所有真实操作必须由合适的工作流和相应授权触发。
