# Proposal — Local OHDSI ATLAS 3.0 Deployment

## Why

现有 Healthcare Local DP 已实现 Synthea CSV → Airflow/Spark → PostgreSQL OMOP Person/Visit 的真实 COMMIT 与重放 SKIP；Fabric 已有完整 39 表 CDM 5.4 基础 Schema 和 9 张 Vocabulary（28,703,753 行），但 Fabric Gold 仍未 COMMIT。项目缺少面向研究人员的 OMOP 探索/队列分析界面。用户决定立即开始独立 Local ATLAS 部署，不等待 Fabric/HL7/FHIR 或 ML 全域同步。

必须特别澄清：Local 与 Fabric 目标采用相同 OMOP CDM **标准**，不证明两套库的数据、39 表和 Vocabulary 已同步。本地 CDM/Vocabulary 缺口必须先独立只读审计，禁止为了部署 UI 假定 Fabric 数据已存在于 PG17。

## What Changes

- 新建 `deploy-local-ohdsi-atlas` Active Change，以功能顺序实施 Local PostgreSQL 数据预检 → ATLAS 3.0 + WebAPI 3.0 配对 → 独立 K8s 部署与数据库权限 → Cloudflare Access / Tunnel / 现有 Nginx 兼容接入 → 真实浏览器和拒绝访问验收。
- 官方 **2026-10-16** 已发布 Atlas3 3.0.0 与 WebAPI 3.0.0；使用匹配的 3.x 组合、固定发行标签和不可变镜像 Digest（发布前实际验证）。**不得把 Atlas3 连接 Broadsea 当前常见的 2.x WebAPI。** Broadsea 可以作为结构参考，但不是直接部署全套 stack 的命令。
- 优先重用本地 PG17 已验收 `cdm.person`/`cdm.visit_occurrence`、既有 K8s 和 Cloudflare Tunnel 连接器；新增隔离 ATLAS 应用配置、Results/Temp 存储与最小权限帐号；不修改历史 OMOP Writer、Batch、Ledger、Identity 或 Marquez PG14。
- 公网架构计划为 `atlas.johnzhang-dataforge.site` → **Cloudflare Access 邮箱 allowlist** → outbound Tunnel → 受控 Nginx reverse proxy → 独立内部 ATLAS UI + WebAPI；**同一受保护 Host 覆盖全部 UI 与 API 路径**，未验收前仅内网可访问。
- 具体 Nginx/Tunnel 路由属现场配置，不假定仓库已管理；必须先只读盘点当前已部署配置，采用最小增量，不覆盖 `lineage.johnzhang-dataforge.site` 的 Marquez 路由。
- WebAPI 3 自带 OAuth/OIDC、角色权限能力；Cloudflare Access 与 WebAPI 自身身份体系是两层不同产品，不得误称自动 SSO。外网启用前必须选择并实际验证 WebAPI 内建安全/RBAC 或经正式风险评审的单用户 Access-only 封闭配置，默认 fail closed。
- ML 与本次 ATLAS 不互相阻断。ATLAS3 3.0.0 初版**不包含**旧版内置 Patient-Level Prediction 模块；ML 应由后续独立 OMOP 特征/训练 Pipeline 实现。

## Capabilities

### New Capabilities

- `local-ohdsi-atlas-deployment`: 本地 OMOP 研究门户的版本配对、数据就绪检查、受限网络/身份、独立查询验收与安全回滚。

### Modified Capabilities

本轮不修改现有 CSV/FHIR/HL7 Adapter、Shared Engine、Local OMOP 写入和 Fabric Writer 的业务合同；仅建立未来研究消费端。Cloudflare/Marquez 服务继续按原有变更管理，不以 ATLAS 授权重配原隧道和共享网关。

## Impact

本设计 PR **仅增加 OpenSpec 文档**，没有安装 Helm、K8s apply、PG DDL/DML、Vocabulary 复制、Cloudflare DNS/Access 更新、Tunnel 规则修改、Secret、端口、付费 Azure Capacity 或公网开放。运行实施在后续相关 PR 与 Safe Operations / Session Coordination Gate 中逐项交付。所有真实 Runtime 操作需核查受影响资源与独立回读。

首版只要求可用界面、已认证的内部 WebAPI、真实 OMOP datasource 可发现、Concept 搜索和最小合成 cohort（须基于实际 CDM/Vocabulary/Observation Period 就绪结果）；不承诺完整临床分析或研究级预测模型。
