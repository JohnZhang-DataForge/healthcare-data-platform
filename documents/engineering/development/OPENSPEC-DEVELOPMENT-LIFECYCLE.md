# OpenSpec 开发接力与 PR 生命周期（G4）

> 状态：G4 治理规则，**G0–G4 已验证并合并**；参见 [正式计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md)。G4 的边界是未创建业务 Specs/Changes，未搬迁或执行业务代码；G5 原应事前建 Change，实际源码搬迁 PR #225–#227 先行发生；现在通过 [Active 追溯 Change](../../../openspec/changes/relocate-local-data-platform/tasks.md) 纳管，运行验证未完成。
>
> 适用权威：[G0–G7 实施计划](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md)、[Development Workflow](DEVELOPMENT-WORKFLOW.md)、[安全操作](../operations/SAFE-OPERATIONS.md)、[Session Coordination](SESSION-COORDINATION.md)。本页解释职责和接力，不建立新的自动执行器/锁服务。

## 生命周期：事实载体与退出条件

| 过程 | 事实载体和责任 | 必须满足 |
| --- | --- | --- |
| Explore | Agent 核对最新双仓 Main、开放 PR、权威状态、代码/Contract、影响范围和资源风险 | 只读；未知并行工作需协调 |
| Proposal / Design / Delta Specs / Tasks | 用户确认需求后，Agent 在 Healthcare OpenSpec Change 中以英文功能名建立文件、中文说明；代码标识和官方语法仍为英文 | G4 只验证方法；首个正式业务 Change 要等 G5 |
| Implement / PR | Healthcare 功能分支维护 canonical source、测试与 CODE.md，PR 保存 Base/HEAD | PR 未合并不是 Main 生效；不得擅自修改冻结运行标识 |
| Static / Test | Healthcare PR 上的 OpenSpec、命名/CODE Map、文档链接 CI；独立 Self-Runner 静态接力可按准确 SHA 额外验证 | 0 Specs 的 Validate PASS 仅是空集通过，不是业务验收 |
| Runtime / Readback | 仅在用户针对具体共享动作授权、资源协调并通过安全 Gate 后进行 | 独立 Run/Artifact 和读回证明相应事实；静态 PASS 不表示写入成功 |
| Merge / Sync | Review、核对最终 PR HEAD 与 CI，合并后确认 Main；仅将已经实施并证实的可观察行为同步 Current Specs | 设计批准不等于实现；不得把尚未实施的目标写成 Current |
| Archive | 相应功能已实施、经适用测试/真实读回、验收条件满足并审查 Archive PR | 单独 CLI Validate PASS 或 PR Merge 不能自动 Archive；G5 设计阶段不得归档 |


## OpenSpec Change Gate（2026-10-18 治理改造）

对 **代码、GitHub Workflow、架构、OpenSpec / AGENTS 治理、CODE.md 与运行配置**的变更，Agent 应先创建或选定 `openspec/changes/<id>/` 的 Active Change，再进入实施 PR。PR Body 必须在独立行写：

```text
OpenSpec-Change: enforce-openspec-change-gate
OpenSpec-Task: 2.3
```

- Change 需要 `.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md`，Task 编号必须在 `tasks.md` 中存在，且本 PR 必须修改对应 `tasks.md`；一个 Change 可覆盖多个有界 PR。
- 只有**非架构、非工程治理**的文档类 PR（`README.md` 或允许的 `documents/**/*.md`，排除 `documents/architecture/**`、`documents/engineering/**`、`documents/README.md` 和所有 `CODE.md`）可在 PR Body 独立写 `OpenSpec-Exemption: docs-only`，且不可夹带任何代码、配置、工作流或 OpenSpec 修改。
- Archive PR 必须关联原 Change、由 Active 移动到 Archive、完成全部 Task；归档不代表部署验证。
- 新 [OpenSpec Change Gate Workflow](../../../.github/workflows/openspec-change-gate.yml) 是全 PR 触发的**静态关联检查**，与原 OpenSpec Schema/CLI Validate 分工互补；由 [Policy Checker](../../../.github/quality/scripts/check_openspec_change_gate.py) 实现严格路径与 Tasks 同步验证。原来 G4 的 0 Active Changes Validate PASS 不再能作为实质性 PR 无 Change 的放行依据。
- **受信任策略执行**：新增 [Trusted Change Gate](../../../.github/workflows/openspec-trusted-change-gate.yml) 从默认分支运行受信任 Python Checker/单测，只把候选 PR checkout 当数据，不执行候选代码。与普通 Head CI 分离；管理员应将可信 Job 设为 Required 并确认组织/仓库的 `pull_request_target` Actions Policy（GitHub 官方 2026-11-02 公共仓库默认策略切换需留意），不可仅凭 Workflow 文件存在认定受信任门禁已生效。
- **合并保护区别**：CI 失败与 Main 确实禁止合并不是一回事；须在 GitHub Rulesets/Branch protection 设置 `OpenSpec Change Gate / require-change` 为 Required，并核对 bypass 权限。当前集成读取 `branches/main/protection` 返回 HTTP 403，尚不能确认或配置 Required。不要把普通 PR CI SUCCESS 当作 Required 已生效的证据。
- 当任务完成后，准确 SHA/Run/必要 Runtime 读回由原 PR 和 `tasks.md` 共同记录；运行验收未达到时保持 Change Active，不为了合并先全部打勾。

