# Proposal

## Why

Local DP 的 Synthea / Landing / Airflow / Spark / PostgreSQL OMOP 早期使用 TASK001–TASK005 文档驱动。现有 Person/Visit 代码、固定的 Runtime 名称、已验收 Batch 和历史报告必须继续有效，不能为了统一管理重写或重新验收。但仓库级 Trusted OpenSpec Gate 已对新增实质性代码/Workflow/架构/治理 PR 要求事前 Active Change。如果未来仍用旧 TASK 文件同步新进度，将出现两个 OPEN/DONE 来源、Agent 选错任务和 CODE Owner 的风险。

## What Changes

- 正式确定 **Local DP Legacy Preservation + OpenSpec Forward-Only**：旧 TASK001–TASK004/已有 TASK005 设计、冻结代码/部署标识/Contracts/Run/PR 仅按原样留作事实和参考；未来新的业务功能、行为变更、运行配置、显著重构统一使用独立 Active OpenSpec Change。
- 明确已有 `relocate-local-data-platform` Active Change 继续只管理历史目录迁移/兼容/清理收尾，**不是** Condition 等新增 OMOP 域的实施计划。
- 为 Local DP 增加简短的“任务→组件 Owner→真实代码→OpenSpec”导航规则，不创建新的平行 CURRENT/NEXT；保留全部原 CODE.md 文件级来源地图。
- 明确历史 Condition TASK005 的 STEP00 设计只能作为输入，未来若选择该功能，需先在新的 Active Change 中重新确认契约、依赖与权限，不能照旧路径 `tests/task005/` / `scripts/task005/` 新增。

## Capabilities

### New Capabilities

- `local-dp-forward-only-change-governance`: 历史业务链保持不变、后续新增领域仅通过 OpenSpec 立项实施的统一 Agent 开发策略。

## Impact

只变更 Git 文档、OpenSpec 规则；不新增、移动、重命名或删除 Local DP 源码、Legacy Tests、DAG/Job/SQL/Contract、容器镜像或任何已提交数据；不访问 K8s、Airflow、Spark、SeaweedFS、PostgreSQL、GHCR、Fabric 等共享运行资源。现有 Required OpenSpec/CODE Map/Layout Gate 不调整。
