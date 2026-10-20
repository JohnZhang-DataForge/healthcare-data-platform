# Fabric Infrastructure Bootstrap

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
