---
status: active
scope: azure-fabric-terraform-component
last_verified: 2026-10-20
---

# Azure / Microsoft Fabric — Terraform IaC

**当前账号唯一 Terraform Root：**
[`fabric-environment`](../../../../azure-fabric/infra-terraform/components/fabric-environment/README.md)。
[源码索引](CODE.md) ·
[最新架构](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) ·
[实施任务](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。

此 Root 复用三个 Modules：Workspace/IAM、Lakehouse/OneLake、Connection。
Terraform CLI Workspace 名与真实 Fabric Workspace **一致**。已存在的
`healthcare-omop` 必须先核对旧 Remote State 归属并明确导入；
新 Workspace 可以使用同一 Root 和独立 CLI State 进行创建。

**平台前置**：当前已授权部署身份、可用 Capacity、既有 Azure Blob Landing
及 Reader 权限、AzureRM Backend 及权限均在本 Terraform 外部。
不实施多账号切换、Tenant/Subscription/Capacity/Storage Bootstrap；
Notebook 和 Pipeline 业务 Items 属于 `fabric-cicd`。

原七个分立 Root、五个已不使用的 Module 以及
`dev.tfvars` 已从当前 Git 工作树移除；历史版本仍可由
[Git 快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/20a6449000fe10eac642ab2dbcef37976339572b/azure-fabric/infra-terraform)
查阅。**删除 Git 源码不影响远端旧 State、已存在 Fabric/Azure 资源**
——旧 State 仍需独立审查，不能同时管理一个 GUID。

静态 CI 不等于真实环境已验证；历史 Plan-only 结果和具体 State 边界
参见 [历史技术记录](ARCHITECTURE.md)。当前真实 Import、Plan/Apply、
Landing 访问与 E2E 仍未执行/确认。
