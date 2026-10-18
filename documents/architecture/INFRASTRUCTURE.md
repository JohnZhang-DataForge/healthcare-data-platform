---
status: active
scope: infrastructure-architecture
last_verified: 2026-10-16
source_sha: 8d276dc7a121c15396a9ce328fcfea4688a795ae
---

# Infrastructure Architecture — Kubernetes、Portal 与 Azure/Fabric

> **源与范围**：依据 Healthcare Main `8d276dc7a121c15396a9ce328fcfea4688a795ae` 的 `kubernetes/`、`platform-portal/`、`airflow/`、`azure/infra-terraform/` 和截至 2026-10-15 的部署/Plan 验收记录重建的**基础设施说明**。不代表 2026-10-16 对每个 Pod/PVC/Node 的实时状态检查；Live 操作前必须单独读取当前集群。总体逻辑参见 [System Overview](SYSTEM-OVERVIEW.md)。

## 1. 本地节点和资源职责

| 位置 | 已验收架构中的职责 | 注意 |
| --- | --- | --- |
| `master01` / control-plane | Kubernetes 控制平面、集群管理 | 不作为主业务数据工作负载的默认位置 |
| `worker01`（`workload=storage`） | SeaweedFS S3、独立 Synthea NEW_ONLY Job 和数据生成持久化 | 两类存储各有 PVC；不把 SeaweedFS PV 当成 Synthea 的工作目录 |
| `worker02`（`workload=platform`） | Airflow 调度、Spark Operator 驱动/执行资源、工作负载 Pod | Spark/Portal 协作时共享调度/CPU/内存，不能只根据 Namespace 判断是否冲突 |
| `worker03`（数据库节点） | PostgreSQL17 OMOP/Airflow metadata 与独立 PostgreSQL14 Marquez metadata | 两套数据库的数据、PV/PVC、变更授权和恢复边界必须区分 |
| Self-Runner ARC `dw-runner-set` | GitHub Actions Self-hosted ephemeral Runner，在允许的 Workflow 中访问相应资源 | Runner 是执行客户端，不是业务 Spark/PG 常驻计算节点 |

注意：这是历史已验收部署职责；不同资源是否**现在**处于 Running/Bound 必须实测。Git 下的 YAML/Helm Values 不是实时运行状态的权威镜像。

### 仓库中可导航的 Kubernetes / Image 源码边界

- [Synthea CODE](../systems/data-platform/synthea/CODE.md)：独立 NEW_ONLY + 历史生成 Job、PVC/StorageClass 模板和 Synthea 容器镜像。
- [Landing CODE](../systems/data-platform/landing/CODE.md)：只读 Discovery、Claim 与 Processing Bridge 镜像；并非整套 SeaweedFS Service/PV 配置。
- [Airflow CODE](../systems/data-platform/airflow/CODE.md)：历史 Task004 控制面镜像和跨 Namespace RBAC。实际 Airflow Helm/GitSync 当前运行配置并未由这些 YAML 全面表达。
- [OMOP CODE](../systems/data-platform/omop/CODE.md)：历史 CDM Runtime 基镜像和 NEW_ONLY Writer 镜像；不包含 PostgreSQL 17 的完整 StatefulSet/Secret 配置。

**范围限制**：`kubernetes/` 当前只是部分工作负载的 Job/StorageClass/RBAC 定义，**不是** SeaweedFS、Local-path、Airflow、PostgreSQL 或 Portal 集群状态的完整导出。Github 源码不等于已部署资源，修改这些文件也不等于自动 Apply。

## 2. Namespace、数据服务和持久化

