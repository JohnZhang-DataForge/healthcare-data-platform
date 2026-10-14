> **2026-10-13 A0 实测补充（新优先级）**：[第二轮真实兼容性和网络安全 Gate](./MARQUEZ-A0-COMPATIBILITY-SECURITY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Run 38491060185](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491060185) PASS：上游固定源码包含 Flyway 8.5.13（PG17 支持版本不匹配），Web 代理 /api/v1、/api/v2beta，且 Chart Web/API 共享 service.type；30999 未占用但 NAT/防火墙未知。**不得直接套用后文的 A1/A2 实施：CURRENT NEXT = 隔离 PG17/Marquez 兼容 PoC，NodePort 必须单独 Web Service + trusted LAN/VPN Gate。**这不影响七阶段总体目标。\n\n# Healthcare Data Platform — 路线 A：OpenLineage + Marquez 真实血缘实施规划 v3.0

> **决策日期**：2026-10-13（EDT）；**状态**：DESIGN APPROVED / IMPLEMENTATION NOT STARTED；**权威目录**：`docs/demo-plan/`。  
> **明确决策**：**先部署 Marquez 和接通 Airflow/Spark 的真实数据血缘**；**不制作任何独立前端展示网站**，不部署 Superset、OpenMetadata、Kafka/Kinesis；第一阶段仅从受控网络经 Kubernetes **NodePort TCP 30999** 访问 **Marquez 原生 Web UI**。  
> **本规划的提交仅涉及文档**：未创建 Namespace、Secret、数据库、NodePort、Pod 或任何模拟 Lineage 事件；上线需后续各阶段分别通过 GitHub PR + exact-SHA Self-Runner 验收。

## 0. 权威事实、与 TASK004 的并行边界

先读 [docs/README.md](../README.md)、[TASK-STATUS](../tasks/TASK-STATUS.md)、[独立 Producer/Consumer 架构](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) 和 [Writer 安全 Gate](../tasks/OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md)。**Main 顶部最新真实 Live Closeout 覆盖历史旧 NEXT**。

截至本规划时的已验证事实：

| 环节 | 已真实验证 | 尚未证明 |
|---|---|---|
| 独立 NEW_ONLY 生成 | worker01 `dw-synthea`、Retain PVC、Synthea 3.3.0、73 Person、12159 Encounter、18 CSV；[Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008) | 正式专用发布镜像、任意新请求自动生成发布 |
| NEW_ONLY → S3 READY | 同一个冻结 Batch `synthea-new-only-gh-38484300008`，18/18 CSV checksum 回读，Manifest 最后发布 `INTAKE_VERIFIED`、SHA `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9`，独立 Resolver readback/replay PASS；[Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236) | Airflow 自动 Claim/消费该新 Batch |
| Airflow | `landing_batch_discovery` 每 15 分钟 S3 Discovery + PG Claim Guard 读/决策接线 PASS；[Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) | Claim 持久化/新批自动流水线（`CLAIM_ENABLE=NO`） |
| Spark | 经明确 manual opt-in 的**历史批** Person/Visit + Processing Reconciliation PASS；[Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452) | NEW_ONLY 新 Batch 自动调度、完整 COMMIT |
| Writer/OMOP | 真实 S3 Parquet → PG Drift Gate 正确拒绝既存 source ID 内容漂移，无持久变更；[Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382) | 新无冲突批次**成功 ROLLBACK 正例**、事务性 Claim fencing、动态 COMMIT、最终 DB reconciliation/replay |
| Marquez/OpenLineage | **尚未部署/仪表化** | 所有目标 Lineage 边均需实测 |

**两个重要身份时间**：NEW_ONLY 固定 request 的 `source_date=2026-10-13`；其 S3 `ingest_date=2026-10-14 UTC`，不可擅自修改为同一天。已经提交的历史 PostgreSQL Person/Visit 不得冒充这个 NEW_ONLY Batch 的 COMMIT。

与 TASK004 完全并行：本 Demo 规划不得更改 Producer、Manifest、`CLAIM_ENABLE`、旧 Writer Batch ID 格式、Existing Target Drift、OMOP schema/data 或 TASK005 状态。新的追踪功能原则上优先通过 Airflow Provider、Spark Listener 和独立配置加入；不得为了画一张完整图而触发 Generator 或绕过安全门槛。另一个 session 的 TASK004 可继续独立演进。

