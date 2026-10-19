# Tasks

> **Active / Stage 0**：先冻结实现边界，再进行小步代码 PR；不得执行任何 Terraform init/plan/apply/destroy 或 Azure/Fabric 写操作。PR 必须绑定本 Change 并更新对应 Task。

## 1. Baseline and safety

- [x] 1.1 核实已批准架构、PR #247 离线 Preflight Main 合并和 PR #248 归档，确认旧 State/Workspace/Storage 保护约束。
- [x] 1.2 核对 Terraform Root/Module/Provider 版本和 Self-Runner `azure-infra.yaml` 当前身份映射；取得真实源码审计结论。
- [x] 1.3 锁定新环境的独立 Root/State Key、Tenant A Backend vs Tenant B Provider 输入、认证选择及负向测试方案。

## 2. Terraform offline implementation

- [ ] 2.1 独立环境 Backend 配置与双身份参数，附旧 `dev` State、跨环境冲突、无效或 Secret 输入的 fail-closed 单测。
- [ ] 2.2 Workspace 与 Capacity attachment Terraform 配置及依赖/输出，验证现存 Workspace 不会被静默接管。
- [ ] 2.3 Lakehouse Terraform 配置和唯一资源所有权，确保 fabric-cicd 不重复管理。
- [ ] 2.4 基于 Provider 已验证 Schema 添加 Azure Blob Connection Root/Module，隔离 Reader 的 Tenant A 与部署身份 Tenant B。
- [ ] 2.5 更新源码 CODE.md/Runbook 和 CI，取得精确 HEAD 的离线验收。

## 3. Review and closeout

- [ ] 3.1 各小 PR 的 CI/源码审核通过并合并，记录 Main SHA/证据；未经单独授权不进行云端 Plan 或 Apply。
- [ ] 3.2 确认 Terraform 交付范围验收后按规定独立归档；真实跨租户连通/部署仍需其他 Change 和授权。

## 2026-10-19 Task 1.2 只读源码审计

- Healthcare Main 基线 `d0447d52d70a593503b6b8e26bd5b14db19a7261`；旧七 Root 无变化。workspace/onelake 的 `versions.tf` 统一为 Terraform `>=1.13.0,<2.0.0`、`microsoft/fabric ~>1.13.0`、`backend "azurerm" {}`；两者 Provider 均 `use_oidc=true`，OneLake 额外 `preview=true`。
- Workspace Module 目前创建 `fabric_workspace` 并引用 Capacity，OneLake Module 创建 `fabric_lakehouse`，`enable_schemas=true` 为创建时选项；不应在旧 State 中复用这些新环境参数。
- Self-Runner `JohnZhang-DataForge/Self-Runner/.github/workflows/azure-infra.yaml`（本轮只读）使用 `dw-runner-set`，只支持 `dev`，按 `$ENVIRONMENT/$COMPONENT.tfstate` 选择 State；`ARM_CLIENT_ID`/`ARM_TENANT_ID` 与 `FABRIC_CLIENT_ID`/`FABRIC_TENANT_ID` 都来源于同一 `AZURE_*` 变量；默认 Plan，但工作流也公开 Apply 选择。这是与设计中跨 Tenant 双身份和独立 State 不兼容的已证实差距。
- 后续实现必须独立于旧 `azure-infra.yaml` 建立新环境入口，确保 `fabric/<environment>/<component>.tfstate`，不得因配置字符串隔离便声称 Azure Blob RBAC 已隔离；身份分离/OIDC 真实验证仍需另行授权。
- 本轮没有调用 Terraform、GitHub Workflow dispatch、Azure/Fabric API 或读写 Remote State；完成的是 1.2 静态审计，不是 1.3 身份方案完成。

## Task 1.3 离线合同设计决策

