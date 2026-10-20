---
status: active
scope: azure-fabric-terraform-source-map
last_verified: 2026-10-20
source_sha: null
---

# Azure / Fabric Terraform — CODE 源码导航

> **CODE.md 保持已存在的源码位置地图（并不宣称已完成重构）**。将来基于 [Module-first 新架构](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) 复用已有 Modules、建立统一环境 Root 的源码提交，必须在同 PR 更新本页和相关 CI/Workflow 导航。

> **唯一 Terraform 组件源码导航（ACTIVE）**。只登记当前 Main 应有的 Root/Module；功能说明见 [README.md](README.md)，历史 State/Plan 证据见 [ARCHITECTURE.md](ARCHITECTURE.md)。此处源码存在不代表云资源已部署或批准 Apply。

## Terraform 根目录与工作流

- [Terraform 源码根目录](../../../../azure-fabric/infra-terraform/) · [`.gitignore`](../../../../azure-fabric/infra-terraform/.gitignore)
- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml)：从 Healthcare `main` 检出源代码，`root=healthcare/azure-fabric/infra-terraform/components/$COMPONENT`；手动选择 `environment=dev` 与 `operation=plan|apply`（默认 Plan）。
- **Root/Module 关系**：每个 `components/<name>/modules.tf` 调用 `../../modules/<name>`，Root 保存 `versions.tf`、`providers.tf`、`variables.tf`、`outputs.tf`、`iam.tf` 和 `environments/dev.tfvars`。每个 Root 远程 State key 独立为 `dev/<component>.tfstate`。

## 七个 Root / Module 源码地图

| Root | Root、环境与 Provider | Module 与 IAM | 职责和限制 |
| --- | --- | --- | --- |
| `storage` | [Root](../../../../azure-fabric/infra-terraform/components/storage/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/storage/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/storage/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/storage/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/storage/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/storage/outputs.tf) | 已有 Azure Storage/Blob 查询；可选 Blob RBAC；不重新创建已有账户或 Landing |
| `workspace` | [Root](../../../../azure-fabric/infra-terraform/components/workspace/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/workspace/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/workspace/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/workspace/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/workspace/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/workspace/outputs.tf) | Fabric Workspace 与角色分配；手工 Workspace 必须先核对 State/Import |
| `onelake` | [Root](../../../../azure-fabric/infra-terraform/components/onelake/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/onelake/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/onelake/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/onelake/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/onelake/outputs.tf) | Fabric Lakehouse 与预览数据访问规则；`data_access_roles={}` 默认不授予权限 |
| `notebook` | [Root](../../../../azure-fabric/infra-terraform/components/notebook/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/notebook/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/notebook/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/notebook/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/notebook/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/notebook/outputs.tf) | Fabric Notebook Item 壳与受控 Bootstrap；Bootstrap 故意失败，非业务 ETL |
| `data-factory` | [Root](../../../../azure-fabric/infra-terraform/components/data-factory/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/data-factory/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/data-factory/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/outputs.tf) | Fabric Data Pipeline Item；未绑定真实 Notebook GUID 时保持 Fail |
| `warehouse` | [Root](../../../../azure-fabric/infra-terraform/components/warehouse/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/warehouse/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/warehouse/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/outputs.tf) | 可选 Fabric Warehouse；非首阶段必选 |
| `foundation-iam` | [Root](../../../../azure-fabric/infra-terraform/components/foundation-iam/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/foundation-iam/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/foundation-iam/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/outputs.tf) | Resource Group 级可选共享角色；`shared_role_bindings={}` 默认无新增授权 |

上表直接定位七个 Root 的核心文件；每个 Root 还包含 [上文说明的](../../../../azure-fabric/infra-terraform/components/) `variables.tf`、`outputs.tf`、`versions.tf` 与 `iam.tf`。**Module 定义资源与权限，Root 选择资源及参数，`dev.tfvars` 提供环境值；源码有定义不代表远程资源已实际创建。**

## Fabric Item 安全 Bootstrap（归 Terraform 管理）

| 实际源文件 | 归属与安全边界 |
| --- | --- |
| [`modules/notebook/main.tf`](../../../../azure-fabric/infra-terraform/modules/notebook/main.tf) | 定义 Terraform 管理的 Notebook Item，引用受控 Bootstrap |
| [`notebook-content.py`](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | 带 `export_id`、`manifest_uri` 参数的 Bootstrap，**故意抛出 RuntimeError** |
| [`modules/data-factory/main.tf`](../../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | 依据 Notebook ID 选择 Pipeline Item 定义 |
| [`pipeline-disabled.json`](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) | 缺少 Notebook GUID 时的 Fail Activity |
| [`pipeline-notebook.json`](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) | Notebook Activity 模板；不是已运行的业务 Pipeline |

这些 Bootstrap 文件不属于未来 `azure-fabric/workspaces/healthcare-omop/notebooks/` 或 `pipelines/` 中的 Fabric Git 原生业务 Item。后者由 [Notebooks CODE](../notebooks/CODE.md) 和 [Pipelines CODE](../pipelines/CODE.md) 负责；未来真实 Item 的 `.platform` 元数据和 Terraform 交付权属必须先完成审查。


## 清理后的真实源码边界

- [原有 `components/`](../../../../azure-fabric/infra-terraform/components/)：七个独立 Terraform Roots，各自以 `modules.tf` 复用 `modules/`，目前仍由 [Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 使用，工作流没有被此轮修改。
- [原有 `modules/`](../../../../azure-fabric/infra-terraform/modules/)：包含 Workspace/Role Assignment、Lakehouse 及其它原先存在的模块；**此轮没有删除或重写**。
- [Provider CI](../../../../.github/workflows/fabric-provider-init-validate.yml)：从新 Bootstrap Roots 验证改为七个旧 Root/Module 的离线 `fmt`、`init -backend=false`、`validate`。
- **已移除且无现行入口**：`bootstrap/`、`tests/`、`tools/`、`new-environments/` 和只为被删 Preflight 工具服务的 `environments/fabric-environment.example.json`；**不要通过本页当作当前源码引用**。
- **未来开发**：在保留旧 Root/Module 架构的前提下，为实际需要的 Connection 增加正式 Module；新增测试与配置跟随所管理的功能，不恢复失效 Bootstrap 合同。

实施任务见 [`simplify-fabric-environment-iac`](../../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。
