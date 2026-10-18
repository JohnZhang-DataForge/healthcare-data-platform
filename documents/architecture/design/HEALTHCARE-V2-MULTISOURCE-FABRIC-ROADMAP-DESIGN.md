---
status: draft
scope: healthcare-v2-multisource-fabric-roadmap
last_verified: 2026-10-18
source_sha: null
evidence: []
---

# Healthcare Data Platform V2：双平台、多数据源与公开展示路线（讨论稿）

> **DRAFT / 目标设计，不代表已部署或获准执行。** 本文整理 2026-10-18 的新方向；关于现状，以 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md)、现有源码、有效 Contract 和实际验收为准。本文不是 Emory 内部架构事实，也不推断其 Snowflake/Fabric/Enterprise OMOP 的实际集成关系。

## 1. 背景、目标与新的边界

此前本地平台的主要成果是 Synthea CSV → SeaweedFS S3 → Airflow → PySpark Person/Visit → PostgreSQL OMOP CDM 5.4。按现行项目状态，**NEW_ONLY Person/Visit** 已有真实 E2E 和重复 Batch SKIP 证据；**UPDATE_ONLY、MIX_DATA、Condition Writer、完整业务 Spark Lineage、Fabric 云端业务 E2E 尚未验收**。

本阶段不再以补齐所有 OMOP Domain 为优先目标，而以可核验的 **Healthcare Research Data Integration Platform** 为目标：

1. **Local Data Platform（简称 Local DP）**：继续保留已验收的本地 Kubernetes、Airflow、Spark、SeaweedFS、PostgreSQL OMOP 及 Marquez；完成维护源码向仓库 `data-platform/` 的受控迁移。
2. **Microsoft Fabric**：将 Local DP 的 PostgreSQL OMOP 视为**一个上游数据源**；再接入独立 FHIR R4 和 HL7 v2 来源，形成多来源的 Bronze、Silver 与研究数据产品。
3. **两侧各有可观测性**：本地 Airflow/Marquez，云端 Fabric Pipeline Monitoring/Spark Monitoring/Lineage；外部观看者通过**无需账号的公开只读 Showcase** 查看真实运行证据，不直接访问管理后台。
4. **业务解耦**：Producer、Landing、Canonical/Transform、Identity、Writer、云端分析副本和展示层各自有清晰所有权；OMOP 是一种标准化数据产品，**不是所有 FHIR/HL7 原始事件都必须先写入的中心库**。

**明确优先级调整**：暂停 Condition/TASK005 后续业务开发（保留计划、代码与历史证据，不删除、不宣称完成）；以 OpenSpec Bootstrap、目录迁移、PG→Fabric、FHIR→Fabric、HL7→Fabric 和公开展示为主线。重新启动 Condition 另行批准。

## 2. 目标逻辑数据流

~~~text
     LOCAL DP (Kubernetes)                   INDEPENDENT CLINICAL SOURCES
  Synthea CSV → S3 → Airflow                  FHIR R4 / NDJSON
                ↓                                │
             PySpark                             ├──→ Azure Blob (FHIR landing)
                ↓                                │
     PostgreSQL OMOP 5.4              HL7 v2 ADT → Mirth Connect
                │                                │
                ↓                                └──→ Azure Blob (HL7 landing)
      Read-only Consistent Export
                │
                └──→ Azure Blob (OMOP snapshot landing)
                              │
                    Fabric Data Pipelines
                        independent flows
                              │
                      OneLake Bronze
                  OMOP / FHIR / HL7 partitions
                              │
               Fabric PySpark + validation
                              │
                  Silver: typed source-aware
                     canonical/analytics
                              │
               Gold: research-ready products
               SQL views / patient / visit trends

Local Observability: Airflow UI + Marquez     Fabric: Monitoring + Lineage
                  \                           /
                   Public Read-only Showcase
             (published evidence; no admin APIs)
~~~

这是**目标逻辑结构**；不表示已配置 Fabric 对原生 FHIR/HL7 的接收能力或各产品的完整血缘。

