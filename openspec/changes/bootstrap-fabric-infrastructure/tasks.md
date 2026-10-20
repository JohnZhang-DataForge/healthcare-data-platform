# Tasks

> **Active / Design First**：Bootstrap as Code + paid Capacity Terraform *ability* 已经用户批准，但**所有真实云端写入、Terraform Init/Plan/Apply/Destroy/Import 与购买付费 Capacity 均未授权**。开发以小 PR/离线证据完成，按真实 Main SHA 和 Run 更新。

## 0. Approved boundary and Change creation

- [x] 0.1 从 Main 核对已批准的 Fabric 多环境修订、现有独立 Root/旧 State 边界和开放 PR；创建专用 Bootstrap OpenSpec Change（仅设计/文档）。
- [x] 0.2 正式验证并合并此 Design/Proposal/Spec/Tasks PR（PR #278，Merge `f0290ca1bea87e054794576bc5803e8f1e060ac8`）；将原 `implement-fabric-multi-environment-terraform` Task 0.2 链接到本 Change。**设计通过不等于已实施**。

## 1. Offline Bootstrap contract

- [x] 1.1 固定 `reuse-existing` 与 `fresh-bootstrap` 配置 Schema（离线 Profile v1 + 负向测试 + CI；仅静态合同，未获得 Live 授权）；拒绝旧 Storage/State 的误创建、自动 Adopt、环境跨 Tenant 混淆、Secret 字段和非法命名。
- [x] 1.2 定义 Seed Operator、Backend Operator、Fabric Deployer、Blob Reader 应用与 GitHub OIDC Environment/Repo/Ref 映射的非敏感输入/输出合同；防止身份复用及跨租户错误。
- [x] 1.3 定义 Capacity `reuse-existing` 默认与 `create-new` 单独允许方案，必须携带 Subscription/Region/SKU、实际账单审核证明；缺失默认 HOLD。不得实现自动 Suspend/Resume。
- [x] 1.4 提交离线 Python 单测（合法、失败、重复/防碰撞、费用拒绝）和 GitHub-hosted *no-cloud* CI，更新 Azure Terraform `CODE.md` 与 Runbook。

## 2. Terraform Bootstrap modules (code only until separately approved)

- [ ] 2.1 核对固定版本的 AzureAD/AzureRM/AzAPI 官方 Provider Schema/权限；区分 Tenant A/B 和 GitHub OIDC 最小授权，提交冻结的官方资料引用。
- [ ] 2.2 实现隔离 Identity/SPN/Group/OIDC Root/Modules；不创建原 `github-terraform` 的重复同名 App、不自动接管旧 App；默认拒绝写操作。
- [ ] 2.3 实现可选 fresh Storage/Containers、最小 RBAC 和独立的初始 Bootstrap State 策略；阻止 backend 自举循环、旧 `dev/*.tfstate` 和 `johnzhang` 资源接管。
- [ ] 2.4 实现 Capacity 的 `reuse-existing` / `create-new` Resource/Output；使用经过验证的官方 ARM Schema，付费创建在 CI/Root 中默认拒绝，`prevent_destroy` 与预算/人工审批不互相代替。
- [x] 2.5 为所有 Terraform Root 增加纯离线 `fmt`/静态合同和负向测试；PR CI 禁止执行 `init/plan/apply/destroy/import` 或访问云端。

## 3. Integration and controlled operational readiness

- [ ] 3.1 非敏感 Bootstrap 输出交接到 `implement-fabric-multi-environment-terraform` Task 0.3，确保已有 Workspace/Lakehouse/Connection 唯一所有权与 Capacity ID 来源可审核。
- [ ] 3.2 单独设计受控 Self-Runner 新入口，区分 Bootstrap/Plan/Apply 权限环境；旧 `azure-infra.yaml` 不被替换，禁止 PR CI 拿云端写 Token。
- [x] 3.3 完成按精确 HEAD 的离线验收、变更范围安全核对、真实运行前置授权清单；**未获得单独授权不得验证 Live 环境**。
- [ ] 3.4 只有受控真实证据到位且无开放阻塞后才审查 Closeout/Archive；不能用 Static PASS 冒充 Deployed。

## Acceptance rules

- 最多三轮同方向调试；停止后将失败原因、尝试、Commit SHA、Workflow Run 和下一步写在对应 Task/PR Evidence。
- 当前 `johnzhang/landing`、`tfstate`、旧七 Root、`healthcare-omop`、Self-Runner 与 Local DP/PG 保持原样。
- 身份凭据值不进 Git/Plan/State 输出；Terraform Provider/State 的真正访问验证要独立审批；批准设计不是费用授权。

