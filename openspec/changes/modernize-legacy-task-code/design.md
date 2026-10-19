# Design

## Historical baseline

来源为 [Legacy Task Code Plan](../../../documents/engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)，其扫描 Main `2c85b485381a72425506829fd321d93b164a231d` 中旧根级 `apps/`、`airflow/`、`scripts/`、`spark/`、`sql/`、`tests/` 等。**2026-10-18 当前业务代码根目录已搬至 `local-data-platform/`**；不能把旧文件计数与路径当作当前清单。

## Future candidate slices

- R2：Manifest、Plan/Adapter、Validation 的功能级封装；确认相同数据的正确/错误/幂等行为与兼容入口。
- R3：Spark reconciliation 与 Airflow glue；固定既有 DAG ID、Contract，新增 DagBag/Import 与按授权的运行验证。
- R4：Docker、Writer SQL、PostgreSQL 持久化接口（如 `etl.task004_batch_ledger`、`etl.task004_batch_stage`、`etl.task004_batch_commit`、`task004_writer_fence.assert_active_claim()`、`/opt/task004/`）；按镜像 Digest 和单 Writer 安全门槛逐项验收。
- R5：仅退役被证明没有调用依赖的历史 Shell、模板、测试；保留 Git 历史及可恢复参考。

## Dependency & safety

首先让 [Local DP Relocation Change](../relocate-local-data-platform/tasks.md) 的路径兼容和 E2E Gate 得到验证。之后仍需新的用户授权、最新 Main 依赖扫描、资源占用审计与清晰回滚；将来可能需要按真实行为改变补充 Delta Spec。本次 Change **只接管计划，不授权实施**，本次没有新源文件、图片、构建或 Runtime 证据。旧系统历史验收不跨 SHA 自动继承。
