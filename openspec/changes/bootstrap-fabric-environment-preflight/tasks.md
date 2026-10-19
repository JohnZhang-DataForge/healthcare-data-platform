# Tasks

> **Active implementation Change — bounded first slice only**。本 Change 交付纯本地配置/静态校验和人工前置 Runbook；不接管或删除既有 Workspace/State，不执行任何 Azure、Fabric、Terraform Plan/Apply。跨账号真实部署仍按后续独立 Change 实施。

## 1. Implement safe preflight

- [x] 1.1 核对已批准多环境设计、旧七 Root/Runner 身份与 State Key、受保护 Workspace 以及官方非交互式部署前置条件。
- [ ] 1.2 提交非敏感环境 JSON 示例与 fail-closed 的 Python Preflight 校验源码；记录旧 State 不可覆盖的约束。
- [ ] 1.3 提交并执行正常/非法/重复配置及 Secret 边界的单元测试，记录准确测试结果。
- [ ] 1.4 编写中文“每个新 Fabric 账号手工前置 Runbook”，同步 Operations 入口与 Terraform CODE.md；区分首次初始化与每次新账号。
- [ ] 1.5 核对本轮仅新增 Tool/Tests/Docs/Spec，不触碰现有 Terraform Root、Runner、State/Workspace，PR HEAD 静态与适用 CI PASS。

## 2. Closeout

- [ ] 2.1 PR 合并后根据确切 Main SHA 与测试证据完成本 Change 的验收与独立归档；不因为本次通过静态检查就称“Fabric 环境已一键重建”。
