# Platform Portal 文档入口（Current）

> **A3 最新 REAL LIVE PASS**：真实 Airflow Provider 事件已进入 Marquez，两个独立 DagRun、两种 Task 各 **2 个 COMPLETED Run**。[Run 38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961)、[Run 38502283003](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502283003)、[Readback Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) 均 SUCCESS。[A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。**CURRENT NEXT = A4 隔离 Spark OpenLineage Agent**；TASK004 Claim/Writer 不变。

> 用户确认从 `docs/demo-plan/` **正式迁移为** `docs/platform-portal/`，代码在 `platform-portal/`。历史方案保存在 `archive/`，不再把静态前端旧版方案当成当前 NEXT。

- [架构](./architecture.md)：Marquez、OpenLineage、PostgreSQL14 与现有业务流
- [实施计划](./implementation-plan.md)：当前路线 A 与分期验收
- [部署与恢复](./deployment-guide.md)：固定版本、Secret 处理和 Helm/Runner
- [真实验收](./validation.md)：Marquez 安装与 A3 Airflow 实际 Job/Run 证据
- [A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)
- [运维](./operations.md)：PV、备份、访问限制与回滚
- [历史归档](./archive/2026-10-13/README.md)：Marquez A0 预检、旧 Demo v2 方案、三次停止

**已存在的独立数据仓库**：`dw-postgre14` PostgreSQL 14.24 / DB `marquez` / Service `dw-postgre14.dw-postgre14.svc.cluster.local:5432` / Retain PVC `dw-postgre14-data`。不用重装。**任务主线 TASK004 仍独立开发**。

**当前部署阶段（2026-10-13 EDT / 2026-10-14 UTC）**：[Marquez Helm/PG14 Schema 真实 Run 38499534795](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499534795) 的 API+Web 1/1 Ready、PG14 37 张表 PASS（此 Run 后续 NodePort 代码失误导致 workflow FAIL）；[独立 Web-only 恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493) **最终 SUCCESS**，30999 Service 已创建、Web /healthcheck PASS、同源 /api/v1/namespaces HTTP 200。详见 [validation.md](./validation.md)。LAN 浏览器和公网 NAT 尚未实测，Airflow 的真实 OpenLineage 已在 A3 接通；Spark/Writer 下一阶段接入。