## 1. 架构与组件职责（观测旁路，不参与业务决策）

```text
worker01 / dw-synthea                  worker01 / SeaweedFS
  Synthea NEW_ONLY standalone Job  --->  health-landing / raw CSV
       |                                   immutable Manifest / READY
       |                                               |
       | [producer evidence: actual run + S3 SHA]      v
       |                              worker02 / dw-airflow
       |                           landing_batch_discovery */15
       |                           Claim Guard [read-only currently]
       |                                               |
       |                         Spark Operator / dw-spark on worker02
       |                                  SparkApplication driver/executors
       |                                  S3 raw input -> PySpark -> Parquet
       |                                               |
       |                         Python OMOP Writer / PostgreSQL worker03
       |                               drift guard -> controlled COMMIT
       |                                       [NOT DONE for new batch]
       |
       |  (actual metadata/events only; no invented business run)
       +-----------------------------------------------+
                                                       |
     Airflow Provider ------ actual DAG/Task events ---+
     Spark Agent ---------- actual Spark IO events ----+---> Marquez API (ClusterIP)
     Producer/Python Writer - only proven explicit events (later)      |
                                                       +---> marquez DB (separate,
                                                       |        on worker03 PG if safe)
                                                       v
                                                Marquez native UI
                                                       |
                                            NodePort TCP 30999
                                            LAN/VPN allowlisted only
```

**OpenLineage**：事件规范 + Airflow/Spark 采集集成，不是独立服务器。**Marquez**：数据接收 API、数据持久化、Job/Run/Dataset 血缘查询、原生 Web UI。先自动采集，缺失事件时在数据真实性核验后才考虑显式自定义事件。**只读 Marquez 浏览不会生成、调度、领取或 COMMIT 任何任务。**

**分层血缘现实**：Airflow 可产生 Task/Run 事件，不代表 Synthea 已产生 OpenLineage Producer 事件；Kubernetes Spark Operator 提交/调度资源也不等于 Spark Listener 自动记录 Operator 控制面事件；Spark I/O 事件可能缺少 S3A/JDBC/自定义 Python 的输入输出；Writer 是独立 Python 过程，自动 Spark 监听器不会替它产生数据库 COMMIT 事件。**自动采集 ≠ 全部七段已连成一条真实图**。

## 2. Kubernetes 部署拓扑与访问端口

| 组件 | Namespace / 位置 | Service / 网络 | 数据存储 |
|---|---|---|---|
| Marquez API | **`dw-marquez`**，优先 scheduler 选择有资源 worker | **ClusterIP**，默认上游 HTTP API 容器端口约 5000，admin 健康端口约 5001；实际以 pin 版本/chart 渲染为准 | `marquez` 独立 DB |
| Marquez Web UI | **`dw-marquez`**，默认不 pin worker | **NodePort `30999/TCP`** 对接 Web UI；上游 Web 端口常见 3000，实际 Service targetPort 需据 chart 核验 | 无业务持久数据 |
| UI → API 读路径 | 同 Namespace 内优先走私有 API；浏览器实际跨域/代理机制必须**真实抓取验证** | 只在受限网络内满足 UI 访问；如前端需要浏览器 API，需经审计的同源/鉴权代理或受限网域路径，不自动开放整个 API 到公网 | 不暴露 API 管理端口 |
| OpenLineage emitters | 现有 Airflow 3、真实 Spark Driver/Job | **Pod → Marquez API ClusterIP** 内网 HTTP，查 NetworkPolicy/DNS | 不需新流式消息系统 |
| PostgreSQL | worker03 现有独立 Postgres 实例（优先审计复用） | 原有私有 DB Service，专用 `marquez` 用户/Secret | 独立 `marquez` database；**不与 `omop`/`airflow` 混库** |

**NodePort 30999 的约束**：

