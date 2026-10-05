# Emory 医疗数据平台三节点架构方案 v2

日期：2026 年 10 月 4 日

## 1. 文档定位

本文件只描述平台架构、组件职责、数据流、部署边界、命名规范、阶段目标和验收原则。

**本文不包含具体安装命令、YAML、Secret 明文、SQL 或逐步部署操作。**  
所有可执行部署步骤统一放在独立的《阶段一部署 Runbook》中，避免把“设计决定”和“操作手册”混在一起。

本方案仍以 Emory Data Engineer II / Senior Data Engineer 相关能力展示为主线：医疗数据接入、PySpark、Airflow、S3 兼容对象存储、PostgreSQL / OMOP、数据质量、研究数据交付，以及后续的 dbt、ATLAS、ClickHouse、治理和 CI/CD。

---

## 2. 当前已确定的三节点职责

当前实际 Kubernetes 节点角色统一如下：

| 节点 | 标签 | 核心职责 | 当前 / 计划组件 |
| --- | --- | --- | --- |
| worker01 | `workload=storage` | Storage / Landing | SeaweedFS、S3 Gateway、Landing/Raw/Processed/Archive |
| worker02 | `workload=platform` | Platform / OLAP / Streaming | ClickHouse、Kafka、ATLAS/WebAPI、MLflow、监控等后续平台服务 |
| worker03 | `workload=compute` | Compute / Orchestration / Relational Serving | PostgreSQL/OMOP、Airflow、Spark/PySpark、dbt Job |

master01 只作为 Kubernetes control plane 和管理入口，安装 `kubectl`、Helm 等管理工具，不承担主要数据工作负载。

### 2.1 为什么这样分

worker01 专门承担对象存储和 Landing Zone，使数据入口与计算、数据库解耦。

worker03 集中部署 PostgreSQL、Airflow 和 Spark，是当前实验环境中的主要计算与数据发布节点。它承担的组件较多，因此 Spark、数据导入、dbt、大型质量检查等重任务需要错峰或限制并发。

worker02 保留给平台型和分析型服务。后续 ClickHouse、Kafka、ATLAS/WebAPI、MLflow 等组件优先放在 worker02，避免继续把 worker03 堆得过重。

---

## 3. 存储架构

### 3.1 local-path-provisioner

集群使用一个 Rancher local-path-provisioner，但划分三个 StorageClass：

| StorageClass | 使用范围 | 实际路径 | 主要用途 |
| --- | --- | --- | --- |
| `local-path` | 通用 | `/data/local-path` | 普通实验组件 |
| `seaweed-local` | 仅 worker01 | `/data/seaweedfs` | SeaweedFS Master/Filer/Volume 底层持久化 |
| `postgres-local` | 仅 worker03 | `/data/postgresql` | PostgreSQL PGDATA |

`seaweed-local` 和 `postgres-local` 均采用 `Retain`，避免误删 PVC 时底层数据立即被清除。删除 PVC 后可能留下 Released PV，需要人工确认后清理。

### 3.2 SeaweedFS 的角色

SeaweedFS 是平台的 **S3 兼容对象存储和 Landing Zone**，不是 PostgreSQL 主数据盘的替代品。

SeaweedFS 自身底层持久化使用 worker01 的 `seaweed-local`，向集群其他工作负载提供网络 S3 API。

当前逻辑：

```text
worker01 本地磁盘
        ↓
seaweed-local
        ↓
SeaweedFS Master / Filer / Volume
        ↓
SeaweedFS S3 Gateway
        ↓
Airflow / Spark / Python / pgBackRest 等客户端
```

### 3.3 PostgreSQL 的角色

PostgreSQL 使用 `postgres-local`，PGDATA 固定在 worker03 的 `/data/postgresql`。

PostgreSQL 用于：

- OMOP CDM
- 医疗数仓关系模型
- 候选区与发布区
- 研究数据服务
- 后续 WebAPI / Airflow / MLflow 等组件的独立 metadata database（按数据库和账号隔离）

PostgreSQL 主数据不直接放在 S3 上。

### 3.4 PostgreSQL 备份

后续使用 pgBackRest / WAL archive 将 PostgreSQL 物理备份和 WAL 写入 SeaweedFS：

```text
PostgreSQL PGDATA
     ↓
pgBackRest / WAL archive
     ↓
SeaweedFS S3
     ↓
postgres-backup
```

因此 SeaweedFS 与 PostgreSQL 是“主存储 + 备份存储”的关系，而不是同一份数据库文件的共享存储。

---

## 4. Namespace 与命名规范

统一使用：

| Namespace | 用途 |
| --- | --- |
| `dw-seaweedfs` | SeaweedFS / S3 / Landing Zone |
| `dw-postgre` | PostgreSQL / OMOP |
| `data-warehouse` | ClickHouse |
| 后续 `data-platform` | Airflow / Spark / dbt 等计算与编排组件（如需要单独隔离） |
| 后续 `streaming` | Kafka（如需要单独隔离） |

