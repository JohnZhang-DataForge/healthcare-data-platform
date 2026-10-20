# Tasks

> **Active / Incremental Live Testing Approved (2026-10-20)**：用户已明确允许隔离环境的 Terraform Init、Validate、真实只读库存与 Plan/OIDC 验证；计划进入真实测试而非只做静态源码。PR CI 仍必须 **无云凭据、无远端 State、无 Plan/Apply**；新增 `init -backend=false` + `validate` 进行真实 Provider Schema 检测。实际带云权限的 Plan 需经源 SHA、Identity/Subscription、隔离 State Key 和现有资源库存核验；可在确认 Plan 后对明确隔离的 Trial 资源进行 Apply。旧 `johnzhang`/历史 State、旧 Workspace 保留保护。新收费 F SKU Capacity、意外成本或破坏性操作需另行批准。开发以小 PR + 真实测试证据验收。

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
- [x] 2.5 为所有 Terraform Root 增加纯离线 `fmt`/静态合同和负向测试；原 `fabric-environment-preflight.yml` fmt-only PR CI 仍禁止 `init/plan/apply/destroy/import` 及云端访问。另有 2026-10-20 批准的独立无凭据 Provider CI，可执行 `init -backend=false` 和 `validate`，仍不得运行真实 Plan/Apply。

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

## Task 3.2 第二批：三阶段权限隔离的 OIDC 阻断器与不可变 Subject 设计（2026-10-20）

- Self-Runner PR #151：<https://github.com/JohnZhang-DataForge/Self-Runner/pull/151>，合并 `7f252b2c9eced200b73e23235be7eba466819418`；新增 `src/ci/fabric_phase_review.py` 和 `tests/ci/test_fabric_phase_review.py`，并接入现有 **GitHub-hosted、无 OIDC、无云调用**的手工 Controller；所有 `bootstrap/plan/apply` 意图继续一律 HOLD。
- **明确发现结构性不匹配**：新 Workflow 归属于 Self-Runner，但当前 Entra Identity Root GitHub Federation 固定引用 Healthcare Repo；并且 `fabric-<env>-backend` / `-deployer` 两个 Role Environment 不能自然兼容同一 Job 的 `fabric-<env>-plan` 或 `-apply` Environment。
- **2026 年 GitHub 不可变 OIDC Subject**：GitHub Repo API 确认两个 Repo 都在 2026-07-15 之后建立（Healthcare `2026-10-05` / Self-Runner `2026-10-11`），官方格式含 `@owner_id/@repo_id`，而当前 Identity Root 使用 name-only Subjects。新增 `tools/fabric_oidc_subject_audit.py` + `tests/test_fabric_oidc_subject_audit.py`，CI 记录此不兼容并禁止未经审查静默切换 Federation Subject；**没有实际获取 OIDC token 或调用云端**。
- 方案决策保留可审查的 A（Healthcare 执行，Self-Runner 只控制）或 B（Self-Runner 执行并修改 Entra OIDC）的分叉；两者都必须先获得 Protected Environment、Main/Source SHA、受控 Plan Artifact、独立审核人与云端调用授权。当前 Task 3.2 checkbox 未勾选，不能使用默认 IAM 或 `id-token:write` 绕过此阻断。

## 2026-10-20 开发策略变更：Provider 真实 Init/Validate，Plan 准备就绪

- 用户撤销了此前对全部 Init/Validate/Plan 的一刀切限制：允许真实云只读检查、OIDC 登录验证、隔离新环境的 Plan，隔离 Trial 资源在审核 Plan 后 Apply；但**不视为批准新建收费的 Fabric F SKU Capacity 或破坏旧状态**。此前的 2.5 fmt-only 静态 CI 保留，作为快速无云回归。
- 新增专门 `.github/workflows/fabric-provider-init-validate.yml`，在 GitHub-hosted 六 Root 矩阵中执行 **Terraform 1.13.5 `init -backend=false` → `validate`**：实际下载相应固定 Provider、检查 HCL/Provider Schema，不配置 Azure/Fabric 身份、不访问 Blob Backend、无 `id-token:write`。此验证可能因 Provider 官方 Schema 不兼容而 FAIL；需要修复源码而不是假装 PASS。
- `tests/test_fabric_provider_validation_workflow.py` 防止 CI 自行增加 Remote Backend、State、OIDC、Secrets 或 Apply。**`init -backend=false` 不等于云端初始化、真实远程 Plan 或资源创建**。后续在 Self-Runner 受保护通道中才设计云身份验证/Plan，先解决 immutable OIDC Subject 与执行仓库不一致，再核实 Trial Capacity UUID 和 State。
- 源码限定在上述 Workflow、静态 Workflow 安全测试及 Task/Runbook；旧 `azure-infra.yaml`/旧 Storage/State/七 Root 不修改。相关真实六 Root GitHub CI Run、准确 SHA/错误与修复记录以本 PR 完成时更新。Task 2.1 Provider 验证**只达到 Schema 子阶段**，仍须完成最小 IAM、真实权限。Task 3.2 真正可信的 Plan/Apply 入口仍开放。

