---
status: active
scope: omop-writer
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# OMOP Writer — 原子提交、身份映射与幂等

**职责**：校验 Batch / Handoff / Claim / 权限 / 写入身份，以受控事务维护 `cdm.*`、`etl.*`、ID Maps、Ledger、Stage、Checkpoint，并允许独立只读对账。

**源码导航**：[CODE.md](CODE.md) 汇集当前 Writer、历史 Visit CDM/ID Map、安全诊断和固定批次 Loader，并直接指向对应测试与 Contract；SQL 目录仍通过 [SQL README](../../../sql/README.md) 导航（待后续独立整理）。

**真实验收**：NEW_ONLY Person/Visit 通过 Airflow 原子 COMMIT 与独立 PostgreSQL 只读读回；已提交批次重复提交路径被 SKIP。证据：[Final Acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。

**最重要的兼容边界**：现有镜像仍 COPY `task004_cdm_*.py` 到 `/opt/task004`，Python/PG 使用 `etl.task004_*` 和 Fence 函数。它们是运行依赖与持久化契约，**绝不全局 Rename**；镜像重构时必须验证基镜像 Digest/Overlay 全部版本及 Writer 安全闸门。详见 [Legacy Refactor Plan](../LEGACY-CODE-REFACTOR-PLAN.md)。

**未来命名**：新增 Condition Writer 使用 `apps/omop_writer/condition_writer.py`、`tests/omop_writer/test_condition_idempotency.py`；必须复用既有安全与幂等原则，不以 TASK005 命名代码，也不能借文档重构去执行真实数据库写入。