主要对象统一使用 `dw-` 前缀，例如：

- `dw-seaweedfs`
- `dw-postgre`
- `dw-postgre-data`
- `dw-postgre-database`
- `dw-postgre-service`

命名重点是统一、可读、便于以后维护，不追求产品官方默认命名。

---

## 5. S3 Landing Zone 架构

### 5.1 S3 Endpoint

SeaweedFS S3 Gateway 作为集群内部 S3 endpoint。

当前服务逻辑地址：

```text
dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
```

### 5.2 S3 认证

S3 已启用认证，不允许匿名访问。

认证采用 Kubernetes Secret 管理：

- `dw-s3-credentials`：保存管理员 access key / secret key
- SeaweedFS S3 Gateway 从 Secret 注入认证凭据
- Airflow / Spark 等客户端在自己的 namespace 中使用对应 Secret
- Secret 不能跨 namespace 直接引用，因此后续客户端 namespace 会创建自己的 S3 credential Secret

**Secret 用于保存凭据，不用于保存数据。**

客户端逻辑：

```text
Kubernetes Secret
      ↓
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
      ↓
Airflow / Spark / AWS CLI / boto3
      ↓
SeaweedFS S3
```

未来如果需要进一步展示企业级 Secret 管理，可引入 Vault；当前阶段 Kubernetes Secret 已足够。

### 5.3 Bucket 分层

当前规划并已验证的 bucket：

| Bucket | 作用 |
| --- | --- |
| `health-landing` | 原始进入平台的数据，尽量保持源格式 |
| `health-raw` | 完成 ingestion 基础规范化后的数据 |
| `health-processed` | Spark 清洗、转换后的 Parquet / Delta 等结果 |
| `health-archive` | 历史批次、归档数据 |
| `postgres-backup` | PostgreSQL pgBackRest / WAL / logical backup |

Landing Zone 内按数据类型、来源和批次日期组织对象，例如：

```text
health-landing/
  fhir/
  patient/
  encounter/
  claims/
  measurement/
  vocabulary/
```

已验证的 S3 行为包括：

- 带 Secret 凭据列举 bucket
- 创建 bucket
- PUT / 上传对象
- LIST 对象
- GET / 下载对象
- 清除凭据后匿名访问被拒绝

因此 S3 Landing Zone 已具备进入下一阶段的基础条件。

---

## 6. PostgreSQL / OMOP 架构

当前 PostgreSQL 为 PostgreSQL 17 单实例 StatefulSet，固定在 worker03。

逻辑结构：

```text
dw-postgre-database
        ↓
dw-postgre-data PVC
        ↓
postgres-local
        ↓
worker03:/data/postgresql
```

服务分为：

- Headless Service：StatefulSet 稳定 DNS
- ClusterIP Service：供 Spark、Airflow、dbt、WebAPI 等集群内部客户端访问

集群内部统一数据库入口：

```text
dw-postgre.dw-postgre.svc.cluster.local:5432
```

当前已完成持久化验证：

1. 创建测试表和数据
2. 删除 PostgreSQL Pod
3. StatefulSet 自动重建 Pod
4. 数据仍存在

这证明 PostgreSQL PGDATA 与 Pod 生命周期解耦。

OMOP CDM 5.4 将在后续阶段部署到该 PostgreSQL 实例中。

---

## 7. Airflow 与 Spark 的位置

当前规划将 Airflow 与 Spark 放在 worker03：

```text
worker03
  PostgreSQL / OMOP
  Airflow
  Spark / PySpark
  dbt Job
```

Airflow 负责：

- 批次编排
- 参数和依赖
- 任务状态
- Spark 提交
- PostgreSQL 导入
- dbt / 质量检查
- 发布与审计

Spark 负责：

- 读取 SeaweedFS Landing/Raw
- CSV / FHIR JSON 解析
- 清洗和标准化
- Parquet / Delta 写回
- JDBC 写入 PostgreSQL 候选区

Airflow 不负责传输大型数据文件；任务之间只传递对象路径、run_id、状态等轻量信息。

---

## 8. ClickHouse 的角色

ClickHouse 不属于阶段一核心基础设施，后续作为独立 OLAP / Warehouse 层放在 worker02，namespace 使用 `data-warehouse`。

职责区分：

```text
SeaweedFS   = Data Lake / Object Storage
PostgreSQL  = OMOP / Relational Serving
ClickHouse  = OLAP / Analytical Warehouse
Spark       = Compute / Transformation
Airflow     = Orchestration
```

ClickHouse 可承载：

- 大宽表
- 事实表和聚合表
- 高频分析查询
- 时间序列 / 大扫描分析

这样 PostgreSQL 不需要同时承担 OMOP 和高吞吐 OLAP 的全部职责。

---

## 9. 医疗数据主线

项目仍采用两类模拟数据源：

- CSV：患者、就诊、诊断、检验
- FHIR R4 JSON：Patient、Encounter、Condition、Observation

