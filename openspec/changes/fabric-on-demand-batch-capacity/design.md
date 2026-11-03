# Design

## Decisions (discussion only)

1. **延后**：Trial 期间不开展付费容量自动启停；先完成当前 Fabric 原生 FHIR/G5/OMOP E2E。Trial 结束后再决定是否购买正式 F SKU 和采用批处理运行窗口。
2. **外部生命周期开关**：Self-Runner / GitHub Actions 是候选的外层控制平面；它在 Fabric 暂停时仍可运行，负责检测 Blob Ready manifest、控制/观察付费 Capacity、触发执行、核验证据与最终暂停。复用 [现有 Capacity API Change](../manage-fabric-capacity-lifecycle-api/design.md) 的既有受控接口；自动调度属于独立的后续授权变更。
3. **编排不重复**：本地 Airflow 可负责整体 DAG 和外部依赖；Fabric 内部的原生 Pipeline 仍负责 Fabric Notebook 活动顺序/重试。具体选择单一执行入口，避免 Runner、Airflow、Fabric Pipeline 三方对同一 Batch 重复触发。
4. **数据边界**：Azure Blob 的直接读写与 Fabric Capacity 解耦；OneLake 的 Delta、Fabric DW、SQL Endpoint 和 Fabric 内部 Notebook/Pipeline 依赖 Active Capacity。暂停时 Fabric 侧读写/查询不可用，业务数据与本地 Marquez 元数据不随之删除。Shortcut 从另一 Active Capacity 消费的例外不作为本方案依赖。
5. **血缘**：Airflow/Spark/明确的 DW 写入适配器负责生成具有输入/输出/Run ID 的真实 OpenLineage 事件；可使用 Blob 不可变事件中转或安全内部 POST，由本地 Consumer/Marquez 持久化。Runner 只负责汇聚、校验、缺失告警；Job 完成状态不得冒充表/列级血缘。
6. **关机门槛**：成功/失败结尾统一执行收尾流程。只有所有 Fabric Job terminal、事务/Delta 提交与独立读回确认、血缘事件已被持久接收或有可靠待送缓冲、运行证据保存、无其他 Workspace/用户负载时，才允许自动暂停。异常须上报并依据配置进行有界收尾/人工介入，不能误暂停共用 Capacity，也不能无上限保持付费容量 Active。
7. **成本与权限**：暂停可能结算 CU Smoothing/carryforward；Blob/OneLake 存储费另计，真实节约必须对照 Metering/账单、启动耗时和吞吐量。正式 Capacity ARM ID 与 Trial GUID 严格区分；需要最低 RBAC、明确的付费许可、并发锁、预算上限、超时、恢复/补偿。

## Candidate batch flow

```text
08:00 (example): Source producers -> Azure Blob + immutable READY manifest
10:00 (example): external Runner preflight (no data => SKIP, no Capacity resume)
             -> Paid F SKU Resume (if approved) -> readiness/status check
             -> one orchestrator: local Airflow -> Fabric Pipeline -> Notebook/Spark
             -> Bronze/Silver approvals -> OMOP Delta and/or Warehouse commit
             -> independent DQ/readback/replay evidence and status
             -> real OpenLineage event -> durable relay/Marquez ACK (or safe spool)
             -> ensure all jobs terminal, no shared users -> Paid F SKU Pause
             -> post-run cost report / notification
```

时间仅用于讨论，不是已配置的 schedule；是否使用 DW Gold 以及是否选择 Local/Fabric/Hybrid Spark 均保留现行 ADR/未来 OpenSpec 决策。

## Compatibility, risks, verification

- 保留 [Fabric-native Notebook / Pipeline ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 的 Git-first 代码/环境交付与 Fabric Pipeline 内部编排边界，不把本地 Airflow 替代现有原生 Pipeline。
- 与 [已存在的 On-Demand Demo Change](../healthcare-on-demand-live-demo/proposal.md) 不同：该 Change 针对访客触发和公网展示；本 Change 针对将来定时批处理/Capacity 成本，彼此不共享自动执行授权。
- 需测试 No Data、重复/并发 Run、DW/Delta 部分写入、异步长任务、Fabric/ARM/API 超时、Marquez 无法访问、血缘缺失/积压、容量被其他 Workspace 占用、暂停/恢复最终状态未知、预算上限、身份过期、失败后人工恢复。
- Trial 到期后先做**只读评估和成本模型**，再单独 OpenSpec、PR、CI 与授权的真实 Paid Capacity 测试。设计讨论稿不作 Runtime PASS 声明。

## References

- [Capacity lifecycle API existing Change](../manage-fabric-capacity-lifecycle-api/tasks.md)
- [External OpenLineage relay design](../healthcare-on-demand-live-demo/design.md)
- https://learn.microsoft.com/en-us/fabric/enterprise/pause-resume
- https://learn.microsoft.com/en-us/fabric/enterprise/throttling
- https://learn.microsoft.com/en-us/fabric/onelake/onelake-consumption
- https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-public-api
