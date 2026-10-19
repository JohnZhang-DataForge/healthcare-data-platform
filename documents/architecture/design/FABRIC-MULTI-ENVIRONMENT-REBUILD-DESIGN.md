---
status: approved-target-design
scope: fabric-multi-environment-rebuild-mvp
last_reviewed: 2026-10-19
implementation_status: not-started
---

# Healthcare V2 — Microsoft Fabric 多环境可重建部署设计

> **APPROVED TARGET DESIGN / NOT IMPLEMENTED**：已确认采用 **Terraform + GitHub Actions（Self-Runner）+ fabric-cicd**；不要求 Fabric Workspace 原生连接 GitHub。本文件规定未来可交付目标、设计取舍与安全边界，**不是实际 Terraform Apply、Fabric 部署或云端 E2E 验收**。具体开发进度只能记录在未来相应 [OpenSpec Changes](../../../openspec/changes/) 与 PR/Run 中；[PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md) 是跨项目唯一状态入口。

## 1. 目标、非目标与约束

### 1.1 目标

1. 长期保留本地 Kubernetes、PostgreSQL OMOP、Synthea/OIE 和 **已有 Azure Storage Account `johnzhang`**；三个模拟来源的只读/原始数据经本地发布者进入现有 Blob `landing`。本地发布者**不感知 Fabric Tenant、Workspace、Capacity、Notebook 或 Pipeline ID**。
2. 继续在相同 Storage Account 的 **`tfstate` Container** 保存 Terraform Backend，但将**每个新的 Fabric 部署环境隔离成独立 State Key**。绝不因为环境切换将旧 `dev/*.tfstate` 改名、清空或挪用。
3. 使用同一份 GitHub Terraform/Notebook/Pipeline 源码，经可控的环境配置支持**不同 Fabric Workspace / Capacity，必要时不同 Entra Tenant**。
4. 给定已准备妥当的有效 Fabric 环境、身份与网络权限，经受控 Self-Runner 一次部署流程（含 Plan/明确授权的 Apply/部署/读回），重建 Workspace、Lakehouse、Blob Connection、真实 Notebooks 与 Pipelines，再从 Blob READY Batch 重新装载并验证。
5. **MVP First**：已有代码/Workflow 优先复用；不新建独立 CI 系统，不为了可迁移性重构本地 OMOP Writer、引入 Kafka 或强制部署 Warehouse。

### 1.2 明确不保证的事情

- 不保证新账号能重复领取 Fabric 60 天试用；不自动开新 Tenant、申请 Trial/购买 Capacity、授权管理员策略或跨租户权限。
- 不把 Fabric Workspace、Fabric Lakehouse 的元数据和 OneLake 内的历史分析数据当作永久存储；**新环境的 Bronze/Silver/Gold 需要从源 Blob 重新生成**。
- 不把 Fabric 原生 GitHub Integration 作为成功依赖；不要求自动把 Fabric Workspace 连接 GitHub。
- 不因 Terraform Provider 存在资源而推断当前 Tenant、Trial、SPN、API 或跨租户连接已通过实测。
- 不承诺“执行一次没有审批的 Apply”；共享云资源写入需要已有安全门槛及用户授权。

## 2. 固定层、替换层与控制平面

```text
   Local Kubernetes (stable)           GitHub: healthcare-data-platform
   ┌───────────────────────┐                       │
   │ PG OMOP / FHIR / HL7  │                       ▼
   │ Producer + Publisher  │                  Self-Runner
   └───────────┬───────────┘                       │
               │                          Plan / approved Apply
               ▼                                  │
      Azure Storage: johnzhang                    ├─ Terraform: Control Plane
       (subscription must remain valid)           │  Workspace / IAM / Lakehouse
        ┌─────────┴──────────┐                    │  Blob Connection
        │                    │                    │
     landing              tfstate                 └─ fabric-cicd: Business Items
     OMOP/FHIR/HL7        (same backend)             Notebook / DataPipeline
        │                    │                            │
        │     ┌──────────────┴──────────────┐             │
        │     │                             │             │
        │  fabric-lab-a/*              fabric-lab-b/*     │
        │     states                        states         │
        │                                                   
        ├──────────────► Fabric A Workspace / Lakehouse ◄──┤
        └──────────────► Fabric B Workspace / Lakehouse ◄──┘
                                   │
                    Pipeline Copy → Bronze Files
                                   │
                       PySpark → Silver / small Gold
```

