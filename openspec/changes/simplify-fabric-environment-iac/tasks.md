# Tasks

> **唯一有效的 Fabric Terraform 重构任务入口（2026-10-20 新决定）。** 长期架构：[Fabric Terraform Module-first Environment Architecture](../../../documents/architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)。此前 Bootstrap/多环境 Changes 的历史记录保留，不再继续以三套 App、A=B/A≠B 或 `new-environments` 作为下一步部署主线。

## 1. Documentation and architecture freeze

- [x] 1.1 核对 Main：旧 `components → modules → environments`、新独立 Roots 的重叠资源、现有 Self-Runner 引用，保留事实与设计差别。
- [x] 1.2 新建权威目标架构、Proposal、Design、Delta Spec，明确已授权部署账号、Landing、State、Capacity 是外部前置，统一组合 Root 可复用 Modules。
- [x] 1.3 更新旧文档/两个旧 OpenSpec Change 的失效标记、导航和项目状态，完成 PR CI 与 Main 合并。

## 2. Terraform refactor (not started)

- [ ] 2.1 盘点仍存的七个 Root/Modules、已删除三个新 Root 的历史源码、Terraform State/地址、业务所有权和 Self-Runner 依赖，确定保留/迁移/删除范围。
- [ ] 2.2 复用 `modules/workspace` 和 `modules/onelake`，整理正式 Workspace/Lakehouse Modules，保留 IAM，抽取 `modules/connection`。
- [ ] 2.3 建立 `components/fabric-environment` 组合 Root；环境配置、Provider、Backend 独立 State Keys、Module 输出与依赖可复用且无硬编码账号。
- [ ] 2.4 形成测试/CI/CODE.md：Terraform fmt/init -backend=false/validate，配置/State 隔离与 Modules 单元测试。

## 3. Real deployment (not started)

- [ ] 3.1 对已授权环境确认真实 Backend、Fabric/Capacity、Landing 权限及 State 所有权，Plan 阶段杜绝非预期 Delete/Replace。
- [ ] 3.2 真实 `terraform init/plan/apply` 并读回 Workspace、Lakehouse、Connection，确认真实 Landing 可读；重复 Plan 应稳定。
- [ ] 3.3 使用第二个 Fabric 账号或第二套环境配置和独立 State Key 部署，不改 Module 源码，验证互不影响。
- [ ] 3.4 整合 Self-Runner 已有成熟的 Plan/Apply 逻辑、使用真实环境资源 Outputs 发布 Notebook/Pipeline，经 fabric-cicd 与数据 E2E 验证。

## 4. Clean superseded scaffolds first (user-authorized 2026-10-20)

- [x] 4.1 按用户明确授权，先删除从未真实部署的新 `bootstrap/`、`tests/`、`tools/`、`new-environments/` 及仅服务于旧工具的 JSON 示例；移除失效 Preflight CI，将 Provider 静态校验重定向到原有七个 Components/Modules；不动远端 State 或 Fabric/Azure 云端资源。
- [x] 4.2 Healthcare [PR #335](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/335) 合并，12/12 CI PASS（含七个旧 Components/Modules 的 Terraform Provider 校验、OpenSpec、链接）；Self-Runner [PR #169](https://github.com/JohnZhang-DataForge/Self-Runner/pull/169) 合并，移除 20 个失效的 Fabric Bootstrap/OIDC 实验工作流、脚本、测试和文档。原 `azure-infra.yaml` 保留，CODE.md、Runbook、目标架构与项目状态已同步；历史代码可通过 Git 追溯。

**Status**：旧 Bootstrap/Tests/Tools/New-environments 源码及 Self-Runner 相关失效实验入口已删除并合并；现存七个 Root/Modules 和 `azure-infra.yaml` 保留。统一可复用 Environment Root 尚未开发，未改远程 State、未执行真实 Apply 或 Fabric E2E。
