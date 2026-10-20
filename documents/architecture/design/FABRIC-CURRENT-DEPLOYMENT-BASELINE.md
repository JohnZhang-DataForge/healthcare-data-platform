---
status: superseded
scope: azure-fabric-bootstrap-current-account-and-storage
decision_date: 2026-10-20
implementation_status: partial; live Entra and Terraform Apply not yet proven
---

# Fabric Bootstrap — 当前账号与现有 Storage 固定基线（2026-10-20）

> **SUPERSEDED / 历史事实快照**：2026-10-20 后续讨论已将新目标改为 [Module-first Environment Architecture](FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)。本文记录当时实际账号/Storage 背景和先前同 Tenant Bootstrap 的决策，**不再要求新部署使用三 App/Seed、A=B 模式或 `johnzhang` 固定参数**。旧 Storage/State 的保护要求和已核实事实继续有效，不能因设计转向破坏既有资源。

> **执行前必读 / 本次用户明确确认的决定**。当前部署路径已经定为 **Tenant A = Tenant B**；不能再将 A/B 是否同租户列为待用户回答的问题。**复用现有 Azure Blob Storage、Landing、Terraform State Backend**，其余 Entra 身份/OIDC/RBAC/Fabric 新资源尽量用代码部署。该决定覆盖此前以 `fresh-bootstrap`、新 Storage、新 Tenant、或要求 `johnzhang-fabric` 通过 `az login` 为当前部署前置条件的建议。原有历史记录保留，但不作为当前工作清单。

## 一、已经确认的现状（用户确认 + Azure CLI 实际查询）

| 领域 | 当前部署基线 |
| --- | --- |
| 主账号 / 首次 Seed 人类操作人 | `guangbinzhang8888@gmail.com`；**只作为人工管理员身份背景，不得硬编码为 Terraform/App/GitHub OIDC 登录凭据** |
| 历史 Fabric 子账号 | `johnzhang-fabric`（由主账号所在 Entra 目录中创建，并授予 Fabric 管理员权限）；这是**历史管理员操作主体**，不是新自动化部署的必需身份 |
| Azure Tenant A | `899a04e8-8d3d-486c-88a1-7bdeb22d5f1a`；2026-10-20 Windows PowerShell Azure CLI `az account list --all` 返回 |
| 当前 Fabric Tenant B | **A = B**，同为 `899a04e8-8d3d-486c-88a1-7bdeb22d5f1a`（用户已明确确认；当前设计输入无需重新查询） |
| Azure Subscription | `Azure subscription 1`；`56107520-5920-4e96-9833-5441ded0a90c`；Azure CLI 状态 `Enabled` |
| 稳定 Azure Storage | 已由主账号管理/创建的现有 Storage Account `johnzhang`；**复用而非新建** |
| 业务数据落地 | `johnzhang/landing`，现有发布目标和数据/ACL 原样保留；不是新 Fabric Workspace 的生命周期资源 |
| Terraform Remote Backend | `johnzhang/tfstate`，**保留同一 Storage/Container**，新增 `fabric/<environment>/<root>.tfstate` 等隔离 Key；历史 `dev/*.tfstate` 不迁移、不覆盖 |
| 旧 Fabric Workspace | 主账号/子账号已经创建过 Workspace 和授权；**仅为历史资源，不作为新的 IaC 环境依赖，也不自动 Import/Adopt/Delete/Destroy** |
| 执行仓库 | `JohnZhang-DataForge/Self-Runner`（private, GitHub Free，单人）；`healthcare-data-platform` 保存 IaC 和 OpenSpec。无 GitHub Environment 审批 |
| 自动化交付目标 | Terraform + GitHub Actions + fabric-cicd；分开的手动 Plan 和 Apply Workflow Runs（默认 Plan；绝不 Plan 自动接 Apply） |

**来源与可信程度**：Azure Subscription/Tenant A 的 UUID 与 Enabled 状态已有本次用户贴出的 CLI 输出；A=B、账号关系、现存 Blob、旧 Workspace 的处置意向是用户明确确认的**架构事实/决定**，并不虚构已经独立测过 Blob RBAC、远程 State Key 是否空位、Fabric Capacity、Service Principal API 权限或 Workspace 的实际删除。网页中显示的个人登录 UPN **不得进入应用配置、CI 变量、OIDC Subject 或云端运行日志**。

## 二、当前实施唯一默认路径

