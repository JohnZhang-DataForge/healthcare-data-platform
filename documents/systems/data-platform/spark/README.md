---
status: active
scope: spark-data-processing
last_verified: 2026-10-16
source_sha: f16e652ce0018fed5bb5d485f6eebe21c96d6603
---

# Spark — Canonical、DQ、映射与 Reconciliation

**职责**：读取已验证 S3 Batch，做 Person/Visit Canonical 处理、质量校验、OMOP 映射、同批次 Reconciliation 和 Writer Handoff；不能绕过 OMOP Writer 提交数据库事务。

**源码入口**：请查看 **[Spark CODE.md](CODE.md)**，直接查找 Person/Visit、Common、Reconciliation、Contract、SparkApplication 模板和相关测试；不再跳转到源码目录 README。旧 `spark/apps/task004/reconcile_person_visit.py` 仍需保留历史兼容，不能随意更名。

**数据流**：Verified S3 Batch → Canonical/Processed → Person/Visit Mapping + DQ → Reconciliation → 受控 Writer Handoff；Spark 不负责最终数据库事务 COMMIT。

**运行边界**：`spark/manifests/**/*.yaml.tpl` 只是参数化模板；需审查镜像 Digest、Namespace、S3 Prefix、权限和共享 Spark Operator 状态，不允许为文档整理重放已完成 Batch。

**验收边界**：Person/Visit NEW_ONLY 真正下游 OMOP 结果已得到数据库独立确认；这不代表所有其他 OMOP Domain 已有 Spark/Writer。Portal A4 的独立 Spark OpenLineage Smoke 也不能直接证明业务数据集血缘完成。

**下一功能命名例子（建议、文件尚不存在）**：`spark/apps/condition/synthea_condition_adapter.py`、`map_condition_to_omop.py`、`validate_condition_fk.py`。优先复用现有稳定 Gate/Manifest 代码；Condition 实现和业务写入仍需要另行批准。参考 [TASK005 STEP00 只读计划](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)。
