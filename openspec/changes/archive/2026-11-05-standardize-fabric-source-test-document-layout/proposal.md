# Proposal — Standardize Fabric source, tests and documentation ownership

## Why

Healthcare 曾多次迁移代码、测试和说明文档，仍有源码树 `tests/`、说明性 `README.md`、过期 Fabric 路径导航，以及互相冲突的 Agent/Shared Engine 指令。这导致开发者按局部习惯创建新目录，即使 CI PASS 也无法证明符合已采用的仓库架构。

本次只治理导致重复返工的**文件归属和静态质量门禁**，不再发起整仓搬家。

## What Changes

1. 以“源码 / Git-native Fabric 资源 / 测试 / 人类文档 / OpenSpec Change”明确唯一归属和过渡期例外。目标是全仓**禁止新增**违规文件，存量只先清理 Azure Fabric。
2. 在 `.github/quality/scripts/` 建立统一只读结构检查及正负向测试，提供受保护的 PR 检查；对不迁移的 Local DP、Portal、Shared Engine 历史测试/README 使用**精确现有路径**临时基线，禁止新建同类违规文件。
3. 先将 Fabric 源码目录的 **8 份 README** 与 2 份说明性 Markdown 做知识对账，独有技术规则归 `documents/systems/azure-fabric/` 或对应架构/运维文档；原始证据及回滚链接保留。
4. 只迁移 Fabric 的 **15 个** Python 测试文件至 `.github/quality/tests/azure-fabric/`，同步 `unittest discover`、工作流 `paths`、Python import、fixture、静态 CODE-map 和跨仓 Self-Runner 依赖。每组 CI 通过后再删除旧路径。
5. 核实 `notebook-development/` 的 2 个 Python 文件归属：仅在明确是测试辅助且全部依赖已验证后，才可迁至 `.github/quality/scripts/`；否则保留有正式功能所有权的源码。**不强制重命名 `warehouse/`、`openlineage/` 或新增 `azure-fabric/src/`。**
6. 修正现有检查仍使用旧 `workspaces/healthcare-omop/notebooks/`、`pipelines/` 的问题，真正保护根级 `*.Notebook/` / `*.DataPipeline/` 等原生 Item。

## Impact

- 范围：Healthcare 仓库治理文档、Agent 规则、`.github/quality/`、相关 GitHub-hosted 测试 CI、Azure Fabric 源码区说明文档与 15 个离线测试。
- 不改变：`shared-data-engine/src/`、Local DP/Portal/Shared Engine 的现有测试物理目录或业务代码；Warehouse SQL/Identity/Writer、OpenLineage 业务逻辑、Fabric Notebook/Pipeline/Environment/Lakehouse 元数据。
- Fabric 现有 `dw-omop-5.4` 仍属于同一 Workspace，但为 Workspace-only、Git UpdateFromGit 保护的真实资源；SQL/Writer 文件仍归 `azure-fabric/warehouse/`。
- 全程不执行 Terraform Apply/Destroy、不启动 Fabric Spark/SQL、无数据库、K8s、Blob 或 Marquez 运行时写入。

## Release Strategy

- 首个 PR **仅提交本 OpenSpec 方案与存量清单**，不修改生产源码、测试位置或工作流；本次方案合并 != 已实施。
- 随后的独立 PR 首先落实规范与 CI Gate，再分组整理文档和测试，必要时再做可证明的辅助工具清理。
- 明确保持开放的任务与 STOP/HOLD 条件，用户无需再经历一次无边界的全仓四天搬迁。
