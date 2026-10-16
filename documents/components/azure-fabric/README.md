---
status: active
scope: azure-fabric-analytics-component
last_verified: 2026-10-16
source_sha: 241944d0a6e0c222f2e862d4b79c4279bf7fd35b
---

# Azure / Microsoft Fabric — OMOP → OneLake 分析副本

> **ACTIVE 是指这里对设计与源码的说明已核对，而不是云端资源已 Apply 或业务 ETL 已完成。** Healthcare Main `241944d0a6e0c222f2e862d4b79c4279bf7fd35b`，Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7`，已保存的 2026-10-15 Terraform Plan。此次只读整理，没有云端查询、Plan、Apply 或数据传输。全局 CURRENT/NEXT：[PROJECT-STATUS](../../status/PROJECT-STATUS.md)。

## 1. 已确定的最小目标架构：OneLake-first

```text
Local PostgreSQL OMOP CDM (authoritative，已验收 Person/Visit)
  → Read-only Consistent Snapshot Exporter (尚未开发)
  → Existing Azure Blob Storage / OMOP Snapshot Landing
  → Microsoft Fabric Data Factory Data Pipeline（负责编排）
  → Fabric PySpark Notebook（读取、DQ、转换及装载）
  → OneLake / Fabric Lakehouse Delta（尚未部署）
