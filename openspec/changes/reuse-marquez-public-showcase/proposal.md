# Proposal: Reuse Native Marquez for Public Lineage Showcase

## Why

Healthcare Data Platform 已在本地 Kubernetes 运行 Marquez 0.51.1、官方 Web UI 与独立 PostgreSQL 14，2026-10-25 的局域网验收证明真实 Patient / Encounter 的 Table Level 和 Column Level 血缘。原计划的 Marquito 网站因作者授权未取得而 HOLD；Agent D 的替代方案调研已作为历史文档合并（PR #526），但用户明确选择 **速度优先，复用现有 Marquez 原生 Web**，不再重做一个 Graph UI。

现有 `healthcare-on-demand-live-demo` 是长线按需触发/静态 Portal 架构。此 Change 专管 **第一版公网只读 Marquez 展示**，不取消未来 Azure Fabric/Blob/OpenLineage 研发。

## What Changes

- 公开展示的首选变为 **既有 Marquez 官方 Web**，通过 Cloudflare Tunnel 转发到小型 GET-only / 明确路径白名单 Gateway，再由 Gateway 访问原内网 Marquez Web；不在本阶段建设 Cloudflare Pages/Marquito/React Flow 展示引擎。
- 保持 `dw-marquez`、`dw-postgre14`、既有 Marquez Web Deployment/Service/NodePort 和历史业务 Batch 不变，先通过静态代码/接口审计和离线测试再考虑真实公网放行。
- 用户负责 Cloudflare Tunnel 创建、DNS/域名和最终启停；Agent 负责只读网关、原生 UI 依赖审计、人工 Runbook/负向验收。
- 端到端只读：默认拒绝所有写方法、未经明确批准的 API 路径、GraphQL/管理接口、敏感元数据。**隐藏按钮仅为 UI 优化，不代表权限控制。** 若关键图表依赖 POST 查询，则先 HOLD 该功能，必须审计为非变更操作后单独设计精准例外；绝不全局放行 POST。
- 先实现作品集最小可用性：Homepage → Job/Run → Dataset → Table/Column Lineage，记下访问时间和非完整边界，不把 START-only 或历史 GUI 验收说成完整 E2E。

## Capabilities

### New Capabilities
- `marquez-public-readonly-showcase` — public-facing native Marquez UI behind a small default-deny read-only gateway and user-operated Cloudflare Tunnel, with bounded UI and data review.

## Impact

- 原先 `healthcare-on-demand-live-demo` 中 4.x 的**首版静态 Web 路线**与 7.1/7.2/7.8/7.10 不再是公网 MVP 的交付前置条件；保留为历史/未来独立方案并另作 supersession 记录。原 Change 3.x、7.5/7.6/7.7 Azure Blob 工作不被逆转；第 5 节访客触发继续延期。
- 原有 P0 `portal.snapshot.v1` 合同与 Exporter 源码保留，不删除、不修改、也不为了复用 Marquez 而假装已通过运行验收。
- 不动付费资源，不直接从 Cloudflare Tunnel 暴露 Marquez API、NodePort 30999 或 PG14。
- 本 PR 只是 OpenSpec/文档变更，**不等于已经部署公开域名或获得共享 Kubernetes/网络修改授权**。