## Task 2.1 第一批真实 Provider Schema 运行验收（2026-10-20）

- 用户已明确将原离线-only 开发模式调整为**真实测试优先**：允许在隔离范围执行 Terraform Init/Validate、Azure/Fabric/OIDC 只读核验和真实 Plan；不允许未经评估破坏既有资源，不允许无审批新建收费 F SKU Capacity。已将旧“禁止一切 Init/Plan”表述改为按职责划分的安全边界。
- 正式 PR #303：<https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/303>；验收精确 HEAD `332cf88f3eed9dcd6e460d44f36f78476126be38`。GitHub-hosted **Terraform Provider Init and Validate (No Backend)** Run `39411572769`，六个 Root 各执行 **Terraform 1.13.5 `init -backend=false -input=false` 与 `validate`，6/6 SUCCESS**；另外原有六个独立 GitHub 检查全部 SUCCESS，合计 **12/12 PASS**。正式 squash merge SHA：`a5f96c17c64682669eee22519084d30dc550fc3e`。
- 已实际下载官方 Provider 并检查配置：AzureAD Identity、AzureRM Storage、AzAPI Capacity、Fabric Workspace、OneLake、Connection。旧 fmt-only PR CI 继续独立运行；新增 `test_fabric_provider_validation_workflow.py` 在 GitHub-hosted Provider CI 中验证无 OIDC Token、无 Remote Backend、无 Plan/Apply，防止高权限意外进入 PR CI。
- PR #303 GitHub Files 审计仅五项：新增 `.github/workflows/fabric-provider-init-validate.yml`、`tests/test_fabric_provider_validation_workflow.py`、更新 Provider 参考、Bootstrap Runbook、本 OpenSpec Tasks；**未修改**六个 Root HCL、旧七 Root、`johnzhang`、`dev/*.tfstate`、旧 Workspace、Self-Runner `azure-infra.yaml`。未触发任何真实收费、OIDC、Azure/Fabric 权限或远端 State 访问。
- **尚未完成的真实运行测试**：Entra/GitHub immutable OIDC subject 对齐及认证，实际 Provider IAM/SKU/Capacity Trial 可见性，新隔离 `fabric/<env>/...` Remote Backend 权限/State 空位，真实 Azure/Fabric Plan，人工审核后隔离 Trial Workspace/Lakehouse Apply+读回。**Task 2.1 保持 OPEN**，因为 Provider Init/Schema 虽 PASS，但真实身份、权限与 Plan 尚未完成。
- **下一 Session 进入 Task 3.2**：在 Self-Runner 执行 Terraform、Healthcare 为 IaC 真正来源的目标架构下，先从受保护且受审核的 GitHub Env 配置 immutable OIDC Subject、独立 Tenant A Backend vs Tenant B Fabric 身份（Plan/Apply 不混用未经授权的 Seed）；优先做只读 OIDC/Capacity/State 库存，然后首个新隔离 Workspace Root 的真实 Plan。保存无敏感信息的 Run/HEAD/审批证据；禁止把 raw Plan/State 写入公开日志。

## Task 3.2 第一批 OIDC Source 修复与 Live 阻断（2026-10-20，PR #305）

