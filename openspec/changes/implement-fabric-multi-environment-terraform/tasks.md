# Tasks

> **Active / Stage 0**：先冻结实现边界，再进行小步代码 PR；不得执行任何 Terraform init/plan/apply/destroy 或 Azure/Fabric 写操作。PR 必须绑定本 Change 并更新对应 Task。

## 0. Revised architecture approval (2026-10-19)

- [x] 0.1 用户通过 **Bootstrap as Code + Terraform + GitHub Actions + fabric-cicd** 修订目标，支持 `reuse-existing` 与 `fresh-bootstrap`。容量支持 Terraform 引用或**显式授权后新建**；**本期不实现自动 Suspend/Resume**。
- [ ] 0.2 以单独的 Bootstrap OpenSpec Change 冻结首次管理员 Seed、身份/Group/OIDC、RBAC、Backend State 初始化、Storage 两模式、Capacity 费用门禁与回滚/离线测试；此项属于后续独立实施，不使本 Change 的 Task 2.1–2.5 自动完成。
- [ ] 0.3 Bootstrap 和 Fabric Root 的**非敏感 Outputs/变量衔接合同**：来源 Tenant/身份与 Backend 真实库存确认、旧 `johnzhang`/State 拒绝接管、Capacity ID 与账单授权证明；须在后续离线源码 PR 实施。
- **修订的权限边界**：本 Change 仅维护已声明 Workspace/Lakehouse/Connection 及静态校验，Bootstrap 新建需独立 OpenSpec 和单独的真实 Azure 写操作授权。设计通过≠允许付费 Capacity 创建/Apply。

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

## Task 2.4 第二批：离线 Supported Connection Types 元数据检查

- 新增 `tools/fabric_connection_metadata.py`：使用**预先取得的**官方 `supportedConnectionTypes` JSON 响应，按显式给定的 connector type、creation method、credential type 检查支持情况，并提取参数名称及是否必填。拒绝未处理分页、重复或不完整元数据、未经支持的 ServicePrincipal/WorkspaceIdentity，不推断 Blob connector 的具体值。
- 新增 Python 单测并接入 Fabric Preflight CI。单测只使用虚构连接类型作为模拟输入，不代表真实 Tenant 支持该类型。
- 该工具不请求访问令牌、不会调用 Fabric API，也不处理真实 Secret。目标 Tenant 元数据、云端 Reader 凭据及 RBAC 尚未验证，`fabric_connection` 资源继续保持未实现；2.4 不勾选。

## Task 2.4 第三批：Connection Metadata 合同加固

- 根据微软 REST API 官方字段，离线校验器增加 `dataType` 枚举与 `allowedValues` 校验，以及 `--user-controlled-code` 对 `supportedCredentialTypesForUsageInUserControlledCode` 的独立许可检查。连接本身可创建不代表可以供 Notebook 等执行用户代码的 Item 使用。
- 完全离线的负向单元测试覆盖未知类型、格式错误、重复 allowed values、Notebook 权限缺失等；不查询租户、不访问 State、不执行 Terraform。Target Tenant Blob Connector 真实元数据与数据读取主体仍待核实；Task 2.4 继续不勾选。

## Task 2.4 第四批：用户 AzureBlobs API 元数据回归

- 用户在当前 Azure CLI 会话中成功调用 Fabric Supported Connection Types API，返回 `type=AzureBlobs`、`creationMethod=AzureBlobs`、必填 `account` 和 `domain` (Text)，ServicePrincipal/WorkspaceIdentity 同时支持，且 ServicePrincipal 允许用户代码使用。由于先前 `az login --tenant YOUR_FABRIC_TENANT_ID` 失败，**响应所属 Tenant 尚未确认**，不可据此授权部署。
- 修复合法 API 响应 `allowedValues: null` 被错误拒绝的问题；添加来自提供的非敏感元数据的回归单测。仍未创建 Connection Terraform resource，未请求或保存 Token，不调用 Azure/Fabric，也未执行 Terraform。
- 下一步需核实当前 Azure CLI Session Tenant、目标 Tenant 一致性、`account`/`domain` 具体允许值与认证策略及真实 Connection/Blob 权限；Task 2.4 保留未完成。

## 2026-10-19 认证拓扑修正（A→A′ / A→B）

