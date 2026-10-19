# Tasks

## 1. 审计与 Change 入口

- [x] 1.1 核对 Main `8a146cf5f5ed4fde8d6a20c7f6d80c62ce81442c`、Engineering 的 19 个 Markdown 及已有两个 Active Changes 的未完成事实。
- [x] 1.2 先建立 `engineering-governance-cleanup` 的 Proposal、Design、Tasks，明确 Engineering/OpenSpec/Project Status 的唯一权威和旧历史保留政策。
- [ ] 1.3 将治理 Change **先以独立 PR** 完成 Strict Validate、Required Trusted Gate 与 Main 合并，记录 PR/HEAD/Run/Main SHA。

## 2. 权威与入口清理

- [ ] 2.1 保留 19 个原文件，纠正 Engineering/README、documents/README、AGENTS 和 config 的 CURRENT 与导航；明确 **Change→OpenSpec，通用规则→Engineering**。
- [ ] 2.2 将历史 G0–G7 实施计划、文档迁移审计标为历史记录，取消“唯一现行 G5/G6 Tasks”的误导；不修改旧验收事实。
- [ ] 2.3 给 Legacy R2–R5 建立独立 `modernize-legacy-task-code` 待授权 Change，并把原 Refactor Plan 标为历史静态清单；不得触碰任何旧 ID 或部署。
- [ ] 2.4 `PROJECT-STATUS.md` 仅汇总跨项目进度及两个已有 Change/待实施 Legacy Change；不复制具体实施 Tasks。
- [ ] 2.5 复核开发生命周期、Session 与文档治理中所有“G5 尚未开始”“Current Change 为空”等过时 CURRENT；标记纯历史快照的时态，不篡改当时证据。

## 3. 测试、合并与归档

- [ ] 3.1 正式实施 PR 的所有适用 CI 对准确 HEAD SUCCESS（尤其 `require-trusted-change`、`validate-openspec`、相对链接检查）；检查 diff 仅限文档/OpenSpec。
- [ ] 3.2 正式实施 PR 合并 Main 后，确认文件 19 份、相关 Change 的准确状态与必要的证据回填。
- [ ] 3.3 清理 Change 自身的 Done/Not Done/Run 记录，若前面任务均有证据，提交独立 Archive PR；不得归档尚未完成的 `relocate-local-data-platform` 或 `enforce-openspec-change-gate`。
