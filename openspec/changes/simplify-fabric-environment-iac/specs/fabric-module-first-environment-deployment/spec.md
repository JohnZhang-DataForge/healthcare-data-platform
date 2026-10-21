# Fabric Module-first Environment Deployment

## ADDED Requirements

### Requirement: Externally prepared Fabric deployment prerequisites

Fabric Environment Terraform SHALL use the currently authorized Fabric deployment identity, existing accessible Terraform Backend, available Capacity and pre-authorized Landing access. The current delivery MUST NOT require multi-account Account Profiles, cross-tenant switching, three new Entra applications, subscription creation or Storage Bootstrap.

#### Scenario: deploy using existing Fabric account

- **GIVEN** 当前已具备必要 Fabric、Capacity、Landing 和 Backend 权限的部署身份
- **WHEN** 为当前账号选择 Fabric Workspace 并运行 Terraform
- **THEN** 复用已有 Modules，无需额外初始化多账号/Seed Bootstrap

### Requirement: Terraform CLI Workspace and Fabric Workspace names match

Each managed Fabric Workspace in the current account SHALL map to a dedicated non-default Terraform CLI Workspace with the **exact same name**. The existing first Fabric Workspace is named `healthcare-omop`; DEV is its environment label, not an alternative resource name. The composed Root SHALL pass `terraform.workspace` to the Workspace Module as the Fabric display name.

#### Scenario: select current existing workspace

- **GIVEN** 已有 Fabric Workspace `healthcare-omop`
- **WHEN** 选择 Terraform CLI Workspace `healthcare-omop`
- **THEN** Terraform 使用完全相同的 Fabric Workspace display name，而不生成 `dev` 或 `HDP-Dev` 名称

#### Scenario: reject default workspace deployment

- **GIVEN** Terraform CLI Workspace 为 `default`
- **WHEN** 尝试真实部署本项目 Fabric 环境
- **THEN** 部署入口明确阻止在 `default` Workspace 创建目标 Fabric Workspace

### Requirement: Module-first composable Fabric environment root with outputs

Terraform SHALL retain `components → modules → configuration` and compose Workspace/IAM, Lakehouse and Connection from reusable Modules. The Root SHALL expose actual workspace name and resolved Fabric Workspace/Lakehouse/Connection IDs via outputs; dependent Modules SHALL use resolved IDs instead of hardcoded Workspace IDs.

#### Scenario: deploy Lakehouse after workspace resolution

- **GIVEN** Terraform Workspace `healthcare-omop` 对应已被正确管理的 Fabric Workspace
- **WHEN** 规划 Lakehouse/Connection
- **THEN** Lakehouse 引用 Workspace Module 输出的真实 ID，Root Outputs 暴露真实资源标识供下游消费

### Requirement: Terraform CLI Workspace state isolation

Each non-default Terraform CLI Workspace SHALL use isolated State in the configured AzureRM Backend. The deployment MUST verify real Backend key derivation and MUST NOT overwrite legacy State.

#### Scenario: second workspace in current account

- **GIVEN** 当前账号使用同一个 AzureRM Backend，已有 Terraform Workspace `healthcare-omop`
- **WHEN** 创建另一个非 default Terraform CLI Workspace 并运行相同 Root/Modules
- **THEN** 新 Workspace 与 State 独立，旧 `dev/*.tfstate` 和 `healthcare-omop` State 均不被覆盖

### Requirement: Explicit adoption of existing Fabric resources

The existing Fabric Workspace `healthcare-omop` MUST be inventoried before the first deployment. Its prior State owner MUST be reviewed, and Import or State Move MUST be explicit where needed. Partial resource operations MUST NOT implicitly remove unrelated managed resources.

#### Scenario: existing workspace not managed by new root state

- **GIVEN** Fabric Workspace `healthcare-omop` 已存在，但新组合 Root State 不包含它
- **WHEN** 准备首次 Apply
- **THEN** 先审查并执行明确的 Import/State Move 路径，不能直接重复创建该 Workspace

#### Scenario: select a subset of resources

- **GIVEN** 当前 State 已管理 Workspace 和 Lakehouse
- **WHEN** Workflow 只请求检查或部署 Connection
- **THEN** 不得因资源选择参数从配置中移除已管理的 Workspace 或 Lakehouse

### Requirement: Exclusive ownership and real deployment evidence

Terraform SHALL own Workspace/IAM, Lakehouse and Connection. `fabric-cicd` SHALL own Notebook/DataPipeline business definitions; no two deployment systems may manage the same Item. Docs/static validation MUST NOT be reported as live Apply, Fabric API readback or business E2E.

#### Scenario: architecture-only revision

- **GIVEN** 仅更新当前 Active OpenSpec 和架构文档
- **WHEN** 汇报进度
- **THEN** 明确写为设计已定、Terraform 实施与真实部署未验证

### Requirement: Canonical single-root and retired legacy deployment sources

The active Fabric IaC source SHALL contain exactly one deployable Root
(`components/fabric-environment`) with exactly the reusable Workspace, OneLake
and Connection Modules. Old standalone Roots, `dev.tfvars` and Terraform-owned
Notebook/Pipeline placeholder modules SHALL NOT be invoked by the canonical
runner. Historical remote State SHALL remain untouched during source cleanup.

#### Scenario: no duplicate Fabric deployment entry

- **GIVEN** 当前仓库 Main 的 Fabric Terraform 和 Self-Runner Workflow
- **WHEN** 执行 Fabric 资源部署
- **THEN** 只调用单组合 Root，不存在旧 workspace/onelake Root 的并行入口

### Requirement: New same-name Fabric Workspace without duplicated Terraform roots

The canonical runner SHALL accept a bounded, validated Workspace name; a new
non-default Terraform CLI Workspace SHALL be created/selected with the same
name, using common input defaults or a versioned per-Workspace nonsecret tfvars
file. Existing `healthcare-omop` SHALL NOT be created again and requires
explicit State adoption before Plan/Apply.

#### Scenario: deploy a fresh workspace

- **GIVEN** 用户选择当前 Fabric 账号内此前不存在的 `healthcare-qa`
- **WHEN** 在唯一 Root 下执行 Plan 然后单独执行 Apply
- **THEN** Terraform CLI Workspace、Fabric Workspace 名称相同且 State 独立
