# Tasks

> **Active / Design First**：Bootstrap as Code + paid Capacity Terraform *ability* 已经用户批准，但**所有真实云端写入、Terraform Init/Plan/Apply/Destroy/Import 与购买付费 Capacity 均未授权**。开发以小 PR/离线证据完成，按真实 Main SHA 和 Run 更新。

## 0. Approved boundary and Change creation

- [x] 0.1 从 Main 核对已批准的 Fabric 多环境修订、现有独立 Root/旧 State 边界和开放 PR；创建专用 Bootstrap OpenSpec Change（仅设计/文档）。
- [ ] 0.2 正式验证并合并此 Design/Proposal/Spec/Tasks PR；将原 `implement-fabric-multi-environment-terraform` Task 0.2 链接到本 Change。**设计通过不等于已实施**。

## 1. Offline Bootstrap contract

- [ ] 1.1 固定 `reuse-existing` 与 `fresh-bootstrap` 配置 Schema；拒绝旧 Storage/State 的误创建、自动 Adopt、环境跨 Tenant 混淆、Secret 字段和非法命名。
- [ ] 1.2 定义 Seed Operator、Backend Operator、Fabric Deployer、Blob Reader 应用与 GitHub OIDC Environment/Repo/Ref 映射的非敏感输入/输出合同；防止身份复用及跨租户错误。
- [ ] 1.3 定义 Capacity `reuse-existing` 默认与 `create-new` 单独允许方案，必须携带 Subscription/Region/SKU、实际账单审核证明；缺失默认 HOLD。不得实现自动 Suspend/Resume。
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
