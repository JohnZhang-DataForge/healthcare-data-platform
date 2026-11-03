# Tasks

> **DISCUSSION ONLY / DEFERRED UNTIL AFTER FABRIC TRIAL.** 不包含部署、调度变更、付费容量购买、真实 Azure/Fabric/Blob/K8s/Marquez 操作。未来工作不得因本文件自动启用。

## 1. 记录讨论稿（本次仅文档）

- [x] 1.1 形成独立中文设计讨论稿，记录外部 Runner → Capacity → Airflow/Fabric Pipeline → Spark/Delta/DW → OpenLineage/Marquez → Pause 的候选架构、失败门槛与费用风险。
- [x] 1.2 为本设计创建 Proposal/Design/Tasks，明确与已有 Capacity API、原生 Fabric ADR 和 On-Demand Demo 的边界，以及未做任何 Runtime 实施。
- [x] 1.3 在架构设计索引增加讨论稿链接，并明确 Draft / Trial 后再评估。

## 2. Future decision gate（Trial 到期后才评估，当前不授权实施）

- [ ] 2.1 取得用户新的明确授权，核实 Trial 期限、F SKU 定价/配额与计费规则、已有手工 Capacity API 的真实权限和多 Workspace 影响。
- [ ] 2.2 在完成 Fabric G5/OMOP E2E 后，对比持续运行与定时启停的真实成本、可用性、吞吐和恢复开销，决定是否采用本设计。
- [ ] 2.3 如获批准，另起实施 OpenSpec，确定单一任务编排 owner、Capacity ARM ID/审批/并发锁、Marquez 接收协议、完整失败回收及 Paid Capacity 实机验收；本讨论稿**不执行此 Task**。
