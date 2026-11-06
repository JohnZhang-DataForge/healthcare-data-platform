---
status: active
scope: portal-postgres14
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# PostgreSQL14 — Marquez 元数据数据库

**职责**：专门存储 Marquez 数据血缘元数据，与 `dw-postgre` PostgreSQL17 的 OMOP 业务库完全隔离。当前 Git 中 [YAML 源码地图](CODE.md) 是 **2026-10-13 已部署资源的快照**，不能直接当成新建/覆盖集群的安装计划。

## 持久化与配置边界

- Namespace：`dw-postgre14`；StatefulSet：`dw-postgre14-database`；DB/User：`marquez`；Service `dw-postgre14`；PVC `dw-postgre14-data`；StorageClass `postgres-marquez`，PV 设为 **Retain**。
- 历史节点要求：worker03 的 `workload=compute`。LocalPath Provisioner 的 `local-path-config` 需要 `postgres-marquez` 对应 worker03 上 `/data/postgres-marquez` 的 nodePathMap；**代码仓库中的 YAML 本身不创建这个外部映射**。
- 使用 `dw-postgre14/postgres-secret` 的 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`；**真实凭据从不放到仓库**，也不能通过文档迁移复制。
- 这些命名和容量/调度要求来自历史部署快照，**不是当前 Pod、SC、PVC/Node 状态的实时读回**。

## 开发环境轻量备份（2026-11-04 方案）
用户批准将 Marquez PG14 的每日备份与数据库放在**同一现有 PVC**，无需新建 Bucket 或外部存储。Kubernetes CronJob `dw-postgre14/marquez-pg14-local-backup` 计划美东 03:00 自动运行 `pg_dump -Fc`，经 `pg_restore --list` 检查后把 `marquez-*.dump` 放在卷内 `marquez-backups/`（与 `pgdata/` 隔离）。每次成功产生新备份之后，自动清理仅此目录中超过 7 天的 `.dump` 文件。计划源码见 [CronJob](../../../../platform-portal/postgres/backup/marquez-pg14-backup-cronjob.yaml)；OpenSpec 见 [变更记录](../../../../openspec/changes/archive/2026-11-05-marquez-pg14-local-seven-day-backup/tasks.md)。

这是**开发环境同卷备份**，可帮助恢复人为误删除的元数据，不保护节点/磁盘/PVC 整体损坏。不要将该 CronJob 与 Marquez `dbRetention` 混淆：后者仍然永久禁用，不会删除任何 Job、Run 或 Dataset。该备份任务不执行 PG Restore，也不接触 OMOP PG17。源码/PR 并入 Main 与现场 CronJob 已部署是不同状态，必须以 Runner 验收为准。

**日常只读检查示例**（不要在这里执行实际恢复）：
```sh
kubectl get cronjob marquez-pg14-local-backup -n dw-postgre14
kubectl get jobs -n dw-postgre14 -l app.kubernetes.io/name=marquez-pg14-local-backup
```

## 运行安全与历史证据

旧 Portal 部署测试读回曾验证 PG14 元数据表（**37 张**）；参见 [Marquez 验收快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md)。PG14 PVC 为 Retain，**Retain 不是备份**，任何重新 Apply、Replace、PVC 删除、导入、迁移、恢复都须单独审批并核实备份；**不得修改 OMOP PG17**。

[PostgreSQL14 CODE](CODE.md) · [Marquez](../marquez/README.md) · [系统 README](../README.md) · [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。