- 修正执行拓扑：Healthcare 只存放经过审查、固定 SHA 的 Terraform IaC；受控 GitHub Actions 执行仓库为 `JohnZhang-DataForge/Self-Runner`。通过 2026-10-20 GitHub Repo API 核对 immutable owner ID `337895338`、Self-Runner Repo ID `1413796156`，Identity Root 已由不兼容的 Healthcare name-only OIDC Subject 改为带不可变 ID 的 **Self-Runner** Subject。
- 精确区分 Tenant A `backend_operator` 与 Tenant B `fabric_deployer`，按 `plan`、`apply` 共声明四个 distinct Environment：`fabric-<env>-plan-backend`、`fabric-<env>-apply-backend`、`fabric-<env>-plan-deployer`、`fabric-<env>-apply-deployer`。它们使用四条不同的 AzureAD Federated Identity Credentials，保持各自应用/租户绑定和默认 `identity_creation_approved=false`，不导入旧 App 或增加权限。Bootstrap Seed 另设 `fabric-<env>-bootstrap` 人工审批环境，不能依赖尚未创建的身份来创建自身。
- 更新 Bootstrap Profile 的 Github Executor 及 Identity v2 四阶段映射，保留机密、错误分支、角色/环境/Subject 漂移的 Fail-Closed 单测；六 Root 的真实 Provider `terraform init -backend=false` / `validate` 继续由无云权限 CI 检测。
- **真实性边界**：源代码静态对齐不等于实际 GitHub OIDC Token `sub` 预览或 Entra Cred/RBAC 验证。由于当前 GitHub Connector 不提供 GitHub Environment 保护规则及 OIDC 配置读取接口，受保护 Environment、OIDC claim、Tenant A/B 权限、实际 Trial Capacity、Remote State、真实 Plan/Apply 均未完成。下一批首先完成 Self-Runner 的受控现场探针和独立云端身份授权，再依次进行只读库存和隔离 Workspace Plan。收费 F SKU Capacity 严格保持不允许自动创建。
- 本节为代码候选的实施记录；**Task 3.2 checkbox 仍然 OPEN**，必须在精确 PR HEAD CI 全部 PASS、合并证据与真实认证完成之后才能评估进度。Source PR #305：<https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/305>。

## Task 3.2 第二批：OIDC Source + Self-Runner Token Exchange Probe 合并验收（2026-10-20）

- Healthcare 正式 Source 修复 PR #305：<https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/305>。审计并发更新后以新 Main `6a428a78cc470f5e0627c398da6494c132d218e1` 重新冻结 HEAD `ca08e8d4f9aa8cf499b6310095ba5c3d91a27dbc`；十二个检查 **12/12 success**（Provider 六 Root 实际 `init -backend=false` / `validate` + Offline/Change/Docs）；Provider 验收 Run <https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39415025887>。Squash merge `59751aab60be8542a5dfca952573cace2c13e2bf`。Local DP 并发 Main #306 已保留，未改旧 Terraform Root、旧 `azure-infra.yaml` 或 Legacy State。
- Self-Runner PR #154：<https://github.com/JohnZhang-DataForge/Self-Runner/pull/154>；Source HEAD `32f34d2ca8c2b86a5a10bc690f84fa8abd12e341`，Controller CI `static-intake-tests=success`，Run <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39415798354>，合并 Self-Runner Main `b39235d4006107a2835119c2f14a5d19cabaffee`。新增 `.github/workflows/fabric-oidc-readonly-probe.yml`，仅 Self-Runner `workflow_dispatch` / `main`：两个 `dw-runner-set` 受保护 Environment `fabric-<env>-plan-backend` 与 `fabric-<env>-plan-deployer` 分别启用最小 `id-token:write`，独立 Entra Application Client/Tenant IDs。预检环境 ACK/变量，然后现场读取 GitHub OIDC Token Claims 并向 Microsoft Entra 执行 Client Assertion token exchange；标准库实现、无 Terraform、无 App/Storage/Capacity 创建、不会输出 JWT、Access Token 或 Entra 错误响应。
- Self-Runner 操作手册 `docs/development/FABRIC-OIDC-READONLY-PROBE.md`：手工建立 GitHub Environment `main` 分支保护、独立 Reviewer；每个 Role Environment 的 `FABRIC_OIDC_CLIENT_ID`/`FABRIC_OIDC_TENANT_ID`（backend 还需 Subscription ID）和环境级确认 Secret `FABRIC_OIDC_PROBE_ACK`；在 Tenant A/B 录入四 Subject 中对应的两条 Plan Federated Identity Credential。只有**已实际创建和授权**的新 App 能进行 Entra Token Exchange，不能偷偷复用现有 `github-terraform`。即使交换成功也**不意味着**具备 Azure RBAC、Fabric Tenant 权限、Capacity 或 State 可见性。
- **未执行真实云登录**：当前可用 GitHub 接口拒绝 GitHub Environments 与 OIDC Customization 设置读取 API，且没有新建 Entra App/FIC 的证据、受保护 Environment 确认信息或直接 `workflow_dispatch` 操作接口。因此仅源码/CI 验证；真实 `GitHub OIDC Token issued`、`Microsoft Entra Token Exchange`、Tenant A/B read-only Inventory、Trial Capacity、remote State keys、Workspace Terraform Plan/Apply 均未发生，Task 3.2 **仍未勾选**。
- 后续顺序：人工核实并配置独立受保护 GitHub Environments、检查 GitHub OIDC `sub` preview → 以 Seed Operator 正确创建新 Entra FIC 和授权（新 App 创建需另行执行初始 Bootstrap 且保管独立 State）→ 手工发起上述 read-only Workflow 并记录 Run → 确认 Tenant/Subscription/Trial Capacity/新 `fabric/<env>/*.tfstate` 空位 → 使用 Healthcare 精确 Main SHA 的隔离 Workspace `terraform plan`（审查无收费与破坏性动作）→ 以后另行审核 Apply。当前不创建收费 F SKU、不触碰 Legacy State。

