---
status: historical-evidence
scope: azure-fabric-terraform-legacy-plan-and-state
last_verified: 2026-10-20
---

# Terraform 历史 Roots、State 与验证证据（只读历史）

本文件仅保留**已退役架构的审计入口**，不再指引直接运行旧 Root。
当前唯一部署入口见 [CODE](CODE.md)、
[单组合 Root](../../../../azure-fabric/infra-terraform/components/fabric-environment/README.md)。

## 旧资源与源码保存

删除前源码为
[Healthcare Git Commit `20a6449000fe10eac642ab2dbcef37976339572b`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/20a6449000fe10eac642ab2dbcef37976339572b/azure-fabric/infra-terraform)。

历史七个独立 Roots：
`storage`、`workspace`、`onelake`、`notebook`、
`data-factory`、`warehouse`、`foundation-iam`。
历史 AzureRM Backend Key 分别是
`dev/storage.tfstate`、`dev/workspace.tfstate`、
`dev/onelake.tfstate`、`dev/notebook.tfstate`、
`dev/data-factory.tfstate`、`dev/warehouse.tfstate`、
`dev/foundation-iam.tfstate`（均为历史**配置的路径**，
不是本次实时检查发现 State Blob 存在的证明）。

历史 Plan-only 验证示例：
[Storage OIDC/Backend Run 38761100632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632)、
[Foundation IAM Run 38767227655](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655)、
[OneLake Provider Run 38797932758](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38797932758)。
这些仅是旧版本流程历史证据，不是新组合 Root 已经 Apply。

## 现有 Workspace 接管边界

`healthcare-omop` 已人工存在，真实 GUID、Capacity、授权及旧 State
所有权仍需独立读回。删除旧 HCL 不删除 Blob 中的远端 State 或云端资源。
如果旧 State 仍记录相同 Fabric Workspace GUID，必须先审查 State
迁移/解绑策略，不允许一份云端资源同时被两份活动 State 管理。
`adopt` 是显式 Import 的 State 写入，必须在所有权确认后执行。