1. 30999 位于 Kubernetes 默认 30000–32767 范围，但**必须实查 apiserver `--service-node-port-range`、现有 Service 是否占用、kube-proxy/node 地址、OS 防火墙/路由**后才能创建；不假设固定某台 worker 的 NodePort 只监听那一台机器。
2. 预期入口 `http://<reachable-node-ip>:30999` **仅用于受控 LAN/VPN**；NodePort 通常可通过多个节点 IP 访问，绝不因 Namespace 叫 `dw-marquez` 就自动隔离公网。
3. **不能把 NodePort 当作身份认证**。Marquez 上游 API 默认不提供通用强制鉴权；须在真正开放前确认只有用户控制的局域网/VPN/IP 集合可访问、没有公网 NAT/端口映射。如网络不可保证，阶段验收标为 `BLOCKED:EXPOSURE_POLICY`，而不是冒险开放。后续公网只读查看属于独立安全评审，此阶段不实现。
4. Marquez Web 自带 UI 可依赖后端 API：**不能仅把 Web Pod 3000 映射到 30999 后就宣称图可用**；测试浏览器开发者工具请求、Cookie/CORS、API 端点、GraphQL/Job/Dataset 读取。任何需要访问浏览器侧 API 的设计必须明确代理路径/认证/防写边界；Admin/health 接口保持内部。
5. 所有 API/DB 的 Service 继续 `ClusterIP`；禁止将数据库/health/admin 或无鉴权的 OpenLineage 写入 API 额外变成 NodePort。初期如还未落实网络隔离，先在集群内部验证 Web/API，NodePort 最后开。
6. 校验 Chart 的 Web/API Service、`MARQUEZ_HOST`/`MARQUEZ_PORT` 或对应参数。优先使用 upstream `MarquezProject/marquez/chart` pin chart/镜像 digest，禁止使用已归档的旧 `marquez-chart` 项目。**版本从真实 chart + 环境兼容审计确定，不按“latest”盲目部署**。

## 3. PostgreSQL 安全复用前置 Gate

必须经 Self-Runner **READ ONLY** 审核：

- `SHOW server_version`、角色/DB 清单（不输出密码）、可用连接数 / `max_connections` / 当前连接与峰值、PostgreSQL 内存/disk/PVC 使用、worker03 资源 requests/limits、表空间和备份可行性。
- 目标 Marquez 版本/迁移机制（Flyway 或实际 chart 的 schema migration）、支持 PostgreSQL 版本、需要的 database/schema/extension 权限和 `CREATE DATABASE`/用户创建职责。**迁移只能作用于新 `marquez` DB**。
- 明确资源增长、连接上限、超限保护和服务失联时 Airflow/Spark 是否继续运行；lineage sink 故障默认不得改变核心 ETL 事务语义。
- 复用通过才另轮创建：数据库 `marquez`、专用非 superuser `marquez_app`（最终名实施时确定）、Secret `dw-marquez/marquez-db`；随机生成 credentials，不写入 Git/日志，不用现有 `omop_admin` 或 `airflow_user`。
- Chart 若带内置 PostgreSQL：**关闭子 chart** 并显式指向现有实例；先验证数据库 migration/role 最小权限，资源异常或不兼容就 STOP，转评估独立 PostgreSQL 实例而不是越权修改现有 PG。

**验证**：只在 `marquez` DB 新建/读回测试元数据，重启 Marquez 后依然存在；对 `omop`、`airflow` 和既有 Claim/OMOP 业务记录执行独立 readback 无变化（数据库授权创建元数据自身是受控 mutation，不会被错写成 READ ONLY）。不得声称部署 Marquez 已成功意味着血缘来自真实业务。

## 4. OpenLineage 采集与真实数据集命名合同

### 4.1 Airflow Provider（第一条真实事件）

- 核对 Airflow 3.2.2 实际安装包/Provider 与 Scheduler、DAG processor、Executor/Worker 的运行方式；按兼容矩阵 pin `apache-airflow-providers-openlineage` 和 Python client，并确认升级不会破坏 gitSync、Airflow 3 DagBag、`KubernetesPodOperator`。
- 仅在被需要的 Airflow 容器/镜像中安装 Provider、配置 `AIRFLOW__OPENLINEAGE__TRANSPORT`（HTTP URL 指向**内网** Marquez API；上游常见 endpoint `api/v1/lineage`，以实测 API 为准）、`AIRFLOW__OPENLINEAGE__NAMESPACE`，必要时通过 Airflow Connection 存储配置。版本和语法见官方文档。
- 先做现有 `landing_batch_discovery` 的**只读 Discovery/Claim Guard** 真正 Airflow DagRun；确认 START/COMPLETE、DAG/task/run IDs、实际时间、状态进入 Marquez。不得启动 Generator 或打开 `CLAIM_ENABLE`。
- 记录 Provider 是否识别 KPO 的 Task 边与输入输出；未知数据集不凭猜测添加。

### 4.2 Spark Listener（第二条真实事件）

