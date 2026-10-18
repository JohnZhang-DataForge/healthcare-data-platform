# Proposal

## Why

OpenSpec G0–G4 已接入，但之前实体目录迁移 PR #225–#227 在没有有效 OpenSpec Change 的情况下合并，且 `validate --all --strict` 对 0 个 Active Changes 仍会通过。命名规范/CODE Map 的成功与否不能证明实施 PR 绑定了设计和任务。2026-10-18 后续 PR #228–#229 只是事后追溯补建 `relocate-local-data-platform`，仍没有防止未来重复遗漏的技术控制。

## What Changes

- 增加对**全部 PR 无路径过滤**的 OpenSpec Change Gate：实质性代码/Workflow/治理/架构变更需要有效的 Active Change，PR Body 显式声明 `OpenSpec-Change: <change-id>` 以及 `OpenSpec-Task: <task-number>`。
- 仅允许明确标记的非架构、非代码轻量文档 PR 使用 `OpenSpec-Exemption: docs-only`；所有其它路径默认 Fail Closed，避免冒充“纯文档”。
- 约束 Change 文件存在、任务编号存在、`tasks.md` 与实施 PR 同步修改；避免只有提案没有进度同步。
- 合法 Archive PR 可使用同一 ID，Archive 时必须所有正式任务完成；归档不等于部署/Runtime 验证。
- 正反向单元测试覆盖无 Change、无 PR 关联、无 Tasks 同步、伪造例外、正常多 PR、归档等。
- 更新 Agent/开发/生命周期入口，并记录分支保护 required check 的权限与可验证状态；不绕过规则，不假装 CI Success 自动禁止管理员合并。

## Capabilities

### New Capabilities

- `development-change-governance`: 实质性 GitHub PR 必须关联并同步合法 OpenSpec Change，轻量非架构文档编辑有严格的可审计例外。

### Modified Capabilities

无业务能力变更；保留已经验证的所有本地平台和 Azure/Fabric 行为不变量。

## Impact

仅 GitHub-hosted 静态 CI、质量工具、其测试与工程治理文档。**不修改任何** Airflow DAG、Docker/镜像、SparkApplication、K8s、PG、S3、Azure、TF，不创建或重放业务批次。Main 分支保护规则若无可用管理权限，需要单独记录待用户操作，不能把 Workflow PASS 与 required branch rule 混为一谈。

这次治理改造先在正式 OpenSpec Change 中跟踪并用 PR 验证，只有 CI 及正反用例达标后才能认定已实现；未通过检查不得绕过合并。
