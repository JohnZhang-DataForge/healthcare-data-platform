# Proposal

## Why

旧 `documents/engineering/development/LEGACY-CODE-REFACTOR-PLAN.md` 在 2026-10-16 设计了 R1–R5 重构，却与现在的 OpenSpec 具体变更唯一进度来源重叠。旧根级 `taskNNN` 语义重命名**不是**已完成的 `local-data-platform/` 物理路径搬迁。未来 R2–R5 必须独立追踪，不能通过改动原工程计划来暗中启动。

## What Changes

- R1 的“新代码组件/功能命名”已经由长期规范和 CI 管理，不作为未来未完成任务。
- R2–R5 的原计划迁入本 Proposal/Design/Tasks，全部保持 `NOT STARTED`；在用户就业务影响、顺序与共享资源授权作进一步决定前，**不得开始改代码**。
- 保留冻结旧接口：DAG ID、`etl.task004_*`、Writer Fencing、原 Batch/Manifest/Claim/Fingerprint、镜像 Digest。
- 依赖 `relocate-local-data-platform` 先完成适用 Import/Docker/Airflow/Spark 的路径兼容和必要运行验收；将来按组件分有界 PR 实施。

## Capabilities

### New Capabilities

无本轮已批准实施的新能力；这只是长期重构意向的变更管理入口。

### Modified Capabilities

无当前业务行为变更。本轮 `skip_specs: true`，后续如需实际行为更改必须另行批准相应 Delta Spec。

## Impact

仅创建 OpenSpec 文档。没有修改 Python、SQL、DAG、Docker、Runner，也没有任何 K8s/PG/S3/Azure 写入或运行验证。