## 新 Session 的恢复流程

读取 AGENTS.md → documents/README.md → PROJECT-STATUS.md → relevant component CODE.md 和本页。再次核对 Healthcare 和 Self-Runner 最新 Main SHA、开放 PR、Branch/HEAD、目标 Change/Tasks、相关 Run/Artifact 及历史 PR/Issue 评论。旧聊天摘要只供线索，不能代替准确 Git/Run 证据。没有正式 Change（包括 G4）则继续使用 PR/Issue 接力，不创建虚假 Change。

PR/Issue 的最小可恢复记录：Done / Not Done / Next，Repo、Branch、Base/HEAD 完整 SHA，受影响文件、成功与失败 Run/Artifact 链接、每个问题的当前尝试次数、风险、环境副作用、HOLD 条件、下一安全动作。跨 Session 必须继承已有失败次数。一个变更不再另建一份按 Session 编号的 Handoff Markdown。

## 三轮失败停止规则（人工强制，不冒充自动实现）

同一故障的一轮是：分析 → 修改 → 验证。结果失败即计入一次；同一问题连续第 3 次仍失败，或更早已无新证据，Agent 必须停止自动修改/重试，不得重开 Session 或改名清零。不同问题分别计数。

停止时**优先在当前开发 PR 的 Conversation 评论**登记：Issue/Symptom、Attempts 1–3 及原因、完整 Base/HEAD SHA、Branch、Workflow Run/Artifact 链接、确认或待确认的副作用、尚未证实假设和 Safe Next。没有 PR 时在对应 GitHub Issue 记录。用户决定是否继续或改方向；Workflow 和 Artifact 负责详细日志，不重复建立历史 Handoff 文件。

## Self-Runner 的独立静态接力

历史 Self-Runner cross-repo-generic-pr-v4、cross-repo-target-head-v2、cross-repo-pr-binding-v3、cross-repo-report-gate-v6 等 Workflow 中仍有 healthcare/docs/BASELINE.md 的旧断言。该路径已从 Healthcare 当前 Main 删除。G4 **不直接复用或放宽历史 Workflow**，也不让静态 CI 接触 dw-runner-set。

新的 [Healthcare OpenSpec PR Handoff (Static)](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/healthcare-openspec-pr-handoff.yml) 只在 Self-Runner 私有仓库运行（需访问权限），使用 GitHub-hosted ubuntu-latest：

- Self-Runner 自身 PR 静态运行 Policy 正向/负向单元测试。
- 推送 feature/** 分支中仅改变固定请求路径 config/targets/healthcare/openspec-pr-handoff.json 的提交，触发单独只读检查。请求仅允许 schema_version、request_id、target_repo、target_ref、target_sha、pr_number、base_ref 和 mode=validate；拒绝 shell、execute、未知字段或多文件混合提交。
- 从 GitHub 实时读取 Healthcare PR 的状态、base/main、head/repo/ref/SHA，并核对远程分支 SHA，拒绝 Stale；checkout 精确目标 SHA，验证 AGENTS、项目状态和 OpenSpec 配置，使用 Node22 + OpenSpec CLI 1.14.3 执行官方 Schema 和 strict validate。
- 不执行目标仓库自带 Python/Shell/DAG、Terraform/Apply、数据库写入、K8s/Airflow/Spark；只产生 GitHub Run/Artifact 证据。新 PR HEAD 必须重新绑定。上传结构化报告包含 controller_sha、target_sha、target_pr、run_id 和运行边界。文件清理触发的无请求 Run 必须标记未执行目标验证。
- 不能因 Self-Runner 仓库私有就假设 Healthcare 公共仓库能够直接调用私有 reusable Workflow；采用独立受控请求，不通过任何可注入的 Action/Shell 参数传递目标代码。

## G4 完成与 G5 入口

G4 的完成门槛是两仓 PR/最终 SHA、策略正负向单测、真实 Healthcare PR 准确 HEAD 绑定成功的 Self-Runner Run、Healthcare PR 适用 CI PASS，并记录失败及未授权边界。这些已在 Healthcare PR #220、Self-Runner PR #136 与 [正式计划的 G4 证据表](../migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 中验证并收口。G4 当时确未移动源码；但此后 PR #225–#227 已完成目录级迁移，正式 Change 是事后追溯建立而非先行审批。以后仍应遵循本文件规定的事前 Change 生命周期；本轮治理 Change `enforce-openspec-change-gate` 正在实现 PR/Task 的自动绑定，Branch protection Required/Bypass 配置仍须独立证实。
