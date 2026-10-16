---
status: active
scope: spark-data-processing
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Spark — Canonical、DQ、映射与 Reconciliation

**职责**：读取已验证 S3 Batch，做 Person/Visit Canonical 处理、质量校验、OMOP 映射、同批次 Reconciliation 和 Writer Handoff；不能绕过 OMOP Writer 提交数据库事务。

**当前代码**：[Person](../../../spark/apps/person/) · [Visit](../../../spark/apps/visit/) · [Common](../../../spark/common/) · [Spark Contracts](../../../spark/contracts/) · [Spark README](../../../spark/README.md)。旧 [`spark/apps/task004/reconcile_person_visit.py`](../../../spark/apps/task004/reconcile_person_visit.py) 尚需保留历史引用兼容。

**验收边界**：Person/Visit NEW_ONLY 真正下游 OMOP 结果已得到数据库独立确认；这不代表所有其他 OMOP Domain 已有 Spark/Writer。Portal A4 的独立 Spark OpenLineage Smoke 也不能直接证明业务数据集血缘完成。

**下一功能命名例子（建议、文件尚不存在）**：`spark/apps/condition/synthea_condition_adapter.py`、`map_condition_to_omop.py`、`validate_condition_fk.py`。优先复用现有稳定 Gate/Manifest 代码；Condition 实现和业务写入仍需要另行批准。参考 [TASK005 STEP00 只读计划](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)。
