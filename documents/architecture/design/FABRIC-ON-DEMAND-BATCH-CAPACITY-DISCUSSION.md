---
status: draft
scope: proposed-fabric-paid-capacity-batch-execution
last_verified: null
source_sha: null
evidence: []
---

# Fabric 按需 Capacity + 定时批处理 + 独立 Marquez 血缘（讨论稿）

> **状态：DRAFT / DISCUSSION ONLY / DEFERRED。** 2026-11-03 讨论形成。**等 Fabric Trial 过期后再评估是否实施**；本文件不是已批准的 ADR、部署计划、Schedule 或 Runtime 授权。当前优先保障 Fabric 原生 FHIR/G5 → Bronze → Silver 与独立 OMOP 工作流的开发、测试和验收，不因此修改现行 Pipeline/Notebook/Environment，也不强制将处理计算迁到本地。

## 1. 核心构想

我们的 Healthcare 数据可能是低频批处理，而非 24×7 SQL 服务。将 Self-Runner 作为**Fabric 外部的 Capacity 生命周期控制器**，数据先到独立 Azure Blob，等批次准备好再恢复正式付费 Fabric F SKU；运行 Fabric 内部 Pipeline/Spark/Delta/OMOP/DW，独立读回和血缘收集完成后暂停 Capacity。Fabric 关机时 Azure Blob 仍可直接由 Local DP 使用，Marquez 仍可在本地展示已保存的血缘。

**不是关闭 Spark Job 就关闭 CU**：F4 是包含 4 CU 的一整个 Capacity；Spark/OneLake/DW 等工作负载共享其预算，而不是各有一个独立的 CU 开关。只有暂停**整个付费 Capacity**才停止该容量的常规运行时长计费，Fabric 内依附该容量的处理和查询也会不可用。

## 2. 示例调度（仅示意，不代表实际 10:00 开始）

```text
08:00  FHIR/HL7/CSV/PG -> Azure Blob + committed READY manifest
10:00  Self-Runner 触发预检（无新 READY batch => SKIP，不启动 F SKU）
       -> 确认获准的 Paid Capacity ARM ID / 费用权限 / 互斥锁 / 预算
       -> Resume Capacity -> 等待 Active 与服务 readiness
       -> 本地 Airflow 负责外部总 DAG（或 Runner 直接触发唯一入口）
       -> Fabric 原生 Pipeline 编排 Notebook/活动（避免双重调度）
       -> Spark -> Bronze Delta -> Silver Delta -> 已批准 OMOP 目标
          （Gold 可采用 Delta 或 DW；依据独立 OMOP 方案决定）
       -> 检查所有 Fabric Job terminal / DQ / Delta & DW durable readback
       -> OpenLineage 事件持久化并由本地 Marquez 验收或安全落盘待送
       -> 检查无其他使用者 / 没有运行中 Job -> Pause Capacity
       -> 保存 Run、成本、血缘、异常与恢复报告
11:00  假设已完成；实际应按终止条件停止，不强制一小时结束
```

### 职责分配

| 服务 | 候选责任 | Capacity 暂停时 |
| --- | --- | --- |
| GitHub Actions / Self-Runner | 外部调度时钟、检测 Manifest、容量启停、状态轮询、审计/报告 | 可运行；不能凭 DAG SUCCESS 宣告数据完成 |
| Local Airflow | 可选外部 DAG：来源/跨平台依赖、批次和重试状态 | 可运行 |
| Fabric 原生 Pipeline | Fabric 内的 Notebook 顺序、参数、失败/重试分支（保持现行 ADR） | 不可执行新任务 |
| Fabric Spark / Delta / OneLake | FHIR 转换、Bronze/Silver、批准写入及读回 | 目标 Capacity 暂停后不可访问 |
| Fabric Warehouse (DW) / SQL Endpoint | 经批准的 OMOP SQL 写入或分析查询 | 不可查询/写入 |
| 独立 Azure Blob / ADLS | 原始批次、Manifest、必要的独立事件缓冲 | 可直接访问，另按 Azure Storage 计费 |
| 本地 OpenLineage + Marquez / PG14 | 收集、持久化、查看 Job/Run/Dataset/列级血缘 | 仍可读取已有血缘和接收本地/缓冲事件 |

**设计边界**：Fabric 数据保留不等于 Fabric 暂停时可读。直接对 OneLake 的事务会在目标容量暂停后被拒绝；外部 Blob 独立运行。通过其他活动 Capacity 访问 Shortcut 的特殊情况不作为本方案可用性承诺。DW 不是 Spark Session，停止 Spark 不妨碍 Active Capacity 上的 DW；暂停 Capacity 才会使 DW 不可用。

## 3. 血缘与 Run Evidence 的边界

