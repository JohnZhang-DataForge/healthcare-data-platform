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

## Task 3.2 — OIDC issuer, immutable subject and phase-separated execution (2026-10-20; BLOCKER)

### Confirmed from current tracked code and GitHub repository metadata

Self-Runner `fabric-controlled-entry.yml` currently executes **only** unprivileged manual, GitHub-hosted intake. Healthcare `bootstrap/identity/main.tf` independently declares Entra federated credentials with source subjects:

- `repo:JohnZhang-DataForge/healthcare-data-platform:environment:fabric-${var.environment}-backend`
- `repo:JohnZhang-DataForge/healthcare-data-platform:environment:fabric-${var.environment}-deployer`

These are **not compatible** with a future privileged job executed in Self-Runner: its GitHub OIDC JWT is issued for the Self-Runner repository, not Healthcare. Nor can a single job Environment `fabric-<env>-plan` or `fabric-<env>-apply` simultaneously equal the above two distinct role-based Environment subjects. Both issues are independent from A→A′ vs A→B Entra Tenant topology.

**Additional 2026 immutability issue:** GitHub created the Healthcare repo on **2026-10-05** (repo ID `1404947726`) and Self-Runner on **2026-10-11** (repo ID `1413796156`); the owner ID from GitHub API is `337895338`. GitHub's post-**2026-07-15** immutable OIDC default includes owner and repository IDs, e.g. `repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-<env>-plan`. The literal *name-only* subjects in current Identity Terraform Root do not match that documented format. This is a **static incompatibility warning**, not a decoded GitHub JWT or authenticated Entra result. Repository-specific OIDC customization and the actual `sub` claim must still be verified in a separately authorized secure diagnostic; **do not request or print a JWT in PR CI**.

Official references:
- GitHub OIDC subject / post-July-2026 behavior: <https://docs.github.com/en/actions/concepts/security/openid-connect>
- Microsoft immutable-subject migration and `@owner_id/@repo_id`: <https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-github-immutable-subjects>
- Microsoft Entra federated trust: <https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust>

### Intended future trust separation; NOT deployed

| Phase | Workflow boundary | Required distinct trust and evidence |
| --- | --- | --- |
| Intake | Self-Runner manual main, GitHub-hosted, `contents:read` | **No** OIDC, Terraform or paid creation. Always HOLD. |
| Bootstrap | Protected operator/Seed scope, independent initial local State | Inventory and Seed/admin grant; avoid self-bootstrapping Backend; never use Backend/Fabric job token as Seed automatically. |
| Plan | Dedicated protected `fabric-<env>-plan` Environment for the **chosen execution repository** | Source SHA, Tenant A/B, Backend-specific lock rights, distinct Fabric provider identity, actual read-only inventories. Plan's state lock may require data-plane write rights, so do not claim Plan cloud read-only categorically. |
| Apply | Separate protected `fabric-<env>-apply` Environment and independently approved **exact** Plan artifact | New reviewer authorization, binary digest and provenance, source/State/tenant/scope match, no destructive changes; do not reuse controller input as approval. |
| Paid Capacity | Additional independent human billing approval prior to any permitted planning/execution | SKU/Region/Subscription, hourly and recurring cost, approved source, resource ownership and trusted external authorization. |

**Execution-location decision remains gated:** Route A runs privileged jobs inside Healthcare (issuer = Healthcare), with Self-Runner remaining an unprivileged trigger; Route B runs privileged jobs within Self-Runner (issuer = Self-Runner), requiring a deliberate new Entra OIDC subject/Environment model and updated Identity Root. Either route requires at least one reviewed cross-repo trust/dispatch design, phase-specific Env protection/identities, secured Plan artifact custody, and explicit authorization **before** any `id-token:write` or `dw-runner-set` privileged job is introduced. **Do not silently repoint** the existing application credentials; they are default-count-zero source and have not been deployed. No environment is created automatically from untrusted input.

Phase review in Self-Runner PR #151 (<https://github.com/JohnZhang-DataForge/Self-Runner/pull/151>, merged `7f252b2c9eced200b73e23235be7eba466819418`) now reports the repository/Environment mismatch as `FABRIC_PHASE_TRUST_BOUNDARY_HOLD`, and a synthetic JSON Plan action/digest scanner always HOLDs. The Healthcare `tools/fabric_oidc_subject_audit.py` captures the additional immutable subject blocker and fails CI on unreviewed changes to the existing Terraform subjects. Neither tool verifies OIDC authentication, actual binary `.tfplan`, cloud IAM, GitHub Environment protections or real billing approval. Task 3.2 remains OPEN.


## Task 3.2 deployment-gate redesign: GitHub Free organization + private repository (2026-10-20)

