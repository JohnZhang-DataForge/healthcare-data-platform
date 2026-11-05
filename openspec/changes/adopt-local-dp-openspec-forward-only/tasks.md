# Tasks — Local DP OpenSpec Forward-Only Governance

## 1. 基线和职责

- [x] 1.1 在最新 main 和开放 PR 上只读核对现有 Local DP README/CODE、旧 TASK005 计划、Active relocation Change 与已有 OpenSpec Trusted Change Gate；确认历史代码无需迁移。
- [ ] 1.2 在根 AGENTS/工程 Agent 规则和 Local DP 系统 README 定版 forward-only：旧 TASK/代码/证据保留，新实质功能和配置变更只使用 Active OpenSpec。
- [ ] 1.3 明确旧 TASK005 Condition 计划与 relocation Change 均不作为未来 Condition 开发的另一套 CURRENT/NEXT；列出新功能分流及 CODE/test 唯一归属，不创建新业务功能 Change 或未实现的任务。

## 2. 无 Runtime 的治理验收

- [ ] 2.1 审计本分支 diff：0 Local DP 实际源码/历史 Contract/部署/数据/Required Gate 改动；文档链接和历史固定记录均可追溯。
- [ ] 2.2 PR 绑定本 Change；OpenSpec Strict、Trusted Change Gate、Docs Links、适用 CODE-map/命名检查 PASS，保持运行环境完全未接触。
- [ ] 2.3 正常 protected Merge 到 main，独立从 main 读回 forward-only 规则；证据确认后在 Archive PR 关闭并进入 Current Specs。

## Hard stop

如需修改可信 Layout/Change Checker、Main Ruleset、冻结 Baseline、旧 `task004_*` 运行标识或共享业务 Runtime，另立变更并先获用户批准。此 Change 不授权 Condition 代码、PostgreSQL COMMIT 或任何历史批次重放。