- 先检查现有 Spark 版本、Scala、Java、Spark Operator、SparkApplication YAML、当前 Hadoop AWS 依赖、类路径和 JAR 获取机制；pin 与现网兼容的 `io.openlineage:openlineage-spark` Agent。
- 以最小实际 Spark **Person Processing-only** 作业 PoC，不修改原始 PySpark 转换逻辑：配置 `spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener`、相应 `spark.openlineage.transport.*` / namespace / Driver JAR 路径；实际键名和版本据 pinned Agent 核验，不假定官方旧指南永远适用。
- 真实执行读取 S3 Raw CSV，生成真实 Processing Parquet：Marquez 分别能查询被使用的输入、输出 Dataset 和对应 Job/Run，且 Dataset URI、时间、row counts 与 S3/Processing 独立读回能对得上。
- Spark Operator Pod 创建、Driver/Executor 生命周期与 Spark Listener 的 Job 事件分别取证；如 KPO 启动的 SparkApplication 未继承 OpenLineage `parent` 信息，不虚构 parent/child。通过 Operator CR UID、KPO Task ID、SparkApplication 名称建立**有证据的映射表**；Provider 若能为相应 Operator 注入 parent facet，需真实验证其支持范围再启用。

### 4.3 数据集与身份约定（建议待实测冻结）

| 物理对象 | 真实来源 | OpenLineage 记录要求 |
|---|---|---|
| Synthea 生产请求 / Job | K8s Job、冻结 params、真实 Self-Runner Run | **自动 Agent 不一定能发现**；只在真实生成/读回成功后可补 producer event |
| S3 Landing Batch | `health-landing` immutable verified Manifest、18 CSV SHA | 将实际对象 URI、batch/manifest SHA 作为 dataset/run facet；不把未发布目录当 READY |
| Airflow Discovery/Claim | `landing_batch_discovery` 实际 DagRun/TaskInstance | Provider 的 run job id 与 Task 状态；Claim 只读不是 `CLAIMED` |
| SparkApplication / Driver | CR/Pod UID、真正 Spark run | Operator 提交控制边须证实，Spark Agent 记录执行边 |
| Raw Input / Processing Output | 真实 `s3a://...` CSV/Parquet | 明确 URI 归一化规则（`s3://` vs `s3a://`）、namespace/name，保留实际物理 URI |
| Python OMOP Writer | 实际 Writer K8s Job + Writer Commit 记录 | 独立 Python 事件仅在后续审查后发出；`BLOCKED`、`ROLLBACK` 不得变成成功写入 |
| PostgreSQL OMOP `cdm.person`/`cdm.visit_occurrence` | PG 内真实 commit + audit/reconcile | **只有正确 COMMIT 及独立对账证据**方可声明写入这两个 Dataset |

关键的事件关联键建议：`generation_request_id`、`batch_id`、`manifest_sha256`、`airflow_dag_run_id`、`airflow_task_instance_id`、`spark_application_uid`、`spark_processing_run_id`、`writer_commit_id/ledger`、`git_sha`。不要将这些不同身份混为一个“run_id”。只有在双方实际事件引用同一不可变输入时才把边拼接成同一条血缘链；URI 前缀相似不足以认定连接。

### 4.4 Python Writer / Generator 事件（延后、避免侵入 TASK004）

原则：先让 Provider + Agent 获得真实 DAG/Task 和 Spark 读写血缘；Producer 与独立 Python Writer 不在这些工具的自动覆盖保证之内。当前已真实发布的 NEW_ONLY Batch 可作为**S3 实体证据**，但不等于“生产器已发 OpenLineage Run”；当需展示其生产环节时，优先考虑独立、只读、消费成功冻结 Run / S3 immutable Manifest 的元数据 adapter，仅在能证明真实历史执行的前提下补发事件，并显式标记历史观测（非在线原生 emitter）。**禁止为未发生的 COMMIT 制造 Lineage**。未来若需要正式实时事件，再对 NEW_ONLY 发布器与 Writer 进行独立 PR、测试和相应 TASK004 owner 审批。

## 5. 实施阶段：一轮一闭环，不交叉主线