**Live administrator inventory (read-only):** `JohnZhang-DataForge` plan = `free`; Self-Runner repository visibility = `private`; `GET /repos/JohnZhang-DataForge/Self-Runner/environments` returned `total=0`, `fabric_environments=[]`. GitHub's official availability documentation states that GitHub Free cannot configure Environments in private repositories, nor use private-repo Environment secrets/variables or native Required Reviewers. This is a **confirmed plan/platform incompatibility**, not a missing reviewer or a temporarily empty inventory.

Sources:
- <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>
- <https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments>
- <https://docs.github.com/en/actions/reference/security/oidc>
- <https://docs.github.com/en/rest/actions/oidc>

### Implications — explicitly fail closed

1. The four original protected `fabric-<env>-(plan|apply)-(backend|deployer)` Environment trust subjects in `bootstrap/identity/main.tf` are **inapplicable to this Free/private execution topology**. Preserve them as a non-deployed alternative; keep `identity_creation_approved=false`. Do **not** set it true against those assumptions, dispatch the current `fabric-oidc-readonly-probe.yml`, create arbitrary insecure Environments, or treat an Environment ACK variable as reviewer evidence.
2. Main-ref immutable OIDC signing **is proven** on Self-Runner by actual issuer Run 39422174619, but the main-ref subject `repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:ref:refs/heads/main` is common to multiple workflows in that repository. Using it for both Tenant A Backend and Tenant B Deployer would **not** enforce role/phase isolation: a GitHub workflow able to mint that JWT may be able to assert either Entra app. Never silently replace four Environment subjects with a shared ref subject.
3. Self-Runner already contains unrelated privileged `azure-infra.yaml`, `azure-terraform-oidc-smoke.yml` and `azure-terraform-landing-blob-write.yml` workflows using Azure OIDC on main. A repository-wide GitHub OIDC customization (`use_default=false`) **changes subjects for all workflows** in the same repository, and could break their existing Entra FICs. Do not change the existing Self-Runner OIDC settings or legacy Azure FICs without an explicit migration/cutover plan.
4. GitHub Free private repository Manual `workflow_dispatch` alone is an execution trigger, **not** a distinct GitHub Environment deployment-review approval. Never claim an automated Plan→Apply safety barrier exists unless a separately validated external approval and artifact-binding service enforces it.

### Preferred zero-upgrade architecture (candidate, not yet deployed)

Create a **dedicated private Fabric execution repository** only after an explicit repository-boundary approval. This avoids changing Self-Runner's already-successful main OIDC/legacy Azure trust. The proposed dedicated repository can be configured with a repository-scoped GitHub OIDC custom Subject claim list including `repo`, `context`, and `workflow_ref`. GitHub documents both customizable subjects and the `workflow_ref` claim. The immutable owner/repository IDs must remain in the resulting `repo` segment.

Use distinct and versioned `main` Workflow files for `backend-plan`, `fabric-plan`, and later separately approved `backend-apply`/`fabric-apply`. With a verified `workflow_ref`-bound JWT Subject, each Tenant A/B Entra Federated Identity Credential can bind to its **own workflow** instead of to a nonfunctional Environment. FIC Subject strings must be derived from *actual dedicated repo OIDC preview and live token claims*, not synthesized from the Self-Runner owner/repository IDs or assumed colon escaping. Entra Apps, roles and State remain separate.

Staged roll-out:
- **Gate A (repo/trust preflight):** authorize dedicated repo creation; test whether custom `workflow_ref` issuer claims work with immutable subjects on GitHub Free/private; read back its custom settings; prove actual role-specific OIDC JWTs on `main`; verify the two subjects differ. No Entra resources yet.
- **Gate B (new identity):** deploy fresh Tenant A/B Entra App/FIC via independently authorized Seed Operator/isolated Bootstrap State; begin with Plan-only, non-destructive token exchange. No legacy App adoption and no assumed Azure RBAC; maintain default-deny creation approvals until Seed authorization.
- **Gate C (Plan):** run isolated new Workspace backend/trial-inventory readback, then approved `terraform plan` using immutable source SHA and verified non-paid Capacity policy. No old State or automatic Apply.
- **Gate D (Apply):** separate, non-GitHub-Environment independent human authorization that binds reviewer/operator identity, approved source SHA, exact saved Plan digest, target tenant/subscription/state key and explicit financial approval. Keep Apply unimplemented/default-DENY until that gate is demonstrably enforceable. A GitHub actor input, dispatch click or repository variable does not count as independent approval.

An alternative is to preserve Self-Runner and explicitly migrate **every** pre-existing default-subject cloud consumer to a custom-subject scheme before switching repo OIDC settings; this has broader regression/cutover risk and is **not** the preferred near-term path. A separately approved manual local Seed/Plan-only execution is also possible but must not be represented as workflow identity isolation or automatic end-to-end delivery.