**存储与计算生命周期分离**：`johnzhang/landing` 是稳定可重放的源数据 Landing，`johnzhang/tfstate` 是稳定 Backend 的容器；Fabric 环境独立部署、独立计算、独立 State。新旧 Fabric 在有合法权限时可读取相同原始 Blob。Terraform 的**远程 State Key**、Terraform CLI Workspace 与 **Fabric Workspace** 是三个不同概念；本设计采用显式 State Key，而非仅靠 `terraform workspace new`。

## 3. 权限与跨 Tenant 身份模型

| 主体 | 所属位置 / 身份 | 最小职责 | 生命周期 |
| --- | --- | --- | --- |
| Local Blob Publisher | 本地 K8s 的专用身份 | 在 `landing` 写入不可变 Batch/READY；建议按需授予 Storage Blob Data Contributor | **稳定**，不随 Fabric 更换 |
| State Backend Operator | Blob 所属 Entra Tenant A 的独立执行身份 | 以 RBAC/OIDC 访问 `johnzhang/tfstate` 的独立 Key；不默认取得 `landing` 管理权限 | **稳定**；运行身份必须持续可用 |
| Blob Data Reader | Blob 所属 Tenant A 的专用 Reader 身份 | 只读 `landing`，用于每个 Fabric 新环境的连接 | **稳定**，可由多环境复用 |
| Fabric Deployer | 当前 Fabric 目标 Tenant B 的部署身份 | Provision Workspace/IAM/Connection、发布 Git Item、运行受控读取验证 | **按 Fabric 环境替换** |
| Fabric Workspace users/groups | 目标 Tenant B 的主体 Object ID | Workspace Admin/Contributor/Viewer，按新 Tenant 重算映射 | **环境相关** |

- **严格隔离身份**：当前 Self-Runner 的 `ARM_*` 与 `FABRIC_*` 实际指向同一 `AZURE_CLIENT_ID/AZURE_TENANT_ID`；未来必须允许 Backend 身份为 Tenant A，而 Fabric Provider / `fabric-cicd` 为 Tenant B。GitHub OIDC 信任和权限需分别预配；Runner 上能取得 Azure Token **不代表**自动可以访问另一个 Fabric Tenant。
- **首选连接**：Fabric Data Factory 对 Azure Blob 的 **Service Principal** 连接，Tenant ID 明确指向 Blob Reader 的 **Tenant A**；在 **Tenant B** 中创建 `fabric_connection` 或相应支持的配置并做实际读回。如果目标租户/连接器的跨租户条件不满足，记录 Blocker，可评估受限只读 SAS 的备用路径，不能默默回退到 Storage Account Key。
- **权限边界**：Fabric Workspace 成员权限不等于 Blob 数据权限；Backend 状态读写权限也不等于业务 Landing 权限。RBAC 最小授予 Container 或可行的更窄 Scope。管理 Role Assignment 需要 Azure 相应授权；仅 RG Contributor 不保证足够。
- **Secrets / State**：Service Principal Secret、SAS、GitHub Token 只从受保护 Secret Store 或 GitHub Environment Secrets 注入；配置与 PR/Run 不显示真实值。Terraform 的 `sensitive` 标注**不能保证 State 不保存敏感值**，应优先使用 Provider 支持且已核验的 write-only 属性，保护 `tfstate`、Plan 输出和日志；确需 Secret 落 State 必须单独审核。
- **网络与可用性**：Storage firewall、Private Endpoint、DNS、Fabric 支持的 Gateway/Network 路径、跨租户策略都是真实连接前置检查；RBAC 正确不自动代表网络可达。

## 4. 资源与交付唯一所有权

| 对象 | 目标交付者 | 说明 |
| --- | --- | --- |
| Azure Storage `johnzhang`、`landing`、`tfstate` | 既有 Azure 稳定资源；必要 IAM 受控管理 | 不为新 Fabric 环境重新创建/导入/销毁；保留现有 Backend 与业务文件 |
| Workspace、Capacity 绑定与 Workspace RBAC | **Terraform** | Capacity **已存在且有效**；新环境可创建 Workspace；旧手工建 Workspace 必须先核对并按需 Import |
| Lakehouse（MVP） | **Terraform**（保留既有 `onelake` Root） | `fabric-cicd` 的 `item_type_in_scope` 明确排除 `Lakehouse`，避免重复管理同一对象 |
| Azure Blob Fabric Connection | **Terraform**（实施前验证 Provider Schema） | 用 Reader 身份，Connection/GUID 以部署结果回填到环境参数；不在业务 Notebook 硬编码 |
| Fabric PySpark Notebook | **fabric-cicd**（GitHub 为源码唯一事实源） | Git 原生 Fabric Item 目录/元数据由真实 Fabric Source Control 输出或验证后的兼容定义保存，首次项目不得凭空仿造 `.platform` |
| Fabric Data Pipeline | **fabric-cicd**（GitHub 为源码唯一事实源） | Copy `landing` READY → OneLake Bronze Files → Notebook Silver；依赖与 Connection/Lakehouse GUID 环境化替换 |
| Pipeline 触发与跨系统读回 | **Self-Runner**（Fabric API/受控执行） | 只在部署检查过关后触发，不在 Terraform `apply` 时偷偷执行业务加载 |
| Warehouse / GitHub Workspace 原生集成 | Future Optional | 不是 MVP 交付门槛，不引入第二套同对象管理器 |