## Task 1.1 离线 Profile 合同实施记录（2026-10-19）

- Git 正式源码：`azure-fabric/infra-terraform/tools/fabric_bootstrap_profile.py`；严格 JSON 字段，拒绝重复 Key/未知字段/Secrets，隔离的 State/Storage/Tenant/Cost/Capacity 目标输出；`bootstrap/PROFILE-CONTRACT.md` 和故意不可部署的样例冻结规则。
- `test_fabric_bootstrap_profile.py` 与 GitHub-hosted `fabric-environment-preflight.yml` 负责静态正负向与样例 fail-closed；请以当前实现 PR 最终 HEAD/Run 为验收引用，绝不声称云端验证。
- **仍未完成**：Task 1.2 身份/OIDC 手工保护与输出映射、Task 1.3 成本审批合同、Task 2 Terraform Provider/Module/Root，以及所有 Init/Plan/Apply/Destroy/Import 与费用授权。

## Task 1.2 独立身份/OIDC 离线合同（2026-10-19）

- `tools/fabric_bootstrap_identity.py`、`bootstrap/IDENTITY-CONTRACT.md` 定义 Seed Operator 人工边界，三个互异新 App 的准确 Tenant、名字和用途，两个精确 GitHub OIDC Environment/Repo/Ref/Audience/Issuer，以及创建后 Client ID 的非敏感交接检查。
- `test_fabric_bootstrap_identity.py` 检验 same/cross Tenant、重复/越权/跨环境/PR ref/secret/自动 Adopt 拒绝，由 GitHub-hosted Fabric Offline CI 执行；只允许格式/静态结果。
- **不代表** GitHub Environment 已受保护、管理员同意已经取得、实际 AzureAD/Fabric/RBAC 权限可用、Client ID 存在或 Terraform 可以执行。下一步 Task 1.3 和 2.1–2.5 保持开放。


## Capacity Billing Gate / Provider freeze（2026-10-19，离线）

- Task 1.3：`tools/fabric_capacity_approval.py` 和 `bootstrap/CAPACITY-APPROVAL-CONTRACT.md` 固定 SKU/Region/Subscription、来源 SHA、估价与月度限额、账单审核记录和独立审查人；无论字段是否齐全，只有外部信任审批才能解除付费创建 HOLD。
- Task 2.1 前置调研：`bootstrap/PROVIDER-SCHEMA-REFERENCE.md` 冻结 AzureAD 3.8.0、AzureRM 4.60.0、AzAPI 2.8.0 的官方链接与资源字段；实际 Provider 安装/Schema/IAM/授权未经核查，Task 2.1 **暂不勾选**。
- 后续仍需身份/存储/Capacity Terraform Module/Root 的静态源码、格式检查和独立授权的真实验证。无云端写入/费用产生。

## Task 2.2 identity source candidate, code-only (2026-10-19)

- New isolated bootstrap/identity Terraform Root pins AzureAD 3.8.0 and uses separately configured Tenant A/B aliases. Three new independently named applications/service principals, two security groups without IAM assignments, and two tightly scoped GitHub OIDC environments are declared with resource count=0 unless creation is separately approved.
- State uses a separately protected initial local backend and cannot depend on new yet-to-exist Storage. No current github-terraform adoption or old Storage/state access. Each resource has prevent_destroy; not a substitute for inventory or manual approval.
- A GitHub-hosted CI step checks terraform fmt only and Python static guardrails (including default false, exact resource count and no credentials). No provider init/validate/plan/apply or remote side effects. Task 2.1 live/provider privileges, Task 2.2 tenant runtime/provider validation and Task 2.3/2.4 implementations still require separate gated steps. This code is NOT DEPLOYED.

## Task 2.3 第一批：Storage / Backend / RBAC 仅源码实现（2026-10-19）

