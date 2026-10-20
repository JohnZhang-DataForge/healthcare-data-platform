# Tasks

> **Active / Design First**：Bootstrap as Code + paid Capacity Terraform *ability* 已经用户批准，但**所有真实云端写入、Terraform Init/Plan/Apply/Destroy/Import 与购买付费 Capacity 均未授权**。开发以小 PR/离线证据完成，按真实 Main SHA 和 Run 更新。

## 0. Approved boundary and Change creation

- [x] 0.1 从 Main 核对已批准的 Fabric 多环境修订、现有独立 Root/旧 State 边界和开放 PR；创建专用 Bootstrap OpenSpec Change（仅设计/文档）。
- [x] 0.2 正式验证并合并此 Design/Proposal/Spec/Tasks PR（PR #278，Merge `f0290ca1bea87e054794576bc5803e8f1e060ac8`）；将原 `implement-fabric-multi-environment-terraform` Task 0.2 链接到本 Change。**设计通过不等于已实施**。

## 1. Offline Bootstrap contract

- [x] 1.1 固定 `reuse-existing` 与 `fresh-bootstrap` 配置 Schema（离线 Profile v1 + 负向测试 + CI；仅静态合同，未获得 Live 授权）；拒绝旧 Storage/State 的误创建、自动 Adopt、环境跨 Tenant 混淆、Secret 字段和非法命名。
- [x] 1.2 定义 Seed Operator、Backend Operator、Fabric Deployer、Blob Reader 应用与 GitHub OIDC Environment/Repo/Ref 映射的非敏感输入/输出合同；防止身份复用及跨租户错误。
- [x] 1.3 定义 Capacity `reuse-existing` 默认与 `create-new` 单独允许方案，必须携带 Subscription/Region/SKU、实际账单审核证明；缺失默认 HOLD。不得实现自动 Suspend/Resume。
- [ ] 1.4 提交离线 Python 单测（合法、失败、重复/防碰撞、费用拒绝）和 GitHub-hosted *no-cloud* CI，更新 Azure Terraform `CODE.md` 与 Runbook。

## 2. Terraform Bootstrap modules (code only until separately approved)

- [ ] 2.1 核对固定版本的 AzureAD/AzureRM/AzAPI 官方 Provider Schema/权限；区分 Tenant A/B 和 GitHub OIDC 最小授权，提交冻结的官方资料引用。
- [ ] 2.2 实现隔离 Identity/SPN/Group/OIDC Root/Modules；不创建原 `github-terraform` 的重复同名 App、不自动接管旧 App；默认拒绝写操作。
- [ ] 2.3 实现可选 fresh Storage/Containers、最小 RBAC 和独立的初始 Bootstrap State 策略；阻止 backend 自举循环、旧 `dev/*.tfstate` 和 `johnzhang` 资源接管。
- [ ] 2.4 实现 Capacity 的 `reuse-existing` / `create-new` Resource/Output；使用经过验证的官方 ARM Schema，付费创建在 CI/Root 中默认拒绝，`prevent_destroy` 与预算/人工审批不互相代替。
- [ ] 2.5 为所有 Terraform Root 增加纯离线 `fmt`/静态合同和负向测试；PR CI 禁止执行 `init/plan/apply/destroy/import` 或访问云端。

## 3. Integration and controlled operational readiness

- [ ] 3.1 非敏感 Bootstrap 输出交接到 `implement-fabric-multi-environment-terraform` Task 0.3，确保已有 Workspace/Lakehouse/Connection 唯一所有权与 Capacity ID 来源可审核。
- [ ] 3.2 单独设计受控 Self-Runner 新入口，区分 Bootstrap/Plan/Apply 权限环境；旧 `azure-infra.yaml` 不被替换，禁止 PR CI 拿云端写 Token。
- [ ] 3.3 完成按精确 HEAD 的离线验收、变更范围安全核对、真实运行前置授权清单；**未获得单独授权不得验证 Live 环境**。
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