**关键技术决定**：`fabric-cicd` 直接从 Runner checkout 的 GitHub 工作树读取 Fabric Item Definition；**不需要先把 Fabric Workspace 连到 GitHub**。Provider 的 `fabric_workspace_git` / Github Connection 不是本次 MVP 的依赖：微软官方 2026-07 端到端教程明确说明，其 Service Principal 非交互式 Git 连接示例支持 Azure DevOps 而**不支持 GitHub**。因此直接发布是主路径，原生 Git Integration 只是以后可选且需另外验证的能力。

**删除风险**：`fabric-cicd` 支持 orphan item unpublish。MVP Deployment **只执行允许类型的 publish，不自动调用 `unpublish_all_orphan_items`**，尤其不能删除 Terraform 所有的 Lakehouse、旧环境的历史对象或人工资源；任何清理由独立审批 Change 处理。

**既有 Bootstrap 冲突**：目前 Terraform `notebook` Root 管理仅会抛 `RuntimeError` 的占位 Item，`data-factory` Root 在未填真实 Notebook GUID 时使用 Fail Activity。切换到 `fabric-cicd` 前必须有一份显式的 **existing-item inventory / ownership transition**，说明保留、停止运行或经审查迁移历史 State 的边界；**绝不对已有 State 直接删除资源条目来“解决冲突”**。新环境不应用旧 Bootstrap 创建同名业务 Item。

## 5. 环境配置与 Terraform State 模型

### 5.1 稳定 Backend，环境隔离 State

```text
Azure Storage: johnzhang / tfstate
├── dev/workspace.tfstate                    # legacy: 不动、不自动迁移
├── dev/onelake.tfstate                     # legacy: 不动、不自动迁移
├── dev/notebook.tfstate                    # legacy: 不动、不自动迁移
├── dev/data-factory.tfstate                # legacy: 不动、不自动迁移
└── fabric/
    ├── lab-a/
    │   ├── workspace.tfstate
    │   ├── onelake.tfstate
    │   └── connection.tfstate
    └── lab-b/
        ├── workspace.tfstate
        ├── onelake.tfstate
        └── connection.tfstate
```

上方是 **State Key 目标示例**，不代表 Backend 中已经存在这些对象；原有 7 个 Root `dev/<component>.tfstate` 均予保护。Fabric 之外的 `storage` / `foundation-iam` Root 仍需明确长期资源所有者，**不为每个新的 Fabric 账号盲目重复 Apply**。分 Root 既有布局可以保留，若新增 `connection` Root 则另开功能 Change 审核。

**Backend `terraform init` 使用 Tenant A 的身份**，Fabric Provider Terraform 操作使用 Tenant B 的身份。两种认证在受支持 Provider/Backend 版本下如何配置、GitHub OIDC 在新租户如何建立联合信任，必须先做隔离只读测试；不能认为把现有 `AZURE_TENANT_ID` 换成 B 就能继续读取 A 的 `tfstate`。

### 5.2 目标环境参数（逻辑示例，不是现存 YAML）

```yaml
environment: fabric-lab-b
source_ref: main
backend:
  storage_account: johnzhang
  container: tfstate
  state_prefix: fabric/lab-b        # 独立文件，不复制旧状态
  tenant_id: TENANT_A
fabric:
  tenant_id: TENANT_B
  capacity_id: EXISTING_CAPACITY_B
  workspace_name: healthcare-omop
  principal_id: FABRIC_DEPLOYER_B
landing:
  storage_account: johnzhang
  container: landing
  connection_name: healthcare-blob-reader
  reader_tenant_id: TENANT_A
  reader_client_id: BLOB_READER_A
deployment:
  repository_path: azure-fabric/workspaces/healthcare-omop
  item_types: [Notebook, DataPipeline]
```