## Task 3.2 — GitHub OIDC Issuer 首轮 Live 尝试（2026-10-20，三轮后暂停）

- Self-Runner PR #155 <https://github.com/JohnZhang-DataForge/Self-Runner/pull/155>，合并 Main `ee201d755eb5ce65bc9676ca7c4638376d8f45ef`，引入 `fabric-oidc-issuer-attestation.yml`：仅影响该探针代码的 Main push，GitHub-hosted、独立 job `id-token:write`、无 Environment/Secrets/Azure/Fabric/Entra/Terraform/State，校验真实 GitHub JWT 默认 immutable `sub`、owner/repo IDs、ref、audience 和 issuer；不输出 JWT 或其原始声明值。PR 静态测试 PASS。**实际 Main-push Run** <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39418821662>（FAIL，负向测试 PASS，Issuer 处理返回 HOLD）；此时没有分阶段原因码。
- Self-Runner PR #156 <https://github.com/JohnZhang-DataForge/Self-Runner/pull/156>，合并 `a7b310395eca922fb8db46cee8014d9af1681e84`：只新增不敏感 `FAILED_STAGE`/`FAILURE_CLASS`/有限白名单 `MISMATCH_CLAIM_NAME` 诊断，静态 CI PASS。**实际 Main-push Run** <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39419068270>：`TRUSTED_MAIN_PUSH_CONTEXT=PASS`，`FAILED_STAGE=TOKEN_REQUEST`，`FAILURE_CLASS=AttestationRejected`。没有发出可用的 JWT Claims PASS 证据。
- Self-Runner PR #158 <https://github.com/JohnZhang-DataForge/Self-Runner/pull/158>，合并 Main `814eec2e27187379f9c01d893d9fe3e1611fa0d3`：查到 GitHub hosted regional OIDC URL 可为 `pipelinesghubeus6.actions.githubusercontent.com`（原精确域名白名单过窄），调整两份 issuer/Entra probe 的 TLS+Github pipeline 请求 Host 正则并加入无网络模拟测试；PR 静态 CI PASS。**实际 Main-push Run** <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39419362519>：负向测试 PASS，`TRUSTED_MAIN_PUSH_CONTEXT=PASS`，但仍 `FAILED_STAGE=TOKEN_REQUEST`，`FAILURE_CLASS=AttestationRejected`，无 JWT 和 Entra 登录成功证据。
- 结论：**真实 GitHub OIDC Token issuance 未通过**。固定理由是 runtime token-request guard/响应阶段抛出 `AttestationRejected`，但现有红acted 日志尚无法确定是 `ACTIONS_ID_TOKEN_REQUEST_URL`/Token 环境缺失、具体 Host 不符合白名单，还是 GitHub OIDC 响应未包含期望 `value`。不得把静态配置、真实 Workflow 已启动、历史 `azure-terraform-oidc-smoke.yml` 视作 Task 3.2 的新 Entra 登录证明；**不要猜测实际 Subject 或修改已经存在的 Entra FIC**。
- 遵守 OpenSpec 的**最多三轮同方向调试**：本次在第三次真实尝试后暂停 issuer 自动重试，不再同方向无证据地重新 merge/dispatch。下一步先从 GitHub Admin 授权的 `GET /repos/JohnZhang-DataForge/Self-Runner/actions/oidc/customization/sub` 获取 `sub_claim_prefix`、`use_immutable_subject`（或 Github UI OIDC Preview），并在新的、明确审批的诊断设计中分别报告“有无 OIDC 请求环境变量、经过批准的 Host 类型、响应是否有非空 value”这三个**非敏感布尔值/枚举**，不打印真实 URL、Token、Claim 值或 HTTP Body；有新的故障证据再开下一轮。
- 独立受保护 GitHub Environments、Tenant A/B 新 Entra App/FIC、真实 `Microsoft Entra Token Exchange`、容量/State/Workspace Plan/Apply 全部仍为 OPEN；没有触及旧 `azure-infra.yaml`、旧七 Root、旧 State 和收费 F SKU Capacity。Task 3.2 **不可勾选**。

