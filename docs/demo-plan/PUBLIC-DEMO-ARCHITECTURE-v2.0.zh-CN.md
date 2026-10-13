# Healthcare Data Platform — Public Demo 架构与实施计划 v2.0（中文）

**日期**：2026-10-13 · **状态**：PROPOSED / documentation-only · **归属**：healthcare-data-platform/docs/demo-plan/  
**来源**：Self-Runner 中英文 Public Demo Plan v1.1（2026-10-11）；本版适配 Main 最新 Producer/Consumer 解耦和真实运行证据。  
**受众**：Emory 等招聘经理、技术面试官及 GitHub 审阅者。**主线 TASK004 IN PROGRESS；TASK005 ON HOLD。**

## 0. 文档权威顺序与并行开发边界

1. 业务状态由 [主仓库 Start Here](../README.md)、[TASK-STATUS](../tasks/TASK-STATUS.md) 和真实 Self-Runner Run 决定，不从早期 NEXT 推断当前进度。
2. 新版独立生产架构参考 [Generator/Consumer v1.0](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)；Writer 安全边界参考 [真 S3/PG Gate](../tasks/OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md)。
3. v2.0 仅规划“观察与展示”；**不是** TASK004 发布授权，不能修改 Generator、Airflow Claim、Spark、OMOP Writer 或 PostgreSQL 身份保护，也不能在演示组件内替代业务状态机。
4. 另一 session 正在实现 NEW_ONLY：不要重复部署或覆盖 PVC、镜像、Manifest、运行状态；每次演示验收绑定 exact Main SHA、Batch ID、Manifest SHA 和证据 Run ID。
5. 2026-10-13 核验时 [PR #89](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/89) 尚 OPEN（NEW_ONLY v2 CSV/Source ID Gate）；其变更不视为已在 Main 验收。后续合并时刷新证据，不改写历史结果。

## 1. 面向招聘审阅的目标

公开无登录静态页面：30–60 秒看清“谁生成数据、谁消费、谁验证、谁入库”；3–5 分钟查看**可信的、具 Run/SHA 证据的** Spark 转换、Airflow 编排、Lineage 图和 OMOP 结果。**不允许匿名用户通过页面调用内部控制面、Job、DAG、数据库或敏感 API。**

核心原则：**真实执行证据 > 漂亮但无来源的线条**。每张图的“已完成边”必须追溯到某次真实运行；待实现边清楚标为 *planned / partial*。可显示已存在的历史 PostgreSQL Person/Visit 统计，但必须附上所属历史批次与时间，不能与 NEW_ONLY 新批次合并宣称成功提交。

## 2. v2.0 真实分层架构

```text
PRODUCER / dw-synthea / worker01 (自主 Job；不受 Airflow 调度)
  synthea-new-only --> LocalPath /data/synthea, Retain PVC
     |                  [replay 参数/CSV/本地源键注册表]
     |--> 18 CSV + versioned contract + checksum + global collision audit [未全完成]
     |--> SeaweedFS S3 health-landing immutable batch/manifest READY [尚未完成]
     |        (未来 EXISTING_ONLY / MIXED: 仅设计，ON HOLD)
     v
S3 IMMUTABLE DATA EXCHANGE (唯一 Producer -> Consumer 数据协议)
     |
CONSUMER / dw-airflow + dw-spark / worker02
  landing_batch_discovery */15 --> PostgreSQL Claim Guard (read-only 运行已验收)
  [manual opt-in historical batch] --> Spark Person + Visit --> Processing Reconcile
  [automatic new-batch claim + full consumer: 尚未完成]
     |
OMOP / worker03 / PostgreSQL
  Source Identity / Existing Target Drift Gate --> ROLLBACK 正例 [待]
   --> transactional fencing / dynamic COMMIT [待] --> DB Reconcile/replay [待]

OBSERVABILITY (旁路、只消费经过允许的元数据；不更改业务执行)
  Airflow OpenLineage emitter --> Marquez private API + dedicated metadata DB
  Spark OpenLineage agent ----> Marquez (actual dataset IO; wiring to validate)
  Producer custom lineage/event bridge [可选，须真实完成 S3 发布才能报告 READY]
      |
SANITIZED EXPORT / explicit evidence allowlist / no private endpoint exposure
      v
PUBLIC STATIC SITE + GitHub README / screenshots / run cards / code links
     [Superset private read-only synthetic views: optional, later]
```

**边界**：Generator 不调用 Airflow；Airflow 不能反向触发 Generator。OpenLineage 不是服务器，是规范与采集生态；Marquez 提供 ingestion API、持久化和 UI。Airflow emitter 只证明实际 Airflow run；Spark agent 只报告实际 Spark I/O。**两者的 Dataset namespace/name/URI、parent/run identity 与 S3→Spark→PG 衔接需实测，不会凭安装自动拼成端到端血缘。** Generator 的 S3 CSV 上传和 PostgreSQL 写入若无法由内置 agent 捕获，使用有准确 run/dataset 身份的自定义事件或明确的展示层“证据链接”，不得伪造自动血缘。

## 3. 当前状态快照（2026-10-13，按验收层级区分）

| 能力 | 判定 | 不可误称 |
| --- | --- | --- |
| worker01 NEW_ONLY 生成 / Retain 5Gi PVC / 18 CSV / 同请求重放 | **PASS**；[Self-Runner 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008)，Person 73 / Encounter 12159 | 全局源键无冲突、S3 READY |
| NEW_ONLY versioned contract / 全局 PG+S3 身份校验 | **IN PROGRESS**（核验时 PR #89 open） | READY、可 COMMIT |
| NEW_ONLY 专用镜像 Digest + immutable S3 READY | **NOT VERIFIED** | 发布成功 |
| S3 Discovery 每15分钟、Claim Guard 已接线 | **PASS（只读决策）**；[Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) | 已自动持久 Claim |
| Airflow 手动历史批 Spark Person/Visit + Processing Reconcile | **PASS**；[Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452) | 新数据自动消费或数据库 COMMIT |
| Writer 真 S3 Parquet→PG drift 安全拒绝 | **PASS（预期负例）**；[Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382) | 正向 PG ROLLBACK 或 COMMIT |
| 完整无冲突新批 PG ROLLBACK → COMMIT → DB 对账 / replay | **PENDING** | TASK004 complete |
| OpenLineage/Marquez/Superset 公共 Demo 部署 | **PROPOSED；尚无实测** | 已上线 |

注意：已冻结历史 OMOP 数据库统计如 Person=136、Visit=9391 来自特定 Writer Gate 只读 Run；只作为带 Run 日期的历史证据，不作为实时指标或当前 NEW_ONLY 提交数。

## 4. 产品展示分两层，不要求等 TASK004 全部完成

**Public static（MVP 必做）**：GitHub Pages 或其他独立静态 HTTPS 托管；单屏架构图展示 Producer、S3、Consumer、OMOP；清晰状态颜色/标签区分 verified、partial、planned；每个真实结果附来源 Run、Git SHA、批次 ID/去标识化标签、验证范围和截图。只呈现经过显式审核的合成数据聚合与伪名化样例；静态 Build 失败不影响生产 ETL。

**Private observability（MVP 的第二步）**：在 `dw-demo` 试验 OpenLineage + Marquez，先真实 Spark `person` 的 input→job→output，再连 Airflow，并按已验证范围截图导出。使用独立 Marquez 数据库/角色；考虑复用现有 PostgreSQL 实例前必须检查容量、连接/迁移与权限，不得改 `omop`/`airflow` schema。Marquez API/UI、Airflow UI、Spark UI、SeaweedFS、PostgreSQL、Kubernetes API 和 Runner **始终不对匿名访客开放**。

**Optional**：待完成真实 OMOP COMMIT 后可研究 Superset 只读合成数据视图；不用它补足缺失 COMMIT 证据。OpenMetadata、Kafka、Kinesis、实时公网 Marquez UI 不在 MVP。

## 5. 推荐实施路线（每阶段一个可运行与可验收闭环）

### D0 — 基线调查与隔离（只读）
使用 Self-Runner 固定主仓库 SHA 采集：可用 CPU/RAM/requests/limits/PVC/StorageClasses、Marquez 网络和独立数据库可行性、Airflow 3.2.2 Provider 兼容性、Spark/Java/Agent 版本。选择**历史已验收** Person Spark 运行作为第一条证据；记录真实 S3 dataset URI、Spark output URI、与 PG 的实际写入分界。验收：兼容性矩阵、资源预算、敏感字段/路径名单、回滚清单；数据库与业务状态不变。

### D1 — 先交付静态演示骨架
建立 `docs/demo-plan/` 中的内容来源和 `demo/`（若后续决定使用）纯静态页面构建管道；仅展示已经真实验收的 run cards，附明确 PARTIAL 状态；从仓库入口添加链接须另起 PR、审查无泄露。通过：构建测试、所有公开链接可访问、无登录访问确认、敏感值扫描、无内部端口暴露。

### D2 — 内部 Marquez 接收与持久化
新建 `dw-demo`（部署环节另行许可），pin 镜像版本；只开放 ClusterIP；独立 DB/Secret，设置最小 requests/limits、探针与恢复方案；发送标记为 synthetic-test 的合法 OpenLineage Run，重启后查询仍存在。通过：API 收到事件、DB 持久、UI 可查、主线 DAG 和业务数据不变。**测试事件不作为真实 ETL 证据**。

### D3 — 真实 Spark 血缘
先对固定已验收的 Person 处理入口安装兼容 Agent；跑受控历史 Processing-only Spark，确认输入真实 SeaweedFS S3 数据集、输出真实 Processing Parquet，并在 Marquez 找到正确的 run/dataset 边。若 S3A 或自定义 adapter 未自动报告，补有真实依据的 custom event。通过：真实 Job、输入、输出三者匹配 Run/Manifest/Processing URI；无 PG mutation。

### D4 — Airflow + Producer 证据接通
对现有 `landing_batch_discovery` 配兼容 Airflow emitter，不改 Claim 的 `CLAIM_ENABLE=NO`；真实 task/run 事件进入 Marquez。将 Producer 的“本地生成已 PASS、S3 READY 尚未完成”单列为证据卡；**仅在独立 READY 真实通过后**再将相应 Producer→S3 边标为 verified。通过：每条 UI 边都能追踪运行证据，Airflow/Spark 如不能自动 stitch 则明确展示两个子图。

### D5 — 安全发布正式 Demo
运行 publish allowlist/checksum、删除内网 IP、Bucket 完整私有地址、token、connection URL、明细患者列、日志环境变量和 Runner 管理链接中的敏感片段；检查生成页面无操作型 API/凭据、外网无痕浏览、CSP/HTTPS；可随时回滚到上一个静态版本。通过：无登录、只能读、截图和状态与对应 Run 一致。可用公开 GitHub 的代码和经过审核的公开 Actions Run 页面链接；不得直接展示敏感 K8s 工件。

### D6 — 后续数据库数据结果展示（条件阶段）
**仅当**另一个 TASK004 session 提供真实 NEW_ONLY S3 READY、无冲突 ROLLBACK 正例、有效 Claim Fencing、COMMIT、独立 DB Reconcile/replay 成功证据，才把 NEW_ONLY→OMOP 标注 VERIFIED。若增加 Superset，只连 demo-only 视图、最小只读 SQL 权限，另行安全评审；TASK005 仍不由 Demo 工作推动。

## 6. 数据身份/血缘契约

- Evidence key：`repo_commit_sha + workflow_run_id + batch_id + manifest_sha256 + entity + processing_run_id`，可缺项时标为 `not_applicable / not_verified`，**禁止猜填**。
- Producer Request ID、Batch ID、Airflow DagRun、SparkApplication Run、OMOP Ledger/Commit 是不同身份，不能凭名称相似映射；S3 manifest SHA 与处理输入绑定。
- 每个展示事件保留 `source_run_url`、`recorded_at`、`verification_level`（`LIVE_PASS`, `EXPECTED_BLOCK`, `PENDING`）、`scope`、`main_sha`、`data_visibility`。
- `EXPECTED_BLOCK` 必须单独渲染：这是 Writer drift gate 的正常安全表现，既不是成功写入，也不是正常 ROLLBACK 正例。
- Contract v1/v2 需要版本标识；当 NEW_ONLY v2 READY 尚未具备兼容 Consumer 时不得宣称自动发现/入库。
- OpenLineage namespace/name 使用固定归一化映射表；事件应报告真实 observed input/output，PostgreSQL 只有成功写入才增加 commit-output 边。

## 7. 安全、可靠性与非目标

公开界面不代理内网 Marquez 或任何执行面 API；不直接暴露 S3；不接纳用户提交 SQL 或触发作业；不能把 Superset 公共 Viewer 的 UI 隐藏当成真实权限控制。仅合成数据也需脱敏主机/IP、内部 URI、账户/Secret、日志、潜在个人字段；对外素材需显式 allowlist。CI/Runner 提权凭据绝不传给网页构建进程；静态资源保持可快速撤销。

Marquez 使用 private PostgreSQL 独立库与角色；若现有 worker03 实例不足以承受元数据负载，评估独立实例而非直接加到 OMOP 数据库。所有版本 pin、Helm rollback、PVC 和资源压力先审计后操作。新 Demo 资源不占用 `synthea-new-only-state`、SeaweedFS 或 OMOP 原有 PVC。**每一开发轮：feature PR → exact SHA → Self-Runner 验证 → evidence → merge Main；相同失败超过 3 次停。**

## 8. 下一轮（本文件合并后才实施）

**建议先 D0：只读运行时容量、兼容性、网络、证据与 Dataset 名称调查**。这是只读闭环，不触碰另一个 session 的 TASK004；随后可优先建设安全静态展示，再安装私有 Marquez。所有数据库或集群部署需另设有界授权及验收，本文仅为架构方案。

## 9. 原始方案与证据

- [Self-Runner 原英文 v1.1](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan.md)
- [Self-Runner 原中文 v1.1](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan-v1.1-zh-CN.md)
- [NEW_ONLY 本地真验收](../tasks/SYNTHEA-NEW-ONLY-LOCAL-GENERATOR-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)
- [OpenLineage](https://openlineage.io/), [Marquez](https://marquezproject.ai/), [Airflow OpenLineage](https://openlineage.io/docs/guides/airflow-quickstart/)