- 新增 `azure-fabric/infra-terraform/bootstrap/storage/`，独立 `azurerm = 4.60.0` Provider、Tenant A/Subscription、`backend "local" {}`，消除新建 Storage 自举循环；复用模式资源数量固定为 0，目标仅为外部库存 ARM ID，禁止自动 Adopt/Import/Migrate/修改旧资源。
- fresh 模式声明仅新环境 RG、新 HDP Storage 与两个 private Containers，关闭 Public Network/Shared Key，下一阶段需先解决私网连通；只有 Seed、库存、初始 State 保管、私网及创建授权全部明确标志才具备创建候选。全新目标名称仍需要真实 Inventory 验证。
- RBAC 严格引用**刚由本 Root 声明**的 Container Resource Manager Scope；Backend Operator 获取新 `tfstate` 的 Data Contributor，Blob Reader 获取新 `landing` 的 Data Reader。三个服务主体不互借；角色使用 Object ID 且必须事前独立核验。变量布尔值不是运行授权。
- 静态回归 `test_fabric_bootstrap_storage_root.py` + GitHub-hosted Terraform `fmt -check` 后可判定代码阶段 PASS；**Task 2.3 不打勾**，直到 Source/Provider 边界审查与独立授权的真实库存/网络/State/权限证据到位。任何 Init/Plan/Apply/Destroy/Import 继续 HOLD。

## Task 2.4 第一批：AzAPI Capacity Terraform（离线资源声明）

- 新增 `bootstrap/capacity/`，锁定 `Azure/azapi = 2.8.0`，仅使用 Microsoft 官方 `Microsoft.Fabric/capacities@2023-11-01` Schema。`reuse-existing` 模式没有资源/DataSource，只引用未核实 Capacity UUID；`create-new` 资源需 Tenant B/订阅/RG、Region、F SKU、管理员与计费审核证据、来源 SHA、受保护 Environment/Seed/库存各标志共同允许，全部默认 false。
- 始终坚持**账单授权与代码审批分别独立**：成本审核字段不等于付款许可，付费授权必须外部核验，未得到许可不运行 Terraform。使用 `prevent_destroy`，不开发 Suspend/Resume。初始 State 仍为独立受控 Local State。
- `created_azure_arm_id` 不是 Fabric Capacity UUID，`created_fabric_uuid=null`，待授权真实独立读回；Provider Init/Plan/Apply、SKU可用性、订阅权限与实际账单均未验证。Task 2.4 **继续未完成真实部署验收**。
- 修订 Profile v1 的一处跨租户限制：Tenant A Storage Subscription 与 Tenant B Capacity Subscription 可以不同，均须真实单独核实；补离线单测。CI 新增 Capacity fmt/static tests。

## Task 2.5 第一批：六 Root 横向离线门禁（2026-10-19）

- 将三项 Bootstrap Root（Identity / Storage / Capacity）与三项新环境 Root（Workspace / Onelake / Connection）全部纳入 GitHub-hosted Terraform `fmt -check -diff`；不执行任何 Terraform init/validate/plan/apply/destroy/import，也不设置 GitHub OIDC token 写权限。
- 新增 `tests/test_fabric_bootstrap_cross_root.py`：固定各 Root 的资源类型与数目、独立 State Backend、自举禁令、单一资源所有权、默认创建审批和 CI 无凭据规则。负向回归阻止跨 Root 重复管理、旧 Storage 接管或 Capacity 付费创建门禁绕过。
- **离线源码/格式关卡，不是可部署证明**：真实 Provider Schema、租户与订阅、RBAC、网络、远端 State 及收费审批仍未验证。Task 2.5 checkbox 暂不勾选，下一批继续校验非敏感 Bootstrap → 新环境交接与 fresh 模式断点。此次变更不触碰旧七 Root、旧 `dev/*.tfstate`、Self-Runner 或真实云端。

## Task 3.1 第一批：非敏感输出交接合同与 fresh 阻断（2026-10-19）

- 新增 `tools/fabric_bootstrap_handoff.py` 和 `bootstrap/HANDOFF-CONTRACT.md`：仅处理 Profile、三独立 Client ID、Storage Target 和 Capacity Target **value-only 离线对象**；逐字段验证 Tenant/Subscription/ARM Resource ID、唯一身份、State Key、容量来源与所有 false 审核标志。
- `reuse-existing + reuse-existing` 仅提供现有 Preflight 可接受的**未验证**环境配置预览和 Backend 静态摘要；真实 State/Storage/Capacity 不做查询，绝不返回 approval=true。
- `fresh-bootstrap` 默认阻断与旧 Root 自动衔接：当前 `fabric_environment_preflight.py` / `fabric_deployment_target.py` / `fabric_backend_config.py` / `new-environments/connection` 仍对 `johnzhang` 写死；下一 PR 必须单独泛化并防止旧 Storage 回退。付费 `create-new` 容量必须独立核验真实 Fabric Capacity UUID，ARM ID 不能转换代替。
- 单独 Python 正/负/跨 Tenant/Secret/付费回归并接入 GitHub-hosted no-cloud CI。**Task 3.1、下游 Task 0.3 保持未完成**，直到代码与实际受控交接边界完成；本 PR 无 Terraform/云端操作/费用/旧资源变更。