- 在旧七 Root 和 Self-Runner `azure-infra.yaml` 之外新增独立 `fabric_deployment_target.py`，复用现有严格 JSON Preflight；新环境 State Key 固定在 `fabric/<environment>/{workspace,onelake,connection}.tfstate`，不得使用旧 `dev/*`。
- 显式传入 Backend Tenant A / Fabric Tenant B 和不同的 Client ID；即使属于同一 Tenant，Backend Operator 和 Fabric Deployer 仍应是不同身份。检查 ID 与批准的环境合同完全匹配；不将凭据写入 JSON。
- 只产生离线 Backend 参数摘要，暂不调用 `terraform init/plan` 或以脚本设置 OIDC；Tenant A RBAC 与 Tenant B Fabric 权限仍属于未授权的后续实测。新增正常及负向单元测试，由现有 Fabric Preflight CI 执行。
- Task 2.1 的实际 Terraform Root/Backend 及 Self-Runner 绑定尚未实现，不因本次纯 Python 合同完成而勾选。

## Task 2.1 — 第一批安全实现（离线配置生成）

- 新增 `fabric_backend_config.py` 和相应负向单测；使用 Task 1.3 已验证的 Tenant A/B 身份合同，给 workspace/onelake/connection 输出 AzureRM Backend `storage_account_name`、`container_name`、`key`、`tenant_id`、`client_id`、OIDC 标志的**纯文本预览**。
- 该 PR **只覆盖** Backend 参数生成与校验，不设置 Runner 身份，也没有 Terraform Root、`init/plan/apply/destroy` 或云端 State 读写；**2.1 保持未完成**，直到新 Root/身份接入及适用静态验收全部完成。

## Task 2.1 第二批：独立 Root Skeleton（PR 待验收）

- 在 `azure-fabric/infra-terraform/new-environments/{workspace,onelake,connection}/` 新建独立 Root：各自配置受版本约束的 `microsoft/fabric` Provider、Fabric OIDC 和 Partial `azurerm` Backend，**没有 Terraform Resource、Module、Data Source 或执行入口**。
- 新增非部署 README 和 fail-closed 的 Root 静态结构单元测试；扩展原有 Fabric Preflight CI 触发路径。
- 禁止使用旧 `components/` 的 `dev` State、不复用 Self-Runner 单租户 Workflow；实际 Backend Init/Provider 验证、Workspace/Lakehouse/Connection 实施仍未授权。**2.1 未整体完成**。

## Task 2.2 Workspace 第一批（PR 审查中）

- 新环境 workspace 资源定义加入显式创建允许开关，默认为 false；明确 HDP 环境命名、Capacity UUID、prevent_destroy 和输出 Workspace ID。
- 尚未进行真实资源存在性检查、State inventory、认证或 Terraform Plan/Apply。审批开关不构成资源不存在的证明，2.2 继续保留未完成。

## Task 2.3 第一批：Lakehouse 资源声明（PR 验证中）

- 新环境 `onelake/` 添加 schema-enabled 的 `fabric_lakehouse`、显式 Workspace UUID、环境绑定的 `HDP-<environment>-omop` 名称、`prevent_destroy`；`workspace_id_verified` 和 `lakehouse_creation_approved` 默认均为 false。
- 仅声明和静态检验依赖合同。两个布尔变量是独立人工审查的确认，不验证目标 Workspace 的真实归属、Fabric item 存在性或 State。实际 Apply/Plan、provider init、跨租户访问均未进行；Task 2.3 保持未完成。

## Task 2.4 — Provider Connection Schema 核对（第一批）

- 查阅 Microsoft Fabric Provider 1.13.x 官方 `fabric_connection` Schema 与 Fabric Connections REST API：确认资源及 Cloud/ServicePrincipal 顶层结构确实支持，且 Provider 部署身份不等于 Blob 数据源身份。
- `new-environments/connection/SCHEMA.md` 冻结资源定义前的阻断条件：目标 Tenant 的 Connector type/creation_method/parameters、Service Principal 或 Workspace Identity 凭据兼容性、原有连接库存与 Blob Reader 权限均待核实。
- 新增静态测试，强制该 Root 继续没有 `main.tf` 或 `fabric_connection` Resource，避免使用推测参数和 Secret 产生貌似可部署的代码。本次未进行租户 API 调用、Terraform Init/Plan/Apply/Destroy，**2.4 保留未完成**。
