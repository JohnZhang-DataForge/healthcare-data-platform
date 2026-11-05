# Tasks — OpenSpec-first Agent Progress Navigation

## 1 — 单一权威与历史保护

- [ ] 1.1 审计 main、开放 PR、现有 AGENTS/PROJECT-STATUS/文档/OpenSpec 链接及 Required Gate，冻结原 PROJECT-STATUS 内容和原始 SHA。
- [ ] 1.2 保留原 PROJECT-STATUS 全文为同目录历史快照；旧入口改为轻量 Router，不再手工维护 CURRENT/NEXT 或复制工作线 Tasks。
- [ ] 1.3 更新权威规则和既有 Agent 入口的描述，明确 OpenSpec Active/Archive、Specs、CODE 与真实 PR/Run 的边界，避免反向引用旧状态。

## 2 — 任务按需导航与验证

- [ ] 2.1 精简 AGENTS，保留全部全局安全/目录/分支保护约束，建立 task-aware 的组件/OpenSpec 导航。
- [ ] 2.2 实现无写入 Active OpenSpec 索引 CLI（Markdown/JSON），含 OPEN/DONE 摘要、明确 Unknown、无外部请求。
- [ ] 2.3 为 CLI 增加标准库单元测试和安全的 PR Hosted CI；确认旧质量规则无需任何维护窗口。

## 3 — 验收

- [ ] 3.1 逐项审计文档引用和真实分支 diff，验证历史内容完整、OpenSpec Strict/links/new index CI PASS、原 Required Checks 未改变。
- [ ] 3.2 走正常 Protected PR Merge，读回 main、校验 PROJECT-STATUS 是路由而非另一份 CURRENT/NEXT；无真实业务 Runtime 操作。

## Stop / HOLD

在检查中发现需要改动 `.github/quality/scripts/check_repository_layout.py`、冻结旧文件清单、Required Ruleset，或任何 Warehouse/Notebook/Local DP/Marquez 运行组件时停止并单独提案；禁止为通过本次精简而绕过保护。
