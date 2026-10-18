---
status: active
scope: portal-postgres14-source-map
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# PostgreSQL14 — CODE / 资源快照导航

> 这里的 Kubernetes Manifest 均为**已部署 PG14 的 Git 快照**，不是立即可重复 Apply 的版本控制声明。职责、备份与隔离边界见 [README](README.md)。

| 实际源码文件 | 描述 |
| --- | --- |
| [`storageclass.yaml`](../../../../platform-portal/postgres/storageclass.yaml) | 独立 `postgres-marquez` StorageClass，依赖外部 LocalPath 配置映射 |
| [`pvc.yaml`](../../../../platform-portal/postgres/pvc.yaml) | Marquez PG14 专属 PVC，**Retain 不等于备份** |
| [`statefulset.yaml`](../../../../platform-portal/postgres/statefulset.yaml) | PostgreSQL14 单副本 StatefulSet，读取现存 `postgres-secret`；不是 OMOP PG17 |
| [`clusterip-service.yaml`](../../../../platform-portal/postgres/clusterip-service.yaml) | PG14 API/数据库访问 Service |
| [`headless-service.yaml`](../../../../platform-portal/postgres/headless-service.yaml) | StatefulSet headless Service |

**不在 Git 的外部依赖**：LocalPath `local-path-config` nodePathMap 和 Kubernetes `postgres-secret`；不得从空白仓库假设可以直接重建数据库。实际 K8s 安全规则：[Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。

[Marquez CODE](../marquez/CODE.md) · [系统 CODE](../CODE.md)。
