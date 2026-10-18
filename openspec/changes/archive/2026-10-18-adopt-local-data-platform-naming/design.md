# Design

## Context

- 2026-10-18 决策：根仓库 `healthcare-data-platform/` 是 Hybrid Healthcare 项目；本地 Kubernetes 数据平台应使用 `local-data-platform/`；云端 Microsoft Fabric 继续 `azure-fabric/`。
- 当前仓库的本地业务源码依旧分散在根目录 `apps/`、`airflow/`、`spark/`、`images/` 等处。G5 本试点不迁移源文件。
- `documents/systems/data-platform/` 为已上线的**文档组件导航**，其含义和目录位置不受未来源码根目录名称影响。
- G3 历史受控迁移工具已验证 `data-platform/**`，还未验证 `local-data-platform/**`。不可把历史 PASS 宣称为新路径 PASS。

## Decision

唯一未来源码目标：`local-data-platform/`。拒绝 `data-platform/` 和简称 `local-dp/` 作为并行根目录。代码迁移与命名决策在不同 Change/PR 中完成。

最终结构：

```text
healthcare-data-platform/
├── local-data-platform/    # future: self-hosted K8s + Airflow + Spark + OMOP sources
├── azure-fabric/           # Azure/Fabric sources (already distinct)
├── platform-portal/        # independent portal
├── documents/              # architecture/systems/engineering
├── openspec/               # specs/changes governance
├── .github/                # repository-wide automation
├── AGENTS.md
└── README.md
```

## Implementation boundaries

1. 此 Change 仅修改**目标方案**及决策索引中的未来源码根目录，历史 G3 检查值、证据链接及已存在真实目录引用必须原样保留。
2. 不改 `documents/systems/data-platform/` 的 CODE.md 相对路径；不改已有源码链接或当前运行路径。
3. 不在同一 Change 修改 CI/Workflow（工具行为）。将 G3 测试的旧前缀 -> 新前缀列为 G5/G6 的前置独立 PR，并补充正向/负向单元测试。
4. `relocate-local-data-platform` 仍负责源码文件分类、依赖图、复制/测试、受控切换和旧目录退役，不由本命名 Change 代替或提前归档。
5. 不接触 K8s、Airflow、Spark、PG、S3、Azure，不使用受保护环境的 Secrets。

## Validation

- 对文档差异进行范围审查：只有明确未来目标路径的文本发生变化；历史 Snapshot 与真实 CODE.md/源码路径保持不变。
- 在 PR 精确 HEAD 上运行 OpenSpec CLI 1.14.3：`openspec status --change adopt-local-data-platform-naming`、`openspec validate --all --strict`。
- 运行仓库现有的 Markdown Relative Links CI；检查是否存在指向尚未创建的 `local-data-platform/` 的可点击链接。
- PR/CI 通过且合并 Main 后，确认批准的命名方案已在权威文档中生效；本 docs-only Change 可在独立归档 PR 完成 archive，而不是等待 G6 物理迁移。
- 文档试点成功不等于 G5 原定迁移设计完成，也不等于 G6 Runtime 验证。

## Rollback / HOLD

若本次命名更新误改历史事实、真实源码路径或破坏链接，回退此 PR 的**文档变更**即可，不需要接触 Runtime。若 CI 与现存事实相矛盾，停止归档并记录 PR/Run、HEAD、失败原因和下一安全动作；同一问题连续第三轮失败立即 HOLD。
