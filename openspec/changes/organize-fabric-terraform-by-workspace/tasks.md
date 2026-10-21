# Tasks

> **本 Change 是当前有效的 Fabric Terraform 目标架构/开发任务入口。** 取代 `simplify-fabric-environment-iac` 的组合 Root/Apply-All 方案。本轮只做文档 PR，不执行 Terraform 源码变更、Workflow 变更、远端 State 迁移、云端操作。

## 1. Freeze architecture and change governance

- [x] 1.1 核对最新 Main 的 `components/`、`modules/`、`fabric-environment/`、旧 OpenSpec/架构和 Self-Runner 关联；旧源码仅记为现状，不再迁移。
- [x] 1.2 将用户批准的两个顶层部署目录、Workspace 同名约定、每种资源独立 Root/State、Workspace ID Remote State Output、Notebook/Pipeline 全归 `fabric-cicd` 和无 Apply-All 固化为 Proposal、Design、Delta Spec。
- [x] 1.3 更新长期架构、导航及历史 Change 的失效说明，明确文档目标与目前实际代码不同；本轮没有任何云端变更。
- [ ] 1.4 PR 完成 OpenSpec/Change Gate/Links CI 并合并 Main，登记真实 PR 及最终 Commit；此项只能有合并证据后勾选。

## 2. Build new workspace-scoped source (not started)

- [ ] 2.1 直接新建 `fabric-workspace/healthcare-omop/workspace/` Root，复用 `modules/workspace`；按非 default Terraform CLI Workspace 同名创建真实 Fabric Workspace，输出 ID、名称，做好变量、IAM、CI。
- [ ] 2.2 新建 `fabric-workspace/healthcare-omop/onelake/` 独立 Root，复用 `modules/onelake`；通过 `terraform_remote_state` 获取 Workspace ID；没有上游 ID 时明确失败。
- [ ] 2.3 按真实平台需要添加 `warehouse/` 等资源 Root；每个目录保存非秘密 `terraform.tfvars`、main/variables/outputs/providers/versions 和适用 IAM；资源 Root 独立 State，不重复管理。
- [ ] 2.4 新建 `shared-infra/` 下必要的 `storage/`、`connection/`、`foundation-iam/` 等 Roots；仅在获明确成本批准时考虑 Capacity 创建，默认使用已有 Capacity。
- [ ] 2.5 为新树增加静态单元/合同测试，验证目录命名、Root State Key 与 CLI Workspace 隔离、Remote State Output 依赖和 Notebook/Pipeline 禁止 Terraform 管理。

## 3. Switch workflows without migrating old source/state (not started)

- [ ] 3.1 修改 Self-Runner Azure/Fabric 工作流：从 `fabric-workspace/<name>/<type>/` 执行 `plan|apply`，校验 Workspace/资源目录输入，记录源码 SHA、独立 State Key、Plan 和 Outputs，不提供 Apply-All。
- [ ] 3.2 为 `shared-infra/<type>/` 配置适当的独立 Workflow；不把账户/租户级资源绑定 Fabric Workspace 名称。
- [ ] 3.3 停止新 Workflow 对旧 `components/`、`components/fabric-environment/`、旧 Notebook/Pipeline Root 的路由；旧 Git 源码、旧 State 保留且不迁移，后续如需删除旧源码另行审批。
- [ ] 3.4 为 `fabric-cicd` 明确 Notebook/Pipeline 的独占创建、更新、删除、发布接口及所需 Workspace/Lakehouse IDs，不再由 Terraform 同时管理相同 Items。

## 4. Live validation and return to data-platform work (not started)

- [ ] 4.1 以具备实际 Fabric/Backend/Capacity/Blob 权限的当前部署身份，真实验证 Backend 与 Terraform CLI Workspace 的 State 隔离；确认 Capacity 可用且不会新增未经授权的持续费用。
- [ ] 4.2 在用户可控的全新/已手工清理同名资源环境，逐项 `workspace`、`onelake`、按需 `warehouse` Plan/Apply，读回真实 Fabric IDs，重复 Plan 验证无漂移。
- [ ] 4.3 验证故意缺失 Workspace State Output 时下游 Plan 失败；单资源 Apply 不触碰其他 Root/State，也不修改旧 `dev/*.tfstate`。
- [ ] 4.4 通过 `fabric-cicd` 创建 Notebook/Pipeline，并完成 Azure Landing → OneLake 的真实业务 E2E；把结果与任务/Run 证据绑定。