实际生效配置文件须在**实施 Change** 内定义：非敏感 ID 进 GitHub 环境变量/按环境输入，Secrets 进受保护密钥存储，不得提交示例中的假值当成实值。临时环境标识不是 Terraform `workspace new` 的硬依赖。

## 6. 单次 Self-Runner 部署的目标阶段与闸门

1. **Preflight（只读）**：固定 Healthcare Main 完整 SHA；核对目标环境名称/State Key 不等于旧环境，检查 Backend Tenant A 访问与 Terraform State 存在性、目标 Fabric Tenant B 的 API 设置、部署身份、Capacity、Workspace 实际是否存在；跨租户 Blob Reader/网络机制前提；检测重复或相互冲突的 Item 所有者。任何未知已有资源都 **HOLD**，不能把空 State 推导为资源不存在。
2. **Plan**：采用精确 Git SHA、Provider 版本和环境配置，对需新建的 Fabric Control Plane 执行 `fmt/init/validate/plan`（Plan 自身会读取远端 State）；保存有权限限制的计划和读回摘要。**默认 Plan，不自动 Apply**。
3. **Approved Apply**：在现有安全规则与用户批准后，针对同一来源 SHA/State/计划执行；阻止非预期 Delete/Replace。按依赖顺序创建 Workspace/RBAC → Lakehouse → Azure Blob Connection；Terraform Outputs 获取真实 GUID。对于已有旧手建 Workspace，走明确 Import/Adopt 决策，不通过名称猜测。
4. **Deploy business Items**：Self-Runner checkout 同一 Git SHA；`fabric-cicd` 仅发布 `Notebook`、`DataPipeline`，用经验证的 `parameter.yml`/等价参数转换动态绑定 Workspace/Lakehouse/Connection ID；输出 Item IDs，确认 Notebook 与 Pipeline 均指向本环境。代码部署独立于数据加载。
5. **Publish data / execute**：在 Blob 有可验证 READY Batch 的前提下，受控触发 Pipeline：Azure Blob Copy → OneLake Bronze → Notebook → Silver / 小规模 Gold。只在已获得相应云端操作授权时执行，不能用部署成功代表业务完成。
6. **Readback / evidence**：核对 Workspace/Capacity/RBAC、Connection Blob 只读连通、Notebook/Pipeline definitions 和动态资源引用；PG Person/Visit、FHIR Patient/Encounter、HL7 ADT 的至少一批原文/哈希/行数/DQ/重复运行幂等；跨源 Patient Crosswalk/Timeline 按各自功能 Change 验证。报告绑定 Git SHA、Environment、Tenant **非敏感标识**、Terraform State Key、Workflow Run、Batch/Manifest 和校验结果。
7. **Failure boundary**：Apply 成功、`fabric-cicd` 发布成功、Blob READY 和业务 E2E SUCCESS 是四个互不等价的验收层级。失败可从相应阶段重试，重试前先读回目标资源与状态；禁止盲目删除/重建已存在的 Workspace 或覆盖旧 State。

**MVP success definition**：准备新 Fabric 环境和必需外部授权后，操作者只需设置环境变量/Secrets并在 Self-Runner 发起受控部署，**不需要人工逐个创建 Workspace/Notebook/Pipeline、抄 GUID 或通过 Portal 连接 GitHub**。仍然允许首次 Tenant 管理员开关/部署身份/Capacity 预备工作和必要的 Plan/Apply 人工批准。

## 7. 与现有仓库的准确差距（截至 2026-10-19，静态核对）

- 现有 `azure-fabric/infra-terraform/` 有七个独立 Root：`storage`、`workspace`、`onelake`、`notebook`、`data-factory`、`warehouse`、`foundation-iam`；Source/Provider/State 映射详见 [Terraform Architecture](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md)。既有 Workspace 原先通过 Portal 创建；Terraform Workspace Apply 前有 Import 防重复闸门。
- Self-Runner 的 `azure-infra.yaml` 目前只接受 `environment=dev`，使用 `johnzhang/tfstate/dev/<component>.tfstate`，且 `ARM_*` 与 `FABRIC_*` 共享身份；尚无跨 Tenant 的 Backend/Fabric Provider 分离实现。
- `workspace` Root 可描述资源及可选授权；`onelake` 可描述 Lakehouse。但 `connection` 部署、真实 Notebook/Pipeline 的 `fabric-cicd`、环境参数绑定、跨租户读回和单入口 Bootstrap 尚未实现。
- 已有 Terraform `notebook` / `data-factory` 定义的是**失败保护占位 Item**，不能把旧 Plan PASS 当作可运行业务 Item；部署设计必须先处理所有权，避免 Terraform 与 `fabric-cicd` 重复写同一资源。
- Azure Blob `landing` / `tfstate` 与既有状态/权限不得被此次设计 PR 改动。本轮**仅文档**，没有运行 `terraform plan/apply`、Fabric API、Kubernetes 或 Azure 探针，跨租户 Blob 连接尚未 E2E 验收。

