---
status: active
scope: azure-fabric-terraform-source-map
last_verified: 2026-10-20
---

# Fabric Terraform — CODE 源码导航

> **唯一可用部署入口**：
> [`components/fabric-environment/`](../../../../azure-fabric/infra-terraform/components/fabric-environment/README.md)。
> 不再运行历史七个独立 Component Roots；旧 `dev.tfvars` 已删除。

| 源码入口 | 职责 |
| --- | --- |
| [单组合 Root `main.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/main.tf) | 用 `terraform.workspace` 传入同名 Workspace，编排三个 Modules |
| [`versions.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/versions.tf) | Fabric Provider 与 AzureRM Backend |
| [`variables.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/variables.tf) | Capacity、IAM、Lakehouse、Connection 输入 |
| [`outputs.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/outputs.tf) | Workspace/Lakehouse/Connection 真实 IDs |
| [`healthcare-omop.tfvars`](../../../../azure-fabric/infra-terraform/components/fabric-environment/environments/healthcare-omop.tfvars) | 已有 Workspace 的非秘密配置，新 Workspace 可使用默认值或另加配置 |
| [Workspace Module](../../../../azure-fabric/infra-terraform/modules/workspace/main.tf) | Fabric Workspace 创建/导入及 Workspace IAM |
| [Lakehouse Module](../../../../azure-fabric/infra-terraform/modules/onelake/main.tf) | Fabric Lakehouse 与可选 OneLake 权限 |
| [Connection Module](../../../../azure-fabric/infra-terraform/modules/connection/main.tf) | 可选 Azure Blob Connection，不包含 Secrets |
| [Terraform CI](../../../../.github/workflows/fabric-provider-init-validate.yml) | 唯一 Root 与三个 Module 的离线 Init/Validate 和合同检查 |
| [Self-Runner 部署入口](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) | Workspace 名称、inspect/adopt/plan/apply，实际权限和 State 需验证 |

## 历史源码与 State

历史独立 Roots（workspace、onelake、storage、data-factory、notebook、
warehouse、foundation-iam）及闲置 Modules 已删除，历史代码见
[删除前 Git 快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/20a6449000fe10eac642ab2dbcef37976339572b/azure-fabric/infra-terraform)。
原 `dev/*.tfstate` 等实际 AzureRM Backend 对象没有因此改变。
接管已有 `healthcare-omop` 时，应先独立检查这些 State 是否管理
相同 Fabric Workspace GUID，禁止重复所有权。

[架构边界](ARCHITECTURE.md) ·
[Active OpenSpec](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)
