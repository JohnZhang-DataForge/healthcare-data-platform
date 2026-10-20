---
status: active
scope: fabric-environment-module-first-target-architecture
decision_date: 2026-10-20
implementation_status: design-agreed-code-refactor-pending
---

# Fabric Terraform 环境部署架构 — Module-first / Environment-driven

> **当前目标设计，优先于旧 Bootstrap / A=B/A≠B 方案。** 本文记录 2026-10-20 用户最终确认的长期架构；设计已确认，但代码重构、真实 Terraform Apply 和 Fabric E2E **均未据此验收**。实施任务入口：[OpenSpec simplify-fabric-environment-iac](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。

## 1. 核心目标和前置条件

**给一个已经能部署目标 Fabric 资源的账号、可用 Capacity、已有且可读写的 Terraform Remote State Backend、预先授权可读取的 Landing 数据源，选择一个环境配置，以同一套 Terraform 代码部署和管理一整套 Fabric 平台。** 来第二个已授权 Fabric 账号或第二套部署环境，只换 Provider/登录配置、环境参数和独立 State Key，不复制、不修改 Module 源码。

前置条件由环境 Owner 提供，不归正常 Fabric Environment Terraform Apply 创建：Azure Subscription 和 Fabric 使用资格、初始管理员账号及授权、Capacity 的使用/分配资格、现有 Blob Landing 的访问身份/网络、Terraform Backend 的现存 Storage/Container 与运行身份的读写/锁定权限。**Fabric Administrator 角色本身不等于拥有 Azure Storage RBAC、所有 Capacity 分配权或 Backend 写入权**；要求的是已实际授权的部署主体，而不强制同一个账号持有所有外部权限。

- Azure/Fabric 订阅注册、Trial 开通、管理员首次授权和费用许可不属于此 Terraform 项目。
- Landing 与 `tfstate` 只是外部配置；Terraform 不管理它们的创建、删除和业务数据。
- `A=B`、`A≠B` 是部署参数可能出现的 Tenant 关系，**不是两个架构、两个 Bootstrap Mode，更不是需要分别开发的 Module**。任何支持的跨 Tenant 认证限制只在 Provider、Backend、Connection 的认证边界处理。
- Fabric Capacity 默认引用已有可用 ID；可选购买付费 F SKU 不属于常规 Environment Apply，不得因缺 Capacity 自动计费。

## 2. 必须沿用已有 Azure-Infra 的三层架构

旧项目中真实存在 `components/<component>/modules.tf` 调用 `../../modules/<component>`，Root 具有 Provider、版本、Backend、`variables.tf`、`outputs.tf`、`environments/dev.tfvars`；这个 **Root → Module → Environment Configuration** 结构是长期标准，不应被直接写资源的 `new-environments/` 取代。

**目标目录（尚未实施）**：

```text
azure-fabric/infra-terraform/
├── components/
│   └── fabric-environment/       # 一个环境组合 Root
│       ├── versions.tf
│       ├── providers.tf
│       ├── backend.tf
│       ├── main.tf               # 只调用 modules，并处理资源依赖
│       ├── variables.tf
│       └── outputs.tf
├── modules/
│   ├── workspace/                # 复用现有定义及 Workspace IAM
│   ├── lakehouse/                # 由 modules/onelake 整理
│   └── connection/               # 从 new-environments/connection 提取
├── environments/
│   ├── dev.tfvars
│   └── trial-lab.tfvars
├── tests/
└── tools/                       # 仅有实际用途的工具
```

- **Root** 负责 Provider 登录、Backend Key、环境输入、Modules 编排及 Outputs；Module 内**不**声明 Backend、登录主体和固定环境/账号/Blob 资源名。
- **Module** 负责可复用的真实 Fabric Resource、可选 IAM、变量验证及输出。现有 `modules/workspace` 的 Workspace + Role Assignment、`modules/onelake` 的 Lakehouse 实现是优先复用来源，连接功能需建正式可复用 Module。
- **Environment** 仅声明非秘密差异，如 Workspace 名称、Lakehouse 名称、Capacity ID、Landing Connection 参数。用户凭据、Token、Secret 不写入 Git 或普通 tfvars。
- **单组合 Root** 可一次 Apply 根据资源依赖创建 Workspace、角色、Lakehouse、Connection；不用为每个环境复制一组 Root。Terraform 不负责 Notebook/Pipeline 业务定义的发布。

## 3. Fabric 与业务资源唯一所有权

| 资源 | 最终所有者 | 说明 |
| --- | --- | --- |
| Fabric Workspace / Workspace Role Assignment | Terraform `module.workspace` | 复用旧 Module/IAM；不要重复资源地址 |
| Fabric Lakehouse | Terraform `module.lakehouse` | 从原 `onelake` Module 整理职责 |
| Fabric Azure Blob Connection | Terraform `module.connection` | 接收已获授权的 Landing Connection 配置，不创建 Landing |
| Capacity | 外部可用资源 ID | 常规 Terraform Root 只引用，不创建付费 SKU |
| Notebook / DataPipeline | `fabric-cicd` | GitHub 是业务定义来源；通过 Terraform Outputs 注入部署目标 GUID |
| 现有 Landing、Remote State | 外部资源 Owner | 平台 Root 无 Create/Replace/Delete/Import 权限 |
| 已有旧 Workspace/State/Notebook 占位 | 原资源/State Owner | 不静默接管；后续核对后明确迁移或保留 |

需要的 Fabric Workspace Identity、Blob Reader 或其他连接身份按**实际 Fabric Connector 认证方式**配置，不强制三套新 Entra Application 作为平台 Bootstrap。预授权 Landing 指的是新环境实际读数据时有合法可用凭据/访问路径，不能只凭 Fabric Administrator 名称推断权限。

## 4. 多环境 State 模型与重复部署

推荐未来一个组合 Root 对应一个环境 State：`fabric/<environment>/platform.tfstate`，保存在已有 Backend Container。比如 `fabric/lab-a/platform.tfstate` 和 `fabric/lab-b/platform.tfstate`。仅更换 `.tfvars` 却保持同一个 Key **不是**创建新环境，会导致对已有资源的更新/销毁。State Key 名称隔离不等于 Azure RBAC 隔离。

现有旧 `dev/*.tfstate` 与已有/可能存在的 `fabric/<environment>/{workspace,onelake,connection}.tfstate` 都**不得被假设为空或自动迁移**。组合 Root 的新 State 与已有 Root 的 Terraform Resource Address 不同：先核对真正的 State/云端持有者，再选择**独立新环境**或单独审查 Import/State Move，不能直接 Apply 让 Terraform 创造重复资源，也不能因文件删除执行 Destroy。

## 5. 真正的部署流程

1. 使用有权限的 Fabric 部署账号（本地 `az login` 或经授权的 CI 身份）和环境参数准备 Provider；已有 Landing/Backend/Capacity 配置已满足前置条件。
2. 为目标环境提供独立 State Key，实际运行 `terraform init`、`validate`、`plan`。在 Plan 中检查已有对象、删除或替换动作；未授权破坏性动作停止。
3. 在批准后对**同一目标环境 State** `terraform apply`，从真实 Fabric API 读回 Workspace/Lakehouse/Connection 和所需访问权限。
4. 使用 `fabric-cicd` 根据 Terraform Outputs 发布 Notebook 与 Pipeline；再做真实 Landing → OneLake 数据运行、对账和幂等检查。**离线 Provider Init/Validate 成功不等于真实 Apply 或 E2E 成功。**
5. 增加第二个环境或账号时，配置新的认证与 `.tfvars` 和 State Key，再执行同一套代码，不改 Modules；验证不影响第一环境。

GitHub Self-Runner 只是这些相同操作的自动化执行入口，先复用旧 `azure-infra.yaml` 的有效设计，运行能力通过测试后再迁移。不把额外 OIDC Bootstrap 开发作为当前手动 Terraform 测试的阻塞前置。

## 6. 现有源码判断与清理顺序

- **保留复用**：`components/* → modules/*` 的正确分层，现有 `modules/workspace` 的 IAM、`modules/onelake` 的 Lakehouse 实现，以及有用的 Provider/State 测试。
- **整合重写**：`new-environments/workspace`、`new-environments/onelake` 的重复 `resource` 定义不能长期与 Module 同时存在；`new-environments/connection` 要提取成可复用 Module。
- **停止作为强制前置**：`bootstrap/identity` 的三 App/SPN/OIDC、`bootstrap/storage` 的新 Blob/Backend、复杂双 Tenant Profile/Seed/批准 Gate；付费 Capacity 创建是按需独立工作，不应被普通部署隐式触发。
- **清理时间**：先实现单一 Root/Modules 和新环境真实验证，再审查并批量删除不再引用的 Bootstrap 工具、重复 Root、测试及 CI；旧 `components/` 可能由 Self-Runner 真实引用，**未经 Workflow/State 审计不能先删**。删除 Git 源码不等于删除云端资源；历史可通过 Git 和旧 OpenSpec 追溯。

**长期架构在本文件；代码实现的任务/状态/验收只记在 [新 OpenSpec Change](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)，不在这里做第二份 Task 清单。**