## 8. 风险、兼容检查与回退

| 风险 | 最小控制与失败行为 |
| --- | --- |
| 新 Tenant 不允许 Service Principal API/Capacity 权限不足 | Preflight FAIL；用户手工准备 Tenant setting、Capacity 与部署主体，不能假装自动化 |
| 跨 Tenant Blob Connection 无法读取 | Service Principal/Tenant A 最小授权 + 真实 Copy/Read；失败 HOLD 并记录连接器/网络限制；必要时设计单独 SAS fallback |
| Terraform 新环境误用旧 State | Backend Key 环境强校验；已占用 State/目标资源不符合预期即 HOLD；旧 `dev` State 不迁移、不覆盖 |
| Terraform 控制平面与 fabric-cicd 双重所有者 | 按 Item 类型明确唯一所有者；每次部署前清点 Item；禁止默认 orphan unpublish |
| Notebook/Pipeline 资源 ID 硬编码 | 取 Terraform Outputs + fabric-cicd 参数重绑定；部署后检查实际 GUID 和关联 |
| Secrets 写入 State/日志 | Secret Store 注入、限制 Remote State 权限、优先 write-only 属性，PR/CI 输出脱敏 |
| 旧 Fabric Trial 到期 | 不依赖旧 Workspace 的 Git 或 Lakehouse 数据；源 Blob/正式 Git 定义保留并在新环境重建 |
| 每次重新部署产生资源费用或破坏 | 受控 Plan/Apply、无隐式 Destroy、预期变更核对、独立环境与隔离状态 |

## 9. 实施边界与后续 Change

本设计冻结的是**技术架构**，不在 `documents/` 维护可反复变化的实现任务状态。后续分别通过经用户批准的 OpenSpec Change 开展：Backend/Tenant 分离与环境隔离、Terraform Fabric Workspace/Lakehouse/Connection 管理、`fabric-cicd` 的真实 Item 定义与部署、受控 Self-Runner 一键编排、OMOP/FHIR/HL7 数据 E2E。可在第一条 OMOP → Fabric MVP 开发中逐步纳入，而**不是**先单独搭建一个庞大多租户平台。

设计相关：
- [Healthcare V2 多来源总路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)
- [FHIR/HL7 已确认的 MVP 设计](FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)
- [Azure/Fabric 系统总览](../../systems/azure-fabric/README.md)
- [Terraform 现有权限、State、历史 Plan 和安全边界](../../systems/azure-fabric/infra-terraform/ARCHITECTURE.md)
- [OpenSpec 开发生命周期](../../engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md)

## 10. 外部技术依据（2026-10-19 查阅）

1. [Microsoft Learn — End-to-end automation with Terraform and fabric-cicd](https://learn.microsoft.com/en-us/fabric/cicd/tutorial-end-to-end-automation)：Control Plane/Data Plane、SPN 前置条件、Notebook/Lakehouse 绑定；**GitHub Service Principal 原生 Git Integration 不作为本方案自动化前提**。
2. [Microsoft Learn — CI/CD overview](https://learn.microsoft.com/en-us/fabric/cicd/cicd-overview)：GitHub Actions 可驱动 Fabric CLI/Terraform/fabric-cicd，且原生 Git Integration 与从 Runner 发布是独立选项。
3. [microsoft/fabric-cicd — documentation](https://github.com/microsoft/fabric-cicd/blob/main/docs/index.md)：`item_type_in_scope`、`publish_all_items` 与 `unpublish_all_orphan_items` 的差别；MVP 禁止不经审批运行清理。
4. [Microsoft Learn — Azure Blob Storage Connector](https://learn.microsoft.com/en-us/fabric/data-factory/connector-azure-blob-storage-overview)：Copy Activity 支持 Service Principal / SAS；真正跨 Tenant 连通仍需目标环境测试。
5. [HashiCorp — AzureRM Backend](https://developer.hashicorp.com/terraform/language/backend/azurerm)：单一 Azure Blob Backend/不同 State Key，凭据与状态分别安全管理。