| 业务域 / Namespace | 组件 | 存储与网络要点 |
| --- | --- | --- |
| `dw-synthea` | 独立 Synthea NEW_ONLY 生成 Job | `synthea-local`（Retain），worker01，保存 Request/生成状态；不与 SeaweedFS PVC 混挂 |
| `dw-seaweedfs` | SeaweedFS S3，包含 Filer/Master/Volume/S3 网关 | `seaweed-local`、worker01 持久化，S3 内网 Service 为本地 Landing 接口 |
| `dw-airflow` | Airflow 3.2.2 Scheduler、GitSync DAG | 业务 DAG 与定时 Discovery 并存；Airflow metadata 位于独立逻辑数据库，不是 Fabric Pipeline |
| `dw-spark` | Spark Operator 工作负载、SparkApplication / KPO | Spark Processor/Writer 可产生 K8s Pods；业务数据交换以固定 S3 Manifest/Processing Handoff 为边界 |
| `dw-postgre` | PostgreSQL17：`omop` / `airflow` | `postgres-local`，worker03；业务 `cdm.*` / `etl.*` 和 Airflow Metadata 各司其职 |
| `dw-postgre14` | 独立 PostgreSQL14：`marquez` | `postgres-marquez`、Retain PVC，worker03；**不参与 OMOP 写库** |
| `dw-marquez` | Marquez 0.51.1 API + Web | API/Web 为 ClusterIP；额外 Web-only `marquez-web-lan` NodePort **30999** |
| `arc-systems` / `dw-runner` | ARC controller、临时 self-hosted runners | 跨仓 PR/SHA/Runner Gate 与真实 K8s 执行分开审查 |

`local-path` Provisioner 与多套 StorageClass 属于有状态基础设施；任何替换/重启/路径调整都要核验 Provisioner、ConfigMap、PV Node Affinity、PVC Bound、后端目录及原数据，并遵循运行授权。

**观察边界**：Portal 的 `dw-postgre14` 和业务 `dw-postgre` 虽共用同一物理数据库节点，**逻辑和存储隔离**。不能为了 Marquez 测试重建/清理 PostgreSQL17 或运行已完成 Writer。Portal 的 Web NodePort 安装验证只确认 Service/Endpoint/HTTP；**未证明外部 LAN 浏览器、公网 NAT、安全边界或备份恢复可用**。

## 3. Portal 真实基础设施状态