## Task 3.1 第二批：Bootstrap 衍生 fresh Backend 参数链（2026-10-20）

- 为原 `fabric_environment_preflight.py` 增加**只接受携带完整 strict Bootstrap Profile 的 v2 内部校验**；已有 v1 CLI/legacy `johnzhang` 不放宽。未经完整 Profile 绑定的 v2 自由 JSON 一律拒绝。
- `fabric_deployment_target.py` 与 `fabric_backend_config.py` 现在支持严格 Profile 来源的 fresh HDP Storage ARM ID、Tenant A/B、三个独立 State Key；拒绝回退到 `johnzhang`、替换资源组或错位存储账户。
- `fabric_bootstrap_handoff.py` 为 fresh + 复用 Capacity 提供 v2 **非部署**参数预览；由于 Connection Terraform Root 尚锁死 `johnzhang`，返回 `STATIC_HANDOFF_HOLD_FRESH_CONNECTION_ROOT_GAP`，禁止将预览解释为已获部署许可。付费新 Capacity 继续 HOLD。
- 代码及 Python 负向测试仅经 GitHub-hosted 离线 CI 验收；下一独立 PR 才更新 Connection Root 的双模式保护。Task 3.1/下游 0.3 仍未完成真实验收。

## Task 3.1 第三批：Connection Root 双 Storage 来源与默认拒绝（2026-10-20）

- 解除新环境 `connection` Root 对 `johnzhang` 的无条件固定，显式增加 `bootstrap_mode`（默认 `reuse-existing`）和 `fresh_storage_provenance_verified`（默认 false）；相同 Resource Precondition 中明确阻止 legacy→fresh、fresh→legacy 账户错用。
- 新账户只接收严格 `hdp*` 账户名；仍由现有独立 Connection Inventory/Reader RBAC/Metadata/Key Vault/WorkspaceIdentity/域名审核标志共同限制，均默认 false，不新增 Storage/RBAC 管理资源。
- `fabric_bootstrap_handoff.py` 为两类 Storage 输出源参数**不含批准**的 Connection 输入预览，fresh 状态为 `STATIC_HANDOFF_HOLD_FRESH_EXTERNAL_APPROVALS`，非 `DEPLOY_READY`；Python 静态负向测试、Terraform `fmt` 使用现有 no-cloud CI。
- **Task 3.1、下游 Task 0.3 仍保持开放**：实际 Storage Network/State/权限和真实 Capacity 身份、Terraform Provider/Backend 连接与独立执行许可尚未确认。没有远端操作或费用。

## Task 3.2 第一批：Self-Runner 手工控制入口（2026-10-20，仅离线，未授权执行）

- **独立 Self-Runner PR #150**：`JohnZhang-DataForge/Self-Runner` 新建 `.github/workflows/fabric-controlled-entry.yml`、`src/ci/fabric_controlled_entry.py`、`tests/ci/test_fabric_controlled_entry.py`、GitHub-hosted PR 测试 `fabric-controlled-entry-ci.yml` 和 `docs/fabric-controlled-entry.md`。来源 PR：<https://github.com/JohnZhang-DataForge/Self-Runner/pull/150>；合并 SHA：`a951cb5e8589815cc1adb2096252e2c221dd0184`；CI Run `39394922136`，`static-intake-tests=success`。
- 手动 `workflow_dispatch` 输入只有 `bootstrap|plan|apply` 意图、六个新 Root 中一个、禁止旧环境名、精确 Healthcare 40 位 SHA；`apply` 意图必须提供 64 位 Plan Digest **语法**，但不视为可信 Plan 审批。所有有效输入返回 `FABRIC_CONTROLLED_ENTRY_OFFLINE_INTAKE_HOLD`，所有权限/资源/执行证据均 false。
- 安全特性：只在 Self-Runner `main` 手动入口接受请求；GitHub-hosted `ubuntu-latest`，最小 `contents:read`，无 `id-token:write`、无 Token/Secrets/Repo Vars、无 Azure/Fabric API、无目标代码 Checkout、无 `dw-runner-set`、无 Terraform Init/Plan/Apply/Destroy/Import。**PR #150 没有实际触发工作流 dispatch**，只由 GitHub 运行 PR 安全单测。
- **保留 Task 3.2 未勾选**：计划中的 Bootstrap/Plan/Apply 受保护 GitHub Environment、实际受控 Self-Runner executor、可信 Main SHA/Plan artifact/State 回读、财务和人工二次审批均尚未实现/授权；此 PR 只是不会部署的安全控制器，绝不把 CI PASS 解释成运行批准。
- 完全未修改旧 `Self-Runner/.github/workflows/azure-infra.yaml`，也没有触及旧 `johnzhang`、`dev/*.tfstate`、旧七 Root 或付费 Capacity。


