# Tasks

> **Active / Stage 0**：先冻结实现边界，再进行小步代码 PR；不得执行任何 Terraform init/plan/apply/destroy 或 Azure/Fabric 写操作。PR 必须绑定本 Change 并更新对应 Task。

## 1. Baseline and safety

- [x] 1.1 核实已批准架构、PR #247 离线 Preflight Main 合并和 PR #248 归档，确认旧 State/Workspace/Storage 保护约束。
- [ ] 1.2 核对 Terraform Root/Module/Provider 版本和 Self-Runner `azure-infra.yaml` 当前身份映射；取得真实源码审计结论。
- [ ] 1.3 锁定新环境的独立 Root/State Key、Tenant A Backend vs Tenant B Provider 输入、认证选择及负向测试方案。

## 2. Terraform offline implementation

- [ ] 2.1 独立环境 Backend 配置与双身份参数，附旧 `dev` State、跨环境冲突、无效或 Secret 输入的 fail-closed 单测。
- [ ] 2.2 Workspace 与 Capacity attachment Terraform 配置及依赖/输出，验证现存 Workspace 不会被静默接管。
- [ ] 2.3 Lakehouse Terraform 配置和唯一资源所有权，确保 fabric-cicd 不重复管理。
- [ ] 2.4 基于 Provider 已验证 Schema 添加 Azure Blob Connection Root/Module，隔离 Reader 的 Tenant A 与部署身份 Tenant B。
- [ ] 2.5 更新源码 CODE.md/Runbook 和 CI，取得精确 HEAD 的离线验收。

## 3. Review and closeout

- [ ] 3.1 各小 PR 的 CI/源码审核通过并合并，记录 Main SHA/证据；未经单独授权不进行云端 Plan 或 Apply。
- [ ] 3.2 确认 Terraform 交付范围验收后按规定独立归档；真实跨租户连通/部署仍需其他 Change 和授权。
