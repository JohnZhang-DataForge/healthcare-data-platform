---
status: active
scope: portal-marquez
last_verified: 2026-10-25
source_sha: b92ccc9b7976e740d9dd77994a0725b115693705
---

# Marquez — OpenLineage API 与原生 Web

> **新增用户浏览器真实视觉证据（2026-10-25）**：iPhone Safari 内网加载官方 Marquez DataOps Dashboard，真实 DAG、Writer、Reconcile 的 Job 卡片和 Reconcile Spark Application 均呈现 `COMPLETED`，首页汇总可见 139 Events / 23 Datasets / 4 Sources / 71 Jobs（截图时点）。**首页和 Job 列表 GUI PASS；Run 详情 / Dataset Lineage 图仍 NOT_CHECKED**。原始含私网地址的截图不上传公开仓库，详见 [文字审查记录](../../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。P6 7.1、7.3 不因此结案。

> **P6 内网实机只读 Web/API 与业务血缘 (2026-10-25)**：[Self-Runner #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308) **SUCCESS**、[Artifact #12609050399](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308/artifacts/12609050399)；K8s 10/10 Namespace/Deployment/Service/Endpoint/PG14 Pod+PVC PASS，官方 Web 首页 `HTTP 200`、`/healthcheck=OK`，Web API Proxy / 直接 API 的 7 namespaces 一致。真实 P5 Batch `synthea-new-only-gh-40208104106` 的 Person/Visit/Reconcile 血缘与 Parent/DatasetVersion `business_edges_gate=PASS`，Writer 真 Airflow OpenLineage Run `COMPLETED`；RDD 物理 Action 仍 START-only、原严格终态 `INCOMPLETE`。**无用户 LAN 浏览器实际 GUI 交互、截图、外网可达性或 PG14 备份恢复验证**。具体 [P6 官方 Web 演示与只读查询手册](SHOWCASE-RUNBOOK.md)；OpenSpec P6 7.1 浏览器实机 Gate 尚未完成，7.3 Archive 尚未批准。P5 PG17 真 COMMIT 必须使用原 P5 独立读回证明，不能凭 Marquez 状态推断。



**职责**：提供 OpenLineage HTTP 接收、Job/Run/Dataset 元数据查询和官方原生 Web；元数据位于隔离的 PostgreSQL14。组件文件地图见 [CODE.md](CODE.md)；完整系统边界见 [Platform Portal](../README.md)。

## 配置和依赖

- Marquez **0.51.1**，Kubernetes Namespace `dw-marquez`；Helm 禁用自带 PostgreSQL（`postgresql.enabled=false`），连接 `dw-postgre14` 的现有 PG14 Metadata DB；K8s Secret 不存入 Git。
- Helm 内 API/Web Service 为 **ClusterIP**；额外 `marquez-web-lan` 仅 Web NodePort **30999**。Marquez Web 可能代理 API，不能描述成无认证、匿名只读公网接口。
- 源码包含部署 `deploy.sh`、Web 受控恢复 `recover-web.sh`、ClusterIP/NodePort 配置与 `verify.sh`。它们可能修改 K8s/Secret/Helm 或发起端口转发；**有脚本不等于允许执行**。

## 历史验收和本次未证实范围

2026-10-13/14 的独立验证记录涵盖 API/Web Deployment Ready、PG14 **37 张元数据表**、NodePort 30999、API HTTP 健康查询与 Web 代理读回；[固定快照证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) 和 [恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493)。这些是**历史观测**，不能据此声称当前集群持续在线、LAN/VPN/NAT 公网访问成功或备份恢复已演练。

**运行安全**：`dw-postgre14` 与 `dw-postgre` PG17 分离；不能删除 PG14 Retain PVC，不能不审计就执行 Helm Upgrade、重建 Secret 或对 `marquez-web-lan` 进行公网上线。所有集群操作先读 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)；本次文档迁移不启动任何 Pod/Deployment。

[Marquez CODE.md](CODE.md) · [Postgres14 组件](../postgres/README.md) · [系统总入口](../README.md)。
