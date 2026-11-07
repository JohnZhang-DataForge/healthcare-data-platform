# Proposal — Fabric dbt 项目目录和 AI 归属治理

## Why
当前正式 HL7 Parser、Delta Staging 和 dbt SQL 均在 `local-data-platform/spark/apps/hl7/`；FHIR Native Items 在 `azure-fabric/workspaces/`，FHIR Adapter 在 Shared Engine。没有统一的 dbt 项目准入规则，后续 Agent 可能再次随意新增目录、复制已有业务逻辑或误搬 Native Items。

## What Changes
- 将未来 Fabric 主线 dbt Core 项目的唯一目标父目录定为 `azure-fabric/dbt/`，首个项目名 `hl7-canonical`，内部 `name: hl7_canonical`。
- 定义完整 dbt 标准骨架，所有标准空目录在项目首次创建时使用 `.gitkeep` 保留，项目内部按 staging/intermediate/canonical 分层。
- 明确 `fhir-canonical`、`csv-canonical` 和公共业务项目只是未来候选，必须另经 OpenSpec、业务 Owner 和重复性审核。
- 将准入要求挂到根 `AGENTS.md`、Agent 规则、开发命名规范与 Fabric 导航，使新 AI 会话直接发现。
- 显式记录受保护 Layout Gate 与原生 dbt `tests/` 的冲突：先单独获批精确例外及正反验证，不能绕过现有门禁。

## Capabilities
### New Capabilities
- `fabric-dbt-project-layout`: Fabric dbt 项目布局、命名、来源/业务职责和 AI 路径治理。

## Impact
本轮**仅文件治理**，不新建或迁移执行源码、不更改受保护 CI、Fabric Native Item、Azure/OneLake/Gold 资源。当前已验证的 HL7 源仍在 Local DP；实际迁移与 gate 例外是后续独立 PR。