主数据流调整为：

```text
模拟数据源
    ↓
SeaweedFS health-landing
    ↓
Airflow 触发
    ↓
Spark / PySpark
    ↓
health-raw / health-processed
    ↓
PostgreSQL 候选区
    ↓
dbt / OMOP 映射 / 质量检查
    ↓
已发布 OMOP / 研究数据
    ↓
ATLAS / Notebook / ClickHouse 分析
```

PostgreSQL backup 独立写入 `postgres-backup`。

---

## 10. 安全边界

当前实验环境采用以下最小安全设计：

- S3 开启认证
- S3 access key / secret key 不写入普通应用 YAML
- 使用 Kubernetes Secret 注入客户端
- PostgreSQL 密码使用 Kubernetes Secret
- 不把对象存储底层 local-path 直接共享给其他节点
- 其他工作负载只能通过 S3 API 访问 SeaweedFS
- 其他工作负载只能通过 PostgreSQL Service 访问数据库
- anonymous S3 access 明确拒绝
- 后续按组件拆分不同 S3 identity 和最小权限

后续可扩展：

- Vault
- NetworkPolicy
- 独立 service account
- PostgreSQL RBAC / RLS
- S3 workload-specific credentials

---

## 11. 资源与并发原则

三台 worker 每台约 25 GB 虚拟内存配置。实验环境不追求高可用和大规模性能。

worker01 以 SeaweedFS 为主，资源压力较低。

worker03 同时承担 PostgreSQL、Airflow 和 Spark，需要：

- PostgreSQL 保持明确 requests/limits
- Spark 作业按需启动
- Spark、dbt、大型质量任务错峰
- 不把所有重任务长期同时运行

worker02 后续承担 ClickHouse、Kafka 和研究平台服务，同样按阶段启用。

---

## 12. 分阶段实施

### 阶段一：基础存储与数据库（当前）

包含：

- 节点标签
- local-path-provisioner
- `local-path`
- `seaweed-local`
- `postgres-local`
- SeaweedFS
- `dw-seaweedfs`
- S3 Secret 认证
- Landing Zone buckets
- PostgreSQL
- `dw-postgre`
- PostgreSQL Secret
- PVC 持久化验证
- S3 PUT/LIST/GET/匿名拒绝验证

**阶段一当前核心内容已经验证完成。**

### 阶段二：DE 数据主线

部署：

- Airflow
- Spark / PySpark
- 模拟 CSV / FHIR 数据
- Landing → Raw → Processed pipeline
- Spark JDBC → PostgreSQL
- dbt

验收：

- Airflow 能使用 Secret 访问 S3
- Spark 能读写 SeaweedFS
- Spark 能写 PostgreSQL
- 两批数据可重放
- 异常数据可隔离

### 阶段三：OMOP 与研究环境

部署 / 完成：

- OMOP CDM 5.4
- Vocabulary
- Mapping
- ATLAS / WebAPI
- Data Quality Dashboard
- 研究队列验证

### 阶段四：分析数仓与治理

加入：

- ClickHouse
- 数据目录
- 血缘
- 权限
- CI/CD
- 备份恢复演示

### 阶段五：扩展

按需要加入：

- Kafka
- Structured Streaming
- MLflow
- Vault
- Notebook
- Feature engineering / ML

---

## 13. 阶段一验收状态

当前已经验证：

| 项目 | 状态 |
| --- | --- |
| `seaweed-local` 只落 worker01 `/data/seaweedfs` | 已验证 |
| `postgres-local` 只落 worker03 `/data/postgresql` | 已验证 |
| SeaweedFS namespace `dw-seaweedfs` | 已完成 |
| PostgreSQL namespace `dw-postgre` | 已完成 |
| SeaweedFS Master/Filer/Volume/S3 均在 worker01 | 已验证 |
| PostgreSQL Pod 在 worker03 | 已验证 |
| PostgreSQL 删除 Pod 后数据仍存在 | 已验证 |
| S3 Secret 认证 | 已验证 |
| S3 bucket 创建 | 已验证 |
| S3 上传 / 列举 / 下载 | 已验证 |
| S3 匿名访问拒绝 | 已验证 |
| PostgreSQL S3 backup | 计划中 |
| Airflow / Spark | 下一阶段 |

---

## 14. 架构原则总结

这套 Lab 不追求把所有软件都装进去，而是保持每个组件有明确职责：

- local-path 解决单节点本地 PVC
- SeaweedFS 解决跨节点对象存储和 Landing Zone
- PostgreSQL 解决 OMOP 与关系型研究数据服务
- Spark 解决大批量数据转换
- Airflow 解决编排
- ClickHouse 后续补充 OLAP
- Kafka 只在需要 streaming 场景时加入
- Vault 只在需要进一步展示 Secret 管理时加入

部署命令、YAML 和测试步骤不写在本架构文件中，统一维护在《阶段一数据平台部署 Runbook》中。
