# Platform Portal 文档入口（Current）

> 用户确认从 `docs/demo-plan/` **正式迁移为** `docs/platform-portal/`，代码在 `platform-portal/`。历史方案保存在 `archive/`，不再把静态前端旧版方案当成当前 NEXT。

- [架构](./architecture.md)：Marquez、OpenLineage、PostgreSQL14 与现有业务流
- [实施计划](./implementation-plan.md)：当前路线 A 与分期验收
- [部署与恢复](./deployment-guide.md)：固定版本、Secret 处理和 Helm/Runner
- [真实验收](./validation.md)：三个失败安装尝试及后续 Live 证据
- [运维](./operations.md)：PV、备份、访问限制与回滚
- [历史归档](./archive/2026-10-13/README.md)：Marquez A0 预检、旧 Demo v2 方案、三次停止

**已存在的独立数据仓库**：`dw-postgre14` PostgreSQL 14.24 / DB `marquez` / Service `dw-postgre14.dw-postgre14.svc.cluster.local:5432` / Retain PVC `dw-postgre14-data`。不用重装。**任务主线 TASK004 仍独立开发**。

**当前部署阶段**：继承上次安装 Draft PR #106 / Self-Runner PR #90；过去三个 Run 失败的事实不会因为文件搬迁变为 PASS。真正的 API/Web、迁移、NodePort 状态以最新 Live Workflow 验收为准。
