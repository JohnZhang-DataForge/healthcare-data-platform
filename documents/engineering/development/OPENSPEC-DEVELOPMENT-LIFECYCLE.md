# OpenSpec 开发接力与 PR 生命周期（G4）

> 状态：G4 治理规则。G0–G3 初始化及 CI 不变；G4 不创建业务 Specs/Changes，不搬迁或执行业务代码。
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

G4 需要两仓 PR/最终 SHA、静态单测正向/负向、至少一个真实 Healthcare PR 绑定与准确 HEAD 的 Self-Runner Run、Healthcare PR 自身的适用 CI PASS、失败/未授权边界清晰，并完成状态和计划登记。未实际执行的 Gate 只能写 NOT VERIFIED。G5 才可以独立设计 relocate-local-data-platform Change；G4 不移动 Data Platform 源码。
