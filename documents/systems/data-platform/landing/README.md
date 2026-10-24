---
status: active
scope: landing-and-claim
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Landing — Batch Manifest、Discovery 与 Claim

**职责**：验证 S3 READY Manifest / Payload / SHA、发现候选、查询或合法领取 Batch，保护下游不重复消费。来源 Producer 只发布数据和完成标志，Landing 层不写 OMOP CDM。

**源码导航**：[CODE.md](CODE.md) 覆盖 Discovery、Claim/Fencing、历史 Intake/Visit S3 发布及测试/Contract；Airflow DAG 的具体导航交给 [Airflow CODE](../airflow/CODE.md)。

**已验收的行为**：`landing_batch_discovery` 每 15 分钟可发现源数据，但默认只读 Claim Guard，不能理解成自动执行写库。业务 `new_only_omop_consumer` 另由授权的人工 Batch 触发；COMPLETED 会 SKIP 下游。

**协议与安全**：不消费半成品 Batch；Batch ID / Manifest SHA / Source Identity 固定；未知 Writer 状态先只读检查数据库 Claim、Stage、Checkpoint。现有旧 `apps/task001/` / `apps/task004/resolve_verified_landing_file.py` 仍可被引用，今后能力扩展使用 Landing 组件目录，不创建新 Task 目录。

**证据**：[NEW_ONLY E2E Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
