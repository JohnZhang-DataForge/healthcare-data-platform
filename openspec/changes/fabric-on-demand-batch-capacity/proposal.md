# Proposal

## Why

当前 Healthcare Data Platform 在 Fabric Trial 中优先完成 FHIR → Bronze → Silver 与 OMOP 的原生 E2E 能力。未来转为付费 F SKU 后，如果仅每天少量批次执行且无需 24×7 Fabric SQL 查询，可评估由外部 Self-Runner 管理 Capacity 生命周期、由 Airflow/Fabric Pipeline 执行批处理、由独立 Marquez 保留血缘，避免整天运行付费 Capacity。

用户明确要求：**本次仅记录讨论稿，Fabric Trial 到期后再评估实施**；不能据此启动/暂停任何资源、改写 G5/OMOP 开发路线或自动建立定时任务。

## What Changes

- 新增 `documents/architecture/design/FABRIC-ON-DEMAND-BATCH-CAPACITY-DISCUSSION.md`，记录目标数据流、运行窗口、管理与计算责任、OpenLineage/Marquez、暂停语义、费用与失败边界，以及 Trial 后的待决事项。
- 在 Architecture Design Index 加入明确标注为 DRAFT/DEFERRED 的导航链接。
- 复用现有 `manage-fabric-capacity-lifecycle-api` 的 **手工、默认只读、受控付费操作**能力作为未来候选基础；**不得**在本次把它改成定时自动操作。
- 不创建任何 Current Spec。本轮不代表架构已获正式采纳或实现。

## Capabilities

### New Capabilities

- 无已采用/已实现能力；仅研究未来 `fabric-on-demand-batch-capacity` 的设计选项。

## Impact

仅修改架构 Markdown 与 OpenSpec 文档。不得修改代码、Airflow DAG、Fabric Notebook/Pipeline、GitHub Actions、Terraform、Capacity、Blob、OneLake、DW、Kubernetes 或 Marquez。后续实现须单独审查成本、授权、兼容性、安全门禁和 E2E 测试，不受本讨论稿自动授权。