| 顺序 | 阶段 | 本轮代码/集群动作 | 必须的独立验收 / 停止门槛 |
|---|---|---|---|
| **A0** | **只读资源/网络/版本/DB/Port 预检** | GitHub PR 中受限 Runner workflow 读 K8s Node/Pod/PVC/Service、PG read-only 容量、Airflow/Spark 版本、Marquez chart/镜像及 API/UI 路径；不建资源 | exact SHA + Runner PASS；`30999` 未占用/NodePort 范围与私网控制确认；兼容版本矩阵、数据库/资源预算、baseline snapshot 和回滚方案 |
| **A1** | **元数据库隔离** | 通过 A0 后独立 PR：经授权在现存 PostgreSQL 创建 `marquez` DB + 最小权限用户，`dw-marquez` namespace/Secret；不改业务库 | 仅 `marquez` 可读写，OMOP/Airflow/Claim readback 不变；备份/连接数/权限检查；失败回滚本轮 metadata 资源 |
| **A2** | **Marquez API + 原生 UI + 30999** | pin Marquez backend/web/Chart 镜像；部署 ClusterIP API/UI，合规后启用 UI-only NodePort 30999；不导入 fake business metadata | Pod/health/DB migrations/重启持久化 PASS；从真实 LAN 浏览器访问 Job/Run/Dataset 空态；API internal；防火墙/NodePort exposure 与 UI 浏览器 API 请求验收；可使用明确标记 `synthetic-test` 的单条协议探针但不得当业务血缘 |
| **A3** | **Airflow 实时事件闭环** | Provider 以可回滚镜像/配置接入既有 Airflow，触发安全 read-only DagRun | Marquez 上真实 DAG/Task START+COMPLETE；Run ID/时间与 Airflow 对齐；`CLAIM_ENABLE=NO`、PG 数据/Claim 无变化；gitSync/调度稳定 |
| **A4** | **Spark 实时血缘闭环** | Agent/Listener 通过受控 SparkApplication 入口启用；仅选已验收历史 `person` Processing-only 输入 | Spark Driver 真跑并发送 dataset input/output；S3/Parquet URI、application UID、运行时间对齐；无需 PostgreSQL mutation；失败可不影响现有未仪表化作业 |
| **A5** | **Airflow → Spark 关联与两实体扩展** | 核验 KPO/Spark CR/Run 相互引用与 `parent` facet；再扩展到 Person + Visit/reconciliation | 有证据的真实上下游边；如果不能自动 stitch 则如实保留独立图，单独记录缺口；不可制造假 parent/child |
| **A6** | **Synthea→S3、Python Writer→OMOP 延伸** | 对真实 NEW_ONLY READY producer 发布事件（如需），对 Writer 的独立成功 COMMIT 再加显式事件；须等待 TASK004 本身对应成功 Run | 对应 batch/SHA/DB checkpoint 的真实链；BLOCKED/ROLLBACK 仅显示失败/拒绝或无写入；直到真 COMMIT + DB reconcile 前，OMOP success edge 为 `PENDING` |

每轮验收流程：Healthcare feature PR → exact PR SHA → Self-Runner workflow（必要时在 Self-Runner 自己的 PR 中定义受限验证）→ 真实读回与安全对照 → evidence Closeout → PR 合并 Main → 必要的 post-merge readback；同问题失败 **超过三轮即停**。命名使用功能名如 `marquez-deployment`、`airflow-lineage-emitter`、`spark-lineage-listener`、`lineage-runtime-audit`，不再新增泛用 `task004-stepXX` 名称。**A0 完成前不得实施 A1–A6**。本次只批准规划文档，未批准 A1/A2 的实际 DB/Service/NodePort mutation。

## 6. 强制验收矩阵（不以 Marquez 上“有点/线”取代事实）

| 想看到的 7 个事实 | 首选采集手段 | 最早可宣称 VERIFIED 的门槛 |
|---|---|---|
| 1. Synthea 真实生产 | 真实 Job/CSV/冻结参数 evidence；后期 Producer adapter | 生成 Run 可核验，**Marquez 实际有 producer 事件**才能宣称 UI 显示其 Run |
| 2. SeaweedFS S3 Raw Landing | immutable Manifest/18 CSV + 真 Spark 读输入 | S3 README/证据只能说明对象真实；Marquez 真 dataset 输入/输出事件需另确认 |
| 3. Airflow 自动发现与调度 | Airflow Provider 的真实 DagRun/Task | 该批确实被实际 scheduled Run 的 discovery task 看见；不能把只读 scan 当 Claim |
| 4. Spark Operator 调度 | K8s SparkApplication CR/UID 与 Airflow KPO 日志/Facet | 能对应提交、Driver、Job 身份；不假定 Agent 代表 CR 生命周期 |
| 5. PySpark 读取/转换/输出 | Spark OpenLineage listener | 真 Run 中见到 S3 输入、Processing Parquet 输出及完整身份 |
| 6. Python Writer 写入 OMOP | Writer audit/PG committed checkpoint；后期明确 Python event | **真正 COMMIT + 独立 PG reconciliation**，不是 Drift 拦截、事务 ROLLBACK 或 Spark 成功 |
| 7. Marquez Run/Job/Dataset/Lineage UI | Marquez API+Web | UI 可查真实 Run，端到端边全部存在且与源数据/业务 Run 一一对应；缺边单列未完成 |

