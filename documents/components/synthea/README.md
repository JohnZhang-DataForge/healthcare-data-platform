---
status: active
scope: synthea-producer
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Synthea Producer — 独立生成与发布

**职责**：依据固定请求、Seed 和 Batch 身份生成/校验 Synthea CSV，随后向 SeaweedFS S3 发布不可变 Payload 和 VERIFIED Manifest。**不**由 Airflow 触发，也不承担数据库 OMOP Writer。

**当前代码**：[NEW_ONLY Python](../../../apps/synthea/new_only/) · [独立镜像](../../../images/synthea-new-only/) · [K8s 模板](../../../kubernetes/manifests/synthea/new-only/) · [Batch Identity 合同](../../../contracts/synthea/producer-batch-identity-v1.json)。

**实证范围**：NEW_ONLY 已通过真实独立生成与 Airflow/Spark/OMOP 消费验收；worker01 上 `synthea-local` 独立 PVC 保存生成请求状态，不是 SeaweedFS 的 PV。Generator 发布 **18 CSV+最终 Manifest**，消费者仅使用发布完成的稳定 Batch。

**尚未实现**：UPDATE_ONLY、MIX_DATA 两类独立 Producer。旧文档的 EXISTING_ONLY/MIXED 名称已废弃；三类业务身份不应用一个新 `task005` 工具混合实现。后两者不得从 NEW_ONLY 的验收推断为已运行。

**以后命名**：新文件按 `apps/synthea/<mode>/<capability>.py`，不追加 Task/Step ID；旧 `apps/task004/` 引用保持直到兼容迁移。依据：[TASK004 Final Acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
