# Azure 旧源码目录退役审计（2026-10-18）

> **范围：仅 Git 源码目录和文档退役。** 本次没有运行 Azure/Kubernetes/PG/S3、Terraform Plan/Apply/Destroy、Fabric Pipeline/Notebook，也没有访问或修改远程 Terraform State。历史 Plan 成功不代表实际云资源已创建。

## 1. 固定检查基线与结论

- Healthcare `main` 删除前固定 Commit：[`a0891d08eb934ef1c954576c9ca006fe99b1c02b`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/a0891d08eb934ef1c954576c9ca006fe99b1c02b)。
- 原位置：`azure/infra-terraform/`；退役后的唯一 Terraform 源码位置：[`azure-fabric/infra-terraform/`](../../../azure-fabric/infra-terraform/README.md)。
- 原目录共 **81 个 tracked 文件**（包括 `.gitignore`、旧 `README.md`、旧 `docs/ARCHITECTURE.md`）；新目录保留全部 Terraform 实现、Provider/Variable/Backend/IAM、环境参数与引用模板。
- Git 对象核对：原、新 `components/` Tree SHA 均为 `8161cbe375a0ca92c56feaf391a6b1dc93ae8ce2`，`modules/` Tree SHA 均为 `c7a44329bb790f393c2885e1bfee97d01d496c48`；`.gitignore` Blob SHA 均为 `9a08c4f01a8c14e9958610731deff75d883ed597`。因此新目录的**所有可执行 Terraform 配置、实现模块及忽略规则完全相同**。两份 README/ARCHITECTURE 文档内容有意不同：新文档是经更新的规范入口，不需要恢复旧表述。
- [新 Terraform README](../../../azure-fabric/infra-terraform/README.md)、[技术架构与验证记录](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md)、[系统说明](../../systems/azure-fabric/README.md) 与 [源码导航](../../systems/azure-fabric/CODE.md) 已承接旧 README 的可用技术知识；旧原文仍可[从固定 Commit 查阅](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/a0891d08eb934ef1c954576c9ca006fe99b1c02b/azure/infra-terraform/README.md)。

## 2. 执行入口和 State 安全

- 正式入口：Self-Runner [`azure-infra.yaml`](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml)，当前以 `healthcare/azure-fabric/infra-terraform/components/$COMPONENT` 为 Root，独立选择七个 Component、`environment=dev`、默认 `operation=plan`。
- **旧目录删除前**新路径七次 Plan-only 验证成功：[storage](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988729752)、[workspace](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988731519)、[onelake](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988732887)、[data-factory](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988734473)、[notebook](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988735923)、[warehouse](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988737433)、[foundation-iam](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988738899)（2026-10-16，均为历史成功证据，非本次重新执行）。
- 所有远程 State Key 维持 `dev/<component>.tfstate`，使用既有 Azure Blob 后端；**删除 Git 文件不会自动 Destroy，亦不会完成已有 Workspace 的 Terraform Import**。
- Self-Runner 的两份手工旧 Smoke Workflow（`azure-terraform-oidc-smoke.yml` 和 `azure-terraform-landing-blob-write.yml`）分别锁定旧 Healthcare Commit `1a42403635a9e40944769c01b78aac0cced7e47f`、`f9d911be125753528e78a739ade1af8e36752db2`。它们不是现行 `main` 的执行入口；此次没有执行、修改或清理那些历史测试及远端状态。

## 3. 文档和路径切换

- 清理 README、[System Overview](../../architecture/SYSTEM-OVERVIEW.md)、[Data Flow](../../architecture/DATA-FLOW.md)、[Infrastructure](../../architecture/INFRASTRUCTURE.md)、[Operations](../operations/README.md)、[Safe Operations](../operations/SAFE-OPERATIONS.md) 以及新的 Azure/Fabric 系统文档中的旧相对链接。
- 更新 [项目状态](../status/PROJECT-STATUS.md)、[文档导航](../../README.md) 和相关过渡说明；新的相对链接必须在同一 PR 经过 [Documentation Relative Links](../../../.github/workflows/documentation-links-check.yml) 检查。
- 旧 `documents/components/azure-fabric/` 仍是迁移过程中的说明副本，未来可以另行收敛到 `documents/systems/azure-fabric/`；**它不是旧 `azure/` 业务源码目录**。历史设计稿提及旧路径的段落只作为当时决策记录，不构成当前执行指引。
- 代码目录 `azure/` 从 Git Main 整体删除；如需审查或回退，用本页固定的删除前 Commit，不在 Main 中保留另一套重复可执行 Terraform 源码。

## 4. 验收边界

此退役仅表示**源码路径和文档导航切换**，不是 `PostgreSQL → Azure Blob → Fabric Data Pipeline → PySpark Notebook → OneLake` 的业务 E2E。Exporter、Fabric-native Git Items、真实 Notebook/Pipeline、IAM/Import、OneLake 写入和跨平台对账仍按 [现行项目状态](../status/PROJECT-STATUS.md) 单独开发与授权。不得仅凭目录删除、文档 CI 成功或旧 Terraform Plan 成功宣称云端已经部署。