- 本地 Marquez/PG14 不依赖 Fabric Capacity。我们已有 OpenLineage Publisher / Blob Relay 的离线设计与部分源码，但 **Fabric 端 Listener、DW 字段/表映射以及跨端可靠转发仍需真实验证**。
- Fabric 任务执行时由 Airflow/Spark/明确的 SQL 适配器发出有证据的 OpenLineage START/COMPLETE/FAIL，携带 source batch、Job/Run ID、输入输出 Dataset 和必要的 schema/映射。Runner 的终态轮询只能证明作业状态，**不能自己猜造数据集或列级血缘**。
- 选择安全的事件接收途径，例如现有 Azure Blob 不可变事件中转 → 本地 Consumer → Marquez 内网 API；或者经过认证的内网 POST。公网 `lineage.johnzhang-dataforge.site` 目前为 GET/HEAD 只读入口，**不能用来 POST 血缘**。
- 暂停前完成必要血缘持久读回，或保证事件可靠缓冲、重试、去重并可在 F4 停止后消费；已保存的图在 Marquez 全天候可查看（以前提本地服务可用为准）。

## 4. 容量收尾与成本安全

- 只能对**未来用户明确批准购买/管理的付费 F SKU ARM 资源**设计自动 Resume/Pause；目前 Trial GUID 不是相同的 ARM Resource ID，现有 Capacity 生命周期 Workflow 默认 Trial inspect、Paid 仅手动二次确认。**本稿不修改它，也不启用定时/付费操作**。
- 无新数据时应 SKIP，避免不必要计费；每个 Batch 用 Manifest、版本、幂等/锁保护，防止重跑和并发双写；禁止为了演示而覆盖正式 OMOP 数据。
- 不能仅靠 Airflow/Fabric Pipeline 绿色状态判断完成：必须确认 Delta/Warehouse 提交、独立读回、OpenLineage 落库/可靠缓冲和所有异步 Job terminal；容量可能被其他 Workspace 或用户共享。
- 失败/超时需要明确最大运行时长、告警、收尾策略、人工覆盖开关和费用上限。不能为了省钱误暂停运行中任务，也不能故障后无限期保持 Active 继续计费。最终状态未知时不得盲目重复 POST。
- **CU Smoothing/Carryforward**：暂停可能将此前累积的计算消耗结算到 Azure 账单；单纯以一天开启的时长乘 F4 小时单价并不代表总成本。存储、请求和网络等费用需另算；上线前做实际成本比较。
- 对频繁或全天查询需求不建议每日长时间暂停 Fabric；仅在明确离线服务等级、可以接受窗口外 DW/OneLake 不可访问时采用。

## 5. 与当前开发和已有设计的关系

1. **保持现行设计**：[Fabric Native Notebook/Pipeline/Environment ADR](FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)、[Bronze/Silver/OMOP ADR](FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 仍是当前业务开发依据；不修改 Git-first、运行时、Environment/Wheel、G5/OMOP 并行任务。
2. **已有生命周期基础**：[Capacity Lifecycle OpenSpec](../../../openspec/changes/manage-fabric-capacity-lifecycle-api/tasks.md) 包含 Trial 只读与未来 Paid 手工 API/Workflow，但并未完成真实 Paid Resume/Pause，更没有自动化。未来应**复用**，不能旁路其付费授权门槛。
3. **已有血缘相关工作**：[On-Demand Demo OpenSpec](../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md) 包含 OpenLineage → Blob → 本地 Marquez 路线，但其主要范围是公开演示/访客触发，不等同于此处定时批处理。
4. 本讨论稿的 Proposal、设计记录及以后是否接受的判断位于 [独立 OpenSpec Change](../../../openspec/changes/fabric-on-demand-batch-capacity/tasks.md)。不在这里维护第二套执行任务。

## 6. Trial 到期后的重新评估（此时才启动）

- 首先确认真实 Trial 状态/到期时间，是否转付费、所需 SKU、按量计价、监控指标和工作区共享情况；没有容量付费授权则保持文档状态。
- 复核 Fabric G5 / OMOP 实际 E2E、单批耗时、CU Consumption、OneLake 请求与 DW 使用；与保持 Active、外部 Blob + Local Spark、定时 Resume/Pause 三个方案比较。
- 决定由谁负责唯一的外层 DAG 触发、如何保护跨容量用户以及 Fabric → Marquez 的完整 Dataset/Column Lineage；评估本地 Runner/Airflow 可用性和失败恢复。
- 获得新的明确决定后，**另开受审查的实施 Change/PR**，执行静态测试、权限只读测试，再在批准的付费 Capacity 上做真实受控 E2E；未通过则维持手工模式。**本轮无代码、Workflow、TF、资源操作或上线验收。**

## References（官方文档，需实施前复核）

- [Pause and resume Fabric Capacity](https://learn.microsoft.com/en-us/fabric/enterprise/pause-resume)
- [Fabric smoothing/throttling](https://learn.microsoft.com/en-us/fabric/enterprise/throttling)
- [OneLake Capacity CU consumption and paused semantics](https://learn.microsoft.com/en-us/fabric/onelake/onelake-consumption)
- [Fabric Notebook REST Job APIs](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-public-api)
