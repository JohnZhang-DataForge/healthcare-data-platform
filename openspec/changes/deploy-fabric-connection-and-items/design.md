# Design

## Baseline / authority

Healthcare Main `e49404ff7fde473d877c13fb37c8ce7ad33e2d4f`；Self-Runner Main `865a8f0eb7fbdcabceb190ac17f3915790ba0e2c`。权威基础设施 Change `organize-fabric-terraform-by-workspace` Task 3.4/4.4 尚未收尾；Trial E2E Change `validate-fabric-trial-free-infrastructure` 已有 Run #39635155333 Attempt 2 通过。旧 `simplify-fabric-environment-iac` 与 `implement-fabric-multi-environment-terraform` 被新架构取代，不能从旧 Roots 发布 Notebook/Pipeline。

## Ownership and dependency graph

1. Terraform `fabric-workspace/johnzhang-test/workspace`: **唯一 Workspace owner**；已通过 Trial F4 真实验收，Output: `fabric_workspace_id`。
2. Terraform `fabric-workspace/johnzhang-test/onelake`: **唯一 Lakehouse owner**；上游 Remote State 取得 Workspace ID，Output: `lakehouse_id`。
3. Terraform `shared-infra/connection`: Tenant/account 层 `fabric_connection` 独立 Owner，Backend `shared-infra/connection.tfstate`、default CLI Workspace，与其他 Root/State 完全分离；只复用 `modules/connection`。**默认 `connection=null` 不创建任何连接**。
4. `fabric-cicd`: 独占 Notebook 与 Pipeline Items；Git 的 `.Notebook/`、`.DataPipeline/` 与 `.platform` 稳定 logicalId 均由代码管理。不得与 Terraform 旧 `components/notebook` / `components/data-factory` 共同管理 Item。
5. Pipeline → Notebook → OneLake；Connection 可为 Blob Reader 使用，但 Fabric Item/Notebook runtime 对连接的具体绑定按支持的 Connector API 和运行测试核验，不把拥有 Workspace 权限当作 Blob Data Reader 权限。

## Connection gates (before Live)

- 校验 Fabric Tenant `supportedConnectionTypes` 中真实 `AzureBlobs/AzureBlobs` 的 mandatory `account`, `domain`、`WorkspaceIdentity` 或 `ServicePrincipal` 支持情况及 user-controlled-code 使用许可（既有验证仅针对历史 API 响应，不自动证明当前 Tenant）。
- Inventory：若已有同名 Connection 未由本 Root State 管理，则 HOLD，由用户决定显式 Import 或调整名称，绝不偷接管、删除。
- Reader 身份与 Deploy OIDC 身份分离；ServicePrincipal 只允许已有 Key Vault Connection secret reference，禁止在源码/JSON/日志提交原始密码；WorkspaceIdentity 需真实验证 workspace identity、Blob RBAC 和 Fabric 使用权限。
- 配置禁用状态静态测试应成立；Live `plan`/任何 `apply` 各有独立受控授权和 Terraform Plan 变更白名单，禁止 delete/replace。
- Connection Item 是租户级对象，不将它嵌入 `johnzhang-test` 具名 Terraform CLI Workspace。

## Fabric items / deployment

- 最小源码位置 `azure-fabric/workspaces/johnzhang-test/notebooks/` 与 `pipelines/`；使用官方 Fabric Git Source 结构，每个 Item 一个带 `.platform` 的 `*.Notebook` / `*.DataPipeline`，Notebook `notebook-content.py`、Pipeline `pipeline-content.json`。
- `fabric-cicd` 运行时从**实际 Terraform Outputs** 确认 `workspace_id` 与 `lakehouse_id`，不得通过复制旧 test GUID 配置伪造依赖。Notebook 首批不执行 Blob/Delta 业务写入。Pipeline 中引用已审核的 Notebook logicalId，跨 Workspace GUID 映射须通过真实发布/读回检查。
- Self-Runner 受控模式：`validate` (无 Azure/Fabric 写入) → `publish-smoke` (仅白名单/现有 Workspace、无孤儿删除) → `run-smoke` (用户批准、检查实际完成) → `publish-omop` (经后续 Change 授权)、`run-omop` (READY Manifest、真实 Delta/DQ 读回)。Workflow 固定 SHA 和 CLI 依赖版本；明确区分 Static、Publish、Runtime、E2E。
- 禁止触碰旧 Terraform Notebook/Pipeline Roots；禁止 `unpublish_all_orphan_items`、批量清除 Workspace、按仓库全量发布其它 Item。Orphan 清理若确需执行，必须独立 Change/授权。

## E2E contract / negative tests

- FIRST smoke：Notebook 不写数据；Pipeline 调用 Notebook，验证固定版本、参数传播、Workspace/Notebook ID 和 Run status；重复发布同一 Item 不产生重复。
- OMOP next：只读 PostgreSQL exporter 生成同一 export_id 的不可变 snapshot/READY manifest；Azure Blob → Notebook 严格校验 hash/count/schema/export_id，OneLake Delta 写入支持幂等重放；验证 person 和 visit_occurrence 双表 PK/FK 和 count，不允许越过 READY 或写回本地 PG。
- 负向测试：不存在上游 Outputs、连接类型或凭据不支持、跨租户/无 Reader RBAC、同名已有对象未经接管、Pipeline Notebook logicalId 不匹配、错误批次 Manifest、Scope 外 Item、试图创建付费 Capacity/删除其它 Item，均 fail closed。
- Rollback：源代码 PR 回退；Terraform Root 受 `prevent_destroy` 保护，连接失败先审查 State 与云端实际对象；已发布的 Fabric Item 通过版本化定义前滚/回退，绝不执行全量清除。

## Stage 1 (this change's first PR)

仅增加独立 Connection Root、默认禁用的非秘密配置、离线单测和现有 CI 的 `init -backend=false` / `validate` 检查；文档/源码导航同步。没有云端操作，也不创建 Notebook/Pipeline Item。下一 PR 再实现 `fabric-cicd` 受控发布与原生 Item。
