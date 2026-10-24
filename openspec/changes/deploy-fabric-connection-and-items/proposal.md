# Proposal

## Why

2026-10-21 已由 Terraform 在现有免费 Trial F4 上真实创建 `johnzhang-test` Workspace 与 `lh_johnzhang_test` Lakehouse，Self-Runner #39635155333 Attempt 2 PASS，两个 Root 重复 Plan 无漂移。下一阶段需连接已有 Azure Blob Landing，并部署可运行的 Notebook/Data Pipeline；不得重做已验证基础设施或启动付费 Capacity。

## What Changes

- 复用现有 `modules/connection`，增加 `shared-infra/connection` 独立可选 Terraform Root/State；默认不创建连接；先完成离线配置/Schema 验证，再在确认 Blob Reader 主体、Fabric Connector 元数据和已存在连接清单后单独申请 Live Plan/Apply。
- `fabric-cicd` 独占 Notebook 和 Data Pipeline 的创建、更新、删除及代码发布；不再让 Terraform 管理这些 Item。为 `johnzhang-test` 增加 Fabric 原生源码、受控部署入口及正负测试，部署前核验 Workspace/Lakehouse Terraform Outputs 和现有 Item 所有权。
- 先通过无数据写入的 Notebook/Pipeline Smoke，再开发 OMOP person/visit_occurrence Blob READY Manifest → Notebook → Lakehouse Delta 双表可重放业务 E2E。
- Self-Runner 必须固定 Healthcare 40 位 SHA、严格白名单、OIDC、单操作模式；部署默认禁用删除/孤儿清理及跨 Workspace 修改。

## Capabilities

### New Capabilities

- `fabric-connection-and-item-delivery`：独立 Connection State 与 Fabric Git Item 的单一所有权/安全发布。

## Impact

不创建或购买 Capacity，不重新 Apply `workspace`/`onelake`，不重放 Local DP 已验收批次。第一批仅独立 Connection Root 源码与静态 CI；不在此 PR 执行 Azure/Fabric Plan/Apply、发布 Notebook 或启动业务 Pipeline。实际连接权限、服务主体凭据、Lakehouse 数据写入及 Fabric-cicd 的运行兼容另行验证。
