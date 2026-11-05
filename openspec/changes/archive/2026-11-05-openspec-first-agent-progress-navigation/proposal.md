# Proposal — OpenSpec-first agent progress navigation

## Why

目前仓库虽然已经采用 OpenSpec 作为具体变更的唯一 Tasks/证据权威，但根 `AGENTS.md`、文档索引及 Session 规则仍要求 Agent 每次加载约四万字符的 `PROJECT-STATUS.md`。该文件混合 Portal/Local DP/Fabric 等历史 CURRENT/NEXT 和过期运行事件，容易造成重复阅读及错误选择旧的工作结论。本 Change 使启动导航不再依赖人工同步的第二份项目状态。

## What Changes

- 将 `AGENTS.md` 精简为必须遵守的规则、任务分流和 OpenSpec-first 的恢复流程，所有危险运行边界仍明确存在。
- `PROJECT-STATUS.md` 退化为短的兼容导航入口；将原文字保存在同一目录的只读历史快照，保留已有相对链接及 Git 来源。
- 新增基于当前 Git 工作树扫描 `openspec/changes/` 的无外网、无写入索引命令：按 Active Change 列出 Tasks 链接、OPEN/DONE 计数及第一个未完成项。无第二份手工 CURRENT/NEXT，也不依赖手工更新列表。
- 最小范围更新 `documents/README.md`、Engineered governance、OpenSpec config 的权威层级、会话恢复与状态说明；新增脚本单测和 GitHub Actions 静态验证。

## Capabilities

### New Capabilities

- `agent-progress-navigation`: 从 Agent 根入口定位 Active OpenSpec 及本次组件 Owner，动态只读列出真正未完成的变更，而不读取所有历史 Project Status。

## Impact

仅 Git 文档、OpenSpec、只读质量脚本、离线单测和无凭据 GitHub Hosted CI；不修改业务源码、冻结 Baseline/可信 Gate、云端资源、Warehouse/PG 数据或任何真实 Runtime。保留历史中的失败事实与 Run 证据，后续 OMOP 等业务 OpenSpec 的独立压缩不属于本次范围。
