# Healthcare Data Platform — Demo Plan / 当前有效实施入口

> **CURRENT / 2026-10-13：路线 A 已获批准，先完成真实 OpenLineage + Marquez 内部血缘，原生 Marquez Web UI；暂不开发额外的前端展示。**

## 当前唯一实施计划

**[路线 A — Marquez + OpenLineage 实施规划 v3.0（中文）](./MARQUEZ-OPENLINEAGE-IMPLEMENTATION-PLAN-v3.0.zh-CN.md)**

- Kubernetes namespace：`dw-marquez`；Marquez API 保持 ClusterIP。
- Marquez 原生 Web UI：受限 LAN/VPN 内经 **NodePort TCP 30999** 访问，实施前验证端口占用、API UI 访问路径与网络隔离。
- PostgreSQL：先只读核对 worker03 实例容量/版本/迁移兼容；条件允许时独立创建 `marquez` 数据库、受限用户和 K8s Secret，绝不使用 `omop`/`airflow` 数据库。
- 数据来源：**只有真实** Synthea、S3 Manifest、Airflow、Spark/Operator、Writer/PG evidence 才可被展示成真实 lineage；尚未 COMMIT 不得画成功 OMOP 输出边。
- 首个 NEXT：**A0 只读预检**（通过 GitHub Connector + Self-Runner）。此文档阶段**没有**执行 A0 / 部署 Marquez。
- TASK004 独立开发继续推进；TASK005 ON HOLD；本 Demo 分支不更改 Claim/Writer/Producer 代码。

## 历史方案（保留供设计审计，不是当前 NEXT）

- [v2.0 中文 Public Demo Architecture](./PUBLIC-DEMO-ARCHITECTURE-v2.0.zh-CN.md) / [v2.0 English](./PUBLIC-DEMO-ARCHITECTURE-v2.0.en.md)：当时选择 *static first*；**该实施顺序已被 v3.0 路线 A 取代**，不得根据 v2.0 静态网站 D1 进行当前开发。
- [Self-Runner 旧 v1.1 英文](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan.md) / [中文](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan-v1.1-zh-CN.md)：历史提案保留，不覆盖。

**业务最新状态权威入口**：[docs/README.md](../README.md) → [TASK-STATUS.md](../tasks/TASK-STATUS.md) → 最新 Main Closeout 和精确 Self-Runner Run。不要使用较旧文档的历史 NEXT 作为现时事实。
