# Proposal

## Why

Healthcare V2 已确认本地 K8s + 长期 Azure Blob 是稳定数据来源，Fabric 是可能随试用环境/合法可用账号变化的分析层。之前的 Terraform/Runner 只完成七个 Root 的 Plan-only 验证，绑定单个 `dev` State 和同一套 Azure/Fabric OIDC；Fabric Notebook/Pipeline 仅为失败保护占位。若不先明确新租户、Backend、业务发布和 Resource ID 的管理边界，未来换号将反复手工创建资源并引入误改旧 State 的风险。

## What Changes

- 以 **Terraform + Self-Runner GitHub Actions + fabric-cicd** 为已批准目标：Terraform 管理 Workspace/RBAC/Lakehouse/Blob Connection；fabric-cicd 从 GitHub 本地检出目录部署 Notebook/DataPipeline，不以 Fabric 原生 GitHub Integration 为第一版依赖。
- 保留现有 `johnzhang/landing` 和 `johnzhang/tfstate`，新 Fabric 环境使用新的 State Key / Fabric 身份；本地 PG/FHIR/HL7 Blob Publisher 与 Fabric 完全解耦。
- 明确 Backend Tenant A 与 Fabric Tenant B 的认证隔离、跨租户 Blob Reader 实测前提、Secrets 与 State 的风险、旧 Workspace Import 和 Terraform/fabric-cicd 同 Item 双写防护。
- 固定准备合法有效 Capacity/Service Principal/管理员许可后由一个受控 Workflow 执行 Plan → 经批准 Apply → 发布 → 数据重建 → 读回的目标路径；本轮仅写长期设计文档与导航。

## Capabilities

### New Capabilities

本 Change **只确认将来的部署架构**，不新增当前可观察功能，不创建 Specs。实施阶段将按照实际功能拆分独立 Active Changes。

### Modified Capabilities

无已运行行为变化。本次 `skip_specs: true`，不能把目标架构记录成已完成 Runtime Contract。

## Impact

只改 `documents/architecture/design/` 的长期目标设计/目录、Azure/Fabric 系统 README 的设计导航和本 OpenSpec Change；不改变 .tf/.tfvars、Self-Runner Workflow、State、K8s、PG、Blob、Fabric，亦不运行 Terraform Plan/Apply。
