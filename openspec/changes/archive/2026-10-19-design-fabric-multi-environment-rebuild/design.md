# Design

## Context

用户已确认 **方案 B：Terraform + GitHub Actions + fabric-cicd**，目标为“有效新 Fabric 账号/容量准备好之后，使用同一份源码和固定的 Azure Blob，一次受控部署就恢复 Fabric 分析环境”。仓库当前只拥有失败保护 Bootstrap Terraform 和 Plan-only 历史证据，不能把设计当作已验证能力。

长期权威设计：[Fabric Multi-Environment Rebuild Design](../../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)；现状请以 [Terraform Architecture](../../../../documents/systems/azure-fabric/infra-terraform/ARCHITECTURE.md) 和 [Project Status](../../../../documents/engineering/status/PROJECT-STATUS.md) 为准。本 Change 不复制完整架构或创建另一份开发任务总账。

## Decisions

1. 稳定本地发布者 + 现有 Azure Blob `johnzhang/landing`；Remote Backend 继续使用 `johnzhang/tfstate`。不触碰原有 `dev/<component>.tfstate`，新环境显式使用隔离 Key，不能单凭 Terraform CLI Workspace 替代身份/权限分离。
2. Terraform 管理 Fabric Control Plane：Workspace、RBAC、Lakehouse（沿用 `onelake` 所有权）和 Blob Connection；不重复 Apply Azure 稳定层 `storage`、`foundation-iam`。Capacity/管理员设置由外部准备。
3. fabric-cicd 从 GitHub Actions 工作树发布 `Notebook`、`DataPipeline`；GitHub 原生 Workspace Git Integration **不要求**存在。业务 Item 的源格式必须验证，避免手写伪 `.platform`；默认不调用 orphan unpublish。既有 Terraform Notebook/Pipeline Bootstrap 在实际过渡前要清查所有权。
4. Backend Azure Tenant A、Fabric Tenant B、Blob Reader A 各有最小独立权限；跨租户 Blob Connection 需要实测。Terraform Secret 注入/State 存储风险显式治理。
5. 有审计门槛的一次入口：Preflight → Plan → 用户批准的 Apply → fabric-cicd → Pipeline/Notebook 执行 → 数据与权限 Readback。Git SHA、State Key、环境 ID、Run/Batch 必须绑定实际证据，不能把 Plan PASS 声称 E2E。

## External evidence and qualifications

- [Microsoft official end-to-end automation tutorial](https://learn.microsoft.com/en-us/fabric/cicd/tutorial-end-to-end-automation)：Terraform / fabric-cicd 分工；官方非交互式 Github Workspace Git 接入案例限制，故直接部署更稳妥。
- [fabric-cicd documentation](https://github.com/microsoft/fabric-cicd/blob/main/docs/index.md)：允许按 `Notebook`/`DataPipeline` Scope 发布，同时支持危险的 orphan unpublish，需主动排除。
- [Blob connector](https://learn.microsoft.com/en-us/fabric/data-factory/connector-azure-blob-storage-overview)：Service Principal/SAS 认证支持；不以一般文档代替跨租户实际验收。
- GitHub current Terraform / Self-Runner 为静态基线；本 Change 不执行 Cloud Plan，不读取实时 Terraform State。

## Validation and rollback

- 本 PR 只要求文档链接、OpenSpec Strict/Schema、受信任 Change Gate 的静态验证；未授权 Terraform/Cloud 写入一律不执行。
- 若某前提实测失败，后续实施 Change 报告阻塞/替代（例如 Reader SAS、连接定义/Provider API），重新批准后再改业务实现；不悄然放宽权限或依赖原生 GitHub Integration。
- 文档方案的回退仅通过后续审查 PR 修改设计/导航；本次无部署副作用。

## Follow-up

本次归档后以相关功能型 OpenSpec Changes 管理环境状态 Key/OIDC 分离、Fabric Workspace/Lakehouse/Connection、fabric-cicd Item 发布、Self-Runner Bootstrap/Readback，先以 OMOP→Fabric 最小可演示链路检验，再加入 FHIR/HL7。不可并行重建一份具体任务表于 `documents/`。
