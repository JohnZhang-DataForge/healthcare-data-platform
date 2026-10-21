# Tasks

> **唯一有效的 Fabric Terraform 重构任务入口（2026-10-20 方案收敛）。** 长期架构：[Fabric Terraform Module-first Environment Architecture](../../../documents/architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)。**本轮仅支持当前已授权 Fabric 账号**，首个 Fabric Workspace 的准确名称为 `healthcare-omop`。Terraform CLI Workspace 必须与 Fabric Workspace 同名。多账号选择/Account Profiles/双 Tenant Bootstrap 不做；此前已完成的清理不得重做。

## 1. Documentation and architecture freeze

- [x] 1.1 核对 Main：旧 `components → modules → environments`、新独立 Roots 的重叠资源、现有 Self-Runner 引用，保留事实与设计差别。
- [x] 1.2 新建权威目标架构、Proposal、Design、Delta Spec，明确已授权账号、Landing、State、Capacity 是外部前置，统一组合 Root 可复用 Modules。
- [x] 1.3 更新旧文档/两个旧 OpenSpec Change 的失效标记、导航和项目状态，完成 PR CI 与 Main 合并。
- [x] 1.4 按最新决定修订现有权威架构与 OpenSpec：只支持当前账号；已有 `healthcare-omop`；Terraform Workspace/Fabric Workspace 同名；CLI Workspace State 隔离；Outputs 与既有 Workspace 接管边界。**此项仅表示文档修改，代码和运行未完成。**

## 2. Terraform refactor (not started)

- [ ] 2.1 定向盘点仍存七个 Root/Modules、实际 State 地址与资源所有权；核对已有 `healthcare-omop` Workspace GUID、旧 Root State 与 Self-Runner 依赖；不重复历史全量清理。**源码和 Workflow 边界已核对；真实 Backend State/Workspace GUID 尚未从云端读回，留在 3.1 前继续核对。**
- [x] 2.2 复用 `modules/workspace`、`modules/onelake` 及 IAM；按 Provider 实际 Schema 实现可复用 `modules/connection`，不因名称调整而无故迁移资源地址。
- [x] 2.3 创建 `components/fabric-environment` 组合 Root：非 default Terraform CLI Workspace 直接作为 Fabric Workspace 名称；同账号多 Workspace；共享 Backend 的各 Workspace State 隔离；输出 Workspace/Lakehouse/Connection ID；无账号切换代码。
- [x] 2.4 必要的 `fmt/init -backend=false/validate`、Modules/Outputs、Workspace 命名与 State 隔离测试；部分资源操作不能使其他已管理资源被销毁；同步 CODE.md 和 CI。

## 3. Real deployment (not started)

- [ ] 3.1 在当前账号核对已有 `healthcare-omop`、Capacity、Landing、Backend 与历史 State 所有权，确定显式 Import/State Move（如需）；Plan 禁止非预期 Delete/Replace。
- [ ] 3.2 使用 Terraform CLI Workspace `healthcare-omop`，真实 Init/Plan/Apply，读回现有 Workspace、Lakehouse、Connection，确认 Landing 可读，重复 Plan 稳定；不得重复创建 Workspace。
- [ ] 3.3 在**同一当前 Fabric 账号**下选择第二个新的 Terraform/Fabric 同名 Workspace，复用同一 Root/Modules，确认相互隔离；**不要求第二个 Fabric 账号**。
- [ ] 3.4 扩展保留的 Self-Runner `azure-infra.yaml`：选择 Terraform/Fabric Workspace、资源操作范围与 Plan/Apply，当前账号认证与安全的 State 选择；输出真实资源 IDs，随后通过 `fabric-cicd` 发布 Notebook/Pipeline 并完成业务 E2E。**源码部分已通过 Self-Runner [PR #170](https://github.com/JohnZhang-DataForge/Self-Runner/pull/170) 合并（Main `de2fda0f181e756cc9029640720631afa566d740`）：原 `azure-infra.yaml` 增加 `fabric-environment / healthcare-omop` 与组合 State 拥有权检查，沿用旧七个 Root 的 Backend Key；尚无真实 Workflow Run/Cloud 读回，故 3.4 保持未完成。**

## 4. Clean superseded scaffolds first (completed 2026-10-20)

- [x] 4.1 按用户授权删除从未真实部署的新 `bootstrap/`、`tests/`、`tools/`、`new-environments/` 等旧实验目录、无效 CI；不动远端 State/云端资源。
- [x] 4.2 Healthcare [PR #335](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/335) 合并、12/12 CI PASS；Self-Runner [PR #169](https://github.com/JohnZhang-DataForge/Self-Runner/pull/169) 合并。原七个 Root/Modules 和 `azure-infra.yaml` 保留。

**Status**：部署就绪修订正在实施：正式 `healthcare-omop.tfvars` 与 Runner 工作流接管/只读检查模式同步修正；实际 Workspace GUID/Capacity/Blob Reader/OIDC 与 Remote State 仍需真实核对。2.2–2.4 **源码/静态验收完成**：新组合 Root、Connection Module、输出、默认 Workspace/既有 Workspace 防误部署检查、独立 Provider Init/Validate 和 4 项源码合同测试均由 PR #340 验证；七个历史 Root 保持原行为。2.1 的真实 Backend State / `healthcare-omop` GUID 盘点仍未完成；3.1–3.4 的真实认证、State 归属、Import、Plan/Apply、Landing 与 E2E 均未执行。不把静态 PASS 作为真实资源验收。