## Task 3.2 — GitHub Immutable OIDC Issuer 真正 PASS 的补充验收（2026-10-20）

- GitHub 管理员通过认证的 `gh api repos/JohnZhang-DataForge/Self-Runner/actions/oidc/customization/sub` 只读输出：`use_default=true`、`use_immutable_subject=true`、`sub_claim_prefix=repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156`、`include_claim_keys=null`。这是**当前 Self-Runner Repo 设置读取的管理员证据**，不代表四个 Environment/Entra FIC 已配置，也不暴露 JWT。
- 与历史失败原因闭环：Self-Runner PR #159（Main `2c91eb1b84ea4b4f3f75ef4cf71901414644cc70`）新增白名单诊断，实际 Run <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421661056> 得到 `TOKEN_REQUEST_CAUSE=REQUEST_HOST_NOT_RECOGNIZED`。Self-Runner PR #160（Main `8d7817b58fdef9dadcac07bac17db92a609768a1`）改用 GitHub 官方 `actions/github-script@v8` 的 `core.getIDToken('api://AzureADTokenExchange')`，不再自行拼接不受支持的请求 Host。
- **真实 On-Main 成功证据**：<https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619>，实际 Run 状态 **completed/success**，Job `github-oidc-real-token-claims` 的离线 Python+Node 负向测试及官方 Toolkit 真正 Token 请求步骤全部成功；安全日志：`TRUSTED_MAIN_PUSH_CONTEXT=PASS`、`ACTUAL_GITHUB_TOKEN_ISSUED=PASS`、`IMMUTABLE_GITHUB_OIDC_SUBJECT=PASS`、`ISSUER_AUDIENCE_AND_MAIN_REF=PASS`、`JWT_PRINTED=NO`、`ENTRA_EXCHANGE_AND_TERRAFORM=NOT_TESTED`。Payload 验证表明 GitHub 默认 **Main ref** Subject 与 Immutable owner/repo ID 预期一致；未声称独立密码学验签。
- **验收范围**：GitHub Main **ref-context** OIDC Token 签发与 Claims = **PASS**；`fabric-<env>-plan-backend` / `fabric-<env>-plan-deployer` **environment-context** Subject、受保护 GitHub Environment 的分支限制/审核人、Tenant A/B 新 Entra App + FIC 的 token exchange、Fabric Trial Capacity、State 读取、Terraform Plan/Apply 全部 **NOT TESTED**。旧三轮失败是历史记录，不覆盖本轮新的真实 PASS；Task 3.2 保持 **OPEN**。
- 下一关键动作：独立核实并配置 Self-Runner `trial-lab` 保护环境和 Entra 新身份（拒绝复用旧 `azure-infra.yaml` SPN）；使用 Self-Runner `fabric-oidc-readonly-probe.yml` 进行真实受保护 Environment 的 Subject + Entra Token Exchange，成功后才核实 Trial Capacity/State 并进行隔离 Workspace Plan。无收费新 F SKU 创建授权。

## Task 3.2 — 受保护 Environment Entra 认证探针的官方 Toolkit 修复（2026-10-20，PR #161）

