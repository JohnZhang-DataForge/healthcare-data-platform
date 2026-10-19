# Tasks

## 1. 审计与 Change 入口

- [x] 1.1 核对 Main `8a146cf5f5ed4fde8d6a20c7f6d80c62ce81442c`、Engineering 的 19 个 Markdown 及已有两个 Active Changes 的未完成事实。
- [x] 1.2 先建立 `engineering-governance-cleanup` 的 Proposal、Design、Tasks，明确 Engineering/OpenSpec/Project Status 的唯一权威和旧历史保留政策。
- [x] 1.3 治理 Change 已先于实施由 [PR #236](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/236) 合并 Main `dc98f621bb0ee12d89518721fcfd3f90ba046d60`，准确 HEAD `12f4152261c148ea97ee67b60af52de2825980db`，可信 Change Gate、OpenSpec Strict、文档链接及普通 Gate 均 SUCCESS；原 Proposal/Design/Tasks 没有夹带实施文件。

## 2. 权威与入口清理

- [x] 2.1 保留 19 个原文件，纠正 Engineering/README、documents/README、AGENTS 和 config 的 CURRENT 与导航；明确 **Change→OpenSpec，通用规则→Engineering**。
- [x] 2.2 将历史 G0–G7 实施计划、文档迁移审计标为历史记录，取消“唯一现行 G5/G6 Tasks”的误导；不修改旧验收事实。
- [x] 2.3 给 Legacy R2–R5 建立独立 `modernize-legacy-task-code` 待授权 Change，并把原 Refactor Plan 标为历史静态清单；不得触碰任何旧 ID 或部署。
- [x] 2.4 `PROJECT-STATUS.md` 仅汇总跨项目进度及两个已有 Change/待实施 Legacy Change；不复制具体实施 Tasks。
- [x] 2.5 复核开发生命周期、Session 与文档治理中所有“G5 尚未开始”“Current Change 为空”等过时 CURRENT；标记纯历史快照的时态，不篡改当时证据。

## 3. 测试、合并与归档

> 本次实施只更改文档与 OpenSpec；以下验收任务尚待真实 PR HEAD 的 CI 和 Main Merge，不提前声明 PASS。


- [x] 3.1 正式实施 [PR #237](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/237) 最终 HEAD `ce890cda665a207d398e0bad9318257f167cc1b8` 上适用 CI 均 SUCCESS：[OpenSpec #39186625899](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39186625899)、[Docs Links #39186625844](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39186625844)、[Component #39186626009](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39186626009)、[OpenSpec Change Gate #39186625956](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39186625956)，受信任 `require-trusted-change` SUCCESS；Docs 77 篇 / 链接 1,073 个 / missing 0，质量单测 63 PASS。Diff 仅限文档、AGENTS 和 OpenSpec。
- [x] 3.2 PR #237 已 Squash Merge Main `07fb861a3b2e106d4f31f8fd44de2fd74f48668c`；只读 Main Git Tree 复核 `documents/engineering/**/*.md` **19/19 均保留**，现有 `relocate-local-data-platform` 与 `enforce-openspec-change-gate` 继续 Active、Legacy `modernize-legacy-task-code` 为 Proposed/Active（R2–R5 全部未开始），历史 Archive 不变。
- [x] 3.3 在本**独立 Archive PR** 中将本 Change 全部文档从 `openspec/changes/engineering-governance-cleanup/` 移入 `openspec/changes/archive/2026-10-18-engineering-governance-cleanup/`，并更新项目总览引用；仅在 Archive PR Required CI 全部通过且合并 Main 后归档正式生效。其他两项未完成的 Active Changes 以及拟议 Legacy Change 不归档、不修改执行状态。
