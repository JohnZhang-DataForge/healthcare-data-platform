---
status: active
scope: healthcare-cross-cloud-portal-infrastructure-index
decision_date: 2026-10-26
---

# Infra — Healthcare 跨云演示基础设施

本目录仅保存用户明确指定的 **Healthcare On-Demand Live Demo** 跨云基础设施目标方案；不是现有 Fabric、Kubernetes、Terraform 源码或已部署基础设施事实的第二份权威。

- [Spark 双运行时真实兼容性 POC（2026-10-26）](SPARK-PORTABILITY-POC-20261026.md)：Fabric Runtime 2.0 / 本地 Spark 3.5.7、实际 K8s 5 人 DataFrame PASS、Fabric Trial 三次输出读回失败与严格 HOLD（非完整跨端验收）。
- **[Healthcare On-Demand Live Demo](HEALTHCARE-ON-DEMAND-LIVE-DEMO.md)**：面向 Emory 的按需真实 E2E、Local/Fabric Spark 可移植性、OpenLineage → Azure Blob → 本地 Marquez/PG14、Cloudflare + Marquito-style 只读展示、限流与免费测试选型（**尚未实施**）。
- [对应 OpenSpec Proposal](../../openspec/changes/healthcare-on-demand-live-demo/proposal.md) 与 [唯一实施 Tasks](../../openspec/changes/healthcare-on-demand-live-demo/tasks.md)。
- [现有基础设施权威](../architecture/INFRASTRUCTURE.md)；[Fabric 组件](../systems/azure-fabric/README.md)；[Portal 组件](../systems/platform-portal/README.md)；[Safe Operations](../engineering/operations/SAFE-OPERATIONS.md)。

公网门户实现和 P4 部署配置统一位于 [`platform-portal/portal/`](../../platform-portal/portal/)（[Portal 文档](../systems/platform-portal/portal/README.md)）。本目录仍只负责跨云基础设施的设计，不新增平行源码 Root。

新增目标方案不意味着已授权付费 Capacity、创建 Cloudflare 公开入口或变更任何共享 Runtime。
