# Fabric Workspace Scoped Terraform

## ADDED Requirements

### Requirement: Workspace-named independent Terraform roots

Terraform SHALL organize target Fabric resources under `fabric-workspace/<fabric-workspace-name>/<resource-type>/`, where each resource-type directory is a separate Terraform Root. The exact Fabric Workspace display name SHALL match both its parent directory and its selected non-default Terraform CLI Workspace. Terraform SHALL reuse generic modules from `modules/` and MUST NOT require a combined `fabric-environment` or Apply-All entry point.

#### Scenario: newly defined workspace

- **GIVEN** 当前已授权的 Fabric 部署身份，新增目录 `fabric-workspace/healthcare-qa/workspace/`
- **WHEN** 在 Terraform CLI Workspace `healthcare-qa` 执行该 Root 的 Plan/Apply
- **THEN** 使用共享 Workspace Module 创建 display_name 为 `healthcare-qa` 的 Fabric Workspace，不触发其他资源 Root

#### Scenario: no root definitions at workspace folder level

- **GIVEN** 资源归档于 `fabric-workspace/healthcare-omop/`
- **WHEN** 检查目录结构
- **THEN** 工作空间本体定义只出现在 `workspace/` 子目录，Notebook/Lakehouse 等不在 Workspace 父目录混写 Root 文件

### Requirement: One independent State per resource type and Fabric Workspace

Each Fabric resource Root SHALL use a stable resource-type-specific AzureRM Backend base key and SHALL select the target Fabric-named non-default Terraform CLI Workspace. The resulting State MUST be distinct from other resource types, other Fabric Workspace names, and historical States. The Workflow SHALL NOT concatenate an extra Fabric name into the base key while ALSO using named Terraform CLI Workspaces.

#### Scenario: same workspace, different resource types

- **GIVEN** 选择 Terraform CLI Workspace `healthcare-omop`
- **WHEN** 依次执行 `workspace` 与 `onelake` Roots
- **THEN** 二者使用不同基础 Backend Key，不共享一份 State，不覆盖旧 `dev/*.tfstate`

#### Scenario: same resource type, different workspaces

- **GIVEN** 同为 `onelake` 资源类型，但 Workspace 名为 `healthcare-omop` 和 `healthcare-qa`
- **WHEN** 分别初始化与选择各自 Terraform CLI Workspace
- **THEN** AzureRM Backend 维护独立 State，切换名称不会修改另一 Workspace 的资源

### Requirement: Downstream resource depends on Workspace State Output

The Workspace Root SHALL publish its actual Fabric Workspace GUID as an Output. Any independent downstream Fabric resource Root requiring that GUID MUST read the correct Workspace Root State via `terraform_remote_state` using the matching Backend base key and Terraform CLI Workspace. Downstream Plan MUST fail clearly if the Workspace State Output does not exist.

#### Scenario: Workspace not created yet

- **GIVEN** `healthcare-omop/workspace/` 还没有成功 Apply 或未产生有效 ID Output
- **WHEN** 运行 `healthcare-omop/onelake/` 的 Plan
- **THEN** 明确阻止创建 Lakehouse，而不是允许硬编码 Workspace ID 或自动创建第二个 Workspace

### Requirement: Shared infrastructure stays outside Fabric Workspace roots

Azure Storage, Capacity, account/tenant-level Connection and shared IAM SHALL be organized under `shared-infra/<resource-type>/` with independent Backend State and may use a separate Workflow. The default deployment MUST reuse existing Capacity and MUST NOT create new billable Capacity without separate authorization.

#### Scenario: Storage provisioning

- **WHEN** 操作 `shared-infra/storage/`
- **THEN** 不需要强行选择或创建某个 Fabric Workspace，且不修改 `fabric-workspace/healthcare-omop/` 的 State

### Requirement: Notebook and Pipeline are owned exclusively by fabric-cicd

The new Terraform Roots and their Workflows MUST NOT create, update or delete Fabric Notebook or Pipeline Items. `fabric-cicd` SHALL own the complete lifecycle, definitions and published code of these Items, preventing Terraform and CI/CD from managing the same Item.

#### Scenario: publish a new Notebook

- **GIVEN** Terraform 已成功创建 Workspace 和所需 Lakehouse
- **WHEN** 用户新增 Notebook 业务资源
- **THEN** 只通过 `fabric-cicd` 创建和发布，不运行旧 `components/notebook` Terraform Root

### Requirement: No historical code/state migration prerequisite

A fresh workspace-scoped Terraform deployment SHALL use newly authored Root directories and new Backend namespaces. It MUST NOT require migration of the old `components/` source, historical State move, or adoption of a disposable manually created Workspace as a prerequisite. Name conflicts with cloud resources SHALL fail explicitly for operator resolution; live deletion is never implicit.

#### Scenario: pre-existing Portal Workspace

- **GIVEN** Fabric Portal 仍存在一个同名但未由新 State 管理的 Workspace
- **WHEN** 新 Root 尝试创建该 Workspace
- **THEN** 给出可处理的资源冲突而不是静默导入、覆盖或删除；用户可以自行决定是否在 Portal 删除

### Requirement: Resource-scoped operation and deployment order

The Fabric Terraform Workflow SHALL accept a validated workspace name, resource type and `plan` or `apply`, execute exactly the selected existing resource Root, and provide output evidence. The documented creation order SHALL put Workspace before Workspace-dependent resources and `fabric-cicd` after Terraform infrastructure; no Apply-All is required.

#### Scenario: deploy only Lakehouse

- **GIVEN** Workspace Root 已完成且 ID Output 可读
- **WHEN** 用户选择 `workspace=healthcare-omop`、`resource=onelake`、`operation=apply`
- **THEN** 只针对 Onelake Root 执行经过审查的 Plan/Apply，不重新 Apply Workspace/Warehouse