- 已根据 Entra Default Directory 截图与 Azure CLI 的同一 Tenant ID 确定：当前 Storage/Fabric 是同一 Tenant 内的两个用户；用户账号不是自动化 Service Principal。当前部署目标采用 A→A′，未来 A→B 保留原有跨租户兼容。
- Preflight 和 Target 增加 `identity_topology` 输出：Tenant ID 相同为 `same-tenant`，否则 `cross-tenant`；不以拓扑模式降低 Client ID 必须独立、Profile 租户匹配、禁止旧 State、审批默认拒绝等限制。新增两模式离线回归测试。
- 此次仅源代码和设计修正；不改旧 Terraform Root、Self-Runner、现有 State、Workspace，也不执行任何 Terraform/Azure/Fabric 实际操作。真正 OIDC/RBAC 与跨租户数据读取仍须单独验证。

## Task 2.4 第五批：Provider v1.13 AzureBlobs Connection Root（本 PR 仅离线）

- 将锁定版本 `microsoft/fabric v1.13.0` 的官方 tag 文档确认为字段依据：`fabric_connection` + `ShareableCloud` + `AzureBlobs/AzureBlobs`，参数 `account`、`domain`；Provider 支持 `service_principal_secret_reference` 和 `WorkspaceIdentity`。参考：<https://github.com/microsoft/terraform-provider-fabric/blob/v1.13.0/docs/resources/connection.md>。
- 在隔离的 `new-environments/connection/` 添加受保护 `fabric_connection.azure_blob`、变量、ID 输出。ServicePrincipal 仅引用已经存在的 Fabric Key Vault Connection 的 Secret 名称/版本，不在 Terraform 源码、State 输入、JSON 或 CI 中注入 Secret 值。WorkspaceIdentity 为显式可选但需独立审查的模式。
- 所有创建/库存/元数据/domain/RBAC/模式审批默认为 false；固定现有 Storage Account 为 `johnzhang`，domain 必须独立提供，禁止从测试值推断。新资源带 `prevent_destroy`，无 Storage、IAM、Role Assignment、Import 或数据源写入。
- 更新 Root 静态测试、专门的默认拒绝/身份隔离/防 Secret 回归测试、Fabric Preflight CI 和非部署文档。真正后端 Init/Plan/Apply、凭据授予、Remote State 空位、Connection 现存库存、真实端点与 Workspace Identity 的可用性尚未授权或验证；**Task 2.4 保留未完成**，并不能把静态测试当云端验收。

## Task 2.5 第一批：静态格式/安全 CI 与人工 Runbook（离线 PR）

- Connection Root 新增共同 `backend_operator_client_id != fabric_deployer_client_id` 前置条件：对 ServicePrincipal 和 WorkspaceIdentity 两种 Blob Reader 方式均适用，而不是仅由 SP 分支约束；补充静态负向测试验证该条件在分支之前执行。
- Fabric PR CI 新增 GitHub-hosted Terraform 1.13.0 **`fmt -check -diff`**（只检查 Connection Root、仅解析格式，无 Terraform Init/Plan/Apply/Destroy、无 Provider 下载）；再新增独立单测限制该 CI 不得执行云端命令、使用 OIDC 写权限或输出凭据。其余测试继续不触发云端。
- 将人工证据表加入 `documents/engineering/operations/FABRIC-ACCOUNT-BOOTSTRAP-RUNBOOK.md`：确认 Tenant A→A′ / A→B、三应用身份、Key Vault 引用、Storage Blob Data Reader、AzureBlobs domain、现存连接及 State Key 库存、OIDC、独立 Plan/Apply 授权。
- 该 PR 仅提供离线静态/格式级别验收，不赋予创建连接、读取现存 State/Container、提交秘密或部署权限；**Task 2.4、2.5 继续未勾选**。真正 Owner Inventory、Provider 初始化/Schema 和现场网络/OIDC/RBAC 证明尚待授权。

## 2026-10-19 Bootstrap/Capacity 方案通过说明

- 本轮为文档与 OpenSpec 目标修订，不运行 `terraform init/plan/apply/destroy`、云端资源写入或远端 State 修改，不移除原 7 Roots、不改 Self-Runner。
- 先完成 Bootstrap 独立 Change 的设计和离线实现，后续再连接当前 `new-environments/` 的三 Root 与 Fabric Capacity Outputs。保留 Task 2.1–2.5 未勾选与 PR #273/#274 的历史静态验收事实；不得把方案批准等同实际部署成功。