```

- **本地 PG 继续是标准化 OMOP 的事实来源**；云端仅建立分析副本，不重做 Synthea/FHIR/HL7 到 OMOP 的 ETL，不反写本地 PG。
- **Fabric Data Factory 是 Data Pipeline item**，负责触发和监控 Notebook，并非新建 `azurerm_data_factory`。Notebook 负责业务处理，OneLake Lakehouse 是最终 MVP 数据落点。
- **既有 Azure Blob 是从 PostgreSQL 导出后的 landing**；本地 SeaweedFS S3 是 Synthea 原始数据 Landing，含义不同。
- 当前不以 Warehouse、dbt、ML 或额外 Azure 服务为首轮前置。Warehouse-first 的 [2026-10-14 旧方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-FABRIC-MINIMAL-IMPLEMENTATION-PLAN-v1.0.zh-CN.md)、旧 Terraform [README 中 Warehouse 可选的段落](../../../azure/infra-terraform/README.md) 与最新 OneLake-first 目标冲突时，以 [10 月 15 日现行方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) 和本页为准；历史文档正文不伪造一致性。

## 2. 代码与基础设施资源实际状态

| 组件 | 源码与目标 | 当前边界 |
| --- | --- | --- |
| PG Exporter | 从 `cdm.*` 做只读一致快照、输出可检验文件与最终 READY manifest | **未实现**；表范围、格式、隔离级别、export_id、重试机制还需设计 |
| Azure Blob Landing / State | 已有 Storage Account 和业务容器；Terraform State 用现有 OIDC Azure Blob backend | **既有基础设施**，不是本次三项 Fabric 资源 Plan 新建结果 |
| Fabric Workspace | 已有手工创建的 `healthcare-omop` Workspace | **不能重复创建**；若用 Terraform 管理须先 Import 及核对 Capacity/权限 |
| Lakehouse | [`fabric_lakehouse`](../../../azure/infra-terraform/modules/onelake/main.tf)，名称 `lh_omop_analytics`，`enable_schemas=true` | 已有 IaC + Plan；**未 Apply、无 Delta 数据验收** |
| Notebook | [`nb_omop_snapshot_load` 源码](../../../azure/infra-terraform/modules/notebook/definitions/notebook-content.py) 有 `export_id`、`manifest_uri` 参数 | 只有故意 `raise RuntimeError` 的 **fail-closed bootstrap**；无 Blob DQ 或 Delta 装载 |
| Data Pipeline | [`fabric_data_pipeline`](../../../azure/infra-terraform/modules/data-factory/main.tf)，名 `pl_omop_snapshot_to_onelake` | `notebook_id=""` 时使用 [Fail Activity](../../../azure/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)；[Notebook Activity](../../../azure/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) 需要未来真实 Notebook GUID；未绑定或执行 |
| IAM | [Terraform IAM boundary](../../../azure/infra-terraform/docs/ARCHITECTURE.md)，组件自身拥有权限配置 | `data_access_roles={}` 不创建 OneLake 权限；Fabric Workspace 权限与 Azure Blob RBAC 不等价，实际授权待核对 |

**代码布局**：[Terraform Root/Module 总入口](../../../azure/infra-terraform/README.md)：`components/<component>/` 是独立 root，`modules/<component>/` 定义资源，`components/<component>/environments/dev.tfvars` 定义环境；State 使用既有 `dev/<component>.tfstate`。Root 有 `storage`、`workspace`、`onelake`、`notebook`、`data-factory`、`warehouse`、`foundation-iam`，不意味着当前 MVP 要全部 Apply。已存在的 Storage 与 Workspace 不需要重建。

**目录清理（2026-10-16）**：早期 OIDC / Blob Terraform Smoke 源码已从 Main 删除；正式 Azure IaC 只使用 [`azure/infra-terraform/components/`](../../../azure/infra-terraform/README.md) 和 `modules/`。历史 Smoke 证据保留在 Git 历史中，不属于 OneLake MVP；本次没有执行云端操作。

## 3. 三个真实 Plan 已完成，但尚未 Apply

Self-Runner [Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 已实现 `workflow_dispatch`，可选组件、`environment=dev`、`operation=plan|apply`。默认 Plan；Terraform CLI、OIDC backend、remote state、fmt/validate/plan 均有验证记录。**工作流具备 Apply 入口不等于这次获得授权。**

2026-10-15 三个 Component 使用同一 Healthcare SHA `6acb59353f5d7630f65b6f417c8e8bfbd39cf651`，全部 `operation=plan`：

| Component | 拟新建资源 | Self-Runner 真实证据 | Plan |
| --- | --- | --- | --- |
| `onelake` | `fabric_lakehouse` — `lh_omop_analytics` | [38799966270 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270/attempts/2) | **1 add / 0 change / 0 destroy** |
| `notebook` | `fabric_notebook` — `nb_omop_snapshot_load` | [38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550) | **1 / 0 / 0** |
| `data-factory` | `fabric_data_pipeline` — `pl_omop_snapshot_to_onelake` | [38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221) | **1 / 0 / 0** |

**已证实**：三项合计 Plan 提议新增 3 个 Fabric Item，`APPLY_EXECUTED=NO`、`DESTROY_EXECUTED=NO`；**尚未实际创建这 3 个资源**。此结论不代表 2026-10-16 重新查询云端状态，也不代表云端真实业务链路已部署。

## 4. 已敲定架构之外，仍需讨论的实施问题

以下属于**待批准设计**，不作为已经冻结的实现合同：

1. **Exporter/Manifest**：首批 OMOP 表、同一快照一致性与 FK、全量或增量策略、数据格式/字段、`export_id`、SHA、READY 时机和只读恢复。
2. **Blob 权限与访问**：源身份、容器 RBAC、Fabric Notebook 读 Azure Blob 的真正凭证/数据面权限、网络与费用。
3. **Notebook 业务逻辑**：Manifest/DQ/PK/FK/行数校验、Delta 目标布局、同 Export 重跑幂等、失败时不得污染已接受的 Delta 内容。
4. **Pipeline 参数和触发**：真实 Notebook GUID、`export_id`/`manifest_uri` 传递、成功/失败 Gate、手工首跑与未来自动调度边界；原 Fail Activity 不能在没有可用 ETL 时被替换成空成功。
5. **真实部署/验收**：Fabric Workspace/Capacity/权限、已有 Item 防重复、受控分组件 Apply/读回、PG→Blob→Notebook→OneLake 的完整 E2E/独立对账。

**保持缩小范围**：先完成最小合成 OMOP Snapshot → 云端 Delta → 只读对账，不把 Warehouse、CDC、Gold、dbt 或跨云全自动调度作为首版阻塞项。

## 5. 代码规范与运行安全

今后代码按 [组件命名标准](../../development/CODE-ORGANIZATION-AND-NAMING.md) 组织，例如 `apps/omop_export/` 等功能路径；不创建 `taskNNN/stepNNN` 正式源码。Azure 现有 `data-factory`、`notebook` 等是**组件名**，可以保留。

**本轮纯文档**；不运行 Terraform Plan/Apply、Fabric Pipeline、Notebook、数据库导出或数据上传。不因“Plan 成功”创建云端资源，也不因“数据最少”跳过权限/幂等/一致性 Gate。运维规范迁移前参考 [Terraform 技术架构](../../../azure/infra-terraform/docs/ARCHITECTURE.md) 与 [Plan Evidence](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)。
