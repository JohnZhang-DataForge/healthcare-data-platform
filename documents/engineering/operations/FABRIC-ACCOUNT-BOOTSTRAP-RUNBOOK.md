---
status: active
scope: fabric-environment-manual-bootstrap-checklist
last_reviewed: 2026-10-19
implementation_status: offline-roots-and-validation-only
---

# Fabric 新账号 / 新环境人工前置 Runbook

> **范围**：本 Runbook 是每次接入新 Fabric 账号/Capacity/Entra Tenant 前，必须由有对应权限的人手工准备或审查的事项。**当前已完成独立 Workspace、Lakehouse、Connection 资源声明与离线 Preflight/CI，但**从未对新环境进行 Terraform Init/Plan/Apply**，仍不是可运行的一键部署流程。** 后续 Terraform Provider/Backend 双身份、Connection、fabric-cicd、Self-Runner Workflow 仍需独立开发、授权与 E2E。长期目标见 [Fabric 多环境架构](../../architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)；原有 [Terraform 安全边界](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md) 仍有效。

## 0. 稳定资产 vs 新账号范围

| 资产/任务 | 首次准备 | 每次更换 Fabric 账号 | 谁负责 |
| --- | --- | --- | --- |
| 保证现有 Azure 订阅和 `johnzhang` Storage 有效 | 核实 | 核实未失效 | Azure 旧 Tenant A 管理员 |
| `johnzhang/landing` 与本地 Blob Publisher | 已有资产，只做权限审查 | 不重新创建/配置 | Local DP + Storage Owner |
| `johnzhang/tfstate`、旧 `dev/*.tfstate` | 核实并保护、备份/审计 | 原位保留，**不迁移、不覆盖** | Terraform Backend Owner |
| Backend Operator 的 Tenant A 身份/OIDC | 一次性配置/核对 | 通常不变；有到期/撤销时更新 | Azure Owner |
| Blob Reader 的 Tenant A 身份（只读 `landing`） | 一次性授予/核对 | 通常不变；每新环境验证连接 | Azure Owner |
| Fabric 有效账号、Capacity、必要许可 | 必须可用 | **每次** | Fabric Tenant B Owner |
| Fabric 部署用 Service Principal、租户 API 设置、Capacity 角色 | 首次建 Tenant B 必须 | 换 Tenant 时**每次** | Fabric Tenant B 管理员 |
| GitHub Environment 中新部署身份的 OIDC/Secrets/Vars | 首次准备 | **每新 Tenant 更新** | Repo 管理员 |
| 新环境独立的 State Prefix/Workspace 名 | 首次选择 | **每新环境生成** | 部署流程 |
| Blob Connection、Workspace、Lakehouse、Notebook/Pipeline | Terraform Root 已声明前三种但尚未部署；Notebook/Pipeline 未实现 | **最终由 Workflow 自动创建，不手工逐项配置** | Terraform + fabric-cicd |

**Fabric Trial 不保证可重复获得**。本架构适用于任何已经合法准备好且有容量的 Fabric 环境，不能自动申请新的 60 天试用。

## 1. 每次新账号的人工必备检查

### A. 确认新账号是否只是新 Capacity，还是新 Entra Tenant

1. 记录 Fabric Tenant ID（Tenant B）、目标 Capacity ID、所在区域与合法使用期限；不要把 Capacity GUID 与 Fabric Workspace GUID 混淆。
2. 如仍属于 Tenant A，允许沿用符合权限要求的部署身份，但使用**新的独立 State Key 和新 Workspace 名**；不共享旧 Fabric 环境 State。
3. 如属于另一个 Tenant B，配置新 Tenant 的部署身份；旧 Azure Backend/Blob Reader 仍归属 Tenant A，不简单把所有 `AZURE_TENANT_ID` 整体替换成 B。
4. 检查 Capacity 角色是否允许部署 Service Principal 创建并分配 Workspace；微软官方 Terraform + fabric-cicd 教程要求适当 Capacity Contributor/Admin 权限。

**手工必要**：Fabric Portal / Tenant 管理员确认 Capacity 正常与目标身份可用；Terraform 无法保证创建一个符合试用资格的 Capacity。

### B. Tenant B 创建或授权部署身份