**成功分级**：`LIVE_PASS`（真实成功）、`EXPECTED_BLOCK`（安全拒绝有效）、`ROLLBACK_PASS`（真事务未持久化）、`PENDING`、`COMMIT_VERIFIED`（真 COMMIT + readback）。任何 `EXPECTED_BLOCK` / `ROLLBACK_PASS` 不能转换为 `COMMIT_VERIFIED`。

## 7. 资源、权限、故障及回退

- Airflow/Spark 的观测埋点只增加发事件行为，不承担业务判定；监测增加的时间/CPU/内存/JVM classpath 影响，保留无插件镜像回退路径。Sink 中断时如果导致业务执行失败，停止推广并调整隔离；不能悄悄忽略业务异常。
- `dw-marquez` 独立 ServiceAccount、NetworkPolicy（先确认实际 CNI enforce）、Secret、无权限访问原始数据表或 Synthea LocalPath PVC。Marquez metadata DB 用户不允许访问 OMOP/Claim Schema。
- 优先调度无状态 API/Web 到有余量 worker；worker03 上已有 PG 负载，谨慎处理数据库连接池、磁盘和内存；LocalPath PVC 的 NodeAffinity 不表示 Kubernetes 能自动漂移已有 Stateful Pod。
- 清除镜像/应用默认 demo credentials、敏感变量、示例 seed job；探针测试记录必须与真实生产 namespace 分开，不上传真实 patient level attributes、SQL 原文或私有 endpoint 到公开文档。
- NodePort 30999 先走 **仅 LAN/VPN**，绝不能假定 `http://node-ip:30999` 属于安全的公网只读服务。要最终无需 VPN 展示，则必须另立公网身份认证/安全网关方案，不能视为本轮已批准。
- 回退顺序：移除 30999 暴露（保证后台仍可运行）→ 停止可观测性 emitter → Helm rollback Marquez backend/web → 仅在确认无其他 consumer 时回收其专用 DB/role。**不删除** `omop`、`airflow`、SeaweedFS、synthea-local 或原任务卷。

## 8. 当前下一步（唯一开工点）

**A0：Self-Runner 只读环境/数据库/端口/版本/Chart 预检**，输出精确兼容性清单与 30999 安全可达性判断，并提交独立验收文档。A0 完成后才进入受控 A1（PostgreSQL 独立元数据库）与 A2（`dw-marquez`、Marquez 原生 UI、30999 NodePort）部署。

## 9. 技术参考与历史方案

- [本目录 README](./README.md)；[此前 v2.0 中文静态-first 提案](./PUBLIC-DEMO-ARCHITECTURE-v2.0.zh-CN.md)（**已被路线 A 取代，保留历史，不应作为实施 NEXT**）。
- [S3 READY 最新真实 Closeout](../tasks/SYNTHEA-NEW-ONLY-FIRST-REAL-S3-READY-2026-10-13.zh-CN.md) / [Self-Runner Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236)。
- [Marquez 官方 Deployment/Chart](https://marquezproject.ai/docs/deployment/)、[Marquez GitHub Chart](https://github.com/MarquezProject/marquez/tree/main/chart)、[Marquez README（默认 API 鉴权风险）](https://github.com/MarquezProject/marquez)。
- [Airflow OpenLineage Provider 官方配置](https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/configurations-ref.html)。
- [OpenLineage Spark Listener](https://openlineage.io/docs/guides/spark/)（官方标注指南曾用于较早版本，实际必须锁定兼容版本）。
- [Kubernetes NodePort 默认范围](https://kubernetes.io/docs/reference/networking/ports-and-protocols/)。
