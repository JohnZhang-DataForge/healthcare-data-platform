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

## 运行安全与历史证据

旧 Portal 部署测试读回曾验证 PG14 元数据表（**37 张**）；参见 [Marquez 验收快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md)。PG14 PVC 为 Retain，**Retain 不是备份**，任何重新 Apply、Replace、PVC 删除、导入、迁移、恢复都须单独审批并核实备份；**不得修改 OMOP PG17**。

[PostgreSQL14 CODE](CODE.md) · [Marquez](../marquez/README.md) · [系统 README](../README.md) · [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。