- Self-Runner PR #161 <https://github.com/JohnZhang-DataForge/Self-Runner/pull/161>：Source HEAD `55f038d0bd97e51f2cfdfd884d7591f20f75d6c8`；GitHub-hosted `static-intake-tests=success`，Run <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422628549>；合并 Main `4561f666d99e4fe1b014acac65332d5215b0c0c8`。修复旧的 Self-Runner `.github/workflows/fabric-oidc-readonly-probe.yml` 中与原失败相同的自定义 OIDC URL Host 白名单：受保护 Environment job 使用已真实验收的 GitHub 官方 `actions/github-script@v8` → `core.getIDToken('api://AzureADTokenExchange')`，仅通过进程内存/子进程标准输入将 JWT 传给 `fabric_oidc_readonly_probe.py --token-stdin`。不支持把 JWT 放进命令行参数、文件、Workflow Output 或环境变量；所有错误输出脱敏。单测覆盖了无效仓库/角色/Subject 和禁止命令行传递 Token，未触碰旧 `azure-infra.yaml`。
- **尚未执行 live protected Environment OIDC 或 Entra 登录**：原先实际 PASS 的 Run 39422174619 只认证无 Environment 的默认 `:ref:refs/heads/main` Subject。本 PR #161 仅为未来 Entra Probe 的源码/CI 验证；还需要独立核实 `fabric-trial-lab-plan-backend` / `fabric-trial-lab-plan-deployer` main-only branch、required reviewer、Role 环境密钥/变量，以及 Tenant A/B 新 App/FIC。届时再以 protected job 的真实 `:environment:` Subject 和 Microsoft Entra Token Exchange 作 Task 3.2 的下一项 live 验收。真实云 RBAC、Trial Capacity、State 空位和隔离 Workspace Terraform Plan 仍 OPEN；不允许未批准的新收费 F SKU。


## Task 3.2 — Free/private GitHub Environment impossibility and OIDC route decision (2026-10-20)

- **Administrator live evidence:** `GET /orgs/JohnZhang-DataForge` returned `plan=free`; `GET /repos/JohnZhang-DataForge/Self-Runner/environments` returned `total=0`, `fabric_environments=[]`. Independently verified Self-Runner is a **private** repository. Official GitHub product availability confirms: Free/private cannot configure Environments and their secrets/variables; native Environment Required Reviewers cannot protect this workload. Task 3.2's prior protected Environment design is **BLOCKED**, not simply pending configuration.
- **Fail closed on existing code:** four Environment-based FICs in `azure-fabric/infra-terraform/bootstrap/identity/main.tf` stay untouched with `identity_creation_approved=false`; manual `fabric-oidc-readonly-probe.yml` remains un-dispatched and may not be treated as an authorized Free/private cloud executor. Do not change GitHub visibility, GitHub plan, `use_default=true` current repo OIDC setting, old Azure identity or legacy `azure-infra.yaml`.
- **Separation audit:** actual Self-Runner Main issuer Run <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619> verified `ref:refs/heads/main` immutable ID Subject, but that ref alone is shared across its workflows and insufficient for independently gated Tenant A/B Plan vs Apply. Existing OIDC consumers `azure-infra.yaml`, `azure-terraform-oidc-smoke.yml`, `azure-terraform-landing-blob-write.yml` make in-place repo-wide custom-Subject changes unsafe without migration.
- **Approved discovery / not yet implementation:** proposed no-upgrade route = **dedicated private Fabric executor** (requires explicit repository creation approval) with custom immutable OIDC `repo/context/workflow_ref` and role-specific files to achieve per-role FIC matching. Verify its actual custom-Subject preview and real JWT before writing FIC literals. Seed, new Entra Apps, proof of independent Apply authorization, Trial inventory, State, isolated Plan/Apply, and any paid F SKU remain **OPEN**. Do not pretend GitHub manual `workflow_dispatch` is a reviewer gate.
- **Next action:** confirm whether a new separate, dedicated executor GitHub repository is acceptable; until then, proceed only with offline repo/trust contracts and design. Do not proceed by substituting a shared main-ref subject, disabling reviewer checks, or provisioning cloud apps against an unverifiable Environment. Task 3.2 checkbox remains **OPEN**.

## Task 3.2 — 用户最终决策：Self-Runner Private / 单人 / 无 Environment 审批（2026-10-20）

