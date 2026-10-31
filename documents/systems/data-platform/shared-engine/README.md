# Shared Data Engine — 公共业务引擎

> **2026-10-31 Shared Engine 与 Fabric 执行架构**：[Fabric Native ADR](../../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。Shared Engine 是唯一新 Python Wheel；Fabric Notebook/Pipeline/Environment 是必须的原生资源，I/O 优先用 Fabric API。

**状态：目录规则已确定，业务 Python 包尚未实现。**

未来唯一源码根目录：[`shared-data-engine/`](../../../../shared-data-engine/)。这里服务 Local DP 与 Azure Fabric 的可复用 Canonical/OMOP 业务算法，不承载 Data Lake/Database I/O 或平台部署。

- 权威目录/边界/迁移规范：[Shared Data Engine directory rules](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)
- 子目录 Agent 约束：[`shared-data-engine/AGENTS.md`](../../../../shared-data-engine/AGENTS.md)
- 数据架构：[Fabric Medallion ADR](../../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)
- 唯一源码归属/未来文件索引：[CODE.md](CODE.md)
- 当前 Canonical/OMOP Contract 源仍为 [Local Spark Contracts](../../../../local-data-platform/spark/contracts/canonical/)；原地保留并以源 hash pin；真正移动需要单独测试和审批。

本组件实行 **纯函数/DataFrame 计算、版本化 wheel、独立 Local/Fabric 运行时测试**；不存在可运行的共享引擎实例、现成 Wheel 或双平台部署。
