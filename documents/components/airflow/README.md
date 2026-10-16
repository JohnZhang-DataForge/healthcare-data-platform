---
status: active
scope: airflow-orchestration
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Airflow — 消费、调度和业务路由

**职责**：按可信 Batch 身份进行 Discovery/Claim 路由，调度 KPO/Spark/受控 Writer，组织 Reconciliation 和状态，不在 DAG 内复制复杂领域处理算法。

**已验收入口**：[NEW_ONLY Consumer](../../../airflow/dags/new_only_omop_consumer.py)：`schedule=None`、`max_active_runs=1`，14 Tasks，受显式 Flag/Secret/Claim 双闸门控制；已完成批次路由到 `already_completed_no_replay`。来源发现 [Discovery DAG](../../../airflow/dags/landing_batch_discovery.py) 定时运行，但不会自动执行所有业务 COMMIT。

**未来方向**：业务 DAG 使用功能名称，如 `condition_omop_consumer`；如果 Contract/Writer 尚未成熟，不提前创建一个“已部署”DAG。当前 [legacy `task004_cdm_*.py`](../../../airflow/README.md) 仍有 Image/DAG Import 依赖；必须按独立迁移计划处理，不能简单重命名并改掉已验收 DAG ID。

**证据与局限**：[TASK004 Final E2E](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。DAG Parse、GitSync 或 Task success 均不单独证明 PG COMMIT。