1. 在新 Tenant 的 **Microsoft Entra 管理中心 → App registrations** 准备部署用应用/Service Principal；记录 **Tenant ID、Application (Client) ID、Service Principal Object ID**，三者不可混用。
2. 由 Fabric Tenant 管理员在 Fabric Portal 的 **Govern → Configurations → Tenant settings → Developer settings** 检查 **Service principals can use Fabric APIs** 是否对部署 SPN 所在的安全组开放（具体 UI 字样可能变化）。
3. 在目标 Capacity 上为部署身份分配允许新建 Workspace 的角色，并确保部署后 Workspace 管理权限能由 Terraform 安全授予；如果策略禁止则 HOLD，不尝试提升到全租户管理员绕过限制。
4. 由 Repo/Entra 管理员为 Self-Runner 的**确切 GitHub Repo/Ref 或 GitHub Environment** 配置对应的 OIDC federated credential。GitHub OIDC token 的 issuer/subject/audience 必须和 Tenant B 的信任记录精确匹配；现有 Tenant A 的 OIDC 不会自动在 B 生效。
5. Fabric **部署身份**优先使用 GitHub OIDC；若未来另行批准使用部署 Client Secret，必须将其隔离存入受保护的 GitHub Environment Secrets 并定义轮换周期。**Blob Reader 凭据不交给 GitHub Runner**：当前 Connection Root 只接受指向**现存 Fabric Key Vault Connection**的 Secret Reference（ID、名称、可选版本），不是 Secret 值。绝不放入 .tfvars、仓库 JSON、日志或 PR。

**未实现部分**：当前 Self-Runner `azure-infra.yaml` 将 `ARM_*` 与 `FABRIC_*` 指向同一套 GitHub 变量，只支持 `dev`；更换 Tenant 前必须由后续 Change 把两个认证流真正分离。此 Runbook 不授予直接运行旧 Workflow 针对新环境的权限。

### C. Tenant A 的 Backend 和业务 Landing

1. 核实 `johnzhang/tfstate` 的实际 Blob 数据、State Key、权限、锁与备份；当前历史七个 Root 的 `dev/<component>.tfstate` 必须原位保护。
2. 确认 Backend Operator 可使用自己的 Tenant A 身份读取/锁定/写入 **指定新** `fabric/<environment>/<component>.tfstate`（将来 Workflow 实现）；不得允许新环境初始化覆盖已有 `dev` State。
3. 核实本地 Blob Publisher 原有权限仍能发布 `johnzhang/landing`，**不要因为换 Fabric 账号而重新生成本地 Publisher Token**。
4. 由 Azure Owner 准备或核实位于 Tenant A 的专用 Blob Reader Service Principal，对 `landing` 给予 **Storage Blob Data Reader**，不要默认开放整个账号的 Account Key；跨 Tenant 访问通过新的 Fabric Connection 使用明确的 Reader Tenant ID。
5. 检查 Azure Storage 网络 ACL、Private Endpoint/DNS、Fabric 支持的网络访问方式。Tenant B 的 API/RBAC 成功**不意味着**可从 Fabric 访问 Tenant A Blob；后续需 Copy Activity 实际读回。若 SPN 连接被限制，先记录原因，再单独审批只读 SAS 方案。

### D. GitHub 环境和信息分层

- GitHub Repository 保存**非秘密**的部署配置、Terraform 源、Fabric 原生 Item 定义、Preflight 代码/测试。
- GitHub Environment 只保存受保护的部署身份配置和 OIDC 所需非敏感标识；不要把 Blob Reader Secret 放进 Runner、GitHub Secrets、TF_VAR 或 Terraform State。Reader Secret 留在被授权的 Azure Key Vault，并由已存在且经过独立验证的 Fabric Key Vault Connection 引用。
- 非敏感的新 Tenant ID、Capacity ID、Workspace 名、State Prefix/环境名可放在隔离的环境配置中；**若部署输出/CI 公开可见，仍避免打印不必要的标识**。
- 保留 `Plan → 人工批准 Apply → fabric-cicd Deploy → E2E Readback` 的审批边界。当前无一键 Workflow，不得将这里的预检步骤解释成资源已创建。只有纯 `terraform fmt` 静态 CI 已启用；此操作不初始化 Backend、不下载 Provider、不会向云端认证。

## 2. 当前已经可以使用的离线检查（不会访问 Azure）

示例源文件：

`azure-fabric/infra-terraform/environments/fabric-environment.example.json`

该文件中的 Tenant/Capacity ID 故意是 `REPLACE_...` 占位符，**直接运行应 FAIL**，以防止意外拿示例发布。

将其复制到个人或受保护环境下的 `fabric-environment.json`，只替换非敏感字段；文件不要包含 Secret。字段示例：

