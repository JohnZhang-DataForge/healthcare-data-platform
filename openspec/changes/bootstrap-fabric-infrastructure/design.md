# Design

## Context

用户已批准 [Fabric Multi-Environment Rebuild Design](../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md) 的 2026-10-19 修订：**Bootstrap as Code**、Capacity IaC 可复用或创建付费 F SKU；不开发 Capacity 自动暂停控制器。现有 Terraform 新环境 Root 由 [implement-fabric-multi-environment-terraform](../implement-fabric-multi-environment-terraform/tasks.md) 独立维护，受保护旧 Azure 资源不在本 Change 直接迁移范围内。

## Execution boundary and two deployment modes

| 模式 | Backend / Storage | Entra/OIDC | Capacity | 默认行为 |
| --- | --- | --- | --- | --- |
| `reuse-existing` | 通过显式配置引用独立库存已核实的 `johnzhang/landing`、`tfstate`；旧 `dev/*.tfstate` 不动 | 可在首次管理员授权后创建**新**独立身份，已有应用不自动 Adopt | 已存在并经过验证的 Capacity ID | 只离线 Preflight，不允许任何自动 Apply |
| `fresh-bootstrap` | 在**目标新订阅**创建新的命名隔离 Storage、Landing Container 和 Backend Container；原 `johnzhang` 不复用、不导入 | 管理独立 Tenant A 的 Backend/Reader 与 Tenant B 的 Fabric Deployer；分别授权 | 默认复用 Capacity；可选择创建受预算审批的付费 F SKU | 所有创建审批默认拒绝，缺少授权直接 HOLD |

名称与 State 作用域不得使用旧 `healthcare-omop`、`dev/*.tfstate`、`johnzhang` 作为待创建或待 Destroy 目标。模式是固定 Profile 字段，不得根据空 ID 或 API 查询失败自动切换模式。

## Bootstrap state: eliminate circular dependency

```text
Operator with time-scoped admin seed (manually authorized)
    |
    +--> Phase 0: offline profile + identity + paid-capacity approval checks
    |
    +--> Phase 1: identity/groups/OIDC setup
    |              (isolated Bootstrap State and provider Tenant A/B aliases)
    |
    +--> Phase 2: optional new Storage/containers/RBAC
    |              (controlled local or separately provisioned Bootstrap State)
    |
    +--> Phase 3: independent backend inventory and ownership proof
    |              (NO automatic state mv, import or force-unlock)
    |
    +--> Phase 4: optional approved new Fabric Capacity (cost gate)
    |              OR verified existing Capacity ID
    |
    +--> outputs: verified non-secret IDs + Tenant/State location summary
    |
    +--> separate downstream Fabric Root plan -> approved apply -> fabric-cicd
```

Fresh Mode 的首次 Terraform Backend **不能放在它自己尚未创建的 Storage 上**。使用专门的受保护本地 Bootstrap State 或独立预先存在的受控 Backend；记录安全保管位置、加密、备份、操作者和恢复方法。未来从 Bootstrap State 迁移到持久 Backend 必须先备份、核对 State/资源 UID 与空位，再**单独授权**；不把 `terraform init -migrate-state` 放进默认 Workflow。State 中的 ID、属性和潜在 Secrets 需要视为敏感运维资产。

## Identity and permissions

- **Seed Operator**：已有 Tenant/Subscription 管理身份，负责首次被授权执行 Bootstrap，尽量限时；其权限不可由 Terraform 自授。为 Microsoft Graph、Fabric Tenant Settings、订阅 IAM 和 GitHub Environment 提供的管理员同意各自独立确认。
- **Backend Operator (Tenant A)**：只对批准的 `tfstate` 容器执行读写与锁定；State Blob **Key 前缀不是 Azure RBAC 边界**；不默认授予 `landing` 写权限。
- **Blob Reader (Tenant A)**：只读已核实 Landing，最小 Scope `Storage Blob Data Reader`。Reader 凭据不进入 Terraform 变量、Plan/State 值、GitHub 日志或 CI；Key Vault/Workspace Identity 实际可用性仍需独立核实。
- **Fabric Deployer (Tenant B，当前与 A 为同一 Tenant)**：独立 App/SPN + GitHub OIDC，Fabric API/Tenant 设置、Capacity 与 Workspace 权限需单独验证；Backend/Fabric 两个 Client ID 不得相等。
- GitHub OIDC Federated Credential 的 issuer、audience、subject 应严格绑定到被批准的 Repository + Ref/Environment；**PR 的不受信任代码不能获取可执行云端写入的 Token**。GitHub Environment 保护及首次管理员访问可能需手工完成。
- Provider 候选：`hashicorp/azuread`（Entra 应用/Group/OIDC）、`hashicorp/azurerm`（Storage/Role Assignment）、`Azure/azapi`（目标版本受支持的 Fabric Capacity ARM 资源）；**版本、Provider Schema、实际所需 IAM 需在编码前从官方锁定文档核实**。无需强求跨 Tenant 的所有资源由单个 Provider 实例管理。

