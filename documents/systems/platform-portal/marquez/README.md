---
status: active
scope: portal-marquez
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Marquez — OpenLineage API 与原生 Web

**职责**：提供 OpenLineage HTTP 接收、Job/Run/Dataset 元数据查询和官方原生 Web；元数据位于隔离的 PostgreSQL14。组件文件地图见 [CODE.md](CODE.md)；完整系统边界见 [Platform Portal](../README.md)。

## 配置和依赖

- Marquez **0.51.1**，Kubernetes Namespace `dw-marquez`；Helm 禁用自带 PostgreSQL（`postgresql.enabled=false`），连接 `dw-postgre14` 的现有 PG14 Metadata DB；K8s Secret 不存入 Git。
- Helm 内 API/Web Service 为 **ClusterIP**；额外 `marquez-web-lan` 仅 Web NodePort **30999**。Marquez Web 可能代理 API，不能描述成无认证、匿名只读公网接口。
- 源码包含部署 `deploy.sh`、Web 受控恢复 `recover-web.sh`、ClusterIP/NodePort 配置与 `verify.sh`。它们可能修改 K8s/Secret/Helm 或发起端口转发；**有脚本不等于允许执行**。

## 已有历史验收和未证实范围

2026-10-13/14 的独立验证记录涵盖 API/Web Deployment Ready、PG14 **37 张元数据表**、NodePort 30999、API HTTP 健康查询与 Web 代理读回；[固定快照证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) 和 [恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493)。这些是**历史观测**，不能据此声称当前集群持续在线、LAN/VPN/NAT 公网访问成功或备份恢复已演练。

**运行安全**：`dw-postgre14` 与 `dw-postgre` PG17 分离；不能删除 PG14 Retain PVC，不能不审计就执行 Helm Upgrade、重建 Secret 或对 `marquez-web-lan` 进行公网上线。所有集群操作先读 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)；本次文档迁移不启动任何 Pod/Deployment。

[Marquez CODE.md](CODE.md) · [Postgres14 组件](../postgres/README.md) · [系统总入口](../README.md)。
