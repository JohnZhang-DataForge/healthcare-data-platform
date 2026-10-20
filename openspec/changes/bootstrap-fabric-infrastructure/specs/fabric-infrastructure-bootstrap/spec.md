# Fabric Infrastructure Bootstrap

> **HISTORICAL / SUPERSEDED DELTA**：旧 Bootstrap 要求不再是当前 Fabric 环境部署合同，按 [Module-first Change](../../../simplify-fabric-environment-iac/tasks.md) 开发。这里的历史 ADDED Requirements 不表示已同步成为生效的 Current Spec。

## ADDED Requirements

### Requirement: Explicit dual-mode Bootstrap ownership

Bootstrap SHALL accept only explicitly selected `reuse-existing` or `fresh-bootstrap` mode. It MUST fail closed for unknown existing resources, legacy `johnzhang` name collisions, unsafe State keys, ambiguous adoption and unreviewed cross-environment inputs. It SHALL NOT automatically Import, Adopt, Destroy or migrate legacy Workspace/Storage/State.

#### Scenario: reuse existing state without adoption

- **GIVEN** 当前 Tenant A→A′ 的已授权现有 `johnzhang/tfstate` 和历史 `dev/*.tfstate`
- **WHEN** 生成新环境 Bootstrap 合同
- **THEN** 仅引用现有 Backend 和独立目标 Key；不得重置、迁移或覆盖旧 State

#### Scenario: fresh Bootstrap has old account name

- **GIVEN** 环境选择 `fresh-bootstrap` 且新 Storage 的目标名称为 `johnzhang`
- **WHEN** 进行离线参数校验
- **THEN** 返回 HOLD，不生成可部署资源定义

### Requirement: Independent initial Bootstrap state

The fresh-bootstrap path SHALL create its Storage/Backend only after selecting an independently protected initial Bootstrap State. It MUST NOT attempt to initialize the not-yet-created Backend as its own initial backend or automatically migrate State without separate review.

#### Scenario: backend bootstrap cycle

- **GIVEN** 一个 fresh-bootstrap 目标 Backend 尚不存在
- **WHEN** 准备其第一次 Terraform 执行
- **THEN** 使用经过审查的独立 Bootstrap State；不对不存在的目标 Remote Backend 执行 Init

### Requirement: Separate identities and least-privilege OIDC

Bootstrap SHALL distinguish initial administrator Seed authorization from Backend Operator, Fabric Deployer and Blob Reader application identities. Provider Tenant A and Tenant B MUST remain independently configurable, and Backend and Fabric deployment Client IDs MUST differ even when A equals B. GitHub OIDC trust MUST be scoped to an approved repository Ref or protected Environment.

#### Scenario: identical application IDs

- **GIVEN** Backend Operator 与 Fabric Deployer 使用同一 Client ID
- **WHEN** Offline contract receives both identifiers
- **THEN** 拒绝配置；不授予凭据或访问云端

#### Scenario: untrusted Pull Request

- **GIVEN** 一个来自 PR 的未授权 Branch 请求云端部署权限
- **WHEN** 评估 OIDC subject 和 GitHub Environment
- **THEN** 不向其发放带写权限的 Bootstrap 或 Fabric 部署凭据

### Requirement: Paid Capacity creation is opt-in and separately authorized

Bootstrap SHALL support `capacity.mode=reuse-existing` by default and `capacity.mode=create-new` only for an approved paid SKU, Subscription, Region, cost estimate, owner and exact execution authorization. A configuration Boolean alone MUST NOT constitute a billing approval. Automatic Capacity Suspend/Resume is out of scope.

#### Scenario: paid Capacity flag without billing evidence

- **GIVEN** 环境请求创建新的 F SKU Capacity，审批旗标为 true，但缺少对应成本审批记录
- **WHEN** Offline Preflight/后续受控 Plan Gate 运行
- **THEN** 返回 HOLD，禁止创建或替换付费资源

#### Scenario: existing Capacity

- **GIVEN** 环境选择 reuse-existing 且提供有效的已核对 Capacity ID
- **WHEN** 生成 Bootstrap Outputs
- **THEN** 只引用已有 ID，不规划或创建付费 Capacity

### Requirement: Non-secret verified handoff and separate live approval

Bootstrap outputs SHALL omit secrets and SHALL identify source Tenant/identity, backend destination and Capacity ownership. Static checks MUST NOT claim real-world privileges or remote State vacancy. Init/Plan/Apply/cloud reads and writes SHALL remain separate authorized execution phases.

#### Scenario: offline successful contract

- **GIVEN** 完整且不含 Secret 的离线 Environment 配置
- **WHEN** 纯本地测试成功
- **THEN** 输出 `verified=false` 的非敏感目标摘要，明确 `remote_state_checked=false`、`terraform_executed=false`，不认证 Azure/Fabric


### Requirement: Current same-Tenant deployment SHALL preserve user-provisioned Storage and State

The CURRENT target SHALL use `reuse-existing`, with A=B and the approved subscription. It MUST preserve `johnzhang/landing`, `johnzhang/tfstate` and `dev/*.tfstate` while using only isolated new State keys. It MUST NOT depend on the old Fabric administrator account or manually provisioned Workspace. Local Seed State is transitional, with explicit recovery/migration before long-term use. Future A!=B SHALL remain configurable without blocking the current A=B deployment.

#### Scenario: current known Tenant/Subscription reused

- **GIVEN** 已确认同一 Tenant GUID `899a04e8-8d3d-486c-88a1-7bdeb22d5f1a`、Subscription `56107520-5920-4e96-9833-5441ded0a90c` 且 Enabled
- **WHEN** 生成当前环境 Profile 和 Identity Terraform Plan
- **THEN** Backend/Fabric 两个 Provider 可以使用相同 Tenant ID，但 App Client ID 必须不同；不得要求另一个 Tenant ID 或旧 Fabric 子账号 CLI 会话

#### Scenario: existing storage remains external to Bootstrap

- **GIVEN** 当前选择 `reuse-existing`、固定 `johnzhang/landing` 和 `johnzhang/tfstate`
- **WHEN** 执行 Bootstrap Identity Plan / downstream Plan
- **THEN** 不创建、更名、Import、Replace、删除既有 Storage/Container/Landing 数据，也不触碰旧 `dev/*.tfstate`；新组件只能指向单独经库存核查的 `fabric/<environment>/<component>.tfstate`

#### Scenario: previous manually created Workspace is not a dependency

- **GIVEN** 历史 Fabric Workspace、`johnzhang-fabric` 子账号和原先授权都存在或曾存在
- **WHEN** 部署新 IaC Fabric 环境
- **THEN** 通过新的 Entra 应用/OIDC/RBAC 和独立 Workspace 名创建，不把旧 Workspace/旧账号作为必需参数，亦不自动删除原对象

#### Scenario: future A!=B configuration

- **GIVEN** 将来 Fabric Tenant 与 Blob Tenant 不同
- **WHEN** 使用已明确提供且经真实权限验证的 Tenant/Provider 配置
- **THEN** 可以单独验证/扩展跨 Tenant 支持；不能以此要求当前 A=B 路径等待或重复做 Tenant 发现