```json
{
  "schema_version": 1,
  "environment": "lab-b",
  "backend": {
    "storage_account": "johnzhang",
    "container": "tfstate",
    "tenant_id": "TENANT_A_UUID",
    "state_prefix": "fabric/lab-b"
  },
  "landing": {
    "storage_account": "johnzhang",
    "container": "landing"
  },
  "fabric": {
    "tenant_id": "TENANT_B_UUID",
    "capacity_id": "CAPACITY_B_UUID",
    "workspace_name": "HDP-lab-b"
  }
}
```

以上 `TENANT_A_UUID` 等字符串**也是说明性占位符**。以下命令为纯离线验证，执行环境需要 Python 3.9+：

```bash
python3 azure-fabric/infra-terraform/tools/fabric_environment_preflight.py \
  --config /path/to/fabric-environment.json
```

成功预期输出包括 `STATIC_PREFLIGHT_PASS`，以及 **`fabric/lab-b/workspace.tfstate`、`fabric/lab-b/onelake.tfstate`、`fabric/lab-b/connection.tfstate`** 的目标 Key；`external_access_verified=false`、`terraform_executed=false`。任何无效 GUID、旧 `dev` Key、混入 Token、旧 Workspace 命名会拒绝。**这只是参数合同，不会判断真实环境里有没有同名 Workspace。**

离线单测：

```bash
python3 -m unittest discover \
  -s azure-fabric/infra-terraform/tests \
  -p 'test_fabric_environment_preflight.py' -v
```


## 2A. Task 2.4/2.5：Connection 凭据与上线前最小证据清单（目前 HOLD）

新环境 `connection/main.tf` 已有 `fabric_connection.azure_blob` 声明，但下列项目必须独立取得证据后才能考虑**单独申请** Terraform Init/Plan 权限。**所有审批变量默认 false；单纯设置 true 不是证据。**

| 关卡 | 需要检查的内容 | 应当保留的非秘密证据 / 停止条件 |
| --- | --- | --- |
| Fabric Tenant | 目标 Entra Tenant ID、Capacity ID、Fabric CLI/API 会话 Tenant 一致；当前同 Tenant A→A′，未来允许 A→B | 记录 Tenant GUID 和日期；任何会话不匹配立即 HOLD |
| Backend Operator | 单独的应用 Client ID、Tenant A OIDC federated credential，仅对批准的 State 容器有适当权限 | 明确区别旧 `dev/*.tfstate`；新 State Key 必须经过独立库存检查；**Blob Prefix 不构成 RBAC 隔离** |
| Fabric Deployer | 独立应用 Client ID、Fabric Tenant OIDC/API/Capacity 权限，不能等于 Backend Operator | 实际令牌颁发、Fabric API 权限未验证前 HOLD；不能借用 Azure CLI 的用户账号冒充应用身份 |
| Blob Reader (ServicePrincipal) | 第三个应用 Client ID，Tenant A，`landing` 容器 **Storage Blob Data Reader**，无 Blob Data Contributor | Client ID 必须与 Backend/Fabric 不同；核对访问范围、网络 ACL、跨 Tenant B→A 读取方式 |
| Key Vault Secret Reference | 目标租户内**已存在**的 Fabric Key Vault Connection GUID、被授权的 Key Vault Secret 名称/版本和凭据轮换责任人 | 不提交 Secret 值、Access Key、SAS、Bearer Token；若引用不存在或无法读取则 HOLD |
| WorkspaceIdentity（可选） | 目标 Workspace 的真实 Workspace Identity、必要 Blob Reader RBAC、Fabric Provider 对该组合的实际支持情况 | 元数据支持类型不等于网络/RBAC/跨 Tenant 可用；未验证继续保持审批为 false |
| AzureBlobs 元数据 | 目标 Tenant 正式 `supportedConnectionTypes` 返回类型 `AzureBlobs` / 方法 `AzureBlobs`，必填 `account`、`domain`；核对 `domain` 的实际值 | 必须从目标 Tenant/连接 UI 验证实际值；不可猜 `blob.core.windows.net` 一定是所需 `domain` 参数 |
| Connection 资源所有权 | 列出新环境预期同名 `HDP-<environment>-azureblobs` 连接及权限；核对是否已有 Connection、后端 State 是否已有对象 | 不在未经批准条件下创建重复连接或导入；遇到未知资源继续 HOLD |
| GitHub CI | GitHub-hosted Fabric Preflight 离线 Python tests + `terraform fmt -check` | 无 `id-token:write`，无 Azure/Fabric Secret、无 `terraform init/plan/apply/destroy`；PASS 不等于真实 Provider Schema 验证 |
| 后续部署授权 | 精确 Change、PR/SHA、Environment、State Key、只读库存结果、预计资源清单以及回退策略 | 未来单独审批 `init/plan`，计划评估后再次独立审批 `apply`；绝不自动降级绕过检查 |