### 2.1 A：PostgreSQL OMOP → Fabric

- PostgreSQL 的 `cdm.person` 和 `cdm.visit_occurrence` 为初期唯一云端复制范围，本地 PG 保持权威。
- 开发只读一致性 Exporter：固定 export_id、来源版本、文件 hash/行数、Schema 与 READY Manifest；最后发布 READY，失败不向消费端暴露半成品。
- Azure Blob 为 PG 快照 Landing；**Fabric Data Factory Data Pipeline 负责调度/调用**，Notebook 负责读取、校验、写入 Delta。
- Notebook 需验证行数、PK/FK、Schema、内容、幂等重放；云端是分析副本，不回写本地 OMOP。首期不强制 Warehouse/dbt。
- 原 [Data Flow](../DATA-FLOW.md) 中约定的 PG→Blob→Pipeline→Notebook→Lakehouse OneLake-first MVP **继续有效**，不得被新多源路线覆盖或绕过。

### 2.2 B：FHIR R4 → Fabric

- FHIR 作为**独立数据交付合同和运行批次**，优先 Patient、Encounter；原始 FHIR JSON/NDJSON 保留、源 ID 与 Reference 可追踪。
- 先按源格式落 Azure Blob / Bronze，Fabric PySpark 执行解析、版本/去重、Schema/Reference/DQ 校验后得到带来源标识的 Silver。
- 可以利用 Synthea 生成测试 FHIR，但**不能仅把同一 CSV 换格式就声称完成跨来源患者整合**；应另设独立源系统命名空间和关联用例。
- 不强制同步 Local PostgreSQL OMOP，不直接假定 FHIR Patient ID 等于 OMOP person_id。

### 2.3 C：HL7 v2 → Fabric

- 明确这里是 **HL7 v2.x 消息**，不是 FHIR（FHIR 本身也属于 HL7 标准家族）。
- 使用 Mirth Connect（待部署）作为消息接入/ACK/解析和失败隔离边界；第一阶段考虑 ADT A01/A08 的合成测试消息，保存原文与可审计的解析输出。
- 经 Azure Blob → Bronze → PySpark Silver；保留消息控制 ID、患者标识分配机构、消息时间、去重与重放信息，避免把消息重试当作新的临床事件。
- 不默认把 ADT 直接写入本地 OMOP；与 FHIR/OMOP 的关联需要可核验的 crosswalk 或明确的模拟身份关联证据。

### 2.4 汇总≠无依据地合并患者

- 首期 Gold 可以展示分源指标、Patient/Visit 汇总、数据质量与可追溯性；跨源 Patient Timeline 仅在明确身份 crosswalk 时启用。
- 不能仅凭姓名、生日或相似字段自动把不同系统 ID 当作同一个人；不清楚时保留独立实体并标记 unresolved。
- 真实临床数据不进入公开作品集；使用合成数据，并对日志、标识、URI、机密信息做公开前审查。

## 3. 两个 Portal 与外部可访问性

| 场景 | 内部管理/诊断（鉴权） | 对外无需登录（只读） |
| --- | --- | --- |
| Local DP | Airflow UI、Marquez 原生 Web/API、Spark UI | 静态流程/运行/血缘证据页 |
| Fabric | Monitoring Hub、Pipeline Runs、Spark Monitoring、Workspace Lineage | 静态 Pipeline/Notebook/Delta 对账与血缘证据页 |

**强制安全边界**：Fabric 原生 Workspace/Monitoring/Lineage 通常受 Workspace/身份权限保护，不能把分享 URL 视为匿名可访问。Airflow 和 Marquez API 不应匿名暴露。首选 GitHub Pages（或同类 HTTPS 静态站点）作为公开入口：一个主页、Local DP 页面、Fabric 页面；内容来自经审核的截图/JSON/摘要，并展示采集时间、Commit SHA、Run ID、数据 Batch/export_id 与验收状态。