## Task 3.3 第一批：跨 Self-Runner × Healthcare 的统一离线 HOLD Gate（2026-10-20）

- 新增 `tools/fabric_execution_readiness.py`，在本地以严格非敏感 JSON 校验 Self-Runner PR #150 的 Controller Intake 摘要 + Bootstrap Profile + 三个身份 + Storage Target + Capacity Target；所有阶段 `bootstrap|plan|apply` 均生成 `FABRIC_OFFLINE_INTEGRATION_HOLD`。
- 对六个新 Root、独立 `fabric/<env>/<component>.tfstate`、Tenant A/B、fresh Storage Profile 绑定与付费 Capacity UUID 来源做交叉检查。全部实际云权限/支付/可信来源/State/Provider/网络布尔值必须为 false；即使输入 Claim 携带 SHA 和 Plan 摘要的语法，**绝不自动证明该 SHA 属于 Main 或 Plan Artifact 已批准**。
- 增加 `tests/test_fabric_execution_readiness.py`，覆盖 Bootstrap/Plan/Apply、A→A′/A→B、旧/新 Storage、已存在/收费 Capacity、未知字段与 Secrets、伪造批准、错误 Root/State/SHA；CI 在 `ubuntu-latest` 上只使用 Python 和六 Root `terraform fmt`。
- 运行前离线检查清单见 `bootstrap/OFFLINE-READINESS.md`，后续必须独立验证保护的 GitHub Environment、真正固定 Main SHA/计划及 State、权限和私网，且再次明确取得真实执行许可。**Task 3.3 checkbox 保持未勾选，直到精确 PR HEAD CI 成功并完成范围审计。无云端操作或新费用。**

## Task 2.5 / 3.3 代码阶段独立验收记录（2026-10-20，正式范围审计）

- 已完成的**仅为离线目标**：Task 2.5 六个 Root 的 `terraform fmt -check -diff` + Python 默认拒绝/所有权/Secret/防旧 State 静态测试；Task 3.3 Controller 意图和 Bootstrap 四份 value-only 文档的 Python 交叉校验、HOLD Matrix、真实运行前置清单。勾选这两项**绝非**验证 Azure/Fabric 资源，也不赋予 `init/validate/plan/apply/destroy/import` 权限。
- 证据 PR：<https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/298>；**精确验证 HEAD** `bfcd37d966654a16eb5ed63ef404496175c96c88`，六个 Required/Relevant Checks 全部 `success`（Document Links、Component Naming、Fabric Environment Preflight、OpenSpec Validation、Change Gate、Trusted Change Gate）。Fabric GitHub-hosted 离线 Workflow Run **39403368850**：<https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39403368850>；已合并 `main` Commit `8388410313c863eaf9e4b199fb476d4ff8c00586`。该 commit 为 PR #298 代码验收基线，不代表后续并发 Main 永久不变。
- 本 PR #298 的 GitHub Files API 确认 **仅 6 个源码范围文件**：`.github/workflows/fabric-environment-preflight.yml`、`tools/fabric_execution_readiness.py`、`tests/test_fabric_execution_readiness.py`、`bootstrap/OFFLINE-READINESS.md`、本 `tasks.md` 与人工 Runbook；没有修改旧七 Terraform Root、`azure-infra.yaml`、既有 Storage/Remote State、任何 `*.tfstate` 或付费 Capacity。
- Self-Runner 对应离线 Intake PR：<https://github.com/JohnZhang-DataForge/Self-Runner/pull/150>，已合并 `a951cb5e8589815cc1adb2096252e2c221dd0184`，GitHub-hosted 受限 Controller CI Run `39394922136` success；没有实际调度该 Workflow，也未从不可信 PR 签发云 Token。
- **仍须 HOLD**：Task 2.1–2.4 官方 Provider Runtime/真实 Azure 权限、Identity/Storage/Capacity 资源库存及私网、Task 3.1 的可信现场 provenance、Task 3.2 真正隔离权限的可执行受保护 Self-Runner Jobs、Task 3.4 部署后验收/Closeout；新 Capacity 的创建、真实 OIDC/RBAC、Plan 与 Apply 均需另行申请独立批准。
