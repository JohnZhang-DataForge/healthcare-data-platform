# Tasks

> **本 Change 是当前有效的 Fabric Terraform 架构和实施任务入口。** 取代旧组合 Root/Apply-All 方案。源码与独立静态 CI 按 Tasks 分批推进；云端运行取证必须另行记录，不将 Git 合并误作云资源已部署。

## 1. Freeze architecture and change governance

- [x] 1.1 核对最新 Main 的 `components/`、`modules/`、`fabric-environment/`、旧 OpenSpec/架构和 Self-Runner 关联；旧源码仅记为现状，不再迁移。
- [x] 1.2 将用户批准的两个顶层部署目录、Workspace 同名约定、每种资源独立 Root/State、Workspace ID Remote State Output、Notebook/Pipeline 全归 `fabric-cicd` 和无 Apply-All 固化为 Proposal、Design、Delta Spec。
- [x] 1.3 更新长期架构、导航及历史 Change 的失效说明，明确文档目标与目前实际代码不同；本轮没有任何云端变更。
- [x] 1.4 文档 [PR #347](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/347) 的 OpenSpec Strict Validation / OpenSpec Change Gate / Trusted Gate / Documentation Links / Code Paths **5/5 PASS**，已合并 Main `4706c1996e8f84e83bb5786f42e9804ceb5d67ac`；合并后核对仅涉及 `documents/` 和 `openspec/` 13 个文件。未执行 Terraform/Workflow/State/云端操作。

## 2. Build new workspace-scoped source (not started)

- [x] 2.1 直接新建 `fabric-workspace/healthcare-omop/workspace/` Root，复用 `modules/workspace`；按非 default Terraform CLI Workspace 同名创建真实 Fabric Workspace，输出 ID、名称，做好变量、IAM、CI。
> Task 2.1 源码/静态阶段：[`PR #349`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/349) 新增 Workspace Root、6 项合同单测、CODE.md 及独立 Terraform CI。[`Run 39536623425`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39536623425) 的 `terraform validate / healthcare-omop / workspace` 成功：`fmt`、`init -backend=false`、具名 CLI Workspace `validate`、default 负向保护、6/6 单测 PASS。仅代表源码/静态 CI 完成；远端 Backend/State、真实 Plan/Apply/Fabric Workspace ID 仍由 Tasks 3/4 实测，未执行云端操作。

- [x] 2.2 新建 `fabric-workspace/healthcare-omop/onelake/` 独立 Root，复用 `modules/onelake`；通过 `terraform_remote_state` 获取 Workspace ID；没有上游 ID 时明确失败。
> Task 2.2 源码/静态阶段：[`PR #350`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/350) 新增独立 OneLake Root、`terraform_remote_state` 依赖、5 项静态合同测试及 CI。[`Run 39536947645`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39536947645) 的 `terraform validate / healthcare-omop / onelake` PASS（包含具名 CLI Workspace、default 负向测试、5/5 单测），不读取真实远端 State，不 Plan/Apply。上游缺失时的真实 Plan 失败测试仍属于 Task 4.3。

- [ ] 2.3 按真实平台需要添加 `warehouse/` 等资源 Root；每个目录保存非秘密 `terraform.tfvars`、main/variables/outputs/providers/versions 和适用 IAM；资源 Root 独立 State，不重复管理。
- [x] 2.4 新建 `shared-infra/` 下必要的 `storage/`、`connection/`、`foundation-iam/` 等 Roots；仅在获明确成本批准时考虑 Capacity 创建，默认使用已有 Capacity。
- [x] 2.5 为新树增加静态单元/合同测试，验证目录命名、Root State Key 与 CLI Workspace 隔离、Remote State Output 依赖和 Notebook/Pipeline 禁止 Terraform 管理。

任务 2.4/2.5 的最小必要范围：仅 Shared Storage lookup Root（其它 Shared 资源不构成本次前置）与静态跨 Root 合同；[PR #352](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/352) 负责源码与独立 CI，不代表真实 Azure 读回、State 隔离实测或 Fabric 部署完成。

## 3. Switch workflows without migrating old source/state (partially complete)

- [x] 3.1 修改 Self-Runner Azure/Fabric 工作流：从 `fabric-workspace/<name>/<type>/` 执行 `plan|apply`，校验 Workspace/资源目录输入，记录源码 SHA、独立 State Key、Plan 和 Outputs，不提供 Apply-All。
- [x] 3.2 为 `shared-infra/<type>/` 配置适当的独立 Workflow；不把账户/租户级资源绑定 Fabric Workspace 名称。
- [x] 3.3 停止新 Workflow 对旧 `components/`、`components/fabric-environment/`、旧 Notebook/Pipeline Root 的路由；旧 Git 源码、旧 State 保留且不迁移，后续如需删除旧源码另行审批。
> Tasks 3.1–3.3 源码及运行证据：Self-Runner [PR #177](https://github.com/JohnZhang-DataForge/Self-Runner/pull/177) 合并 Main `b9a343a12ae2c50a53e2f0e4a52ba99a75970aca`，静态 [Run #39538140248](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39538140248) PASS，正式 Workflow 不再路由 `components/` 或旧 Notebook/Pipeline；Shared Infra 独立 Workflow。Plan-only [PR #178](https://github.com/JohnZhang-DataForge/Self-Runner/pull/178) 触发的真实 Storage [Run #39538288616](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39538288616) SUCCESS：OIDC、AzureRM Backend、现有 OMOP Resource Group / johnzhang Storage 读回、Plan PASS；Apply/Destroy 未执行。Workspace [PR #179](https://github.com/JohnZhang-DataForge/Self-Runner/pull/179) 的 [Run #39538646279](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39538646279) 在 Runner 缺少 `FABRIC_CAPACITY_ID` 时预检 FAIL（退出码 4），没有运行 Terraform init/Plan，也没有修改 Workspace State 或云端资源。

- [ ] 3.4 为 `fabric-cicd` 明确 Notebook/Pipeline 的独占创建、更新、删除、发布接口及所需 Workspace/Lakehouse IDs，不再由 Terraform 同时管理相同 Items。

## 4. Live validation and return to data-platform work (partial; no Fabric Apply)

> Task 4.1 保持未完成：Shared Storage 的 default State/Backend 已经真实可用，但具名 `healthcare-omop` CLI Workspace 的 State 隔离、实际 Capacity GUID 和 Fabric Plan 尚未通过真实验证；先补齐 Runner `FABRIC_CAPACITY_ID` 才能进行下一次受控 Plan。不要推断现有 Workspace/Capacity GUID，更不能把 Plan 当成 Apply。

- [ ] 4.1 以具备实际 Fabric/Backend/Capacity/Blob 权限的当前部署身份，真实验证 Backend 与 Terraform CLI Workspace 的 State 隔离；确认 Capacity 可用且不会新增未经授权的持续费用。
- [ ] 4.2 在用户可控的全新/已手工清理同名资源环境，逐项 `workspace`、`onelake`、按需 `warehouse` Plan/Apply，读回真实 Fabric IDs，重复 Plan 验证无漂移。
- [ ] 4.3 验证故意缺失 Workspace State Output 时下游 Plan 失败；单资源 Apply 不触碰其他 Root/State，也不修改旧 `dev/*.tfstate`。
- [ ] 4.4 通过 `fabric-cicd` 创建 Notebook/Pipeline，并完成 Azure Landing → OneLake 的真实业务 E2E；把结果与任务/Run 证据绑定。