静态快照**必须标注历史时间**，不可伪装为实时监控；后续若开发只读代理/自动导出，需单独 Change、只读身份、匿名查询限制和安全审查。公开页面应在本地集群停机、Fabric Capacity 暂停时仍可查看已验证结果。

## 4. 仓库所有权及源码迁移

保持现有四个主要业务/文档目录的目标设计，OpenSpec 作为额外的治理目录，与 `documents/` 同级；`Local DP` 是逻辑称呼，仓库物理路径仍用已定稿候选 `data-platform/`，**不再造 `local-dp/` 根目录**。

~~~text
healthcare-data-platform/
├── .github/             # Repository CI/CD
├── AGENTS.md
├── README.md
├── openspec/            # change/spec governance (future STEP09)
├── data-platform/       # Local DP runtime source (future relocation)
├── azure-fabric/        # Infra Terraform + Fabric workspace items
├── platform-portal/     # Local Marquez / OpenLineage integration
└── documents/           # Architecture, Systems, Engineering
~~~

**目录物理迁移与应用模块重构必须分开验证**：

- 第一批只做现有应用源码的路径迁移和**必需的引用适配**，修复 GitHub Actions/Self-Runner、Docker build context/COPY、DAG GitSync、SparkApp、Python import/path、Contracts、CI 和 `CODE.md` 链接。
- 保留已验收 DAG ID、持久化 `etl.task004_*`、Batch/Manifest/Claim/Checkpoint、镜像 Digest、容器运行兼容路径；以行为不变和回滚为硬条件。
- 之后再拆 Change 重命名旧 `task004` 源码、提取公共身份/Manifest/DQ/Writer；不在首次 `git mv` 批次中穿插业务语义修改。
- 保留旧 `azure/` 的并行 Terraform 来源直到 State/Workflow/Import/链接验证无歧义，再依据单独审计淘汰，严禁意外重复 Apply/Destroy。
- 本方案沿用 [Data Platform V2 Migration Design](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)，该文件负责具体迁移边界、兼容和回退细节；此处仅描述跨工作线顺序。

## 5. OpenSpec 与建设顺序

**OpenSpec 先于代码迁移，但不要求先写完全仓 Current Specs。** 按 [OpenSpec Adoption Design](OPENSPEC-ADOPTION-DESIGN.md) 的 G0–G4：从最新 Main 建立独立 Bootstrap PR，使用官方 CLI Init + Validate（实际版本和工具集成由执行时核查）；只建立最小 `openspec/` 及配置，不复制全部 `documents/` 或历史 `docs/`。

建议后续独立的 Change（名称为候选，实施时按范围拆分）：

| 顺序 | Change 候选 | 范围 | 验收重点 |
| --- | --- | --- | --- |
| 0 | OpenSpec Bootstrap（独立 PR） | CLI / config / 静态验证 | 无业务 Runtime 副作用 |
| 1 | `relocate-local-data-platform` | 根目录 → `data-platform/` | 路径/Workflow/Import/契约/回归；业务行为保持 |
| 2 | `refactor-local-component-boundaries` | 旧 Task 命名及公共能力 | 新旧结果对照、兼容和回滚 |
| 3 | `replicate-omop-to-fabric` | PG Exporter → Blob → Fabric → Delta | 一致性、双表对账、幂等 |
| 4 | `ingest-fhir-to-fabric` | FHIR R4 → Bronze/Silver | 来源标识、Reference、重放 |
| 5 | `ingest-hl7v2-to-fabric` | HL7 v2 → Mirth → Bronze/Silver | ACK、消息幂等、审计 |
| 6 | `publish-public-showcase` | Local/Fabric 公开只读证据 | 匿名访问、安全、准确状态 |
| 7 | `integrate-lineage-reporting` | 业务运行证据与血缘关联 | 不虚构 Dataset/Job 事件 |

第 2 项可以在不影响 PG→Fabric 的情况下后移；第 6 项可在 Local DP 首批真实证据基础上**提前完成最小展示**，不需等三个 Fabric Pipeline 全部运行。