- `platform-portal/marquez/helm/values.yaml` 使用外部 PostgreSQL14：`postgresql.enabled=false`，不会通过 Marquez Chart 额外创建业务数据库。
- [Marquez API/Web 与 PG14 Schema 真实部署证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md)：Helm 0.51.1、独立 PG14 metadata schema（37 表），[NodePort Recovery Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493) SUCCESS，Web `30999` / Healthcheck / API Proxy PASS；不代表可从个人浏览器公网直连。
- Airflow A3 使用 `apache-airflow-providers-openlineage=2.17.0` 的受控 opt-in Probe，已在 Marquez 看到对应 Job/Run：[A3 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。
- Spark A4 在 worker02 执行过隔离 Spark 3.5.7 / OpenLineage 1.47.1 Smoke，应用 Job `portal_a4_a438628542127` 的 Run 关联仍不完整，完成 Run 位于 `unknown` Job，Dataset I/O 未验收；原工作流 FAIL + 随后三次只读 PASS：[A4 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。
- 这是**数据血缘实验与基础设施子系统**；目前只有 Marquez 原生 Web，没有自建 React/其他 Portal UI，也不宣称全局 Operator/业务 DAG 已统一接入。
- 共享 Airflow/Spark/K8s 更改需检查并行 Session 的运行，人工串行协调：[Session Policy](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md)。历史文档中“TASK004 仍在开发”不再作为今天的事实。

## 4. Azure/Fabric 的简化基础设施

```text
已存在（先前人工配置 / 不由本轮 Terraform 创建）：
  - Azure Subscription / OIDC bootstrap identity
  - Storage Account + Blob business landing
  - 供 Terraform Remote State 使用的 Blob container
  - Fabric Workspace healthcare-omop（曾手工创建，需先验身份/容量/权限）

目前 Healthcare 源代码已有 Terraform roots：
  storage | workspace | onelake | notebook |
  data-factory | warehouse | foundation-iam

第一批业务 MVP 只打算创建/验证：
  [Fabric Lakehouse]   onelake
  [Fabric Notebook]    notebook
  [Fabric Data Pipeline] data-factory

不要求第一批创建：
  Warehouse、额外的 Azure Data Factory 账户、第二个 Storage Account、
  新 Workspace、完整 dbt / ML 数据链
```

### 4.1 Terraform 的组件组织与状态

- Healthcare canonical IaC：[Azure infra-terraform](../../azure/infra-terraform/README.md)。各 `components/<name>/` 是独立 root，调用 `modules/<name>/`，拥有自己 Remote State key `dev/<component>.tfstate`。
- GitHub 执行器：[Self-Runner `Azure-Infra-TF`](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/azure-infra.yaml)。以 GitHub OIDC/Azure Blob remote backend 跑 `fmt/init/validate/plan`；源码 checkout `main`，真正操作应固定日志显示的 Healthcare SHA。
- `operation` 是 `plan|apply`（默认 Plan）；**工具支持 Apply 并不意味着本次获得授权**。目前三个 MVP Item 仅做真实 Plan，不执行 Apply。
- Azure RBAC 与 Fabric Workspace/OneLake Data Access IAM 互不等价；IAM 配置分组件管理，`foundation-iam` 仅共享 RG 级别，OneLake 的 access security 属 Preview，默认 `data_access_roles={}` 不生成权限。不能从 Terraform Plan 推断身份数据面权限完整。

### 4.2 三个已经完成的实际 Plan

| 组件 | Terraform 目标资源 | 实际已验证 | 未实现 |
| --- | --- | --- | --- |
| `onelake` | `fabric_lakehouse`，`lh_omop_analytics`、`enable_schemas=true` | [Run 38799966270 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270/attempts/2)，**1 add / 0 change / 0 destroy** | 真实 Create API/Item 和 Delta 数据 |
| `notebook` | `fabric_notebook`，`nb_omop_snapshot_load` | [Run 38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550)，**1/0/0** | 当前 Python Notebook `raise RuntimeError`，无真实 ETL |
| `data-factory` | `fabric_data_pipeline`，`pl_omop_snapshot_to_onelake` | [Run 38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221)，**1/0/0** | 当前 `notebook_id=""`，定义是 **Fail activity**，未实际触发 Notebook |

3 次成功 Plan 使用同一 Healthcare SHA `6acb59353f5d7630f65b6f417c8e8bfbd39cf651`，运行 `operation=plan`，日志 `APPLY_EXECUTED=NO`、`DESTROY_EXECUTED=NO`。**总计 3 个将新增的资源提案，但新增到 Azure/Fabric 的资源数在本次验收中是 0**。目标 Workspace ID 和 Blob state 路径在相应 Terraform 文件中已有引用，但部署前须验证它们仍属于正确环境。

### 4.3 后续真实部署的先决条件（不是本轮允许执行的命令）

1. 确认既有 Fabric Workspace、Capacity/Trial、Azure Blob Landing、Service Principal/OIDC 与 Fabric tenant permissions。
2. 编写独立 PostgreSQL 一致性 Exporter，并定义不可变 Export Manifest、只读权限、传输校验与故障恢复。
3. 在明确授权后执行分组件 Apply 并读回真实 Lakehouse/Notebook/Pipeline Item IDs；对既有 Workspace 先 Import，避免重复创建。
4. 将**真实 Notebook GUID** 写入 Pipeline 参数，替换 Fail activity 的占位定义；Notebook 实现 Azure Blob snapshot 读取、DQ、Delta 写入和幂等加载。
5. 执行真实 Fabric Pipeline/Notebook，并独立对账 Lakehouse 与本地 Postgres 同一 Export ID；验证失败/重复加载的可恢复性。

**第一阶段不把 Warehouse、dbt、再造 ETL 引擎或跨云自动调度作为前置条件。**

## 5. 状态结论

| 范围 | 结论 |
| --- | --- |
| Kubernetes / SeaweedFS / Airflow / Spark / PostgreSQL OMOP | **已有真实业务验收**；当前在线状态本轮未重新检查 |
| Platform Portal Marquez API/Web/PG14 + Airflow A3 | **真实部署和 Airflow 事件验证** |
| Platform Portal Spark A4 | **独立 Runtime Smoke 部分完成**，业务数据集级 Lineage **未验收** |
| Azure Storage 与 Workspace | **之前已存在**；不代表这些资源受本次 Terraform 管理 |
| Fabric Lakehouse/Notebook/Pipeline | **IaC + 真实 Plan PASS**；未 Apply，未创建，未业务运行 |
| PostgreSQL → Azure Blob Exporter + Fabric → OneLake | **目标设计**；需要实现和 E2E 验证 |

历史项目其他模块和 Runtime 细节仍从相应已验证证据、Contract、当前源码按需读取。本架构不包含已部署的 Mirth/FHIR/HL7、dbt、MLflow、Superset 或自定义 Portal UI。
