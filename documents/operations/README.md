---
status: active
scope: operations-index
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# Operations — 运行、检查、排障与恢复

> **STEP07 运维索引**。核验依据：Healthcare Main `d1962f79e1c7337c372de1aebfaaec87dfc7d1c8`、Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7` 和既有历史验收；**本轮没有访问 Live Kubernetes/PG/S3/Azure**。这里只记录长期有效的操作原则，历史 Runbook 的具体命令必须与当前源码、权限和实际资源核对后再使用。

- [Safe Operations](SAFE-OPERATIONS.md)：跨组件运行前 Gate、故障与恢复边界。
- [Session Coordination](../development/SESSION-COORDINATION.md)：不同 AI Session 如何协调共享 Airflow/Spark/PG/K8s/Azure。**只有规则，没有逐 Session 日志。**
- [Development Workflow](../development/DEVELOPMENT-WORKFLOW.md) 与 [Testing & Evidence](../development/TESTING-AND-EVIDENCE.md)：PR、Workflow、SHA、测试分级。
- [PROJECT-STATUS](../status/PROJECT-STATUS.md)：唯一全项目 CURRENT/NEXT；Operations 不复制项目进度。

## 按组件检索原始技术资料

| 组件 | 现行组件/架构 | 原始操作/故障参考 | 关键 Gate |
| --- | --- | --- | --- |
| Kubernetes、local-path、SeaweedFS | [Infrastructure](../architecture/INFRASTRUCTURE.md)、[Landing](../components/landing/README.md) | [Kubernetes](../../kubernetes/README.md)、[Lessons](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/development-lessons-cn.md) | PV/PVC/StorageClass/目录先只读核实；Retain 不代表备份 |
| 独立 Synthea | [Synthea](../components/synthea/README.md) | [历史独立生成方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) | 不为排查重放历史 Batch 或覆盖 READY Manifest |
| Airflow / Spark | [Airflow](../components/airflow/README.md)、[Spark](../components/spark/README.md) | [Airflow 源码入口](../../airflow/README.md)、[Spark 源码入口](../../spark/README.md) | 先查活跃 DagRun、SparkApplication/Pods、镜像 SHA/Digest |
| PostgreSQL17 OMOP | [OMOP](../components/omop/README.md) | [TASK004 最终验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)、[PG Lessons](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/development-lessons-task003-step06-cn.md) | Writer UNKNOWN 先只读检查 Ledger、Claim、Stage、Checkpoint |
| Marquez / PostgreSQL14 | [Portal](../components/platform-portal/README.md) | [Portal Operations](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/operations.md)、[验收总览](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) | PG14/PG17 隔离；Web 30999 不是匿名只读入口 |
| Azure Blob / Fabric | [Azure/Fabric](../components/azure-fabric/README.md) | [Terraform IAM 架构](../../azure/infra-terraform/docs/ARCHITECTURE.md)、[Plan 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) | OneLake/Notebook/Pipeline **Plan PASS、未 Apply**；不能重复创建既有 Workspace |

## 旧文档的已知过时部分（不再作为指令）

- [Legacy Runbooks README](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/README.md) 写 TASK004 Airflow NEXT；真实 TASK004 NEW_ONLY Person/Visit 已 [E2E Closed](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
- [旧 Portal Operations](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/operations.md) 曾写「TASK004 仍在开发、Portal A4 Live HOLD」；实际 A4 已有**隔离 Smoke 部分验收**，业务 Spark 完整血缘**仍待讨论**。真正共享资源协调 Gate 没过时。
- [旧开发手册](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md) 的 `scripts/taskNNN` 新代码命名与当前 [Naming](../development/CODE-ORGANIZATION-AND-NAMING.md) 冲突，以新规范为准。
- 旧 Azure Warehouse-first 不再是当前 MVP，`docs/archive/` 不得从旧 Lifecycle 文件重新创建。

**维护原则**：引用历史失败/Closeout 证据，不改写为成功或复制大段日志。对真正新的部署/恢复动作，在单独授权后审查当前源码和环境并记录 Run/Readback；本文件没有授权任何操作。
