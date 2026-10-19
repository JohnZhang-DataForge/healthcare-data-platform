# Design

## Context and audited inventory

审计基线：Healthcare Main `8a146cf5f5ed4fde8d6a20c7f6d80c62ce81442c`，`documents/engineering/` 有 **19 个 Markdown**。两项已有 Active Change：
- [`relocate-local-data-platform`](../../relocate-local-data-platform/tasks.md)：393 业务文件物理目录移到 `local-data-platform/`，文档/CODE Map 和 `.github/quality/` 已搬；Import、Docker、GitSync、Spark 与 E2E 等 **仍待完成**。
- [`enforce-openspec-change-gate`](../../enforce-openspec-change-gate/tasks.md)：可信 CI、Main Ruleset #25365902 与受控正反 PR 均通过；治理收尾/Current Spec/Archive **仍待完成**。

## Classification of the 19 existing Engineering documents

| 类别 | 数量 | 文件 | 后续权威 |
| --- | ---: | --- | --- |
| 长期开发/安全/测试/协作规范 | 7 | `development/AGENT-RULES.md`、`CODE-ORGANIZATION-AND-NAMING.md`、`DEVELOPMENT-WORKFLOW.md`、`DOCUMENTATION-GOVERNANCE.md`、`OPENSPEC-DEVELOPMENT-LIFECYCLE.md`、`SESSION-COORDINATION.md`、`TESTING-AND-EVIDENCE.md` | Engineering，仅描述通用政策，不存具体 Change Tasks |
| 通用源码导航 | 1 | `development/CODE.md` | Engineering；真实代码所有权导航 |
| 运维规则和索引 | 2 | `operations/README.md`、`SAFE-OPERATIONS.md` | Engineering，保留共享资源安全门槛 |
| 跨系统总览 | 1 | `status/PROJECT-STATUS.md` | Engineering，仅 CURRENT/NEXT 总览，细节链接到 Active Change |
| 历史审计/Bootstrap/迁移记录 | 7 | `migration/FINAL-DOCUMENTATION-AUDIT.md`、`LEGACY-DOCS-SNAPSHOT.md`、`MIGRATION-STATUS.md`、`OPENSPEC-BASELINE-AUDIT.md`、`OPENSPEC-IMPLEMENTATION-PLAN.md`、`OPENSPEC-READINESS.md`、`development/LEGACY-CODE-REFACTOR-PLAN.md` | 保留真实历史、旧路径与当时状态；**不再维护为实时任务账本** |
| 总索引 | 1 | `engineering/README.md` | 引导到长期规则、历史索引与 OpenSpec |

合计 7+1+2+1+7+1 = 19。

## Authority & migration decisions

1. **不移动、删除 19 个历史/长期文件的物理位置**；只修改过时的权威声明、导航及必要的时态。历史 G0–G7 表格保留为 *as-written*，标注原方案和当前执行偏差，避免重写 2026-10-16/18 的验收事实。
2. 旧 `LEGACY-CODE-REFACTOR-PLAN.md` 的源目录 `apps/`、`airflow/`、`scripts/` 等表示 2026-10-16 老树，**不是现在根目录结构**。保留原清单；新 Active `modernize-legacy-task-code` 收编 R2–R5（R1 新代码命名已有规则），仅追踪未来有明确授权时才实施。其 R4 持久接口/镜像需要在 `relocate-local-data-platform` 的 Runtime 兼容验收之后启动。
3. 现行 OpenSpec G0–G7 实施计划是 Bootstrap 历史（已验证 G0–G4、G5/G6 实际顺序与原设计不同，G7 是持续工作模式），不再指挥新 PR 或复制 Task 4.x；`relocate-local-data-platform` 与治理 Change 各自负责现行 Task 和证据。
4. Current Specs 的数量只按 Git 主线实际 `openspec/specs/` 内容确定；不能把尚未归档的 `openspec/changes/*/specs/` 算作 Current。最终治理 Spec 的实际 Sync/Archive 仍由 `enforce-openspec-change-gate` 原 Change 独立完成；本轮**不得**代替其 3.3 自动勾选。
5. `PROJECT-STATUS.md` 不再复制每个 Active Change 的 Task 细节，只链接并说明执行/未验证边界；`AGENTS.md` 保持第一入口，`documents/README.md` 保持长期知识入口。
6. OpenSpec Change Gate 只验证关联和 Tasks 同步，不自动保证文档内容正确；因此加可核对的旧说法回归检查与实际 Main SHA/PR Runs。

## Verification and rollback

- 纯文档路径与 `openspec/`，Git PR HEAD 的 `require-trusted-change` / `validate-openspec` / Documentation Relative Links PASS，修改的文件中没有业务源码/部署。
- 合并后检查 `documents/engineering/` 仍为 19 份且历史文件完整，`openspec/changes/` 保留原两个 Active Changes，新 Legacy Change 不标业务代码已实施。
- 任何验收结论记录 GitHub 实际 PR/HEAD/Run，不猜测运行通过。
- 回滚是恢复该 PR 改动的文档版本；不能回退/重写原历史成功与失败 PR，也不触碰数据平面。