- 用户明确选择：**继续使用现有 `JohnZhang-DataForge/Self-Runner` Private 仓库**执行 Fabric 基础设施，**不设置 GitHub Environment、Required Reviewers，不建立额外仓库，也不迁往 Healthcare Public 执行**。该决定覆盖本 Change 先前因 GitHub Free/private 建议的独立 Executor/Public 方案；旧方案仅保留为历史。GitHub 组织 Free + Private Self-Runner `environments.total=0` 已由用户真实 CLI 证实。
- Self-Runner PR #162 <https://github.com/JohnZhang-DataForge/Self-Runner/pull/162>，GitHub-hosted 静态 CI PASS，合并 Main `c9bb734517a0e809b2d6451eb84fa024ff88e917`：改为纯 `workflow_dispatch`、`main`、GitHub-hosted runner 与两角色 repo Actions Variables，不再依赖 `environment:`、ACK Secret 或本地 K8s Runner；JWT 经 GitHub 官方 Toolkit → masked stdin → Python 检查真实 Main-ref Subject 并尝试 Entra Token Exchange。只读认证，无 Terraform 资源修改。
- Healthcare 此 PR #320：Bootstrap Identity Root 从 **4 条 Environment FIC** 精简为 **2 条新 App 的 Main-ref FIC**（Backend/Tenant A、Deployer/Tenant B）；Identity 离线合同升到 v3、Profile 指定 `refs/heads/main`；静态安全审计、跨 Root 单元测试以及示例同步修正。真正 Immutable Subject 来自实际 Self-Runner Issuer PASS Run <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619>，两条 FIC 均为 `repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:ref:refs/heads/main`。
- **用户接受的隔离边界**：两条 FIC 的 GitHub `sub` **完全相同**；不同 Entra Apps、Tenant、RBAC 是权限范围的区分，不是 workflow/phase 的 OIDC 身份隔离。现有 Self-Runner 其他 Main workflow 可能申请同一 JWT；不迁移旧 OIDC 配置，不复用现有 `github-terraform` App。任务执行限制 Main/手动、精确 Repo Commit、无生产/旧 State、Plan 审查、Apply 不自动启用；这些不会被称为独立审批。
- **真实状态**：Main-ref GitHub OIDC Issuer = LIVE PASS；Self-Runner/Healthcare 源码及 CI = 按 PR 证据；新 Tenant A/B App/FIC 尚未创建，GitHub Actions 新 Role Variables 尚未配置，真实 Microsoft Entra Exchange、RBAC/Trial Capacity/State 核验及独立 Plan = **OPEN**。Terraform 默认 `identity_creation_approved=false`，任何付费 F SKU 或破坏旧资源的 Apply 仍需单独授权。Task 3.2 保持 OPEN。


## Task 3.2 — 手动 Plan / Apply UI 必须分开（2026-10-20，执行器仍 OPEN）

- 用户进一步明确：**GitHub Environment 审批已放弃，但必须在 Self-Runner Actions 用户界面手工选择 `plan` 或 `apply`，默认 `plan`**。取消 Environment 审批**绝不意味着**可以把 Plan 自动接到 Apply。
- **实际 UI 源码已修改且合并**：Self-Runner PR [#163](https://github.com/JohnZhang-DataForge/Self-Runner/pull/163)，合并 Main `fb1be4292e295fd0824b1af255171a846f541fb2`；`fabric-controlled-entry.yml` 的 `workflow_dispatch.inputs.operation` 为 choice `plan|apply`，默认 `plan`，不再让旧 `bootstrap` 占用手动 UI 选项。内部 Python `bootstrap` offline phase 合同继续保留以兼容原测试。
- **严格阶段语义**：Plan 是一次独立手动 Run，只生成/审查 Plan，不得执行 Apply、触发 Apply Workflow、或在完成后自动推进；Apply 必须重新手动选择，并作为另一个 Run 验证**原保存的准确二进制 Plan**、摘要、不可变源码 Commit、Tenant、Subscription、Root、State 和费用/破坏性操作边界。Plan 成功不等于 Apply 批准；不能在 Apply 中悄悄重新生成不同的 Plan 并直接执行。
- **回归覆盖**：Self-Runner PR #163 的 `Fabric Controlled Entry Contract (Offline)` 必须 success，新增断言下拉框恰为 Plan/Apply 且默认 Plan、无 GitHub Environment 绑定、无 `needs:` 自动链和实际 Terraform Apply 命令。这个验证的是**入口 UI/合同**，不是 Terraform 真实执行。
- **真实状态仍 HOLD**：当前两种入口均只有无云端凭据的离线语法检查；尚未实现受控 Terraform Plan / 保存 Artifact / 二次选择 Apply / Binary Plan 校验 / 真实 Azure/Fabric IAM/State。Task **3.2 checkbox 仍 OPEN**，不因为 UI 改善而标注部署成功。保留 Self-Runner、个人单人运维、不升级 GitHub Plan、不新增 Environment 或仓库；收费 Capacity、新云端资源和历史资源修改仍要独立确认相应安全及成本边界。
