# Tasks — OpenSpec-first Agent Progress Navigation

## 1 — 单一权威与历史保护

- [x] 1.1 审计 main、开放 PR、现有 AGENTS/PROJECT-STATUS/文档/OpenSpec 链接及 Required Gate，冻结原 PROJECT-STATUS 内容和原始 SHA。
- [x] 1.2 保留原 PROJECT-STATUS 全文为同目录历史快照；旧入口改为轻量 Router，不再手工维护 CURRENT/NEXT 或复制工作线 Tasks。
- [x] 1.3 更新权威规则和既有 Agent 入口的描述，明确 OpenSpec Active/Archive、Specs、CODE 与真实 PR/Run 的边界，避免反向引用旧状态。

## 2 — 任务按需导航与验证

- [x] 2.1 精简 AGENTS，保留全部全局安全/目录/分支保护约束，建立 task-aware 的组件/OpenSpec 导航。
- [x] 2.2 实现无写入 Active OpenSpec 索引 CLI（Markdown/JSON），含 OPEN/DONE 摘要、明确 Unknown、无外部请求。
- [x] 2.3 为 CLI 增加标准库单元测试和安全的 PR Hosted CI；确认旧质量规则无需任何维护窗口。

## 3 — 验收

- [x] 3.1 逐项审计文档引用和真实分支 diff，验证历史内容完整、OpenSpec Strict/links/new index CI PASS、原 Required Checks 未改变。
- [x] 3.2 走正常 Protected PR Merge，读回 main、校验 PROJECT-STATUS 是路由而非另一份 CURRENT/NEXT；无真实业务 Runtime 操作。

## Stop / HOLD

在检查中发现需要改动 `.github/quality/scripts/check_repository_layout.py`、冻结旧文件清单、Required Ruleset，或任何 Warehouse/Notebook/Local DP/Marquez 运行组件时停止并单独提案；禁止为通过本次精简而绕过保护。

## Implementation evidence (2026-11-05, candidate branch)

- Source main before edits: `704aa40f40bb257d78308d909458fcfd2dccaa2c`; initial old `PROJECT-STATUS.md` Git blob `249cb533e1b762fc811291e61fbc550a414301e1`, full 39,677 characters preserved verbatim after a history banner in same-directory `PROJECT-STATUS-HISTORY-20261105.md` to protect original relative links.
- `AGENTS.md` shrank from 13,542 to 6,857 characters; the retained safeguards route Code/Native/Runtime tasks to their existing detailed rules without mirroring historical Run facts.
- `PROJECT-STATUS.md` shrank from 39,677 to 2,317 characters; its new body contains only OpenSpec/Code Owner/archival navigation and a standard-library, read-only dynamic index command.
- Index, synthetic offline tests and new GitHub Hosted CI are self-contained. Actual PR check runs and protected merge evidence must be added/verified before closing 2.3, 3.1 or 3.2. No Azure/Fabric/Local K8s/SQL runtime action was authorized or attempted.

## Final protected merge and independent main readback — 2026-11-05 ET

- PR [#694](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/694) merged by normal protected GitHub process. Final code commit: `dcc87c020f0497002718324821b55c625a0f3226`; initial base `704aa40f40bb257d78308d909458fcfd2dccaa2c`.
- Required `OpenSpec Change Gate` [Run #42026743455](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42026743455) and `OpenSpec Static Validation` [Run #42026742997](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42026742997) PASS; docs links #42026743209, naming/CODE-map #42026744155, Local DP static #42026743294, Fabric Notebook offline #42026743138 each PASS on final head.
- New read-only index [Run #42026743158](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42026743158) PASS, 5 synthetic tests; current Checkout had 36 active changes including this Change. After archive it is expected to be absent from Active listings (not a second status table).
- Independent `main` fetch confirmed Agent entry 7,300 characters, PROJECT-STATUS router 2,317 characters and the real index script 4,012 characters. The legacy 39,677-character PROJECT-STATUS content is appended **verbatim** after a clear historical banner; original blob SHA `249cb533e1b762fc811291e61fbc550a414301e1`.
- This Change contains no modification of the protected repository layout checker/baseline, production sources, Fabric Native Items, Warehouse/OMOP data, K8s resources or Azure/Fabric Runtime. Archive/current-spec PR itself also requires Protected Checks and final main readback.
