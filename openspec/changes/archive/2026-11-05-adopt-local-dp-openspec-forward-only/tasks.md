# Tasks — Local DP OpenSpec Forward-Only Governance

## 1. 基线和职责

- [x] 1.1 在最新 main 和开放 PR 上只读核对现有 Local DP README/CODE、旧 TASK005 计划、Active relocation Change 与已有 OpenSpec Trusted Change Gate；确认历史代码无需迁移。
- [x] 1.2 在根 AGENTS/工程 Agent 规则和 Local DP 系统 README 定版 forward-only：旧 TASK/代码/证据保留，新实质功能和配置变更只使用 Active OpenSpec。
- [x] 1.3 明确旧 TASK005 Condition 计划与 relocation Change 均不作为未来 Condition 开发的另一套 CURRENT/NEXT；列出新功能分流及 CODE/test 唯一归属，不创建新业务功能 Change 或未实现的任务。

## 2. 无 Runtime 的治理验收

- [x] 2.1 审计本分支 diff：0 Local DP 实际源码/历史 Contract/部署/数据/Required Gate 改动；文档链接和历史固定记录均可追溯。
- [x] 2.2 PR 绑定本 Change；OpenSpec Strict、Trusted Change Gate、Docs Links、适用 CODE-map/命名检查 PASS，保持运行环境完全未接触。
- [x] 2.3 正常 protected Merge 到 main，独立从 main 读回 forward-only 规则；证据确认后在 Archive PR 关闭并进入 Current Specs。

## Hard stop

如需修改可信 Layout/Change Checker、Main Ruleset、冻结 Baseline、旧 `task004_*` 运行标识或共享业务 Runtime，另立变更并先获用户批准。此 Change 不授权 Condition 代码、PostgreSQL COMMIT 或任何历史批次重放。

## Evidence / scope notes (before PR CI)

- Base main `3ebc7baf153383d9646b724cde8c96603dee5eb8`; open PR search returned none. Existing Local DP Source/CODE and historic TASK005 Condition design were read only.
- This Change updates `AGENTS.md`, `documents/systems/data-platform/{README.md,spark/README.md,omop/README.md}`, engineering Agent Rules and OpenSpec Lifecycle plus its own OpenSpec files. **No files under `local-data-platform/`, `.github/quality/`, `.github/workflows/` or `shared-data-engine/` are changed**; no new Condition implementation claimed.
- The existing `relocate-local-data-platform` Active Change continues its own cleanup scope, and TASK001–TASK005 historical records retain original authority at their recorded SHA. Future Condition needs a separate Active Change and current-code review.
- The pre-PR self-audit confirms the intended file list; final trusted PR, CI, merge and main readback remain pending tasks 2.2–2.3.

## Final gate evidence — 2026-11-05 ET

- [PR #696](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/696) merged normally through protected main. Base `3ebc7baf153383d9646b724cde8c96603dee5eb8`; final main commit `a41710c9095dc4ae5de22580bd399dd2cdad1dda` verified independently.
- Final head `81a21bc02942c7b28f3dcd08245a85ba37686a34` CI PASS: Trusted OpenSpec Change Gate [#42052884640](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42052884640), Strict OpenSpec [#42052884785](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42052884785), Documentation Relative Links [#42052884681](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42052884681), OpenSpec Active Index Readonly [#42052884641](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42052884641).
- Changed files: six existing entry/governance Markdown documents and five new OpenSpec files only (11 total). No business source, `local-data-platform/`, `shared-data-engine/`, `.github/` protected Gates, legacy evidence/Contracts, or shared Runtime/PG mutation.
- Independent `main` readback confirmed forward-only policy in `AGENTS.md`, `documents/systems/data-platform/README.md`, `omop/README.md` and `AGENT-RULES.md`. Old TASK005 remains Git history design only; Condition implementation **NOT STARTED**.
- This archive/current spec PR separately requires its own Protected OpenSpec, links and index CI plus main readback. This Change accepts governance only; no business or Runtime verification claim.
