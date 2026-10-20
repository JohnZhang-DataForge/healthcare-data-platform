# Fabric Module-first Environment Deployment

## ADDED Requirements

### Requirement: Externally prepared Fabric deployment prerequisites

Fabric Environment Terraform SHALL accept an already-authorized Fabric deployment identity, accessible existing Terraform Backend, usable Fabric Capacity and pre-authorized Landing data access as external prerequisites. Normal deployment MUST NOT require three new Entra applications, Tenant A/B topology selection, subscription creation or Storage Bootstrap.

#### Scenario: new authorized Fabric account

- **GIVEN** 一个新的、已经具备目标 Fabric/Capacity 权限且已配置 Landing 与 Backend 访问的部署身份
- **WHEN** 为其提供环境参数并执行 Terraform Plan
- **THEN** 可以使用已有 Module 规划目标平台，不需先建立独立 Seed Bootstrap 或重建 Storage

### Requirement: Module-first composable Fabric environment root

Terraform SHALL retain the `components → modules → environment configuration` model. One composable Fabric Environment Root SHALL reuse Workspace, Lakehouse and Connection modules, rather than duplicate resource definitions per account or environment.

#### Scenario: reuse modules for a second environment

- **GIVEN** 两套独立 Fabric 部署参数与已授权身份
- **WHEN** 分别选择其 Environment 运行相同的 Root
- **THEN** 不需要修改 Module 资源定义，即可规划第二套 Workspace/Lakehouse/Connection

### Requirement: Distinct Terraform state keys for environments

Every Fabric Environment deployment SHALL use a distinct explicit Backend State Key. It MUST NOT automatically adopt, overwrite or migrate existing `dev/*.tfstate` or old Fabric Root resources.

#### Scenario: sharing backend without state collision

- **GIVEN** 两个 Fabric 环境共享已有的 Terraform Backend Container
- **WHEN** 初始化各自的环境组合 Root
- **THEN** 分别使用 `fabric/<environment>/platform.tfstate` 且不改变另一个环境的 State

### Requirement: Exclusive owner of Fabric platform and business resources

Terraform SHALL own the agreed Fabric platform Resources including Workspace, its role assignments, Lakehouse and Connection. In this deployment path, `fabric-cicd` SHALL own Notebook and DataPipeline business definitions. Resources of unknown prior ownership MUST NOT be implicitly imported, replaced or destroyed.

#### Scenario: deploy infrastructure and business items

- **GIVEN** Terraform 已创建并读回目标环境的 Platform Resource IDs
- **WHEN** 使用部署结果发布 Notebook 和 Pipeline
- **THEN** 业务发布使用对应环境的真实 IDs，并不与 Terraform 同时管理相同 Fabric Item

### Requirement: Verified real deployment evidence

The project MUST distinguish architecture decisions, static CI, real Terraform Apply, Fabric API readback and business E2E evidence. A documents-only change SHALL NOT be reported as deployed infrastructure.

#### Scenario: architecture PR complete without cloud tests

- **GIVEN** 仅合并了新的设计和 OpenSpec Change
- **WHEN** 汇报平台实施状态
- **THEN** 明确表示架构已更新、代码未重构、真实 Apply 与 E2E 尚未执行
