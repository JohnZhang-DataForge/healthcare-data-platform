# Tasks

> **DESIGN-ONLY / NO RUNTIME AUTHORIZATION**：本 Change 仅冻结跨账号 Fabric 可重建架构。下面勾选只表示设计文档交付，不代表 Terraform Apply、Fabric 部署、Blob 跨租户连接或业务 E2E 验收。所有后续开发任务须由独立功能 Changes 承担。

## 1. Design review and documentation

- [x] 1.1 只读核对 Healthcare Main、既有 Azure/Fabric 七个 Terraform Roots 与 Self-Runner 身份/State/Bootstrap 行为、相关架构及当前真实验收范围；检查微软官方 Terraform + fabric-cicd 部署思路与 GitHub 原生集成限制。
- [x] 1.2 在 `documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md` 冻结稳定 Blob、独立 State/身份、唯一资源所有者、fabric-cicd 发布、跨租户 Blob 连接前置条件、安全闸门与最小验收目标。
- [x] 1.3 维护设计索引及 Azure/Fabric 组件 README 与 V2 总路线的单一设计导航，不在工程或项目状态中维护平行实施 Tasks。
- [x] 1.4 审核原设计 HEAD `56f98a7a22de109f54d3ebbc5b52b491ffaf3dfe` 的三项静态 CI 均 SUCCESS：Documentation Relative Links Run `39276208292`、OpenSpec Change Gate Run `39276208546`、OpenSpec Static Validation Run `39276208530`；PR #244 仅改八个 Markdown/OpenSpec YAML 文件，不含 .tf、Runner Workflow 或运行环境操作。最终 HEAD/受信任合并门禁由 PR 的合并检查决定。

## 2. Closeout

- [x] 2.1 设计 PR [#244](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/244) 已于 2026-10-19 Squash Merge Main `efda4df4bb6a1d7c2163c06b6c8de2a77eaa234b`；精确 PR HEAD `091e2a0587959637db002c9472049303bde720ca` 的 OpenSpec Static Validation `39276328160`、Change Gate `39276327906`、Documentation Relative Links `39276328073` 均 SUCCESS，主分支 Required Merge Gate 通过。无 Terraform / Fabric / Runner Runtime 操作。本独立 Archive PR 仅迁移这个纯设计 Change 的 4 个文件，保留后续实施为未完成的独立 Change；合并后 Archive 才正式生效。
