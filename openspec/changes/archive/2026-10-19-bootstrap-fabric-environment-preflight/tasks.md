# Tasks

> **Active implementation Change — bounded first slice only**。本 Change 交付纯本地配置/静态校验和人工前置 Runbook；不接管或删除既有 Workspace/State，不执行任何 Azure、Fabric、Terraform Plan/Apply。跨账号真实部署仍按后续独立 Change 实施。

## 1. Implement safe preflight

- [x] 1.1 核对已批准多环境设计、旧七 Root/Runner 身份与 State Key、受保护 Workspace 以及官方非交互式部署前置条件。
- [x] 1.2 提交非敏感环境 JSON 示例与 fail-closed 的 Python Preflight 校验源码；静态合同禁止旧 `dev` State、非法 GUID 和旧 Workspace 名称，且不访问 Azure/Fabric。
- [x] 1.3 提交并执行正常/非法/重复配置及 Secret 边界的单元测试，记录准确测试结果。
- [x] 1.4 编写中文“每个新 Fabric 账号手工前置 Runbook”，同步 Operations 入口与 Terraform CODE.md；区分首次初始化与每次新账号，并新增离线单测 PR CI 工作流。
- [x] 1.5 核对本轮仅新增 Tool/Tests/Docs/Spec，不触碰现有 Terraform Root、Runner、State/Workspace，PR HEAD 静态与适用 CI PASS。

## 2. Closeout

- [x] 2.1 PR 合并后根据确切 Main SHA 与测试证据完成本 Change 的验收与独立归档；不因为本次通过静态检查就称“Fabric 环境已一键重建”。

## 验收记录（PR #247）

- 实施 HEAD：`968e7adda66fe0834abbc512be4bf193dda6c65b`；仅静态 Preflight/Runbook/CI，未执行云端操作。
- Offline tests: [Fabric Environment Preflight Run #39280299661](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39280299661) SUCCESS；包含正反向与示例 fail-closed。
- OpenSpec Static [Run #39280299540](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39280299540)、Docs Links [Run #39280299477](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39280299477)、Naming [Run #39280299375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39280299375) SUCCESS。
- Change Gate [Run #39280299409](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39280299409) 的 job 各步骤 SUCCESS；最终 Run 结论与 merge 前重新确认。
- 1.3/1.5 表示静态与代码范围检查，不代表 Backend/Fabric 身份、网络、实际 State/资源存在性、Terraform Plan/Apply 或 Fabric E2E 已验收。2.1 已由 Main 合并 `882a7248f059508b2c135403b3bf3ad01438f604` 和本独立归档 PR 收尾；仅离线行为验收，不代表云端 E2E。

- Final PR HEAD: `5eebe04f610255554ed7f2d6ec63a16f23c45505`；[Offline #39283789373](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39283789373)、[OpenSpec #39283789389](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39283789389)、[Change Gate #39283789353](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39283789353)、[Naming #39283789371](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39283789371)、[Docs #39283789447](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39283789447) 全部 SUCCESS；[PR #247](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/247) 已合并。归档 PR 合并仍需独立 CI 门槛。