1. **`bootstrap_mode=reuse-existing`、`tenants.backend_tenant_id == tenants.fabric_tenant_id`**。其值为上述同一个 Tenant UUID。当前运行时不新建 Tenant、Azure Subscription、Storage Account、`landing` / `tfstate` 容器；不要求 `johnzhang-fabric` 成功 `az login`。
2. 首次授权使用已有**主账号或经其授权的管理员**；自动化需要的 Backend Operator、Blob Reader、Fabric Deployer 分别使用 **三个新 Entra Application + Service Principal**。即使 A=B，也必须各自具有独立 Client ID、最小角色和 GitHub OIDC / Fabric API 授权；**不要求新建一个人类用户账号**。这些身份优先由 Terraform 创建；需要首次 Graph/Tenant/Fabric 管理员同意的操作通过可重放脚本/简明 Runbook 完成。
3. **Storage/Landing 原样保留**：对既有 `johnzhang/tfstate` 精确隔离新 Key 并核查 Backend Operator 的 Blob 数据权限/锁；对 `johnzhang/landing` 仅授予 Blob Reader 所需只读范围。新 Terraform Root **不对已有 Storage、容器、Landing 内容执行 Create/Replace/Delete/Import**；原 Local DP Blob Publisher 不改目标。
4. **State 目的地是现有 `johnzhang/tfstate`**，新组件使用 `fabric/<environment>/<component>.tfstate`。初始 Entra Seed 在 OIDC/Backend Operator 尚不存在时可以使用**短期隔离、加密、可备份的本地 Bootstrap State** 破除认证自举循环；但这只是过渡，必须补齐**审计后的专用 State Key（例如 `fabric/<environment>/identity.tfstate`）持久化/迁移/恢复方案**，不能永久把本地临时 State 当作最终架构，也不能混用 `dev/*.tfstate`。迁移之前不能重复 Apply 产生重复 App。
5. 旧 `johnzhang-fabric`、手工 Workspace/RBAC/旧应用不继续作为新部署的依赖；新的 Workspace/Lakehouse/Connection/Notebook/Pipeline 由 Terraform + fabric-cicd 用不同的隔离名字创建。**“不依赖旧 Workspace”不等于“允许删除旧 Workspace”**；以后若要清理，单独列清单和审查是否被业务/State 引用。未知现存对象时仅对那个对象的破坏性操作 HOLD。
6. Capacity 优先引用真实存在且已授权的 Capacity；若需新建付费 F SKU，必须独立核准费用和购买。当前没有授权创建收费 SKU；不把 Trial 当成免费资源的已验证证据。
7. 实施时先完成当前 A=B 的真实端到端路径，不因可迁移性而重复要求用户出示 Tenant B ID；Tenant/Subscription/Storage 的固定信息纳入当前 Profile/脚本参数生成，但 Azure Blob Container 名称和凭据不作为 Secret 生成或打印。

## 三、跨 Tenant 兼容性：保留设计，不作为当前交付障碍

- **当前部署**：A=B，同一 Entra Tenant 内的两个 Terraform `azuread` alias 可以传入相同 `tenant_id`；各 Provider 角色使用不同 App/权限。
- **将来可选**：A≠B 时只切换显式 `backend_tenant_id`、`fabric_tenant_id` 及各自身份/OIDC/授权；Backend 和 Landing 仍可固定在 A，Fabric 资源在 B。跨租户 Fabric Blob Connection 是否可用要另做 E2E，不保证自动成立。
- **优先级规则**：双 Tenant 扩展若明显增加现阶段复杂度，允许延期；**不得因此阻塞 A=B 的开发、真实 Plan、审核过的 Apply 或 E2E**。

## 四、开发与验收责任

- **OpenSpec 执行进度**：[`bootstrap-fabric-infrastructure/tasks.md`](../../../openspec/changes/bootstrap-fabric-infrastructure/tasks.md)。其中 Task 3.2 真实 Terraform Plan/State/Apply 尚未全部完成，不能因本文写了固定信息就标记为 PASS。
- **方案约束**：[`bootstrap-fabric-infrastructure/design.md`](../../../openspec/changes/bootstrap-fabric-infrastructure/design.md) 及 [多环境总体设计](FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)。此前涉及 `fresh-bootstrap` 的讨论仍是未来可选路径，**不是当前模式**。
- **真实操作**：[`bootstrap/SEED-LIVE-OPERATIONS.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/d95da9f0e62c77b025d466e51f78ad9a48241158/azure-fabric/infra-terraform/bootstrap/SEED-LIVE-OPERATIONS.md)。当前工具中 `fabric_seed_identity_plan.py` 仅为 Seed Plan、尚未触发云端真实执行；新身份 RBAC、GitHub Variables、隔离新 Remote State Key、Fabric Tenant Settings 和 Plan/Apply 都需要逐项真实验收。
- 后续对话无需再问“Tenant A 是否等于 Tenant B”“要不要重新建 Tenant”“原 `johnzhang-fabric` 为什么不能 CLI 登录”“要不要重建 Storage/Landing”；**只有真正执行时缺少的具体非敏感 ID、角色权限或容量证据才按单步询问**，并以本文件作为默认输入。