**Approval and billing boundary:** This OpenSpec change authorizes only the design revision and offline validations. No new repository, OIDC customization, Entra application, Azure resource, Fabric F SKU, GitHub plan upgrade, Terraform State/Plan/Apply or pre-existing IAM mutation is authorized by the discovery alone.

## Final solo-operator choice — Self-Runner Main-ref trust (supersedes earlier executor alternatives)

The user explicitly selects **existing Private Self-Runner**, no Environment check or GitHub Environment reviewer, no new Fabric-Executor, and no Fabric executor in Healthcare Public. This replaces the previous Free/private dedicated-executor candidate. The only approved changes here are source/contracts and ordinary CI validation; cloud-environment creation, protected account credentials, RBAC, State/Apply and paid Capacity remain unperformed.

Two distinct newly created Entra Apps (Tenant A Backend Operator, Tenant B Fabric Deployer) can each have a separate FIC entry bound to the **same** default immutable Self-Runner Main-ref `sub` from a real token. Default GitHub JWTs on a repository/branch are not bound to a workflow or to the intended role. This is an explicitly accepted one-person operational tradeoff, **not** cryptographic role separation: any allowed Main job with `id-token:write` can present the same assertion. Enforce truly least-privileged per-app permission assignment, no reuse of legacy privileged `AZURE_CLIENT_ID`, no unreviewed PR checkout in OIDC jobs, and no self-hosted token job with K8s secrets.

Implement plan-only identity bindings in the new Identity v3 Bootstrap contract; Apply is not activated by creating additional duplicate subject credentials. Cloud Plan requires a fresh isolated State and inspected target; apply requires an explicit, reviewed exact Plan digest and no unapproved billed/destructive operations. Do not interpret `workflow_dispatch` itself as independent reviewer approval. The user intentionally waived GitHub Environment approval for this personal lab.

Evidence: <https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619>; Self-Runner PR #162 and Healthcare PR #320. Previous dedicated executor/Public Healthcare suggestions remain historical, not executable requirements.


## Final manual execution UI contract — Plan / Apply must be separately selected (2026-10-20)

This section refines the **final solo-operator Self-Runner decision above** and **supersedes** all earlier advice that requires GitHub Environment protection or automatically couples Plan and Apply. The user does **not** require Environment / Required Reviewers, a new executor repository, or a two-person approval service for this personal lab. Their **non-negotiable** control is an explicit GitHub Actions **Run workflow** operation selector:

| Manual `operation` | UI default | Allowed meaning | Never allowed |
| --- | --- | --- | --- |
| `plan` | **YES** | Inspect source/target/State and create a Terraform Plan artifact to review, once the live executor exists | Running `terraform apply`, automatically dispatching an Apply workflow/job, promoting a Plan success to approval |
| `apply` | No; operator must select explicitly | In a **new, independent workflow_dispatch Run**, verify and execute the **exact previously generated and reviewed binary Plan** after confirming source SHA, root/environment, State, Tenant/Subscription, digest and cost/destruction safeguards | Automatic chaining from Plan, silently creating a new unreviewed Plan, trusting only a user-typed SHA/digest, unapproved paid Capacity |

GitHub Action `fabric-controlled-entry.yml` in the **existing private Self-Runner repository** now exposes `operation` as a required **choice** with only `plan` and `apply` (default `plan`); the old `bootstrap` option remains internal/offline API compatibility but **not in this UI dropdown**. The selection is wired to the existing offline `--phase` validator. There must be **two separate dispatches / Run IDs / logs**, with no `needs:` Plan→Apply dependency and no automated `workflow_run` / reusable-workflow trigger bridging the phases. `target_environment` is a logical Fabric deployment target input; it is **not** a GitHub Environment approval.

**Present implementation stage:** Self-Runner PR [#163](https://github.com/JohnZhang-DataForge/Self-Runner/pull/163), merged Main `fb1be4292e295fd0824b1af255171a846f541fb2`, updates only the manual **offline HOLD** selector, tests and runbook. This is **not** yet a real Terraform executor: both chosen operations still produce `HOLD`, no Terraform or Azure/Fabric Plan/Apply, no OIDC access, no State access, no billing. Test success validates the UI contract, **not** deployment capability.

**For future live work:** preserve manual Plan vs Apply as separate jobs/runs in the **same Self-Runner repository**, with separate exact immutable artifact verification prior to Apply and auditable Run IDs. Use least-privilege Tenant A/B identities without pretending that a shared Main-ref OIDC subject provides cryptographic workflow separation. Do not enforce GitHub Environment reviewers. Continue to refuse missing/mismatched Plan, unreviewed destructive actions, legacy State adoption and paid F SKU purchases without cost authorization. Never automatically apply immediately after a successful Plan.
