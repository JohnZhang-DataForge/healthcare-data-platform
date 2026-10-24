# Fabric Multi-Environment Terraform

## ADDED Requirements

### Requirement: Isolated Fabric environment remote state

New-environment Terraform SHALL use unique `fabric/<environment>/<component>.tfstate` keys for `workspace`, `onelake` and `connection` in the existing `johnzhang/tfstate` container. It MUST NOT read or write existing `dev/*.tfstate` through the new environment deployment path. Offline validation SHALL reject mismatched names or unsafe keys.

#### Scenario: separate environment state targets

- **GIVEN** 一个有效环境合同，指定 `lab-b`
- **WHEN** 生成 Terraform 新环境的 Backend Key
- **THEN** 只产生 `fabric/lab-b/workspace.tfstate`、`fabric/lab-b/onelake.tfstate`、`fabric/lab-b/connection.tfstate`，并不改变旧 `dev` State

### Requirement: Explicit independent backend and Fabric deployer identities

Backend Tenant A and Fabric Tenant B SHALL be supplied independently. No code path SHALL assume a single `AZURE_TENANT_ID` or `AZURE_CLIENT_ID` covers both identities; sensitive credentials MUST NOT be committed to source or printed in CI logs.

#### Scenario: cross-tenant configuration validation

- **GIVEN** 一个新的 Fabric Tenant B 与原 Storage Tenant A
- **WHEN** 执行离线认证参数校验
- **THEN** 明确区分两种 Tenant 和执行主体，不在无授权条件下访问 Azure 或 Fabric

### Requirement: Single owner for Fabric control-plane resources

Terraform SHALL own only new-environment Workspace, Lakehouse and Blob Connection resources. Deployment MUST fail closed for unreviewed existing Workspace/State collisions. Notebook/DataPipeline belong to a later fabric-cicd Change and SHALL NOT be created by this new-environment Terraform path.

#### Scenario: preexisting workspace ownership unknown

- **GIVEN** 目标 Workspace 可能已存在但没有审核后的 Adopt/Import 决策
- **WHEN** 计划部署前检查资源所有权
- **THEN** 阻断自动接管或销毁，并要求独立核实与批准

### Requirement: Verified Bootstrap output handoff without legacy adoption

New-environment Workspace/Lakehouse/Connection Terraform SHALL accept only independently validated Backend, identity and (existing or approved newly created) Capacity outputs from the appropriate Bootstrap mode. It MUST NOT treat a design approval or a guessed environment value as authorization to create a paid Capacity or adopt existing Storage, Workspace or remote State. Infrastructure Bootstrap provisioning belongs to a separately governed Change.

#### Scenario: approved Capacity in a new account

- **GIVEN** 新 Fabric Tenant 使用 fresh-bootstrap 且 Capacity 已通过独立 SKU/region/cost approval 与库存验证
- **WHEN** 控制平面获取经过验证的 Capacity ID
- **THEN** 允许后续受控 Workspace 资源规划；在未批准新 Capacity 创建前不会自动购买资源

#### Scenario: legacy tenant reuse without ownership transfer

- **GIVEN** 当前 Tenant A→A′ 的 reuse-existing 环境合同和旧 `johnzhang` Storage
- **WHEN** 生成新环境 Terraform 输入
- **THEN** 旧 `dev/*.tfstate`、Landing、历史 Workspace 原样保留，未被默认 Import/Destroy/Replace

### Requirement: No implicit live operation

Static checks SHALL NOT invoke Terraform remote backend initialization, Terraform plan/apply/destroy, cloud API calls, or mutations of existing Storage, State and Fabric resources.

#### Scenario: PR-only validation

- **GIVEN** 一个修改新环境 Terraform 的 Pull Request
- **WHEN** 执行 PR CI
- **THEN** 只执行无云端副作用的格式、契约和静态测试，真实操作需要单独授权