结构性重构 Change 不应编造业务新功能。是否采用 OpenSpec 的 `skip_specs` 等能力由 Bootstrap 时安装版本的 CLI/Schema 校验决定；无论如何，迁移需要可测试的“不改变现有行为”验收说明。

跨阶段共同遵守：单一 Change/PR 的边界、源 SHA、增量验证、回滚、Self-Runner 运行证据；**同一问题连续调试三轮仍无法通过则停止**，留下失败原因、已尝试方案、Branch、Commit SHA、Workflow Run 与安全下一步。OpenSpec Task 的完成标记不代替 CI 或真实业务独立读回。

## 6. 最小可展示成果与验收

- **Local DP**：原 NEW_ONLY Person/Visit 路径迁移后继续通过 Import/Contract/受控回归；既有已提交 Batch 不自动重放；Marquez 已验证部分和未验证业务血缘明确区分。
- **PG → Fabric MVP**：仅 `person` + `visit_occurrence`；Snapshot/Manifest/Notebook/Delta 对账，重复 export 不产生重复记录；验证 Source SHA、export_id、Fabric Job 与读回结果。
- **FHIR/HL7**：独立批次/源身份，至少一条成功与一条失败/重试场景；Silver 结果可根据保留的来源标识追溯原始输入。
- **研究侧**：一组经过验证的 SQL 查询或 Gold 数据产品，说明三源数据在 Fabric 中可被分析；不夸称已实现临床真实身份匹配。
- **公开展示**：互联网匿名可访问、只读、稳定；Local/Fabric 两个页面有真实证据、更新时间与状态；不得公开管理端点、密钥、内部 IP/主机名、真实敏感健康记录。
- **实施证明**：每个新能力标明 planned / coded / tested / deployed / live verified，PR/Run 和独立读回证据准确匹配，不用截图代替完整测试。

## 7. 非目标、风险及实施门禁

**本阶段不做**：Condition/Procedure/Drug 完整业务 Writer、完整 UPDATE_ONLY/MIX_DATA OMOP 提交、Kafka/自建 Portal UI、全部 ATLAS、Snowflake 第三运行环境、公开 Fabric Workspace 匿名访问、全量重新设计 OMOP 核心表。

主要风险与防护：

1. **目录迁移影响运行路径**：先依赖审计和纯迁移 PR，再按组件静态/合同/镜像回归，需授权的 Live 验证独立进行。
2. **Terraform 与外部云成本**：设计和 Plan 不等于 Apply；Fabric Capacity、IAM、Workspace 及部署操作单独审批。
3. **FHIR/HL7 双写或错误身份合并**：保留独立源合同、稳定源键、可审计交叉映射和失败隔离。
4. **公众访问带来泄露风险**：公开静态证据与私有管理面隔离；每次发布前清理 Secrets、内部路径和敏感数据。
5. **证据范围夸大**：Local Portal 只有部分 OpenLineage 成果，Fabric 目前仅 Plan-only；写作始终区别目标与已验收。

## 8. 相关设计与权威资料

- [OpenSpec 接入与开发治理设计](OPENSPEC-ADOPTION-DESIGN.md)；[OpenSpec Readiness](../../engineering/migration/OPENSPEC-READINESS.md)。
- [Data Platform V2 源码迁移设计](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)；[Legacy 代码重构计划](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。
- [项目 CURRENT/NEXT](../../engineering/status/PROJECT-STATUS.md)；[当前架构](../SYSTEM-OVERVIEW.md)；[数据流](../DATA-FLOW.md)；[Data Platform 组件导航](../../systems/data-platform/README.md)。
- [文档治理](../../engineering/development/DOCUMENTATION-GOVERNANCE.md)；[Runtime 安全规则](../../engineering/operations/SAFE-OPERATIONS.md)。

> **批准/实施状态**：这是供审核的方向设计和实施顺序，不初始化 OpenSpec、不修改源码、不执行迁移/部署/真实运行；未来按独立 OpenSpec Change 和 PR 推进。