**用户现在无需执行 Azure 命令。** 等需要核实实际 Fabric Tenant/Capacity、Connection 现存库存、Reader/RBAC 或 Key Vault 引用时，再按最小权限提供明确的只读操作。核验时不要回传 JWT、Secret、SAS、Storage Key 或包含凭据的导出。

### 不涉及云端的验收命令（仅在本地检出仓库时）

```bash
python3 -m unittest discover -s azure-fabric/infra-terraform/tests -v
# 仅格式及 HCL 解析：不需要 init、不读取 State、不安装 Provider。
terraform fmt -check -diff azure-fabric/infra-terraform/new-environments/connection
```

如果无法在本地安装 Terraform CLI，可直接使用 PR 的 **Fabric Environment Preflight (Offline)** 检查结果。该格式检查仅覆盖本批 Connection Root；旧 Workspace/OneLake Roots 未因此获得 live validation。

## 3. 旧手工 Workspace：不能因为“空”就直接删除

用户已确认**不需要旧 Workspace 作为新 Fabric 架构的业务依赖**；**这不是对其云端资源或 Terraform State 的删除授权**。

新环境建议起独立名称 `HDP-<environment>`，并使用新的 `fabric/<environment>/...` State：

1. 后续正式运行前先只读列出旧 Workspace GUID、Tenant、Capacity、所有 Items/数据、Workspace/Container 授权、现有 Terraform State 是否包含其地址及其他 Agent 是否引用。
2. 若旧 Workspace 已在 State 中，严禁直接删 State、换 Tenant 或让新环境的 Terraform 规划去替换旧 Workspace；先独立审查 Import/Adopt/Detach/Destroy 方案。
3. 若经核实完全无依赖，**可以继续留着**，或另行获得具体删除授权后在受控窗口清理。Fabric 删除 Workspace/Items 有保留期和潜在不可逆后果，不能仅靠 “看起来没内容” 判断安全。
4. 新账号第一次创建的 Workspace 通过自动化建立，后续同环境只做 Plan/Update；不能每次重跑都新建一个同名 Workspace。

## 4. 自动化实现之后的人工作业清单（目标，不是现状）

```text
Fabric Tenant B Owner: 预备账号/容量/权限
           ↓
Azure Owner: 核实稳定 Blob、Backend 与 Reader
           ↓
Repo Admin: 配置新环境 OIDC/Secrets 和环境 Profile
           ↓
Self-Runner: offline preflight / cross-tenant access checks
           ↓
Terraform: isolated backend init / plan
           ↓
Owner: review expected changes and explicitly authorize apply
           ↓
Self-Runner: approved apply / workspace / lakehouse / connection
           ↓
fabric-cicd: publish Notebook + DataPipeline only
           ↓
Self-Runner: Blob READY → Bronze → Silver E2E readback
           ↓
Evidence: actual SHA / state prefix / environment / batch / Run
```

**停止条件**：Capacity/API 无权限、Service Principal 认证失败、同名旧 Workspace 未处理、旧 State Key 被复用、Plan 出现 Delete/Replace、Blob 跨租户连接失败、Secret 出现在输出日志，均为 HOLD；不得继续自动重试或降级安全限制。

## 5. 参考与权威

- [批准的目标设计](../../architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)
- [Azure/Fabric 实现事实](../../systems/azure-fabric/README.md) 与 [Terraform IAM/State](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md)
- [Shared Runtime Safe Operations](SAFE-OPERATIONS.md)、[OpenSpec 生命周期](../development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md)
- [Microsoft Learn — Terraform + fabric-cicd end-to-end tutorial](https://learn.microsoft.com/en-us/fabric/cicd/tutorial-end-to-end-automation)
- [Microsoft Learn — Azure Blob connector authentication](https://learn.microsoft.com/en-us/fabric/data-factory/connector-azure-blob-storage-overview)
- [Microsoft Learn — Fabric Workspace retention and recovery](https://learn.microsoft.com/en-us/fabric/admin/portal-workspaces)
