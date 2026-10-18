# Tasks

## 1. Explore / Propose / Design

- [x] 1.1 核对 2026-10-18 Main 基线、现有 `data-platform/**` 规则和 OpenSpec G0–G7 权威文档。
- [x] 1.2 固定本地平台的目标源码根目录 `local-data-platform/`，明确现有源码和文档路径不动。
- [x] 1.3 编写 Proposal / Design，声明纯文档命名调整且 `skip_specs: true`。

## 2. Apply（本 Change 仅文档）

- [x] 2.1 更新当前架构方案中的未来源码根目录，不修改历史验证信息和真实源文件路径。
- [x] 2.2 在 Architecture Decisions 记录已批准的目标根目录和理由。
- [x] 2.3 更新 G0–G7 计划、Agent 入口和项目状态，记录 CI 新路径兼容尚未完成。

## 3. Verify / Review

- [x] 3.1 在精确 PR HEAD 上完成 OpenSpec CLI 1.14.3 `validate --all --strict`。
- [x] 3.2 对关联的文档链接 / PR Diff 进行静态验证，检查未改变真实业务源码、CI 或运行入口。
- [x] 3.3 PR 合并 Main，记录 PR、Merge SHA、Run ID。

## 4. Sync / Archive

- [x] 4.1 将上述完成证据写回 Tasks/PR；对无业务 Delta 的 Change 不生成 Current Spec。
- [x] 4.2 采用独立 Archive PR 将本命名决策 Change 归档，验证后合并；单独保留后续 `relocate-local-data-platform` 迁移 Change。

## 5. Verification evidence (2026-10-18)

- Source baseline: Healthcare Main `6b7aba492a6c2f23212daa54db7ec579cfc4e871`.
- Naming implementation: [PR #223](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/223), validated PR HEAD `f16baba0e993c5f4d92d1aed2b3eb5ec31fcf00f`, squash-merged Main `d97f7bb7babe1468cc2fc115e511c836360f721a`.
- [OpenSpec Static Validation Run #39155840396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840396) SUCCESS (Node22 / OpenSpec CLI 1.14.3, strict validate) on exact PR HEAD.
- [Documentation Relative Links Run #39155840375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840375) SUCCESS on exact PR HEAD.
- Impact review: PR #223 modified exactly 13 files: only `AGENTS.md`, `documents/`, `openspec/`; no business code, CI, SQL, manifests or Runtime touched.
- Archive action: files relocated to this OpenSpec archive namespace via reviewed Git PR; **the `openspec archive` CLI command was not executed** in this environment. Previous CLI Strict Validate provides Change correctness; archive PR validation and merge establish Git history closeout.
- No Current Specs created; no local platform source moved, no new-root CI checker tested, and no business E2E repeated. Original G5 `relocate-local-data-platform` design/G6 migration remain open.