## Capacity policy: ownership and billing

- `capacity.mode=reuse-existing` 为默认，`create-new` 不是按任务创建的瞬时计算资源。用户明确批准 Capacity **可由 Terraform 创建**，但**未批准实际购买**。
- 创建需要：Azure Subscription、目标 Tenant、SKU `F*`、Region、Capacity 管理员参数、每小时/月上限的预算估算、被批准的预计持续费用、唯一环境名与库存证明；准确 ARM Schema 和最小 SKU/许可证约束待 Provider 版本验证。
- 将 `capacity_creation_approved=false` 作为默认拒绝，不把单一 Bool 当作账单批准证明。受保护的 Environment 需与不可篡改的 PR SHA、批准者与批准时间/成本证据对应；Plan 出现未批准 Capacity 创建/替换/删除即 HOLD。
- `prevent_destroy`、资源锁或不允许自动 Destroy 可作为纵深防护，但不能替代真实成本监控；**不实施 Suspend/Resume、空闲探测、自动缩容、定时停止、按任务删除 Capacity**。

## Non-secret handoff contract (offline implementation; no live approval)

目标输出仅包含已审查过的 `bootstrap_mode`、`backend_tenant_id`、`fabric_tenant_id`、互异 Client IDs、`storage_account`、`landing_container`、`backend_container`、`backend_state_prefix`、`capacity_id`、`capacity_origin`、`resource_ownership_status` 与执行证据（Source SHA/Run）。新环境 Workspace/Lakehouse/Connection 的现有离线 Root 不依赖尚未创建的 Outputs；后续在跨 Change 合同 PR 接入。

严禁在输出中出现 Client Secret、SAS、Storage Key、OIDC/JWT、GitHub Token、Terraform Plan JSON 或 Key Vault Secret Value。**输出 ID 不代表真实访问已验证**，须标注 `verified=false` 直到独立 Runtime 授权检查。

## Verification, operations and rollback

1. **Design PR**：OpenSpec Strict/Trusted Gate、文档链接检查，只有方案不产生云端副作用。
2. **Offline Profile PR**：Python 严格 Schema、正常/非法/越权/重入/缺失费用审批测试，代码路径更新 Terraform CODE.md 和仅离线 GitHub-hosted CI；不可执行 `init/plan/apply/destroy`。
3. **Identity/Backend/Capacity Terraform PRs**：每个模块单独固定官方 Provider Schema、`fmt -check` 和静态测试；提供默认拒绝且没有凭据值的变量，**没有云端初始化或 Plan**。
4. **Controlled live gates (later authorization)**：单独的只读 Inventory、Init/Plan 审批 → 核对创建清单/账单风险 → Apply 审批 → 独立 API/State/权限读回与证据。
5. **Failure**：未知资源/State/RBAC、费用不明确、目标 Tenant 不匹配、已有同名对象、跨 Tenant 访问失败 = HOLD。最多三轮相同方向失败调试后停下记录精确 SHA、Run、问题原因和尝试，不盲目重试。代码回退靠 Git，旧资源回退**不得以 Destroy 为默认策略**。

## Out of scope

- 在本 Change 中直接替换旧 Self-Runner `azure-infra.yaml` 或现有七 Root。
- 新 Tenant/Subscription 开通、Trial 获取、自动 Fabric Tenant 管理员提权、无授权 Cloud/State 操作。
- Capacity 动态启停或无审批付费创建，Notebook/Pipeline 的 fabric-cicd 正式交付和 OMOP/FHIR/HL7 数据 E2E。

## Controlled Self-Runner intent (offline-only implementation, Task 3.2)

Self-Runner now contains a **separate unprivileged manual intake** `fabric-controlled-entry.yml` (PR #150), independent of old `azure-infra.yaml`. Main-only workflow_dispatch validates target environment, root and exact Healthcare SHA syntax for `bootstrap`/`plan`/`apply`. The Apply intent also requires Plan digest syntax. It uses GitHub-hosted `ubuntu-latest`, never `dw-runner-set`, never OIDC tokens, Terraform, Azure/Fabric, cross-repo checkout or State. Successful input validation returns `HOLD`, **never execution approval**. Each future real phase requires its own explicitly verified protected Environment, SHA/source and saved Plan identity binding, isolated Tenant A/B roles and operator authorization; paid Capacity requires independent billing permission. No live executor is built or authorized yet. The authoritative Self-Runner runbook is <https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/fabric-controlled-entry.md>.
